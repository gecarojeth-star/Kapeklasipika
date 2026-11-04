"""
preprocessing.py
----------------
Data quality checks for the image dataset. Nothing here edits the raw images;
every function only reads them and returns results you can inspect and save.

- `image_color_stats`     : average color and brightness of each image (for EDA charts)
- `find_exact_duplicates` : byte-for-byte identical files (MD5 checksum)
- `find_near_duplicates`  : visually near-identical images across splits
                            (perceptual hash), which would leak test answers
                            into training and inflate the test score
"""

import hashlib

import numpy as np
import pandas as pd
from PIL import Image


# ---------------------------------------------------------------------------
# Color / brightness statistics
# ---------------------------------------------------------------------------
def image_color_stats(df, sample_size=64):
    """
    For each image in `df` (from build_inventory), compute mean R, G, B and brightness.
    Images are shrunk to sample_size x sample_size first, which is plenty for averages
    and much faster.

    Returns a copy of df with columns mean_r, mean_g, mean_b, brightness (0-255).
    """
    stats = []
    for path in df["file_path"]:
        with Image.open(path) as img:
            arr = np.asarray(img.convert("RGB").resize((sample_size, sample_size)), dtype=np.float32)
        r, g, b = arr[..., 0].mean(), arr[..., 1].mean(), arr[..., 2].mean()
        # Standard perceived-brightness weights (ITU-R BT.601)
        stats.append((r, g, b, 0.299 * r + 0.587 * g + 0.114 * b))
    out = df.copy()
    out[["mean_r", "mean_g", "mean_b", "brightness"]] = np.round(stats, 1)
    return out


# ---------------------------------------------------------------------------
# Exact duplicates
# ---------------------------------------------------------------------------
def _md5(path, chunk=1 << 20):
    h = hashlib.md5()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def find_exact_duplicates(df):
    """Return rows whose file contents are identical to at least one other file."""
    out = df.copy()
    out["md5"] = [_md5(p) for p in out["file_path"]]
    dupes = out[out.duplicated("md5", keep=False)].sort_values("md5")
    return dupes[["file_path", "split", "label", "md5"]]


# ---------------------------------------------------------------------------
# Near duplicates (perceptual hashing)
# ---------------------------------------------------------------------------
# A perceptual hash ("pHash") turns an image into a 64-bit fingerprint that stays
# almost the same when the image is resized, recompressed or slightly brightened.
# Two images whose fingerprints differ in only a few of the 64 bits look nearly identical.

_POPCOUNT = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)


def compute_phashes(df):
    """Return an (n, 8) uint8 array: each row is one image's 64-bit pHash."""
    import imagehash

    hashes = []
    for path in df["file_path"]:
        with Image.open(path) as img:
            bits = imagehash.phash(img.convert("RGB")).hash.flatten()  # 64 booleans
        hashes.append(np.packbits(bits))  # -> 8 bytes
    return np.stack(hashes)


def _hamming_matrix(a, b):
    """Number of differing bits between every row of a and every row of b -> (len(a), len(b))."""
    return _POPCOUNT[np.bitwise_xor(a[:, None, :], b[None, :, :])].sum(axis=2, dtype=np.uint16)


def find_near_duplicates(df, max_distance=3, chunk=256):
    """
    Compare images ACROSS splits (train-val, train-test, val-test) and list pairs
    whose pHash differs by <= max_distance bits (0 = identical fingerprint).

    Note: coffee beans on a plain background all look broadly similar, so a loose
    threshold produces false alarms. Always look at a sample of flagged pairs
    before deciding anything (notebook 02 shows them side by side).

    Returns a DataFrame: file_a, split_a, label_a, file_b, split_b, label_b, distance
    """
    df = df.reset_index(drop=True)
    hashes = compute_phashes(df)
    pairs = []
    for split_a, split_b in [("train", "val"), ("train", "test"), ("val", "test")]:
        idx_a = np.flatnonzero(df["split"].values == split_a)
        idx_b = np.flatnonzero(df["split"].values == split_b)
        if len(idx_a) == 0 or len(idx_b) == 0:
            continue
        hb = hashes[idx_b]
        for start in range(0, len(idx_a), chunk):  # chunks keep memory use small
            block = idx_a[start:start + chunk]
            dist = _hamming_matrix(hashes[block], hb)
            for i, j in zip(*np.nonzero(dist <= max_distance)):
                a, b = df.loc[block[i]], df.loc[idx_b[j]]
                pairs.append({
                    "file_a": a.file_path, "split_a": a.split, "label_a": a.label,
                    "file_b": b.file_path, "split_b": b.split, "label_b": b.label,
                    "distance": int(dist[i, j]),
                })
    cols = ["file_a", "split_a", "label_a", "file_b", "split_b", "label_b", "distance"]
    return pd.DataFrame(pairs, columns=cols).sort_values("distance").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Confirming near duplicates with a pixel comparison
# ---------------------------------------------------------------------------
# Notebook 02's first run showed that pHash alone over-flags this dataset: a dark
# bean on a white background gives similar fingerprints even for different beans
# (many flagged pairs even had different labels). So every flagged pair gets a
# second, stricter test: the average pixel difference between the two images.
# A true duplicate (same photo, maybe recompressed) differs by only a few levels
# out of 255; two different beans differ by much more.

def pixel_difference(path_a, path_b, size=64):
    """Mean absolute difference of two grayscale thumbnails, on a 0-255 scale."""
    def load(p):
        with Image.open(p) as img:
            return np.asarray(img.convert("L").resize((size, size)), dtype=np.float32)
    return float(np.abs(load(path_a) - load(path_b)).mean())


def confirm_near_duplicates(near, max_pixel_diff=3.0):
    """Add a pixel_diff column and a confirmed flag (pixel_diff <= max_pixel_diff)."""
    out = near.copy()
    out["pixel_diff"] = [round(pixel_difference(a, b), 2) for a, b in zip(out["file_a"], out["file_b"])]
    out["confirmed"] = out["pixel_diff"] <= max_pixel_diff
    return out.sort_values("pixel_diff").reset_index(drop=True)


def build_exclusions(exact, confirmed_near):
    """
    Decide which files to leave out, without touching the raw data. Rules:
    1. Exact copies inside the dataset: keep the first file of each group in the
       earliest split (train < val < test) and exclude the rest. If the copies
       carry different labels, the label is unreliable, so exclude all of them.
    2. Confirmed near duplicates across splits: exclude the copy in the later split
       (val or test), so evaluation never sees an image the model trained on.
       If the two labels differ, exclude both.
    Returns a DataFrame: relative_path, reason.
    """
    from src.data_loading import relative_key

    order = {"train": 0, "val": 1, "test": 2}
    rows = []

    for _, group in exact.groupby("md5"):
        group = group.assign(o=group["split"].map(order)).sort_values(["o", "file_path"])
        if group["label"].nunique() > 1:
            rows += [(relative_key(p), "exact copy with conflicting labels") for p in group["file_path"]]
        else:
            rows += [(relative_key(p), "exact copy of another file") for p in group["file_path"].iloc[1:]]

    for _, r in confirmed_near[confirmed_near["confirmed"]].iterrows():
        if r.label_a != r.label_b:
            rows += [(relative_key(r.file_a), "duplicate photo with conflicting labels"),
                     (relative_key(r.file_b), "duplicate photo with conflicting labels")]
        else:
            later = r.file_b if order[r.split_b] >= order[r.split_a] else r.file_a
            rows.append((relative_key(later), "duplicate of an image in an earlier split"))

    df = pd.DataFrame(rows, columns=["relative_path", "reason"])
    return df.drop_duplicates("relative_path").sort_values("relative_path").reset_index(drop=True)

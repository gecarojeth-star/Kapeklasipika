"""
data_loading.py
---------------
Two jobs:
1. `build_inventory`  -> a table (pandas DataFrame) with one row per image file,
                          used for exploration and quality checks.
2. `load_split`       -> a TensorFlow dataset that feeds images to the model in batches.

Folder layout expected (the USK-Coffee download, unchanged):
    02_data/raw/usk_coffee/
        train/{defect,longberry,peaberry,premium}/*.jpg
        val/  {...}
        test/ {...}
"""

from pathlib import Path

import pandas as pd
from PIL import Image

CLASS_NAMES = ["defect", "longberry", "peaberry", "premium"]
SPLITS = ["train", "val", "test"]
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}


def build_inventory(raw_dir):
    """
    Walk through every split/class folder and record facts about each image.

    Returns a DataFrame with columns:
        file_path, split, label, width, height, mode, file_size_kb, readable
    `readable` is False for files PIL cannot open (corrupt or not really an image).
    """
    raw_dir = Path(raw_dir)
    rows = []
    for split in SPLITS:
        for label in CLASS_NAMES:
            folder = raw_dir / split / label
            if not folder.exists():
                print(f"WARNING: missing folder {folder}")
                continue
            for path in sorted(folder.iterdir()):
                if path.suffix.lower() not in IMAGE_EXTENSIONS:
                    continue
                row = {
                    "file_path": str(path),
                    "split": split,
                    "label": label,
                    "file_size_kb": round(path.stat().st_size / 1024, 1),
                    "width": None,
                    "height": None,
                    "mode": None,
                    "readable": True,
                }
                try:
                    with Image.open(path) as img:
                        row["width"], row["height"] = img.size
                        row["mode"] = img.mode  # "RGB", "L" (grayscale), "RGBA", ...
                except Exception:
                    row["readable"] = False
                rows.append(row)
    return pd.DataFrame(rows)


def relative_key(path):
    """'.../train/peaberry/img_01.jpg' -> 'train/peaberry/img_01.jpg'.
    Used to match files no matter where the dataset folder lives (Drive or Colab disk)."""
    parts = Path(path).parts
    return "/".join(parts[-3:])


def load_exclusions(cfg):
    """Set of relative keys listed in 02_data/interim/excluded_files.csv (made by notebook 02).
    Returns an empty set if notebook 02 has not been run."""
    path = cfg["paths"]["exclusions"]
    if not Path(path).exists():
        return set()
    return set(pd.read_csv(path)["relative_path"])


def list_files(folder, exclude=None):
    """All image files in folder/<class>/, sorted, minus excluded ones. Returns (paths, labels)."""
    folder, exclude = Path(folder), exclude or set()
    paths, labels = [], []
    for idx, label in enumerate(CLASS_NAMES):
        class_dir = folder / label
        if not class_dir.exists():
            continue
        for f in sorted(class_dir.iterdir()):
            if f.suffix.lower() in IMAGE_EXTENSIONS and relative_key(f) not in exclude:
                paths.append(str(f))
                labels.append(idx)
    return paths, labels


def load_split(folder, img_size=224, batch_size=32, shuffle=False, seed=42, exclude=None, files=None):
    """
    Load one split folder (e.g. .../train) as a tf.data.Dataset of (images, labels).

    - Files listed in `exclude` are skipped. Pass `files=(paths, labels)` to use a
      ready-made file list instead of reading the folder (see clean_split_files).
    - Non-square photos (e.g. your phone pictures) are center-cropped to a square,
      then resized to img_size x img_size, so beans are not stretched.
      The phone app does exactly the same.
    - Pixels stay as 0-255 floats; the model normalizes them itself.
    - Labels are integers 0-3 in CLASS_NAMES order.
    - shuffle=True only for training (new order every epoch). Val/test keep a fixed
      order so predictions line up with ds.file_paths.
    """
    import tensorflow as tf  # imported here so inventory work doesn't need TensorFlow

    paths, labels = files if files is not None else list_files(folder, exclude)

    def read(path, label):
        raw = tf.io.read_file(path)
        img = tf.io.decode_image(raw, channels=3, expand_animations=False)
        img.set_shape([None, None, 3])
        # center-crop to square + resize (same as Keras' crop_to_aspect_ratio)
        img = tf.keras.preprocessing.image.smart_resize(img, (img_size, img_size))
        return tf.cast(img, tf.float32), label

    ds = tf.data.Dataset.from_tensor_slices((paths, labels))
    if shuffle:
        ds = ds.shuffle(len(paths), seed=seed, reshuffle_each_iteration=True)
    ds = ds.map(read, num_parallel_calls=tf.data.AUTOTUNE).batch(batch_size)
    # prefetch lets the next batch load while the current one trains (faster)
    ds = ds.prefetch(tf.data.AUTOTUNE)
    ds.file_paths = paths
    return ds


def _md5(path, chunk=1 << 20):
    import hashlib
    h = hashlib.md5()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def clean_split_files(cfg, verbose=True):
    """
    The cleaned file lists used for every experiment: {split: (paths, labels)}.

    Two layers of cleaning, applied in split order train -> val -> test:
    1. Content check: if a file's bytes (MD5) were already seen, in this split or an
       earlier one, it is skipped. This removes exact copies no matter what the files
       are called, so it works on Drive and on Colab's local copy alike.
    2. Name check: files listed in notebook 02's excluded_files.csv are skipped
       (this covers near duplicates that are not byte-identical).
    """
    exclude = load_exclusions(cfg)
    seen, out = set(), {}
    for split in ("train", "val", "test"):
        paths, labels = list_files(cfg["paths"][split], exclude)
        keep_p, keep_l = [], []
        for path, label in zip(paths, labels):
            digest = _md5(path)
            if digest in seen:
                continue
            seen.add(digest)
            keep_p.append(path)
            keep_l.append(label)
        out[split] = (keep_p, keep_l)
        if verbose:
            counts = {c: keep_l.count(i) for i, c in enumerate(CLASS_NAMES)}
            print(f"{split:5s}: {len(keep_p):,} images {counts}")
    return out


def load_clean_split(cfg, split, shuffle=False, files=None):
    """One cleaned split as a tf.data.Dataset (see clean_split_files)."""
    paths, labels = (files or clean_split_files(cfg, verbose=False))[split]
    return load_split(None, cfg["img_size"], cfg["batch_size"], shuffle=shuffle,
                      seed=cfg["seed"], files=(paths, labels))


def load_all_splits(cfg):
    """(train_ds, val_ds, test_ds), cleaned, using config.yaml settings."""
    files = clean_split_files(cfg)
    return tuple(load_clean_split(cfg, s, shuffle=(s == "train"), files=files)
                 for s in ("train", "val", "test"))

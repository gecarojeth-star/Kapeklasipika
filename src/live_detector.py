"""
live_detector.py
----------------
Reference implementation (Python) of the live scanner's bean finder, tracker and camera
guidance. The phone app runs the SAME steps in Dart (07_deployment/mobile_app/lib/live/);
this file exists so the logic can be tested, explained in the paper, and re-used on photos.

Stage 1 - find beans (classical image processing, no training needed):
  1. Work on the brightness channel only (the camera's Y plane), shrunk to ~160 px wide.
  2. Otsu's method picks the brightness that best separates dark objects from the light
     background (it maximizes the difference between the two groups).
  3. Dark pixels -> a mask; a morphological "close" fills small gaps (e.g. the bright crease
     of a bean), then an "open" removes specks of dust.
  4. Connected-component labelling turns the mask into separate blobs.
  5. Each blob gets shape measurements: area, center, bounding box, elongation (long axis /
     short axis of the best-fit ellipse) and ellipse fill (how ellipse-like it is).
Stage 2 - track: blobs are matched to the previous frame's beans by nearest center, so each
  bean keeps an ID (#1, #2, ...) while the camera moves. Each bean's label is the average of
  its last classifications (voting), which stops labels from flickering.
Stage 3 - guide the user: too dark, background not light, too far (beans too small for the
  classifier to see detail), too close / cut off, beans touching.
"""

from dataclasses import dataclass, field

import numpy as np

# ---------------------------------------------------------------------------
# Tunable settings (same names and values as lib/live/detector.dart)
# ---------------------------------------------------------------------------
SMALL_WIDTH = 160            # analysis width in pixels
MIN_BLOB_AREA = 10           # in small-image pixels; smaller = dust
MAX_BLOB_FRACTION = 0.25     # a blob covering >25% of the frame is too close (or a hand)
MIN_BG_BRIGHTNESS = 90       # frame darker than this -> "too dark"
LIGHT_BG_BRIGHTNESS = 170    # a proper light tray/paper is brighter than this
MIN_CONTRAST = 25            # background minus object brightness
MAX_ELONGATION = 3.0         # longer than 3:1 -> not bean-shaped
MIN_ELLIPSE_FILL = 0.55      # less ellipse-like than this -> irregular object
MERGED_AREA_RATIO = 1.7      # blob > 1.7x the median bean area -> probably touching beans
MERGED_ELONGATION = 2.2      # ...or long AND clearly bigger than one bean (a longberry alone
MERGED_ELONG_AREA = 1.5      #    is long but about one bean in area, so it isn't flagged)
MIN_BEAN_PX = 36             # bean's long side in full-res pixels; smaller -> "move closer"
CROP_SCALE = 2.0             # crop side = 2x bean long side (dataset beans fill ~half the frame)


@dataclass
class Blob:
    cx: float; cy: float           # center, full-resolution pixels
    w: float; h: float             # bounding box size, full-resolution pixels
    x0: float; y0: float           # bounding box top-left, full-resolution pixels
    area: float                    # full-resolution pixels
    elongation: float
    ellipse_fill: float
    touches_edge: bool
    shape_ok: bool = True
    merged: bool = False

    @property
    def long_side(self):
        return max(self.w, self.h)


@dataclass
class FrameResult:
    blobs: list
    median_brightness: float     # whole frame
    contrast: float              # background minus objects
    dark_fraction: float         # share of the frame darker than the threshold
    threshold: int


def downsample(y_plane, width, height, row_stride, step):
    """Average 2x2 pixels at every `step` pixels -> small grayscale image (float32)."""
    y = np.frombuffer(y_plane, np.uint8)[: row_stride * height].reshape(height, row_stride)[:, :width]
    sh, sw = height // step, width // step
    ys = (np.arange(sh) * step)[:, None]
    xs = (np.arange(sw) * step)[None, :]
    y1 = np.minimum(ys + 1, height - 1); x1 = np.minimum(xs + 1, width - 1)
    return (y[ys, xs].astype(np.float32) + y[ys, x1] + y[y1, xs] + y[y1, x1]) / 4


def otsu(small):
    hist = np.bincount(small.astype(np.uint8).ravel(), minlength=256).astype(np.float64)
    total = hist.sum(); sum_all = (np.arange(256) * hist).sum()
    w_b = sum_b = 0.0; best_t, best_var = 0, -1.0
    for t in range(256):
        w_b += hist[t]
        if w_b == 0: continue
        w_f = total - w_b
        if w_f == 0: break
        sum_b += t * hist[t]
        m_b = sum_b / w_b; m_f = (sum_all - sum_b) / w_f
        var = w_b * w_f * (m_b - m_f) ** 2
        if var > best_var: best_var, best_t = var, t
    return best_t


def _dilate(m):
    o = m.copy()
    o[1:, :] |= m[:-1, :]; o[:-1, :] |= m[1:, :]; o[:, 1:] |= m[:, :-1]; o[:, :-1] |= m[:, 1:]
    return o


def _erode(m):
    o = m.copy()
    o[1:, :] &= m[:-1, :]; o[:-1, :] &= m[1:, :]; o[:, 1:] &= m[:, :-1]; o[:, :-1] &= m[:, 1:]
    o[0, :] = o[-1, :] = False; o[:, 0] = o[:, -1] = False
    return o


def find_beans(y_plane, width, height, row_stride):
    """Stage 1 on one camera frame (Y plane). Returns FrameResult (full-res coordinates)."""
    step = max(1, width // SMALL_WIDTH)
    small = downsample(y_plane, width, height, row_stride, step)
    sh, sw = small.shape
    t = otsu(small)
    dark = small < t
    bg = small[~dark]; fg = small[dark]
    bg_b = float(bg.mean()) if bg.size else 0.0
    contrast = bg_b - (float(fg.mean()) if fg.size else bg_b)
    median_b = float(np.median(small))
    dark_frac = float(dark.mean())
    # No clear objects, too dark, or the "objects" are most of the frame (dark background)
    if contrast < MIN_CONTRAST or median_b < MIN_BG_BRIGHTNESS or dark_frac > 0.5:
        return FrameResult([], median_b, contrast, dark_frac, t)

    mask = _erode(_dilate(dark))          # close: fill small gaps
    mask = _dilate(_erode(mask))          # open: remove specks

    labels = np.zeros(mask.shape, np.int32); blobs = []; next_label = 0
    for sy in range(sh):
        for sx in range(sw):
            if not mask[sy, sx] or labels[sy, sx]: continue
            next_label += 1
            stack = [(sy, sx)]; labels[sy, sx] = next_label
            n = sx_sum = sy_sum = sxx = syy = sxy = 0.0
            minx, maxx, miny, maxy = sx, sx, sy, sy
            while stack:
                py, px = stack.pop()
                n += 1; sx_sum += px; sy_sum += py; sxx += px * px; syy += py * py; sxy += px * py
                minx = min(minx, px); maxx = max(maxx, px); miny = min(miny, py); maxy = max(maxy, py)
                for qy, qx in ((py - 1, px), (py + 1, px), (py, px - 1), (py, px + 1)):
                    if 0 <= qy < sh and 0 <= qx < sw and mask[qy, qx] and not labels[qy, qx]:
                        labels[qy, qx] = next_label; stack.append((qy, qx))
            if n < MIN_BLOB_AREA: continue
            mx, my = sx_sum / n, sy_sum / n
            cxx = sxx / n - mx * mx; cyy = syy / n - my * my; cxy = sxy / n - mx * my
            tr, det = cxx + cyy, cxx * cyy - cxy * cxy
            disc = max(tr * tr / 4 - det, 0.0) ** 0.5
            l1, l2 = tr / 2 + disc, max(tr / 2 - disc, 1e-6)
            elong = (l1 / l2) ** 0.5
            fill = n / (4 * np.pi * (l1 * l2) ** 0.5)
            edge = minx == 0 or miny == 0 or maxx == sw - 1 or maxy == sh - 1
            blobs.append(Blob(
                cx=(mx + 0.5) * step, cy=(my + 0.5) * step,
                w=(maxx - minx + 1) * step, h=(maxy - miny + 1) * step,
                x0=minx * step, y0=miny * step, area=n * step * step,
                elongation=elong, ellipse_fill=fill, touches_edge=edge))

    if len(blobs) >= 3:
        med = float(np.median([b.area for b in blobs]))
        for b in blobs:
            b.merged = (b.area > MERGED_AREA_RATIO * med
                        or (b.elongation > MERGED_ELONGATION and b.area > MERGED_ELONG_AREA * med))
    for b in blobs:
        b.shape_ok = b.merged or (b.elongation <= MAX_ELONGATION and b.ellipse_fill >= MIN_ELLIPSE_FILL)
    return FrameResult(blobs, median_b, contrast, dark_frac, t)


def guidance(result, width, height):
    """Stage 3: one message for the user, most important first."""
    if result.median_brightness < MIN_BG_BRIGHTNESS:
        return "too_dark"
    if result.dark_fraction > 0.5 and result.contrast >= MIN_CONTRAST:
        return "need_light_background"
    if not result.blobs:
        # Nothing found: on a bright frame there are simply no beans in view; on a dull
        # grey/brown surface the beans don't stand out, so ask for a lighter background.
        return "no_beans" if result.median_brightness >= LIGHT_BG_BRIGHTNESS else "need_light_background"
    if any(b.area > MAX_BLOB_FRACTION * width * height for b in result.blobs):
        return "too_close"
    beans = [b for b in result.blobs if not b.merged]
    if beans and sum(b.touches_edge for b in beans) / len(beans) > 0.3:
        return "move_back"
    if beans and np.median([b.long_side for b in beans]) < MIN_BEAN_PX:
        return "move_closer"
    if any(b.merged for b in result.blobs):
        return "spread_beans"
    return "good"


# ---------------------------------------------------------------------------
# Stage 2: tracking with IDs and label voting
# ---------------------------------------------------------------------------
@dataclass
class Track:
    id: int
    blob: Blob
    hits: int = 1
    missed: int = 0
    prob_sum: np.ndarray = field(default_factory=lambda: np.zeros(4))
    ood_sum: float = 0.0
    votes: int = 0

    @property
    def confirmed(self):
        return self.hits >= 3

    def label(self):
        return int(self.prob_sum.argmax()) if self.votes else None

    def is_bean(self):
        if not self.blob.shape_ok:
            return False
        return self.votes == 0 or self.ood_sum / self.votes <= 1.0


class Tracker:
    MAX_MISSED = 6       # frames a bean may disappear before its ID is dropped
    MATCH_RADIUS = 0.7   # match if centers are closer than 0.7 x bean size
    MAX_VOTES = 8        # stop re-classifying a bean after 8 votes
    PER_FRAME = 2        # classify at most 2 beans per frame (keeps the app smooth)
    SMOOTH = 0.5         # box smoothing (0 = jumpy, 1 = frozen)

    def __init__(self):
        self.tracks, self.next_id = [], 1

    def update(self, blobs):
        pairs = []
        for ti, t in enumerate(self.tracks):
            for bi, b in enumerate(blobs):
                d = ((t.blob.cx - b.cx) ** 2 + (t.blob.cy - b.cy) ** 2) ** 0.5
                if d < self.MATCH_RADIUS * max(t.blob.long_side, b.long_side):
                    pairs.append((d, ti, bi))
        used_t, used_b = set(), set()
        for d, ti, bi in sorted(pairs):
            if ti in used_t or bi in used_b: continue
            used_t.add(ti); used_b.add(bi)
            t, b = self.tracks[ti], blobs[bi]
            s = self.SMOOTH
            b.cx, b.cy = s * t.blob.cx + (1 - s) * b.cx, s * t.blob.cy + (1 - s) * b.cy
            t.blob, t.hits, t.missed = b, t.hits + 1, 0
        for ti, t in enumerate(self.tracks):
            if ti not in used_t: t.missed += 1
        self.tracks = [t for t in self.tracks if t.missed <= self.MAX_MISSED]
        for bi, b in enumerate(blobs):
            if bi not in used_b:
                self.tracks.append(Track(self.next_id, b)); self.next_id += 1

    def to_classify(self):
        cands = [t for t in self.tracks if t.confirmed and t.missed == 0 and t.blob.shape_ok
                 and not t.blob.merged and t.votes < self.MAX_VOTES]
        return sorted(cands, key=lambda t: t.votes)[: self.PER_FRAME]

    def add_vote(self, track, probs, anomaly_ratio):
        track.prob_sum += probs; track.ood_sum += anomaly_ratio; track.votes += 1

    def visible(self):
        return [t for t in self.tracks if t.confirmed and t.missed == 0]


def crop_box(blob, width, height):
    """Square crop around a bean, like the dataset's framing. Returns (x0, y0, side)."""
    side = CROP_SCALE * blob.long_side
    return blob.cx - side / 2, blob.cy - side / 2, side

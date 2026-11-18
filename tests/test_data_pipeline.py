"""
Quick automatic checks of the data code in src/. They build a tiny fake dataset in a temporary
folder, so they need neither the real images nor TensorFlow, and finish in seconds.

Run from the project folder:   python -m pytest tests -q
"""
import numpy as np
import pandas as pd
import pytest
from PIL import Image

from src.data_loading import (CLASS_NAMES, build_inventory, clean_split_files,
                              list_files, relative_key)
from src.evaluate import PAPER_BENCHMARK_ACC, metrics_report
from src.preprocessing import build_exclusions


def _save(path, color, size=32):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (size, size), color).save(path)


@pytest.fixture
def fake_dataset(tmp_path):
    """3 splits x 4 classes x 2 images, plus one corrupt file and one copied image."""
    root = tmp_path / "usk_coffee"
    for s, split in enumerate(["train", "val", "test"]):
        for c, label in enumerate(CLASS_NAMES):
            for i in range(2):
                _save(root / split / label / f"img_{i}.jpg", (40 * c + i, 20 * s, 10 * i))
    (root / "train" / "defect" / "broken.jpg").write_bytes(b"not an image")
    # an exact copy of a training image hiding in the test split (leakage)
    (root / "test" / "defect" / "copy.jpg").write_bytes(
        (root / "train" / "defect" / "img_0.jpg").read_bytes())
    return root


def _cfg(root, tmp_path):
    return {"paths": {"train": root / "train", "val": root / "val", "test": root / "test",
                      "exclusions": tmp_path / "no_exclusions_yet.csv"}}


def test_relative_key_ignores_where_the_dataset_lives():
    assert relative_key("/content/drive/x/train/peaberry/a.jpg") == "train/peaberry/a.jpg"
    assert relative_key("/content/usk_coffee/train/peaberry/a.jpg") == "train/peaberry/a.jpg"


def test_inventory_counts_files_and_flags_unreadable(fake_dataset):
    inv = build_inventory(fake_dataset)
    assert len(inv) == 3 * 4 * 2 + 2           # 24 normal + corrupt + copy
    assert (~inv["readable"]).sum() == 1
    assert set(inv["label"]) == set(CLASS_NAMES)


def test_list_files_skips_excluded_and_uses_class_order(fake_dataset):
    paths, labels = list_files(fake_dataset / "val", exclude={"val/defect/img_0.jpg"})
    assert len(paths) == 7
    assert labels == sorted(labels)             # folders read in CLASS_NAMES order
    assert not any(p.endswith("val/defect/img_0.jpg") for p in paths)


def test_clean_split_files_removes_copy_from_later_split(fake_dataset, tmp_path):
    (fake_dataset / "train" / "defect" / "broken.jpg").unlink()
    files = clean_split_files(_cfg(fake_dataset, tmp_path), verbose=False)
    assert len(files["train"][0]) == 8
    assert not any(p.endswith("copy.jpg") for p in files["test"][0])


def test_exclusion_rules():
    exact = pd.DataFrame({
        "file_path": ["/d/train/defect/a.jpg", "/d/test/defect/a2.jpg",      # same label
                      "/d/train/premium/b.jpg", "/d/val/peaberry/b2.jpg"],   # conflicting labels
        "split": ["train", "test", "train", "val"],
        "label": ["defect", "defect", "premium", "peaberry"],
        "md5": ["m1", "m1", "m2", "m2"]})
    near = pd.DataFrame({
        "file_a": ["/d/train/longberry/c.jpg"], "file_b": ["/d/test/longberry/c2.jpg"],
        "split_a": ["train"], "split_b": ["test"],
        "label_a": ["longberry"], "label_b": ["longberry"], "confirmed": [True]})
    excluded = set(build_exclusions(exact, near)["relative_path"])
    assert "test/defect/a2.jpg" in excluded and "train/defect/a.jpg" not in excluded
    assert {"train/premium/b.jpg", "val/peaberry/b2.jpg"} <= excluded
    assert "test/longberry/c2.jpg" in excluded and "train/longberry/c.jpg" not in excluded


def test_metrics_report_on_known_predictions():
    y_true = np.array([0, 0, 1, 1, 2, 2, 3, 3])
    y_pred = np.array([0, 1, 1, 1, 2, 2, 3, 3])   # one Defect bean missed
    rep = metrics_report(y_true, y_pred)
    assert rep["accuracy"] == 0.875
    assert rep["per_class"]["defect"]["recall"] == 0.5
    assert rep["beats_paper_benchmark"] == (0.875 > PAPER_BENCHMARK_ACC)


def test_config_matches_code():
    from src.config import load_config
    cfg = load_config()
    assert cfg["classes"] == CLASS_NAMES        # model output order = labels.txt order
    assert cfg["img_size"] == 224

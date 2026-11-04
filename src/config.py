"""
config.py
---------
Loads config/config.yaml so every notebook and script uses the same settings
(image size, batch size, class names, folder paths, random seed).

Usage:
    from src.config import load_config
    cfg = load_config()
    cfg["img_size"]          -> 224
    cfg["paths"]["train"]    -> absolute Path to the training images
"""

from pathlib import Path

import yaml

# The project root is the folder that contains src/ (one level up from this file).
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_config(path=None):
    """Read the YAML config and turn every entry under `paths` into an absolute Path."""
    path = Path(path) if path else PROJECT_ROOT / "config" / "config.yaml"
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    cfg["paths"] = {name: PROJECT_ROOT / rel for name, rel in cfg["paths"].items()}
    return cfg


def use_local_copy(cfg, local_root="/content/usk_coffee"):
    """
    Google Colab only: reading 8,000 small images straight from Google Drive is slow.
    This copies the raw dataset to Colab's own fast disk once per session and points
    cfg's train/val/test paths at the copy. The original on Drive is never touched.
    """
    import shutil

    local_root = Path(local_root)
    if not local_root.exists():
        print("Copying dataset from Drive to the Colab disk (one time per session)...")
        shutil.copytree(cfg["paths"]["raw"], local_root)
    for split in ("train", "val", "test"):
        cfg["paths"][split] = local_root / split
    return cfg

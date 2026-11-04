"""
evaluate.py
-----------
Turns model predictions into the numbers and charts for the paper.

Key metrics (plain language):
- Accuracy  : share of all test images classified correctly.
- Precision : of the beans the model called X, how many really were X.
- Recall    : of the beans that really were X, how many the model caught.
- F1-score  : one number balancing precision and recall.
- Macro avg : the simple average over the 4 classes (each class counts equally).
- Confusion matrix: a table of true class (rows) vs predicted class (columns);
  everything off the diagonal is a mistake, and it shows WHICH classes get mixed up.
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from src.data_loading import CLASS_NAMES

PAPER_BENCHMARK_ACC = 0.8131  # Febriana et al. (2022), ResNet-18 test accuracy on USK-Coffee


def predict(model, ds):
    """Run the model over a dataset. Returns (y_true, y_pred, probabilities)."""
    y_true, probs = [], []
    for images, labels in ds:
        probs.append(model(images, training=False).numpy())
        y_true.append(labels.numpy())
    probs = np.concatenate(probs)
    return np.concatenate(y_true), probs.argmax(axis=1), probs


def metrics_report(y_true, y_pred, model_name="model"):
    """Accuracy, per-class precision/recall/F1 and macro averages as a dict."""
    report = classification_report(
        y_true, y_pred, labels=range(len(CLASS_NAMES)), target_names=CLASS_NAMES,
        output_dict=True, zero_division=0,
    )
    return {
        "model": model_name,
        "accuracy": round(accuracy_score(y_true, y_pred), 4),
        "macro_precision": round(report["macro avg"]["precision"], 4),
        "macro_recall": round(report["macro avg"]["recall"], 4),
        "macro_f1": round(report["macro avg"]["f1-score"], 4),
        "per_class": {
            c: {k: round(report[c][k], 4) for k in ("precision", "recall", "f1-score", "support")}
            for c in CLASS_NAMES
        },
        "beats_paper_benchmark": bool(accuracy_score(y_true, y_pred) > PAPER_BENCHMARK_ACC),
    }


def per_class_table(report):
    """The per-class part of metrics_report as a tidy DataFrame (good for the paper)."""
    df = pd.DataFrame(report["per_class"]).T
    df["support"] = df["support"].astype(int)
    return df


def save_report(report, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


def plot_confusion_matrix(y_true, y_pred, title, save_path=None, normalize=False):
    """Heatmap of the confusion matrix. normalize=True shows row percentages (= recall)."""
    cm = confusion_matrix(y_true, y_pred, labels=range(len(CLASS_NAMES)))
    data, fmt = cm, "d"
    if normalize:
        data, fmt = cm / cm.sum(axis=1, keepdims=True).clip(min=1), ".0%"
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    sns.heatmap(data, annot=True, fmt=fmt, cmap="Blues", cbar=False,
                xticklabels=CLASS_NAMES, yticklabels=CLASS_NAMES, ax=ax)
    ax.set_xlabel("Predicted class")
    ax.set_ylabel("True class")
    ax.set_title(title)
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=200)
    return fig


def plot_history(history_csv, title, save_path=None):
    """Training vs validation accuracy and loss per epoch, from a CSVLogger file."""
    h = pd.read_csv(history_csv).reset_index(drop=True)
    h["epoch_n"] = np.arange(1, len(h) + 1)  # continuous count across stages
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    for ax, metric in zip(axes, ["accuracy", "loss"]):
        ax.plot(h["epoch_n"], h[metric], label="train")
        ax.plot(h["epoch_n"], h[f"val_{metric}"], label="validation")
        ax.set_xlabel("Epoch")
        ax.set_ylabel(metric.capitalize())
        ax.grid(alpha=0.3)
        ax.legend()
    fig.suptitle(title)
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=200)
    return fig


def misclassified(y_true, y_pred, probs, file_paths):
    """Table of wrong predictions, most confident mistakes first."""
    wrong = np.flatnonzero(y_true != y_pred)
    df = pd.DataFrame({
        "file_path": np.asarray(file_paths)[wrong],
        "true": [CLASS_NAMES[i] for i in y_true[wrong]],
        "predicted": [CLASS_NAMES[i] for i in y_pred[wrong]],
        "confidence": probs[wrong].max(axis=1).round(3),
    })
    return df.sort_values("confidence", ascending=False).reset_index(drop=True)


def show_image_grid(file_paths, titles, ncols=6, save_path=None):
    """Small helper to display images in a grid with a title under each."""
    from PIL import Image

    n = len(file_paths)
    nrows = max(1, int(np.ceil(n / ncols)))
    fig, axes = plt.subplots(nrows, ncols, figsize=(2.2 * ncols, 2.4 * nrows))
    for ax in np.ravel(axes):
        ax.axis("off")
    for ax, path, title in zip(np.ravel(axes), file_paths, titles):
        with Image.open(path) as img:
            ax.imshow(img.convert("RGB"))
        ax.set_title(title, fontsize=8)
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=200)
    return fig

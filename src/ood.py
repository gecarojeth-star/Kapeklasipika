"""
ood.py
------
"Is this even a coffee bean?"  (out-of-distribution / anomaly detection)

Why it's needed: a classifier always answers one of its classes. In app testing a coin
was labeled Defect at 100% confidence, so the confidence score alone can't flag objects
the model has never seen.

Method (Mahalanobis distance on deep features, Lee et al., 2018):
1. Take the 1,280 numbers MobileNetV2 produces for each image just before the final
   layer (its "features": a learned description of the image).
2. Compress them to 64 numbers with PCA (keeps the main directions of variation,
   drops noise, and makes the math small enough for a phone).
3. Describe each bean class by the average of its training features (class center) and
   how features spread around those centers (shared covariance).
4. For a new image, the anomaly score = squared Mahalanobis distance to the NEAREST class
   center: how many "standard deviations" away it is from every kind of bean we know.
5. Threshold: the score below which 97.5% of real validation beans fall. Anything above
   is reported as "not a coffee bean (or unclear photo)".

The scoring is built into the phone model itself as an extra output, so the app only
compares one number with 1.0 (score / threshold).
"""

import numpy as np
import tensorflow as tf


# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------
def build_feature_model(model, feature_layer="avg_pool"):
    """
    Rebuild the trained model WITHOUT augmentation and with two outputs:
    (class probabilities, 1,280-d features from `feature_layer`).
    Reuses the same trained layers (no retraining).
    """
    inputs = tf.keras.Input(model.input_shape[1:], name="image")
    x, features = inputs, None
    for layer in model.layers[1:]:          # layers[0] is the Input layer
        if layer.name == "augmentation":
            continue
        x = layer(x)
        if layer.name == feature_layer:
            features = x
    if features is None:
        raise ValueError(f"Layer '{feature_layer}' not found")
    return tf.keras.Model(inputs, [x, features], name="classifier_with_features")


def extract(feature_model, ds):
    """Run over a dataset -> (features [n,1280], probabilities [n,4], labels [n])."""
    feats, probs, labels = [], [], []
    for images, y in ds:
        p, f = feature_model(images, training=False)
        feats.append(f.numpy()); probs.append(p.numpy()); labels.append(np.asarray(y))
    return np.concatenate(feats), np.concatenate(probs), np.concatenate(labels)


# ---------------------------------------------------------------------------
# Fitting the detector
# ---------------------------------------------------------------------------
class MahalanobisDetector:
    """PCA + class-conditional Gaussians with a shared covariance."""

    def __init__(self, n_components=64, ridge=1e-3):
        self.n_components = n_components
        self.ridge = ridge  # small value added to the covariance so it can be inverted

    def fit(self, features, labels, n_classes=4):
        from sklearn.decomposition import PCA

        self.pca = PCA(n_components=self.n_components, random_state=42).fit(features)
        z = self.pca.transform(features)
        self.class_means = np.stack([z[labels == c].mean(0) for c in range(n_classes)])
        resid = z - self.class_means[labels]
        cov = np.cov(resid, rowvar=False) + self.ridge * np.eye(self.n_components)
        self.inv_cov = np.linalg.inv(cov)
        # Whitening matrix A with A^T A = inv_cov, so distance = ||A z - A mu||^2
        self.whiten = np.linalg.cholesky(self.inv_cov).T
        return self

    def score(self, features):
        """Squared Mahalanobis distance to the nearest class center (higher = stranger)."""
        z = self.pca.transform(features)
        y = z @ self.whiten.T
        m = self.class_means @ self.whiten.T
        d = ((y[:, None, :] - m[None, :, :]) ** 2).sum(-1)
        return d.min(1)

    def set_threshold(self, val_features, keep=0.975):
        """Threshold that keeps `keep` of real (validation) beans."""
        self.threshold = float(np.quantile(self.score(val_features), keep))
        return self.threshold

    # Everything the phone needs, folded into one linear layer + 4 points
    def phone_params(self):
        # y = A (W (f - mean))  ->  y = f @ K + b
        W = self.pca.components_                       # [64, 1280]
        K = W.T @ self.whiten.T                        # [1280, 64]
        b = -self.pca.mean_ @ K                        # [64]
        M = self.class_means @ self.whiten.T           # [4, 64]
        return K.astype("float32"), b.astype("float32"), M.astype("float32")


# ---------------------------------------------------------------------------
# Phone model with the anomaly score built in
# ---------------------------------------------------------------------------
class AnomalyScore(tf.keras.layers.Layer):
    """features -> (squared Mahalanobis distance to nearest class) / threshold."""

    def __init__(self, K, b, M, threshold, **kwargs):
        super().__init__(**kwargs)
        self.K = tf.constant(K)
        self.b = tf.constant(b)
        self.M = tf.constant(M)
        self.threshold = float(threshold)

    def call(self, f):
        y = tf.matmul(f, self.K) + self.b                       # [n, 64]
        d = tf.reduce_sum(tf.square(y[:, None, :] - self.M[None, :, :]), axis=-1)  # [n, 4]
        return tf.reduce_min(d, axis=-1, keepdims=True) / self.threshold           # [n, 1]


def build_phone_model(feature_model, detector):
    """Inputs: raw 0-255 image. Outputs: probabilities [n,4] and anomaly ratio [n,1]
    (ratio > 1.0 means 'not a coffee bean / unclear')."""
    K, b, M = detector.phone_params()
    probs, feats = feature_model.outputs
    ratio = AnomalyScore(K, b, M, detector.threshold, name="anomaly_ratio")(feats)
    return tf.keras.Model(feature_model.inputs, [probs, ratio], name="kapeklasipika_phone")


def to_tflite_two_outputs(phone_model, out_path, check_images, max_rel_error=0.05):
    """
    Convert to TFLite, trying float16 weights first (half the size).
    float16 keeps only ~3 significant digits, which is fine for the classifier but can
    distort the anomaly score. So the converted model is checked on `check_images`: if the
    anomaly ratio or the predicted class drifts from the Keras model, it falls back to
    full float32 precision (about twice the size, still well under 15 MB).
    Returns (size_mb, precision_used, max_relative_error).
    """
    from pathlib import Path

    k_probs, k_ratio = phone_model(check_images, training=False)
    k_probs, k_ratio = k_probs.numpy(), k_ratio.numpy().ravel()

    for precision in ("float16", "float32"):
        converter = tf.lite.TFLiteConverter.from_keras_model(phone_model)
        if precision == "float16":
            converter.optimizations = [tf.lite.Optimize.DEFAULT]
            converter.target_spec.supported_types = [tf.float16]
        Path(out_path).write_bytes(converter.convert())
        t_probs, t_ratio = tflite_run_two_outputs(out_path, check_images)
        rel = np.abs(t_ratio - k_ratio) / np.maximum(np.abs(k_ratio), 1e-6)
        same_class = (t_probs.argmax(1) == k_probs.argmax(1)).mean()
        if rel.max() <= max_rel_error and same_class >= 0.98:
            break
        print(f"{precision}: anomaly ratio off by up to {rel.max():.1%} or classes differ "
              f"({same_class:.0%} agree) -> trying higher precision")
    return round(Path(out_path).stat().st_size / 1e6, 2), precision, float(rel.max())


def tflite_run_two_outputs(tflite_path, images):
    """Run the two-output .tflite on a batch. Returns (probs [n,4], ratio [n])."""
    interp = tf.lite.Interpreter(model_path=str(tflite_path))
    inp = interp.get_input_details()[0]
    outs = interp.get_output_details()
    interp.resize_tensor_input(inp["index"], [1, *images.shape[1:]])
    interp.allocate_tensors()
    outs = interp.get_output_details()
    p_idx = next(o["index"] for o in outs if o["shape"][-1] == 4)
    r_idx = next(o["index"] for o in outs if o["shape"][-1] == 1)
    probs, ratios = [], []
    for img in images:
        interp.set_tensor(inp["index"], img[None].astype(np.float32))
        interp.invoke()
        probs.append(interp.get_tensor(p_idx)[0]); ratios.append(interp.get_tensor(r_idx)[0, 0])
    return np.stack(probs), np.array(ratios)


# ---------------------------------------------------------------------------
# Non-bean test images
# ---------------------------------------------------------------------------
def synthetic_coins(n=300, size=224, seed=0):
    """
    Coin-like discs (silver/gold radial gradient, rim, embossed noise) on a light,
    dataset-like background with a soft shadow. A stand-in for the coin we tested in the
    app, since no photo dataset of coins on white backgrounds is bundled with TensorFlow.
    Returns uint8-range float32 images [n, size, size, 3].
    """
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    out = np.empty((n, size, size, 3), np.float32)
    for i in range(n):
        bg = rng.uniform(205, 240) + rng.normal(0, 2, (size, size))
        img = np.repeat(bg[..., None], 3, -1) * np.array([1.0, 0.99, 0.96])
        r = rng.uniform(0.18, 0.32) * size
        cx, cy = size / 2 + rng.uniform(-25, 25, 2)
        sx, sy = cx + 6, cy + 8                                        # shadow offset
        shadow = np.clip(1 - np.hypot(xx - sx, yy - sy) / (r + 6), 0, 1) ** 0.6
        img *= (1 - 0.25 * shadow[..., None])
        d = np.hypot(xx - cx, yy - cy)
        inside = d <= r
        base = np.array([200, 170, 90]) if rng.random() < 0.5 else np.array([175, 175, 170])
        shade = 0.75 + 0.35 * (1 - d / r) + rng.normal(0, 0.06, (size, size))
        rim = (d > 0.85 * r) & inside
        shade[rim] *= 0.8
        coin = np.clip(base[None, None, :] * shade[..., None], 0, 255)
        img[inside] = coin[inside]
        out[i] = np.clip(img, 0, 255)
    return out


def ood_report(detector, in_scores, ood_sets):
    """AUROC and rejection rate at the threshold for each named set of non-bean scores."""
    from sklearn.metrics import roc_auc_score
    import pandas as pd

    rows = [{"set": "USK-Coffee test beans (should be ACCEPTED)", "n": len(in_scores),
             "flagged_as_not_bean": float((in_scores > detector.threshold).mean()), "auroc": None}]
    for name, s in ood_sets.items():
        y = np.r_[np.zeros(len(in_scores)), np.ones(len(s))]
        rows.append({"set": f"{name} (should be REJECTED)", "n": len(s),
                     "flagged_as_not_bean": float((s > detector.threshold).mean()),
                     "auroc": float(roc_auc_score(y, np.r_[in_scores, s]))})
    return pd.DataFrame(rows)

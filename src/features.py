"""
features.py
-----------
With CNNs we don't hand-craft features (like "bean length" or "roundness"):
the network learns its own features from the pixels. What we *do* control is
data augmentation, which is the image version of feature engineering.

Data augmentation = showing the model randomly altered copies of the training
images (rotated, flipped, brighter, darker, zoomed) so it learns what a bean
class looks like rather than memorizing exact photos. This directly fights the
overfitting seen in the original USK-Coffee paper (98.8% train vs 81.3% test),
and it mimics the variety of real phone photos.

These layers are only active during training; at prediction time they do nothing.
"""

import tensorflow as tf


def build_augmentation(seed=42):
    """Random transformations applied to every training batch."""
    return tf.keras.Sequential(
        [
            # A bean has no "up" in a photo, so any flip or rotation is realistic.
            tf.keras.layers.RandomFlip("horizontal_and_vertical", seed=seed),
            tf.keras.layers.RandomRotation(0.5, fill_mode="nearest", seed=seed),  # up to +/-180 deg
            # Phones are held at different distances.
            tf.keras.layers.RandomZoom((-0.15, 0.15), fill_mode="nearest", seed=seed),
            # Different lighting conditions (values are on the 0-255 scale).
            tf.keras.layers.RandomBrightness(0.2, value_range=(0, 255), seed=seed),
            tf.keras.layers.RandomContrast(0.2, seed=seed),
        ],
        name="augmentation",
    )

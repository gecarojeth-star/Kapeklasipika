"""
models.py
---------
Model builders and training helpers.

1. `build_baseline_cnn`  : a small CNN trained from scratch. It sets the bar:
                           the pretrained model must clearly beat it to justify itself.
2. `build_mobilenetv2`   : transfer learning. MobileNetV2 already learned general
                           visual features (edges, textures, shapes) from 1.4 million
                           ImageNet photos; we reuse those and train only a new
                           4-class "head" on top.
3. `unfreeze_top_layers` : fine-tuning. After the head is trained, we let the top
                           layers of MobileNetV2 adjust slightly to coffee beans,
                           with a very small learning rate.

Both models take raw 0-255 pixels and normalize inside the model, so the phone
app does not need to know any preprocessing formula.
"""

import tensorflow as tf

from src.features import build_augmentation

NUM_CLASSES = 4


def _compile(model, lr):
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=lr),
        loss="sparse_categorical_crossentropy",  # labels are integers 0-3
        metrics=["accuracy"],
    )
    return model


def build_baseline_cnn(img_size=224, lr=1e-3, augment=True, seed=42):
    """Three convolution blocks -> global average pooling -> softmax over 4 classes."""
    inputs = tf.keras.Input((img_size, img_size, 3), name="image")
    x = build_augmentation(seed)(inputs) if augment else inputs
    x = tf.keras.layers.Rescaling(1.0 / 255, name="scale_0_1")(x)
    for filters in (32, 64, 128):
        # Convolution = small filters that slide over the image and detect patterns.
        x = tf.keras.layers.Conv2D(filters, 3, padding="same", activation="relu")(x)
        x = tf.keras.layers.BatchNormalization()(x)
        # Pooling = shrink the image by keeping the strongest signal in each 2x2 area.
        x = tf.keras.layers.MaxPooling2D()(x)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dropout(0.3)(x)  # randomly switch off 30% of units -> less overfitting
    outputs = tf.keras.layers.Dense(NUM_CLASSES, activation="softmax", name="predictions")(x)
    return _compile(tf.keras.Model(inputs, outputs, name="baseline_cnn"), lr)


def build_mobilenetv2(img_size=224, lr=1e-3, augment=True, weights="imagenet", dropout=0.3, seed=42):
    """
    MobileNetV2 (frozen) + new classifier head.
    weights="imagenet" downloads pretrained weights (needs internet, e.g. Colab).
    weights=None gives a randomly initialised network (only for quick code tests).
    Returns (model, base) so the base can be unfrozen later for fine-tuning.
    """
    base = tf.keras.applications.MobileNetV2(
        input_shape=(img_size, img_size, 3), include_top=False, weights=weights
    )
    base.trainable = False  # freeze: keep ImageNet knowledge intact during stage 1

    inputs = tf.keras.Input((img_size, img_size, 3), name="image")
    x = build_augmentation(seed)(inputs) if augment else inputs
    # Same as tf.keras.applications.mobilenet_v2.preprocess_input: 0..255 -> -1..1
    x = tf.keras.layers.Rescaling(1.0 / 127.5, offset=-1.0, name="scale_minus1_1")(x)
    # training=False keeps BatchNorm statistics fixed even when we fine-tune later
    x = base(x, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D(name="avg_pool")(x)
    x = tf.keras.layers.Dropout(dropout, name="dropout")(x)
    outputs = tf.keras.layers.Dense(NUM_CLASSES, activation="softmax", name="predictions")(x)
    model = tf.keras.Model(inputs, outputs, name="mobilenetv2_transfer")
    return _compile(model, lr), base


def unfreeze_top_layers(model, base, n_layers=40, lr=1e-5):
    """
    Fine-tuning: make only the last n_layers of MobileNetV2 trainable.
    BatchNormalization layers stay frozen (standard practice for small datasets).
    The model must be recompiled for the change to take effect.
    """
    base.trainable = True
    for layer in base.layers[:-n_layers]:
        layer.trainable = False
    for layer in base.layers:
        if isinstance(layer, tf.keras.layers.BatchNormalization):
            layer.trainable = False
    return _compile(model, lr)


def make_callbacks(checkpoint_path, log_path, patience=5):
    """
    - EarlyStopping: stop when validation loss stops improving, and roll back
      to the best epoch (prevents training into overfitting).
    - ModelCheckpoint: save the best model to disk as training goes.
    - CSVLogger: write per-epoch loss/accuracy to a CSV for the report.
    """
    return [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=patience, restore_best_weights=True
        ),
        tf.keras.callbacks.ModelCheckpoint(
            str(checkpoint_path), monitor="val_loss", save_best_only=True
        ),
        tf.keras.callbacks.CSVLogger(str(log_path), append=True),
    ]


def count_params(model):
    """Total and trainable parameter counts, for the experiments log."""
    trainable = sum(int(tf.size(w)) for w in model.trainable_weights)
    total = trainable + sum(int(tf.size(w)) for w in model.non_trainable_weights)
    return {"total_params": total, "trainable_params": trainable}

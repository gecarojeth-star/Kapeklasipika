"""
export.py
---------
Converts the trained Keras model into a TensorFlow Lite (.tflite) file for the phone.

TensorFlow Lite = a compact model format made to run on phones, offline.
We also apply float16 quantization: weights are stored in 16-bit instead of
32-bit numbers, roughly halving the file size with almost no accuracy loss.

The exported model:
    input : 1 x 224 x 224 x 3 float32, raw RGB pixels 0-255
    output: 1 x 4 float32 probabilities in CLASS_NAMES order
"""

from pathlib import Path
import tempfile

import numpy as np
import tensorflow as tf

from src.data_loading import CLASS_NAMES


def strip_augmentation(model):
    """
    Rebuild the model without the augmentation block, reusing the same trained layers.
    Augmentation does nothing at prediction time anyway, but removing it keeps the
    phone model small and avoids random-op conversion problems.
    """
    inputs = tf.keras.Input(model.input_shape[1:], name="image")
    x = inputs
    for layer in model.layers[1:]:  # layers[0] is the Input layer
        if layer.name == "augmentation":
            continue
        x = layer(x)
    return tf.keras.Model(inputs, x, name=f"{model.name}_inference")


def to_tflite(model, out_path, float16=True):
    """Convert and save. Returns the file size in MB."""
    model = strip_augmentation(model)
    try:
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        if float16:
            converter.optimizations = [tf.lite.Optimize.DEFAULT]
            converter.target_spec.supported_types = [tf.float16]
        tflite_bytes = converter.convert()
    except Exception as err:  # some TF/Keras versions prefer the SavedModel route
        print(f"Direct conversion failed ({err}); retrying via SavedModel export...")
        with tempfile.TemporaryDirectory() as tmp:
            model.export(tmp)
            converter = tf.lite.TFLiteConverter.from_saved_model(tmp)
            if float16:
                converter.optimizations = [tf.lite.Optimize.DEFAULT]
                converter.target_spec.supported_types = [tf.float16]
            tflite_bytes = converter.convert()

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(tflite_bytes)
    return round(out_path.stat().st_size / 1e6, 2)


def write_labels(out_path):
    """labels.txt: one class name per line, in the model's output order."""
    Path(out_path).write_text("\n".join(CLASS_NAMES) + "\n", encoding="utf-8")


def tflite_predict(tflite_path, images):
    """Run the .tflite model on a batch of images (N, 224, 224, 3), 0-255 floats."""
    interpreter = tf.lite.Interpreter(model_path=str(tflite_path))
    inp = interpreter.get_input_details()[0]
    out = interpreter.get_output_details()[0]
    interpreter.resize_tensor_input(inp["index"], [1, *images.shape[1:]])
    interpreter.allocate_tensors()
    probs = []
    for img in images:
        interpreter.set_tensor(inp["index"], img[None].astype(np.float32))
        interpreter.invoke()
        probs.append(interpreter.get_tensor(out["index"])[0])
    return np.stack(probs)


def check_agreement(keras_model, tflite_path, ds, max_batches=5):
    """
    Sanity check after conversion: the phone model should predict the same class
    as the Keras model on (almost) every image. Returns the share that agree.
    """
    agree, total = 0, 0
    for i, (images, _) in enumerate(ds):
        if i >= max_batches:
            break
        k = keras_model(images, training=False).numpy().argmax(1)
        t = tflite_predict(tflite_path, images.numpy()).argmax(1)
        agree += int((k == t).sum())
        total += len(k)
    return agree / max(total, 1)

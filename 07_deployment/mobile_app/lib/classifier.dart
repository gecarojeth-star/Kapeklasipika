// classifier.dart
// ----------------
// Loads the TensorFlow Lite model and turns a photo into a prediction.
//
// Everything heavy runs OFF the screen-drawing thread, so the app never freezes:
//   1. Photo decoding, cropping and resizing run in a background isolate (Isolate.run).
//   2. The model itself runs in its own isolate (IsolateInterpreter).
//
// The model expects: 1 x 224 x 224 x 3 float32, raw RGB pixel values 0-255.
// (All normalization happens inside the model, so we only crop and resize here.)
// The model returns: 4 probabilities in the order listed in assets/labels.txt.

import 'dart:isolate';
import 'dart:math';
import 'dart:typed_data';

import 'package:flutter/services.dart' show rootBundle;
import 'package:image/image.dart' as img;
import 'package:tflite_flutter/tflite_flutter.dart';

/// One prediction: the winning class plus the probability of every class.
class Prediction {
  final String label;
  final double confidence;
  final Map<String, double> probabilities;
  final Duration elapsed; // time from "photo chosen" to "answer ready"

  /// Anomaly score / threshold from the "is it a bean?" detector (notebook 06).
  /// Above 1.0 = doesn't look like a coffee bean. Null with the older v1 model.
  final double? anomalyRatio;

  const Prediction(this.label, this.confidence, this.probabilities, this.elapsed, {this.anomalyRatio});

  bool get isBean => anomalyRatio == null || anomalyRatio! <= 1.0;

  /// Probabilities sorted from highest to lowest.
  List<MapEntry<String, double>> get ranked =>
      probabilities.entries.toList()..sort((a, b) => b.value.compareTo(a.value));
}

/// "peaberry" -> "Peaberry"
String displayName(String label) =>
    label.isEmpty ? label : label[0].toUpperCase() + label.substring(1);

const int kInputSize = 224;

/// Runs in a background isolate: bytes of a photo -> flat 224*224*3 list of 0-255 values.
/// Must be a top-level function so it can be sent to another isolate.
Float32List preprocessImage(Uint8List bytes) {
  final decoded = img.decodeImage(bytes);
  if (decoded == null) {
    throw const FormatException('Could not read this image.');
  }
  // 0. Safety net for very large photos (e.g. a 50 MP gallery image): shrink first, so the
  //    rotation and crop below never copy a huge image in memory. The picker normally
  //    delivers at most 1024 px already.
  const maxSide = 1600;
  final small = max(decoded.width, decoded.height) > maxSide
      ? (decoded.width >= decoded.height
          ? img.copyResize(decoded, width: maxSide, interpolation: img.Interpolation.linear)
          : img.copyResize(decoded, height: maxSide, interpolation: img.Interpolation.linear))
      : decoded;

  // 1. Respect the phone's rotation tag so the photo is upright.
  final upright = img.bakeOrientation(small);

  // 2. Center-crop to a square (same as training), so the bean isn't stretched.
  final side = min(upright.width, upright.height);
  final square = img.copyCrop(
    upright,
    x: (upright.width - side) ~/ 2,
    y: (upright.height - side) ~/ 2,
    width: side,
    height: side,
  );

  // 3. Resize to 224 x 224 (bilinear, like training).
  final resized = img.copyResize(
    square,
    width: kInputSize,
    height: kInputSize,
    interpolation: img.Interpolation.linear,
  );

  // 4. Flatten to [R, G, B, R, G, B, ...] row by row.
  final out = Float32List(kInputSize * kInputSize * 3);
  var i = 0;
  for (var y = 0; y < kInputSize; y++) {
    for (var x = 0; x < kInputSize; x++) {
      final p = resized.getPixel(x, y);
      out[i++] = p.r.toDouble();
      out[i++] = p.g.toDouble();
      out[i++] = p.b.toDouble();
    }
  }
  return out;
}

/// Top-level wrapper so the background isolate receives only the photo bytes.
Future<Float32List> preprocessInBackground(Uint8List bytes) =>
    Isolate.run(() => preprocessImage(bytes));

class BeanClassifier {
  static const String modelAsset = 'assets/kapeklasipika.tflite';
  static const String labelsAsset = 'assets/labels.txt';

  final Interpreter _interpreter;
  final IsolateInterpreter _isolate;
  final List<String> labels;
  final int _probsIndex; // which model output holds the class probabilities
  final int? _anomalyIndex; // which output holds the anomaly ratio (null for the v1 model)

  BeanClassifier._(this._interpreter, this._isolate, this.labels, this._probsIndex, this._anomalyIndex);

  /// True if the model includes the "is it a bean?" detector.
  bool get hasAnomalyDetector => _anomalyIndex != null;

  /// Load the model and labels from the app's assets (call once at startup).
  static Future<BeanClassifier> load() async {
    final interpreter = await Interpreter.fromAsset(modelAsset);
    final isolate = await IsolateInterpreter.create(address: interpreter.address);
    final rawLabels = await rootBundle.loadString(labelsAsset);
    final labels = rawLabels
        .split('\n')
        .map((l) => l.trim())
        .where((l) => l.isNotEmpty)
        .toList();
    // The v2 model has two outputs: probabilities [1,4] and anomaly ratio [1,1].
    // Their order inside the file isn't guaranteed, so tell them apart by shape.
    var probsIndex = 0;
    int? anomalyIndex;
    final outputs = interpreter.getOutputTensors();
    for (var i = 0; i < outputs.length; i++) {
      if (outputs[i].shape.last == 1) {
        anomalyIndex = i;
      } else {
        probsIndex = i;
      }
    }
    return BeanClassifier._(interpreter, isolate, labels, probsIndex, anomalyIndex);
  }

  /// Classify the bytes of a photo (from the camera or gallery).
  Future<Prediction> classifyBytes(Uint8List bytes) async {
    final watch = Stopwatch()..start();
    final flat = await preprocessInBackground(bytes); // background isolate: decode + crop + resize
    return _run(flat, watch);
  }

  Future<Prediction> _run(Float32List flat, Stopwatch watch) async {
    // Reshape the flat list into [1][224][224][3] for the model.
    final input = [
      List.generate(
        kInputSize,
        (y) => List.generate(kInputSize, (x) {
          final i = (y * kInputSize + x) * 3;
          return [flat[i], flat[i + 1], flat[i + 2]];
        }),
      ),
    ];
    final probsOut = [List<double>.filled(labels.length, 0.0)];
    double? anomaly;

    // Model isolate: run the network.
    if (_anomalyIndex == null) {
      await _isolate.run(input, probsOut);
    } else {
      final anomalyOut = [List<double>.filled(1, 0.0)];
      await _isolate.runForMultipleInputs([input], {_probsIndex: probsOut, _anomalyIndex: anomalyOut});
      anomaly = anomalyOut[0][0];
    }
    watch.stop();

    final probs = probsOut[0];
    var best = 0;
    for (var i = 1; i < probs.length; i++) {
      if (probs[i] > probs[best]) best = i;
    }
    return Prediction(
      labels[best],
      probs[best],
      {for (var i = 0; i < labels.length; i++) labels[i]: probs[i]},
      watch.elapsed,
      anomalyRatio: anomaly,
    );
  }

  Future<void> close() async {
    await _isolate.close();
    _interpreter.close();
  }
}

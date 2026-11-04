// frame.dart
// -----------
// Holds one camera frame (YUV 4:2:0) and cuts out a bean as a 224x224 RGB image
// for the classifier, framed like the dataset photos (bean fills about half the crop).

import 'dart:math';
import 'dart:typed_data';

import 'package:camera/camera.dart';

import 'detector.dart';

class FrameData {
  final int width, height;
  final Uint8List y;
  final int yRowStride;
  final Uint8List uBytes, vBytes;
  final int uOffset, vOffset;
  final int uvRowStride, uvPixelStride;

  const FrameData({
    required this.width,
    required this.height,
    required this.y,
    required this.yRowStride,
    required this.uBytes,
    required this.vBytes,
    required this.uOffset,
    required this.vOffset,
    required this.uvRowStride,
    required this.uvPixelStride,
  });

  /// Works with the 3-plane YUV420 format (requested) and single-plane NV21 (fallback).
  factory FrameData.fromCameraImage(CameraImage img) {
    final p = img.planes;
    if (p.length >= 3) {
      return FrameData(
        width: img.width,
        height: img.height,
        y: p[0].bytes,
        yRowStride: p[0].bytesPerRow,
        uBytes: p[1].bytes,
        vBytes: p[2].bytes,
        uOffset: 0,
        vOffset: 0,
        uvRowStride: p[1].bytesPerRow,
        uvPixelStride: p[1].bytesPerPixel ?? 1,
      );
    }
    // NV21: Y plane followed by interleaved V,U at quarter resolution.
    final bytes = p[0].bytes;
    final ySize = img.width * img.height;
    return FrameData(
      width: img.width,
      height: img.height,
      y: bytes,
      yRowStride: img.width,
      uBytes: bytes,
      vBytes: bytes,
      uOffset: ySize + 1,
      vOffset: ySize,
      uvRowStride: img.width,
      uvPixelStride: 2,
    );
  }

  /// Brightness of the frame's background, used to pad crops that run off the edge.
  int backgroundY(FrameAnalysis a) => a.medianBrightness.round().clamp(0, 255).toInt();
}

/// Square crop around [blob] -> flat 224*224*3 RGB (0-255), same layout as photo mode.
Float32List cropBean(FrameData f, Blob blob, {int size = 224, int padY = 220}) {
  final side = kCropScale * blob.longSide;
  final x0 = blob.cx - side / 2, y0 = blob.cy - side / 2;
  final scale = side / size;
  final out = Float32List(size * size * 3);
  var i = 0;
  for (var oy = 0; oy < size; oy++) {
    final sy = y0 + (oy + 0.5) * scale - 0.5;
    for (var ox = 0; ox < size; ox++) {
      final sx = x0 + (ox + 0.5) * scale - 0.5;
      double yy, uu, vv;
      if (sx < 0 || sy < 0 || sx > f.width - 1 || sy > f.height - 1) {
        // Outside the frame: fill with neutral background (like the dataset's paper).
        yy = padY.toDouble();
        uu = 128;
        vv = 128;
      } else {
        // Bilinear brightness, nearest colour (colour is stored at half resolution).
        final xi = sx.floor(), yi = sy.floor();
        final x1 = min(xi + 1, f.width - 1), y1 = min(yi + 1, f.height - 1);
        final fx = sx - xi, fy = sy - yi;
        final r0 = yi * f.yRowStride, r1 = y1 * f.yRowStride;
        yy = (f.y[r0 + xi] * (1 - fx) + f.y[r0 + x1] * fx) * (1 - fy) +
            (f.y[r1 + xi] * (1 - fx) + f.y[r1 + x1] * fx) * fy;
        final uvIndex = (sy.round() >> 1) * f.uvRowStride + (sx.round() >> 1) * f.uvPixelStride;
        uu = f.uBytes[min(f.uOffset + uvIndex, f.uBytes.length - 1)].toDouble();
        vv = f.vBytes[min(f.vOffset + uvIndex, f.vBytes.length - 1)].toDouble();
      }
      // YUV -> RGB (BT.601, full range)
      out[i++] = (yy + 1.402 * (vv - 128)).clamp(0, 255).toDouble();
      out[i++] = (yy - 0.344136 * (uu - 128) - 0.714136 * (vv - 128)).clamp(0, 255).toDouble();
      out[i++] = (yy + 1.772 * (uu - 128)).clamp(0, 255).toDouble();
    }
  }
  return out;
}

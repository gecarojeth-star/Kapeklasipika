// detector.dart
// --------------
// Stage 1 of the live scanner: find every bean in a camera frame.
// Same algorithm and settings as src/live_detector.py (tested in Python first).
//
//  1. Use only brightness (the camera's Y plane), shrunk to ~160 px wide.
//  2. Otsu's method picks the brightness that best separates dark objects from the
//     light background.
//  3. Dark pixels -> mask; "close" fills small gaps (the bright crease of a bean),
//     "open" removes dust specks.
//  4. Connected components -> one blob per object, with shape measurements.
//
// Everything here is plain Dart (no Flutter), so it can run in a background isolate.

import 'dart:math';
import 'dart:typed_data';

// Tunable settings (same names and values as src/live_detector.py)
const int kSmallWidth = 160; // analysis width in pixels
const int kMinBlobArea = 10; // small-image pixels; smaller = dust
const double kMaxBlobFraction = 0.25; // blob over 25% of the frame -> too close (or a hand)
const double kMinBgBrightness = 90; // frame darker than this -> "too dark"
const double kLightBgBrightness = 170; // a proper light tray/paper is brighter than this
const double kMinContrast = 25; // background minus object brightness
const double kMaxElongation = 3.0; // longer than 3:1 -> not bean-shaped
const double kMinEllipseFill = 0.55; // less ellipse-like than this -> irregular object
const double kMergedAreaRatio = 1.7; // blob > 1.7x median bean area -> touching beans
const double kMergedElongation = 2.2; // ...or long AND clearly bigger than one bean
const double kMergedElongArea = 1.5; //    (a longberry alone is long but ~one bean in area)
const double kMinBeanPx = 36; // bean's long side in full-res pixels; smaller -> move closer
const double kCropScale = 2.0; // crop side = 2x bean long side (dataset framing)

/// One object found in the frame (full-resolution sensor coordinates).
class Blob {
  double cx, cy; // center
  final double w, h; // bounding box size
  final double x0, y0; // bounding box top-left
  final double area;
  final double elongation; // long axis / short axis of the best-fit ellipse
  final double ellipseFill; // ~1.0 for ellipse-like shapes, lower for irregular ones
  final bool touchesEdge;
  bool shapeOk = true; // passes the bean-shape check
  bool merged = false; // probably two or more touching beans

  Blob({
    required this.cx,
    required this.cy,
    required this.w,
    required this.h,
    required this.x0,
    required this.y0,
    required this.area,
    required this.elongation,
    required this.ellipseFill,
    required this.touchesEdge,
  });

  double get longSide => max(w, h);
}

class FrameAnalysis {
  final List<Blob> blobs;
  final double medianBrightness;
  final double contrast;
  final double darkFraction;
  final int threshold;
  const FrameAnalysis(this.blobs, this.medianBrightness, this.contrast, this.darkFraction, this.threshold);
}

enum Guidance { good, tooDark, needLightBackground, noBeans, tooClose, moveBack, moveCloser, spreadBeans }

/// Find beans in a Y (brightness) plane. Safe to call from a background isolate.
FrameAnalysis findBeans(Uint8List y, int width, int height, int rowStride) {
  final step = max(1, width ~/ kSmallWidth);
  final sw = width ~/ step, sh = height ~/ step;

  // 1. Downsample: average of 2x2 pixels every `step` pixels.
  final small = Uint8List(sw * sh);
  final hist = List<int>.filled(256, 0);
  for (var sy = 0; sy < sh; sy++) {
    final y0 = sy * step, y1 = min(y0 + 1, height - 1);
    for (var sx = 0; sx < sw; sx++) {
      final x0 = sx * step, x1 = min(x0 + 1, width - 1);
      final v = (y[y0 * rowStride + x0] + y[y0 * rowStride + x1] + y[y1 * rowStride + x0] + y[y1 * rowStride + x1]) >> 2;
      small[sy * sw + sx] = v;
      hist[v]++;
    }
  }
  final n = sw * sh;

  // 2. Otsu threshold.
  var sumAll = 0.0;
  for (var t = 0; t < 256; t++) {
    sumAll += t * hist[t];
  }
  var wB = 0.0, sumB = 0.0, bestVar = -1.0;
  var threshold = 0;
  for (var t = 0; t < 256; t++) {
    wB += hist[t];
    if (wB == 0) continue;
    final wF = n - wB;
    if (wF == 0) break;
    sumB += t * hist[t];
    final mB = sumB / wB, mF = (sumAll - sumB) / wF;
    final v = wB * wF * (mB - mF) * (mB - mF);
    if (v > bestVar) {
      bestVar = v;
      threshold = t;
    }
  }

  // Brightness statistics.
  var darkCount = 0, darkSum = 0.0, brightSum = 0.0;
  for (var t = 0; t < 256; t++) {
    if (t < threshold) {
      darkCount += hist[t];
      darkSum += t * hist[t];
    } else {
      brightSum += t * hist[t];
    }
  }
  final brightCount = n - darkCount;
  final bgB = brightCount > 0 ? brightSum / brightCount : 0.0;
  final fgB = darkCount > 0 ? darkSum / darkCount : bgB;
  final contrast = bgB - fgB;
  var cum = 0, median = 0;
  for (var t = 0; t < 256; t++) {
    cum += hist[t];
    if (cum * 2 >= n) {
      median = t;
      break;
    }
  }
  final darkFrac = darkCount / n;
  if (contrast < kMinContrast || median < kMinBgBrightness || darkFrac > 0.5) {
    return FrameAnalysis(const [], median.toDouble(), contrast, darkFrac, threshold);
  }

  // 3. Mask, then close (dilate -> erode) and open (erode -> dilate).
  var mask = Uint8List(n);
  for (var i = 0; i < n; i++) {
    mask[i] = small[i] < threshold ? 1 : 0;
  }
  mask = _erode(_dilate(mask, sw, sh), sw, sh);
  mask = _dilate(_erode(mask, sw, sh), sw, sh);

  // 4. Connected components (4-neighbour flood fill).
  final labels = Int32List(n);
  final stack = Int32List(n);
  final blobs = <Blob>[];
  var nextLabel = 0;
  for (var start = 0; start < n; start++) {
    if (mask[start] == 0 || labels[start] != 0) continue;
    nextLabel++;
    var top = 0;
    stack[top++] = start;
    labels[start] = nextLabel;
    var cnt = 0.0, sx = 0.0, sy = 0.0, sxx = 0.0, syy = 0.0, sxy = 0.0;
    var minX = sw, maxX = -1, minY = sh, maxY = -1;
    while (top > 0) {
      final p = stack[--top];
      final px = p % sw, py = p ~/ sw;
      cnt++;
      sx += px;
      sy += py;
      sxx += px * px;
      syy += py * py;
      sxy += px * py;
      if (px < minX) minX = px;
      if (px > maxX) maxX = px;
      if (py < minY) minY = py;
      if (py > maxY) maxY = py;
      if (py > 0) top = _push(p - sw, mask, labels, nextLabel, stack, top);
      if (py < sh - 1) top = _push(p + sw, mask, labels, nextLabel, stack, top);
      if (px > 0) top = _push(p - 1, mask, labels, nextLabel, stack, top);
      if (px < sw - 1) top = _push(p + 1, mask, labels, nextLabel, stack, top);
    }
    if (cnt < kMinBlobArea) continue;
    final mx = sx / cnt, my = sy / cnt;
    final cxx = sxx / cnt - mx * mx, cyy = syy / cnt - my * my, cxy = sxy / cnt - mx * my;
    final tr = cxx + cyy, det = cxx * cyy - cxy * cxy;
    final disc = sqrt(max(tr * tr / 4 - det, 0.0));
    final l1 = tr / 2 + disc, l2 = max(tr / 2 - disc, 1e-6);
    blobs.add(Blob(
      cx: (mx + 0.5) * step,
      cy: (my + 0.5) * step,
      w: (maxX - minX + 1) * step.toDouble(),
      h: (maxY - minY + 1) * step.toDouble(),
      x0: minX * step.toDouble(),
      y0: minY * step.toDouble(),
      area: cnt * step * step,
      elongation: sqrt(l1 / l2),
      ellipseFill: cnt / (4 * pi * sqrt(l1 * l2)),
      touchesEdge: minX == 0 || minY == 0 || maxX == sw - 1 || maxY == sh - 1,
    ));
  }

  // Touching beans and the bean-shape check.
  if (blobs.length >= 3) {
    final areas = blobs.map((b) => b.area).toList()..sort();
    final med = areas[areas.length ~/ 2];
    for (final b in blobs) {
      b.merged = b.area > kMergedAreaRatio * med || (b.elongation > kMergedElongation && b.area > kMergedElongArea * med);
    }
  }
  for (final b in blobs) {
    b.shapeOk = b.merged || (b.elongation <= kMaxElongation && b.ellipseFill >= kMinEllipseFill);
  }
  return FrameAnalysis(blobs, median.toDouble(), contrast, darkFrac, threshold);
}

int _push(int q, Uint8List mask, Int32List labels, int label, Int32List stack, int top) {
  if (mask[q] == 1 && labels[q] == 0) {
    labels[q] = label;
    stack[top++] = q;
  }
  return top;
}

Uint8List _dilate(Uint8List m, int w, int h) {
  final o = Uint8List.fromList(m);
  for (var y = 0; y < h; y++) {
    for (var x = 0; x < w; x++) {
      final i = y * w + x;
      if (m[i] == 1) continue;
      if ((y > 0 && m[i - w] == 1) || (y < h - 1 && m[i + w] == 1) || (x > 0 && m[i - 1] == 1) || (x < w - 1 && m[i + 1] == 1)) {
        o[i] = 1;
      }
    }
  }
  return o;
}

Uint8List _erode(Uint8List m, int w, int h) {
  final o = Uint8List(m.length);
  for (var y = 1; y < h - 1; y++) {
    for (var x = 1; x < w - 1; x++) {
      final i = y * w + x;
      if (m[i] == 1 && m[i - w] == 1 && m[i + w] == 1 && m[i - 1] == 1 && m[i + 1] == 1) o[i] = 1;
    }
  }
  return o;
}

/// One message for the user, most important first.
Guidance guidanceFor(FrameAnalysis r, int width, int height) {
  if (r.medianBrightness < kMinBgBrightness) return Guidance.tooDark;
  if (r.darkFraction > 0.5 && r.contrast >= kMinContrast) return Guidance.needLightBackground;
  if (r.blobs.isEmpty) {
    return r.medianBrightness >= kLightBgBrightness ? Guidance.noBeans : Guidance.needLightBackground;
  }
  if (r.blobs.any((b) => b.area > kMaxBlobFraction * width * height)) return Guidance.tooClose;
  final beans = r.blobs.where((b) => !b.merged).toList();
  if (beans.isNotEmpty && beans.where((b) => b.touchesEdge).length / beans.length > 0.3) {
    return Guidance.moveBack;
  }
  if (beans.isNotEmpty) {
    final sides = beans.map((b) => b.longSide).toList()..sort();
    if (sides[sides.length ~/ 2] < kMinBeanPx) return Guidance.moveCloser;
  }
  if (r.blobs.any((b) => b.merged)) return Guidance.spreadBeans;
  return Guidance.good;
}

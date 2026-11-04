// tracker.dart
// -------------
// Stage 2 of the live scanner: give each bean an ID and keep it while the camera moves.
// Same logic as the Tracker in src/live_detector.py.
//
// - Each new frame's blobs are matched to existing beans by nearest center
//   (closest pairs first), so bean #7 stays #7.
// - A bean must be seen in 3 frames before it is shown (filters flicker).
// - Each bean's label is the AVERAGE of its classifications (up to 8 votes), so labels
//   don't flip from frame to frame.

import 'dart:math';

import 'detector.dart';

class Track {
  final int id;
  Blob blob;
  int hits = 1;
  int missed = 0;
  final List<double> probSum;
  double anomalySum = 0;
  bool hasAnomaly = false; // model provides an anomaly score
  int votes = 0;

  Track(this.id, this.blob, int nClasses) : probSum = List<double>.filled(nClasses, 0);

  bool get confirmed => hits >= 3;

  /// Index of the most likely class, or null if not classified yet.
  int? get labelIndex {
    if (votes == 0) return null;
    var best = 0;
    for (var i = 1; i < probSum.length; i++) {
      if (probSum[i] > probSum[best]) best = i;
    }
    return best;
  }

  double get confidence => votes == 0 ? 0 : probSum[labelIndex!] / votes;
  double? get anomalyRatio => (votes == 0 || !hasAnomaly) ? null : anomalySum / votes;

  /// False if the shape check or the anomaly detector says this is not a coffee bean.
  bool get isBean {
    if (!blob.shapeOk) return false;
    final r = anomalyRatio;
    return r == null || r <= 1.0;
  }
}

class Tracker {
  static const int maxMissed = 6; // frames a bean may disappear before its ID is dropped
  static const double matchRadius = 0.7; // match if centers closer than 0.7 x bean size
  static const int maxVotes = 8; // stop re-classifying a bean after 8 votes
  static const int perFrame = 2; // classify at most 2 beans per frame (keeps the app smooth)
  static const double smooth = 0.5; // box smoothing (0 = jumpy, 1 = frozen)

  final int nClasses;
  final List<Track> tracks = [];
  int _nextId = 1;

  Tracker(this.nClasses);

  void reset() {
    tracks.clear();
    _nextId = 1;
  }

  void update(List<Blob> blobs) {
    final pairs = <(double, int, int)>[];
    for (var ti = 0; ti < tracks.length; ti++) {
      final t = tracks[ti].blob;
      for (var bi = 0; bi < blobs.length; bi++) {
        final b = blobs[bi];
        final d = sqrt(pow(t.cx - b.cx, 2) + pow(t.cy - b.cy, 2));
        if (d < matchRadius * max(t.longSide, b.longSide)) pairs.add((d, ti, bi));
      }
    }
    pairs.sort((a, b) => a.$1.compareTo(b.$1));
    final usedT = <int>{}, usedB = <int>{};
    for (final (_, ti, bi) in pairs) {
      if (usedT.contains(ti) || usedB.contains(bi)) continue;
      usedT.add(ti);
      usedB.add(bi);
      final t = tracks[ti], b = blobs[bi];
      b.cx = smooth * t.blob.cx + (1 - smooth) * b.cx;
      b.cy = smooth * t.blob.cy + (1 - smooth) * b.cy;
      t.blob = b;
      t.hits++;
      t.missed = 0;
    }
    for (var ti = 0; ti < tracks.length; ti++) {
      if (!usedT.contains(ti)) tracks[ti].missed++;
    }
    tracks.removeWhere((t) => t.missed > maxMissed);
    for (var bi = 0; bi < blobs.length; bi++) {
      if (!usedB.contains(bi)) tracks.add(Track(_nextId++, blobs[bi], nClasses));
    }
  }

  /// Beans that most need a (new) classification this frame.
  List<Track> toClassify() {
    final c = tracks
        .where((t) => t.confirmed && t.missed == 0 && t.blob.shapeOk && !t.blob.merged && t.votes < maxVotes)
        .toList()
      ..sort((a, b) => a.votes.compareTo(b.votes));
    return c.take(perFrame).toList();
  }

  void addVote(Track t, List<double> probs, double? anomalyRatio) {
    for (var i = 0; i < probs.length; i++) {
      t.probSum[i] += probs[i];
    }
    if (anomalyRatio != null) {
      t.anomalySum += anomalyRatio;
      t.hasAnomaly = true;
    }
    t.votes++;
  }

  List<Track> get visible => tracks.where((t) => t.confirmed && t.missed == 0).toList();
}

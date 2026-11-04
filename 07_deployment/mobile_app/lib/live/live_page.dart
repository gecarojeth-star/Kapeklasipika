// live_page.dart
// ---------------
// Live scanner: point the camera at a light tray of green beans. For every frame:
//   1. find beans            (detector.dart, background isolate)
//   2. keep IDs per bean     (tracker.dart)
//   3. classify new beans    (classifier.dart, up to 2 per frame, labels averaged over frames)
//   4. show boxes, counts, estimated weight and camera guidance.

import 'dart:isolate';
import 'dart:typed_data';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';

import '../classifier.dart';
import '../look.dart';
import '../settings.dart';
import 'detector.dart';
import 'frame.dart';
import 'tracker.dart';

/// Runs the bean finder in a background isolate (receives only the brightness plane).
Future<FrameAnalysis> analyzeInBackground(Uint8List y, int width, int height, int rowStride) =>
    Isolate.run(() => findBeans(y, width, height, rowStride));

/// Counts shown in the summary panel.
class LiveSummary {
  final Map<String, int> perClass;
  final int analyzing; // found but not classified yet
  final int notBeans;
  final int touchingGroups;
  final int touchingBeans; // estimated beans inside touching groups
  const LiveSummary(this.perClass, this.analyzing, this.notBeans, this.touchingGroups, this.touchingBeans);

  int get beans => perClass.values.fold(0, (a, b) => a + b) + analyzing + touchingBeans;

  static LiveSummary from(List<Track> visible, List<String> labels) {
    final perClass = {for (final l in labels) l: 0};
    var analyzing = 0, notBeans = 0, groups = 0, inGroups = 0;
    final singles = visible.where((t) => !t.blob.merged).map((t) => t.blob.area).toList()..sort();
    final medianArea = singles.isEmpty ? 0.0 : singles[singles.length ~/ 2];
    for (final t in visible) {
      if (t.blob.merged) {
        groups++;
        final est = medianArea > 0 ? (t.blob.area / medianArea).round() : 2;
        inGroups += est < 2 ? 2 : est;
      } else if (!t.isBean) {
        notBeans++;
      } else if (t.labelIndex == null) {
        analyzing++;
      } else {
        perClass[labels[t.labelIndex!]] = perClass[labels[t.labelIndex!]]! + 1;
      }
    }
    return LiveSummary(perClass, analyzing, notBeans, groups, inGroups);
  }
}

class LivePage extends StatefulWidget {
  final BeanClassifier? classifier;
  final WeightSettings weight;
  const LivePage({super.key, required this.classifier, required this.weight});

  @override
  State<LivePage> createState() => _LivePageState();
}

class _LivePageState extends State<LivePage> with WidgetsBindingObserver {
  CameraController? _controller;
  int _sensorOrientation = 90;
  String? _cameraError;

  Tracker? _tracker;
  Guidance _guidance = Guidance.noBeans;
  Size _imageSize = const Size(720, 480);
  int _rotation = 90;
  bool _busy = false;
  bool _frozen = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _initCamera();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _controller?.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final c = _controller;
    if (state == AppLifecycleState.inactive || state == AppLifecycleState.paused) {
      _controller = null;
      c?.dispose();
      if (mounted) setState(() {});
    } else if (state == AppLifecycleState.resumed && _controller == null) {
      _initCamera();
    }
  }

  Future<void> _initCamera() async {
    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty) throw CameraException('none', 'No camera found');
      final back = cameras.firstWhere((c) => c.lensDirection == CameraLensDirection.back, orElse: () => cameras.first);
      final controller = CameraController(
        back,
        ResolutionPreset.medium, // ~720x480: fast enough for low-end phones
        enableAudio: false,
        imageFormatGroup: ImageFormatGroup.yuv420,
      );
      await controller.initialize();
      if (!mounted) {
        await controller.dispose();
        return;
      }
      _sensorOrientation = back.sensorOrientation;
      _controller = controller;
      _frozen = false;
      await controller.startImageStream(_onFrame);
      setState(() => _cameraError = null);
    } catch (e) {
      if (mounted) setState(() => _cameraError = 'Camera not available: $e');
    }
  }

  Future<void> _onFrame(CameraImage image) async {
    final classifier = widget.classifier;
    if (_busy || _frozen || !mounted || classifier == null) return;
    _busy = true;
    try {
      _tracker ??= Tracker(classifier.labels.length);
      final tracker = _tracker!;
      final frame = FrameData.fromCameraImage(image);

      // 1. Find beans (background isolate).
      final analysis = await analyzeInBackground(frame.y, frame.width, frame.height, frame.yRowStride);

      // 2. Keep IDs.
      tracker.update(analysis.blobs);

      // 3. Classify the beans that need it most (max 2 per frame).
      final padY = frame.backgroundY(analysis);
      for (final t in tracker.toClassify()) {
        final crop = cropBean(frame, t.blob, padY: padY);
        final p = await classifier.classifyFlat(crop);
        tracker.addVote(t, [for (final l in classifier.labels) p.probabilities[l] ?? 0], p.anomalyRatio);
      }

      if (!mounted) return;
      setState(() {
        _imageSize = Size(frame.width.toDouble(), frame.height.toDouble());
        // Some devices deliver frames already upright (portrait); then no rotation is needed.
        _rotation = frame.width > frame.height ? _sensorOrientation : 0;
        _guidance = guidanceFor(analysis, frame.width, frame.height);
      });
    } catch (e) {
      debugPrint('Live frame error: $e');
    } finally {
      _busy = false;
    }
  }

  Future<void> _toggleFreeze() async {
    final c = _controller;
    if (c == null) return;
    if (_frozen) {
      await c.resumePreview();
      setState(() => _frozen = false);
    } else {
      setState(() => _frozen = true);
      await c.pausePreview();
      if (mounted) _showDetails();
    }
  }

  void _resetIds() => setState(() => _tracker?.reset());

  void _showDetails() {
    final classifier = widget.classifier;
    if (classifier == null) return;
    final visible = [...?_tracker?.visible]..sort((a, b) => a.id.compareTo(b.id));
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (context) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.55,
        builder: (context, scroll) => ListView(
          controller: scroll,
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
          children: [
            Text('Scan details', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 4),
            _SummaryLine(summary: LiveSummary.from(visible, classifier.labels), weight: widget.weight),
            const Divider(height: 24),
            if (visible.isEmpty) const Text('No beans in view.'),
            for (final t in visible) _TrackTile(track: t, labels: classifier.labels),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final classifier = widget.classifier;
    final c = _controller;
    final visible = _tracker?.visible ?? const <Track>[];
    final summary = classifier == null ? null : LiveSummary.from(visible, classifier.labels);

    Widget preview;
    if (_cameraError != null) {
      preview = Center(child: Padding(padding: const EdgeInsets.all(24), child: Text(_cameraError!, style: const TextStyle(color: Colors.white))));
    } else if (c == null || !c.value.isInitialized) {
      preview = const Center(child: CircularProgressIndicator(color: Colors.white));
    } else {
      preview = Center(
        child: AspectRatio(
          aspectRatio: 1 / c.value.aspectRatio, // portrait
          child: Stack(
            fit: StackFit.expand,
            children: [
              CameraPreview(c),
              CustomPaint(
                painter: _BeanPainter(
                  tracks: visible,
                  labels: classifier?.labels ?? const [],
                  imageSize: _imageSize,
                  rotation: _rotation,
                ),
              ),
            ],
          ),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Live scan', style: TextStyle(fontWeight: FontWeight.w600)),
        actions: [
          IconButton(tooltip: 'Reset IDs and counts', icon: const Icon(Icons.restart_alt), onPressed: _resetIds),
          IconButton(
            tooltip: 'Weight estimate settings',
            icon: const Icon(Icons.scale_outlined),
            onPressed: () => showWeightCalibration(context, widget.weight),
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: Container(
              color: Colors.black,
              child: Stack(
                children: [
                  Positioned.fill(child: preview),
                  Positioned(
                    top: 12,
                    left: 12,
                    right: 12,
                    child: Center(child: _GuidanceChip(guidance: _frozen ? null : _guidance)),
                  ),
                ],
              ),
            ),
          ),
          _BottomPanel(
            summary: summary,
            weight: widget.weight,
            frozen: _frozen,
            onFreeze: _toggleFreeze,
            onDetails: _showDetails,
            modelHasDetector: classifier?.hasAnomalyDetector ?? false,
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Overlay: a box and label per bean
// ---------------------------------------------------------------------------
class _BeanPainter extends CustomPainter {
  final List<Track> tracks;
  final List<String> labels;
  final Size imageSize; // camera frame size (sensor orientation)
  final int rotation; // degrees to rotate frame coordinates into the portrait preview

  _BeanPainter({required this.tracks, required this.labels, required this.imageSize, required this.rotation});

  Offset _map(double x, double y) {
    final w = imageSize.width, h = imageSize.height;
    switch (rotation) {
      case 90:
        return Offset(h - y, x);
      case 270:
        return Offset(y, w - x);
      case 180:
        return Offset(w - x, h - y);
      default:
        return Offset(x, y);
    }
  }

  @override
  void paint(Canvas canvas, Size size) {
    final rotated = rotation == 90 || rotation == 270;
    final dispW = rotated ? imageSize.height : imageSize.width;
    final dispH = rotated ? imageSize.width : imageSize.height;
    final sx = size.width / dispW, sy = size.height / dispH;

    for (final t in tracks) {
      final b = t.blob;
      final p1 = _map(b.cx - b.w / 2, b.cy - b.h / 2);
      final p2 = _map(b.cx + b.w / 2, b.cy + b.h / 2);
      final rect = Rect.fromPoints(Offset(p1.dx * sx, p1.dy * sy), Offset(p2.dx * sx, p2.dy * sy)).inflate(3);

      final Color color;
      final String text;
      if (b.merged) {
        color = kTouchingColor;
        text = '#${t.id} touching';
      } else if (!t.isBean) {
        color = kNotBeanColor;
        text = '#${t.id} unusual';
      } else if (t.labelIndex == null) {
        color = kAnalyzingColor;
        text = '#${t.id} ...';
      } else {
        final l = labels[t.labelIndex!];
        color = classColor(l);
        text = '#${t.id} ${displayName(l)} ${(t.confidence * 100).round()}%';
      }

      canvas.drawRRect(
        RRect.fromRectAndRadius(rect, const Radius.circular(8)),
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 3
          ..color = color,
      );
      final tp = TextPainter(
        text: TextSpan(
          text: text,
          style: TextStyle(
            color: color == kAnalyzingColor ? Colors.black : Colors.white,
            fontSize: 12,
            fontWeight: FontWeight.w600,
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout();
      final top = rect.top - tp.height - 6 < 0 ? rect.bottom + 2 : rect.top - tp.height - 6;
      final bg = Rect.fromLTWH(rect.left, top, tp.width + 10, tp.height + 4);
      canvas.drawRRect(RRect.fromRectAndRadius(bg, const Radius.circular(6)), Paint()..color = color.withValues(alpha: 0.9));
      tp.paint(canvas, Offset(bg.left + 5, bg.top + 2));
    }
  }

  @override
  bool shouldRepaint(covariant _BeanPainter old) => true;
}

// ---------------------------------------------------------------------------
// Guidance chip
// ---------------------------------------------------------------------------
class _GuidanceChip extends StatelessWidget {
  final Guidance? guidance; // null when frozen
  const _GuidanceChip({required this.guidance});

  static const Map<Guidance, (IconData, String)> _text = {
    Guidance.good: (Icons.check_circle, 'Good distance. Hold steady'),
    Guidance.tooDark: (Icons.light_mode, 'Too dark. Add more light'),
    Guidance.needLightBackground: (Icons.crop_square, 'Use a plain, light background (white paper or tray)'),
    Guidance.noBeans: (Icons.search, 'Point the camera at the beans'),
    Guidance.tooClose: (Icons.zoom_out_map, 'Too close. Move the phone back'),
    Guidance.moveBack: (Icons.zoom_out, 'Beans are cut off. Move back a little'),
    Guidance.moveCloser: (Icons.zoom_in, 'Too far. Move closer so beans look bigger'),
    Guidance.spreadBeans: (Icons.open_with, 'Some beans are touching. Spread them apart'),
  };

  @override
  Widget build(BuildContext context) {
    final g = guidance;
    final (icon, text) = g == null ? (Icons.pause_circle, 'Frozen. Tap Resume to continue') : _text[g]!;
    final ok = g == Guidance.good;
    final color = g == null ? Colors.blueGrey : (ok ? const Color(0xFF2E7D32) : const Color(0xFFB26A00));
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 250),
      child: Container(
        key: ValueKey(g),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(color: color.withValues(alpha: 0.92), borderRadius: BorderRadius.circular(24)),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: Colors.white, size: 18),
            const SizedBox(width: 8),
            Flexible(child: Text(text, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600))),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Bottom panel: counts, weight, freeze
// ---------------------------------------------------------------------------
class _BottomPanel extends StatelessWidget {
  final LiveSummary? summary;
  final WeightSettings weight;
  final bool frozen;
  final VoidCallback onFreeze;
  final VoidCallback onDetails;
  final bool modelHasDetector;

  const _BottomPanel({
    required this.summary,
    required this.weight,
    required this.frozen,
    required this.onFreeze,
    required this.onDetails,
    required this.modelHasDetector,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final s = summary;
    return Material(
      color: theme.colorScheme.surface,
      elevation: 8,
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (s == null)
                const Text('Loading model...')
              else ...[
                _SummaryLine(summary: s, weight: weight),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [
                    for (final e in s.perClass.entries)
                      if (e.value > 0) _CountChip(color: classColor(e.key), text: '${displayName(e.key)} ${e.value}'),
                    if (s.analyzing > 0) _CountChip(color: Colors.blueGrey, text: 'Analyzing ${s.analyzing}'),
                    if (s.touchingGroups > 0) _CountChip(color: kTouchingColor, text: 'Touching ≈${s.touchingBeans}'),
                    if (s.notBeans > 0) _CountChip(color: kNotBeanColor, text: 'Unusual ${s.notBeans}'),
                  ],
                ),
                if (!modelHasDetector)
                  Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Text('Using the v1 model: only the shape check can flag non-beans.',
                        style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
                  ),
              ],
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: FilledButton.icon(
                      style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(48)),
                      onPressed: onFreeze,
                      icon: Icon(frozen ? Icons.play_arrow : Icons.pause),
                      label: Text(frozen ? 'Resume' : 'Freeze'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: OutlinedButton.icon(
                      style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(48)),
                      onPressed: onDetails,
                      icon: const Icon(Icons.list_alt),
                      label: const Text('Details'),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SummaryLine extends StatelessWidget {
  final LiveSummary summary;
  final WeightSettings weight;
  const _SummaryLine({required this.summary, required this.weight});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return ListenableBuilder(
      listenable: weight,
      builder: (context, _) {
        final grams = summary.beans * weight.gramsPerBean;
        return Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text('${summary.beans}', style: theme.textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w700)),
            const SizedBox(width: 6),
            Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Text(summary.beans == 1 ? 'bean' : 'beans', style: theme.textTheme.titleMedium),
            ),
            const Spacer(),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text('≈ ${grams.toStringAsFixed(1)} g', style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w600)),
                Text(
                  '${weight.gramsPerBean.toStringAsFixed(3)} g/bean · ${weight.isCalibrated ? 'calibrated' : 'published avg.'}',
                  style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurfaceVariant),
                ),
              ],
            ),
          ],
        );
      },
    );
  }
}

class _CountChip extends StatelessWidget {
  final Color color;
  final String text;
  const _CountChip({required this.color, required this.text});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: color.withValues(alpha: 0.6)),
      ),
      child: Text(text, style: TextStyle(color: color == Colors.blueGrey ? null : color, fontWeight: FontWeight.w600)),
    );
  }
}

class _TrackTile extends StatelessWidget {
  final Track track;
  final List<String> labels;
  const _TrackTile({required this.track, required this.labels});

  @override
  Widget build(BuildContext context) {
    final t = track;
    final String title;
    final String subtitle;
    final Color color;
    if (t.blob.merged) {
      title = 'Touching beans';
      subtitle = 'Spread them apart to classify each one';
      color = kTouchingColor;
    } else if (!t.isBean) {
      title = 'Unusual or not a bean. Check by hand';
      subtitle = !t.blob.shapeOk
          ? 'Shape is not bean-like'
          : 'Looks unlike the training beans (${t.anomalyRatio!.toStringAsFixed(1)}x the limit)';
      color = kNotBeanColor;
    } else if (t.labelIndex == null) {
      title = 'Analyzing...';
      subtitle = 'Waiting for the first classification';
      color = Colors.blueGrey;
    } else {
      final l = labels[t.labelIndex!];
      title = displayName(l);
      subtitle = '${(t.confidence * 100).toStringAsFixed(0)}% average over ${t.votes} '
          '${t.votes == 1 ? 'look' : 'looks'}';
      color = classColor(l);
    }
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: CircleAvatar(
        backgroundColor: color.withValues(alpha: 0.15),
        child: Text('#${t.id}', style: TextStyle(color: color, fontWeight: FontWeight.w700, fontSize: 13)),
      ),
      title: Text(title),
      subtitle: Text(subtitle),
    );
  }
}

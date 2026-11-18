// photo_page.dart
// ----------------
// Photo mode: take or choose a photo of ONE green coffee bean and see whether it is
// Peaberry, Longberry, Premium, or Defect (or not a coffee bean at all).
//
// Screen layout (top to bottom):
//   app bar (logo, name, tips button)
//   photo card        -> empty state / photo / "Analyzing..." overlay
//   result card       -> class, confidence, animated probability bars
//   recent scans      -> tap a thumbnail to see that result again; "Clear" empties the list.
//                        Kept in memory only: nothing is saved, and closing the app clears it.
//   bottom bar        -> Take photo | Upload (always reachable with the thumb)

import 'dart:typed_data';

import 'package:flutter/foundation.dart' show defaultTargetPlatform, TargetPlatform;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show PlatformException;
import 'package:image_picker/image_picker.dart';

import 'classifier.dart';
import 'look.dart';

/// One finished scan: the photo and what the model said about it.
class Scan {
  final int id;
  final Uint8List bytes;
  final Prediction prediction;
  const Scan(this.id, this.bytes, this.prediction);
}

class PhotoPage extends StatefulWidget {
  final BeanClassifier? classifier; // null while the model is still loading
  final String? loadError;
  const PhotoPage({super.key, required this.classifier, this.loadError});

  @override
  State<PhotoPage> createState() => _PhotoPageState();
}

class _PhotoPageState extends State<PhotoPage> {
  static const int _maxHistory = 12;

  final _picker = ImagePicker();
  BeanClassifier? get _classifier => widget.classifier;
  Scan? _current; // the scan whose result is shown
  final List<Scan> _history = []; // newest first
  Uint8List? _pendingPhoto; // photo being analyzed right now
  String? _error;
  bool _busy = false;
  int _nextId = 0;

  bool _picking = false; // the camera or gallery is open
  Uint8List? _recovered; // photo recovered after Android closed the app (see below)

  @override
  void initState() {
    super.initState();
    _recoverLostPhoto();
  }

  @override
  void didUpdateWidget(PhotoPage oldWidget) {
    super.didUpdateWidget(oldWidget);
    // The model finished loading after a photo was recovered: classify it now.
    if (oldWidget.classifier == null && widget.classifier != null && _recovered != null) {
      final bytes = _recovered!;
      _recovered = null;
      _classify(bytes);
    }
  }

  /// On low-memory phones Android may close this app while the camera app is open.
  /// When the user comes back the app restarts, and the photo would be lost. image_picker
  /// keeps it for us; fetch it here so the scan continues instead of silently vanishing.
  Future<void> _recoverLostPhoto() async {
    if (defaultTargetPlatform != TargetPlatform.android) return;
    try {
      final lost = await _picker.retrieveLostData();
      if (lost.isEmpty || lost.file == null) return;
      final bytes = await lost.file!.readAsBytes();
      if (!mounted) return;
      if (_classifier != null) {
        _classify(bytes);
      } else {
        _recovered = bytes; // classified in didUpdateWidget once the model is ready
      }
    } catch (_) {
      // Nothing to recover, or it could not be read: just start normally.
    }
  }

  Future<void> _pickAndClassify(ImageSource source) async {
    if (_classifier == null || _busy || _picking) return;
    setState(() {
      _picking = true; // disables both buttons, so a double tap can't open the camera twice
      _error = null;
    });

    Uint8List? bytes;
    try {
      // Ask the picker for a small image (max 1024 px). A full-size camera photo can be
      // 12-50 megapixels, which is slow to decode and can run the phone out of memory.
      final picked = await _picker.pickImage(
          source: source, maxWidth: 1024, maxHeight: 1024, imageQuality: 95);
      if (picked != null) bytes = await picked.readAsBytes();
    } on PlatformException catch (e) {
      _showError(e.code.contains('access_denied')
          ? 'KapeKlasipika needs permission to use the camera or photos. '
              'Allow it in your phone settings, then try again.'
          : 'Could not open the ${source == ImageSource.camera ? 'camera' : 'gallery'}: '
              '${e.message ?? e.code}');
    } catch (e) {
      _showError('Could not read the photo: $e');
    } finally {
      if (mounted) setState(() => _picking = false);
    }
    if (bytes != null && mounted) await _classify(bytes);
  }

  Future<void> _classify(Uint8List bytes) async {
    final classifier = _classifier;
    if (classifier == null || _busy) return;
    setState(() {
      _pendingPhoto = bytes;
      _error = null;
      _busy = true;
    });
    try {
      final prediction = await classifier.classifyBytes(bytes);
      if (!mounted) return;
      final scan = Scan(_nextId++, bytes, prediction);
      setState(() {
        _current = scan;
        _history.insert(0, scan);
        if (_history.length > _maxHistory) _history.removeLast();
      });
    } catch (e) {
      _showError('Could not classify this photo: $e');
    } finally {
      if (mounted) {
        setState(() {
          _busy = false;
          _pendingPhoto = null;
        });
      }
    }
  }

  void _showError(String message) {
    if (mounted) setState(() => _error = message);
  }

  /// "Clear" next to Recent scans: asks first, then removes every scan from the screen.
  Future<void> _confirmClear() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Clear recent scans?'),
        content: const Text('This removes all recent scans and the current result from the screen.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Clear')),
        ],
      ),
    );
    if (ok == true && mounted) {
      setState(() {
        _history.clear();
        _current = null;
        _error = null;
      });
    }
  }

  void _showTips() {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (context) => const _TipsSheet(),
    );
  }

  @override
  Widget build(BuildContext context) {
    final ready = _classifier != null && !_busy && !_picking;
    final shownPhoto = _pendingPhoto ?? _current?.bytes;

    return Scaffold(
      appBar: AppBar(
        titleSpacing: 16,
        title: Row(
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Image.asset('assets/icon/icon.png', width: 32, height: 32),
            ),
            const SizedBox(width: 12),
            const Text('KapeKlasipika', style: TextStyle(fontWeight: FontWeight.w600)),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'Photo tips',
            icon: const Icon(Icons.info_outline),
            onPressed: _showTips,
          ),
        ],
      ),
      body: SafeArea(
        bottom: false,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
          children: [
            _PhotoCard(photo: shownPhoto, busy: _busy),
            const SizedBox(height: 16),
            AnimatedSwitcher(
              duration: const Duration(milliseconds: 350),
              switchInCurve: Curves.easeOutCubic,
              transitionBuilder: (child, animation) => FadeTransition(
                opacity: animation,
                child: SlideTransition(
                  position: Tween(begin: const Offset(0, 0.06), end: Offset.zero).animate(animation),
                  child: child,
                ),
              ),
              child: _buildStatus(context),
            ),
            if (_history.length > 1) ...[
              const SizedBox(height: 24),
              Row(
                children: [
                  Expanded(child: Text('Recent scans', style: Theme.of(context).textTheme.titleSmall)),
                  TextButton.icon(
                    style: TextButton.styleFrom(
                      visualDensity: VisualDensity.compact,
                      padding: const EdgeInsets.symmetric(horizontal: 8),
                    ),
                    onPressed: _busy ? null : _confirmClear,
                    icon: const Icon(Icons.delete_outline, size: 18),
                    label: const Text('Clear'),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              SizedBox(
                height: 76,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: _history.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 10),
                  itemBuilder: (context, i) {
                    final scan = _history[i];
                    return _HistoryTile(
                      scan: scan,
                      selected: scan.id == _current?.id,
                      onTap: _busy ? null : () => setState(() => _current = scan),
                    );
                  },
                ),
              ),
            ],
          ],
        ),
      ),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
          child: Row(
            children: [
              Expanded(
                child: FilledButton.icon(
                  style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)),
                  onPressed: ready ? () => _pickAndClassify(ImageSource.camera) : null,
                  icon: const Icon(Icons.photo_camera_outlined),
                  label: const Text('Take photo'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(52)),
                  onPressed: ready ? () => _pickAndClassify(ImageSource.gallery) : null,
                  icon: const Icon(Icons.photo_library_outlined),
                  label: const Text('Upload'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// What goes under the photo: loading, error, result, or nothing.
  Widget _buildStatus(BuildContext context) {
    final error = _error ?? widget.loadError;
    if (error != null) {
      return _MessageCard(
        key: const ValueKey('error'),
        icon: Icons.error_outline,
        color: Theme.of(context).colorScheme.error,
        text: error,
      );
    }
    if (_classifier == null) {
      return const _MessageCard(
        key: ValueKey('loading'),
        icon: Icons.hourglass_top,
        text: 'Loading model...',
      );
    }
    if (_busy) {
      return const SizedBox(key: ValueKey('busy'), height: 0);
    }
    final scan = _current;
    if (scan == null) {
      return const SizedBox(key: ValueKey('none'), height: 0);
    }
    return _ResultCard(key: ValueKey(scan.id), prediction: scan.prediction);
  }
}

// ---------------------------------------------------------------------------
// Photo card
// ---------------------------------------------------------------------------
class _PhotoCard extends StatelessWidget {
  final Uint8List? photo;
  final bool busy;
  const _PhotoCard({required this.photo, required this.busy});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return AspectRatio(
      aspectRatio: 4 / 3,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: Container(
          color: scheme.surfaceContainerHighest,
          child: Stack(
            fit: StackFit.expand,
            children: [
              AnimatedSwitcher(
                duration: const Duration(milliseconds: 300),
                // Make the photo fill the whole card while cross-fading.
                layoutBuilder: (current, previous) => Stack(
                  fit: StackFit.expand,
                  children: [...previous, if (current != null) current],
                ),
                child: photo == null
                    ? const _EmptyState(key: ValueKey('empty'))
                    : Image.memory(photo!, key: ValueKey(photo.hashCode), fit: BoxFit.cover, gaplessPlayback: true),
              ),
              AnimatedOpacity(
                opacity: busy ? 1 : 0,
                duration: const Duration(milliseconds: 200),
                child: IgnorePointer(
                  child: Container(
                    color: Colors.black.withValues(alpha: 0.45),
                    alignment: Alignment.center,
                    child: const Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        CircularProgressIndicator(color: Colors.white),
                        SizedBox(height: 12),
                        Text('Analyzing...', style: TextStyle(color: Colors.white, fontSize: 16)),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.center_focus_weak, size: 56, color: theme.colorScheme.primary),
            const SizedBox(height: 12),
            Text('Take or upload a photo of one green bean',
                textAlign: TextAlign.center, style: theme.textTheme.titleMedium),
            const SizedBox(height: 4),
            Text('Works offline. Nothing leaves your phone.',
                textAlign: TextAlign.center,
                style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Result card
// ---------------------------------------------------------------------------
class _ResultCard extends StatelessWidget {
  final Prediction prediction;
  const _ResultCard({super.key, required this.prediction});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final notBean = !prediction.isBean;
    final color = notBean ? kNotBeanColor : classColor(prediction.label);
    final isDefect = prediction.label == 'defect';
    final unsure = !notBean && prediction.confidence < kLowConfidence;
    final seconds = prediction.elapsed.inMilliseconds / 1000;

    return Card(
      elevation: 0,
      color: theme.colorScheme.surfaceContainerLow,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: BorderSide(color: color.withValues(alpha: 0.35)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(
                  radius: 22,
                  backgroundColor: color.withValues(alpha: 0.15),
                  child: Icon(
                      notBean
                          ? Icons.help_outline
                          : (isDefect ? Icons.warning_amber_rounded : Icons.check_rounded),
                      color: color),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(notBean ? 'Unusual or not a bean' : displayName(prediction.label),
                      style: theme.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w600)),
                ),
                if (!notBean)
                  Text('${(prediction.confidence * 100).toStringAsFixed(1)}%',
                      style: theme.textTheme.titleLarge?.copyWith(color: color, fontWeight: FontWeight.w700)),
              ],
            ),
            const SizedBox(height: 8),
            Text(
                notBean
                    ? 'This looks unlike the beans the model learned from '
                        '(${prediction.anomalyRatio!.toStringAsFixed(1)}x the limit). It may not be a coffee '
                        'bean, or it may be an unusual bean such as an odd-looking defect. Check it by hand; '
                        'the bars below show the closest bean classes.'
                    : (kClassDescriptions[prediction.label] ?? ''),
                style: theme.textTheme.bodyMedium),
            if (unsure) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: theme.colorScheme.errorContainer,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  children: [
                    Icon(Icons.camera_alt_outlined, color: theme.colorScheme.onErrorContainer),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text('Low confidence. Retake the photo with better light and a plain background.',
                          style: TextStyle(color: theme.colorScheme.onErrorContainer)),
                    ),
                  ],
                ),
              ),
            ],
            const Divider(height: 28),
            Opacity(
              opacity: notBean ? 0.45 : 1,
              child: Column(
                children: [for (final e in prediction.ranked) _ProbabilityBar(label: e.key, value: e.value)],
              ),
            ),
            const SizedBox(height: 8),
            Text('Analyzed on-device in ${seconds.toStringAsFixed(2)} s',
                style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
          ],
        ),
      ),
    );
  }
}

class _ProbabilityBar extends StatelessWidget {
  final String label;
  final double value;
  const _ProbabilityBar({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    final color = classColor(label);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        children: [
          SizedBox(width: 92, child: Text(displayName(label))),
          Expanded(
            // The bar grows from 0 to its value when the result appears.
            child: TweenAnimationBuilder<double>(
              tween: Tween(begin: 0, end: value),
              duration: const Duration(milliseconds: 700),
              curve: Curves.easeOutCubic,
              builder: (context, v, _) => ClipRRect(
                borderRadius: BorderRadius.circular(6),
                child: LinearProgressIndicator(
                  value: v,
                  minHeight: 10,
                  color: color,
                  backgroundColor: color.withValues(alpha: 0.12),
                ),
              ),
            ),
          ),
          SizedBox(
            width: 60,
            child: Text('${(value * 100).toStringAsFixed(1)}%', textAlign: TextAlign.right),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Small pieces
// ---------------------------------------------------------------------------
class _HistoryTile extends StatelessWidget {
  final Scan scan;
  final bool selected;
  final VoidCallback? onTap;
  const _HistoryTile({required this.scan, required this.selected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final notBean = !scan.prediction.isBean;
    final color = notBean ? kNotBeanColor : classColor(scan.prediction.label);
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        width: 76,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: selected ? color : Colors.transparent, width: 3),
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(11),
          child: Stack(
            fit: StackFit.expand,
            children: [
              Image.memory(scan.bytes, fit: BoxFit.cover, cacheWidth: 200),
              Align(
                alignment: Alignment.bottomCenter,
                child: Container(
                  width: double.infinity,
                  color: color.withValues(alpha: 0.85),
                  padding: const EdgeInsets.symmetric(vertical: 2),
                  child: Text(notBean ? 'Unusual' : displayName(scan.prediction.label),
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w600)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _MessageCard extends StatelessWidget {
  final IconData icon;
  final String text;
  final Color? color;
  const _MessageCard({super.key, required this.icon, required this.text, this.color});

  @override
  Widget build(BuildContext context) {
    final c = color ?? Theme.of(context).colorScheme.onSurfaceVariant;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Icon(icon, color: c),
          const SizedBox(width: 10),
          Expanded(child: Text(text, style: TextStyle(color: c))),
        ],
      ),
    );
  }
}

class _TipsSheet extends StatelessWidget {
  const _TipsSheet();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    const tips = [
      (Icons.filter_1, 'One green (unroasted) bean per photo, in the center'),
      (Icons.crop_square, 'Plain, light background'),
      (Icons.wb_sunny_outlined, 'Even light, no strong shadows'),
      (Icons.zoom_in, 'Hold the phone close so the bean fills about half the frame'),
    ];
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('For best results', style: theme.textTheme.titleLarge),
            const SizedBox(height: 12),
            for (final (icon, text) in tips)
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: Icon(icon, color: theme.colorScheme.primary),
                title: Text(text),
              ),
            const SizedBox(height: 8),
            Text(
              'KapeKlasipika supports sorting decisions; it does not replace a trained sorter. '
              'It only knows green Arabica beans; anything that looks too different is flagged as '
              '"Unusual or not a bean". Check those by hand.',
              style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurfaceVariant),
            ),
          ],
        ),
      ),
    );
  }
}

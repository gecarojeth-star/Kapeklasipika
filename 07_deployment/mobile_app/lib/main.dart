// main.dart
// ----------
// KapeKlasipika: offline green Arabica coffee bean classifier.
// Two modes, switched with the bottom navigation bar:
//   - Live scan: point the camera at a tray; every bean gets a box, an ID and a label,
//     with counts, estimated weight and camera guidance (lib/live/).
//   - Photo:     one bean per photo, detailed probabilities (lib/photo_page.dart).
// The model and settings are loaded once here and shared by both modes.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'classifier.dart';
import 'live/live_page.dart';
import 'look.dart';
import 'photo_page.dart';
import 'settings.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Portrait only: keeps the camera overlay simple and steady.
  await SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]);
  runApp(const KapeKlasipikaApp());
}

class KapeKlasipikaApp extends StatelessWidget {
  const KapeKlasipikaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'KapeKlasipika',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: kBrand),
        useMaterial3: true,
      ),
      home: const AppShell(),
    );
  }
}

class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  BeanClassifier? _classifier;
  String? _loadError;
  final WeightSettings _weight = WeightSettings();
  int _tab = 0;

  @override
  void initState() {
    super.initState();
    _weight.load();
    BeanClassifier.load().then((c) {
      if (mounted) setState(() => _classifier = c);
    }).catchError((Object e) {
      if (mounted) setState(() => _loadError = 'Could not load the model: $e');
    });
  }

  @override
  void dispose() {
    _classifier?.close();
    _weight.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      // Only the visible page is built, so the live camera is released in photo mode.
      body: _tab == 0
          ? LivePage(key: const ValueKey('live'), classifier: _classifier, weight: _weight)
          : PhotoPage(key: const ValueKey('photo'), classifier: _classifier, loadError: _loadError),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (i) => setState(() => _tab = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.center_focus_weak), selectedIcon: Icon(Icons.center_focus_strong), label: 'Live scan'),
          NavigationDestination(icon: Icon(Icons.photo_outlined), selectedIcon: Icon(Icons.photo), label: 'Photo'),
        ],
      ),
    );
  }
}

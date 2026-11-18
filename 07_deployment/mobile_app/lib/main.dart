// main.dart
// ----------
// KapeKlasipika: offline green Arabica coffee bean classifier.
// One screen: take or upload a photo of ONE bean and see its class (lib/photo_page.dart).
// The model is loaded once here and handed to the photo screen.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'classifier.dart';
import 'look.dart';
import 'photo_page.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
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

/// Loads the model once, then shows the photo screen.
class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  BeanClassifier? _classifier;
  String? _loadError;

  @override
  void initState() {
    super.initState();
    BeanClassifier.load().then((c) {
      if (mounted) setState(() => _classifier = c);
    }).catchError((Object e) {
      if (mounted) setState(() => _loadError = 'Could not load the model: $e');
    });
  }

  @override
  void dispose() {
    _classifier?.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => PhotoPage(classifier: _classifier, loadError: _loadError);
}

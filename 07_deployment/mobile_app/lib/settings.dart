// settings.dart
// --------------
// Weight estimate settings. A camera can't weigh beans, so the app multiplies the number
// of beans by an average weight per bean:
//   - Default: 0.155 g per green Arabica bean, from a 100-bean weight of 15.49 g
//     (Urugo et al., 2024, Beverage Plant Research 4:e021), consistent with 15.2-16.2 g
//     for Indonesian Arabica (Nugroho et al., 2016, Pelita Perkebunan 32(3)).
//   - Calibration: weigh N of YOUR beans on a kitchen scale and enter the total; the app
//     then uses your grams-per-bean instead.

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class WeightSettings extends ChangeNotifier {
  static const double defaultGramsPerBean = 0.155;
  static const String _key = 'grams_per_bean';

  double _gramsPerBean = defaultGramsPerBean;
  double get gramsPerBean => _gramsPerBean;
  bool get isCalibrated => (_gramsPerBean - defaultGramsPerBean).abs() > 1e-9;

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    _gramsPerBean = prefs.getDouble(_key) ?? defaultGramsPerBean;
    notifyListeners();
  }

  Future<void> calibrate({required int beans, required double grams}) async {
    if (beans <= 0 || grams <= 0) return;
    _gramsPerBean = grams / beans;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setDouble(_key, _gramsPerBean);
    notifyListeners();
  }

  Future<void> resetToDefault() async {
    _gramsPerBean = defaultGramsPerBean;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_key);
    notifyListeners();
  }
}

/// Dialog: "I weighed N beans and they weighed X grams".
Future<void> showWeightCalibration(BuildContext context, WeightSettings settings) {
  final beansCtrl = TextEditingController(text: '100');
  final gramsCtrl = TextEditingController();
  return showDialog<void>(
    context: context,
    builder: (context) {
      final theme = Theme.of(context);
      return AlertDialog(
        title: const Text('Weight estimate'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Currently ${settings.gramsPerBean.toStringAsFixed(3)} g per bean '
                  '(${settings.isCalibrated ? 'your calibration' : 'published average'}).'),
              const SizedBox(height: 8),
              Text(
                'Default 0.155 g = average 100-bean weight of green Arabica (Urugo et al., 2024). '
                'For better accuracy, weigh some of your own beans:',
                style: theme.textTheme.bodySmall,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: beansCtrl,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'Number of beans weighed', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: gramsCtrl,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(labelText: 'Their total weight (g)', border: OutlineInputBorder()),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () async {
              await settings.resetToDefault();
              if (context.mounted) Navigator.pop(context);
            },
            child: const Text('Use default'),
          ),
          FilledButton(
            onPressed: () async {
              final n = int.tryParse(beansCtrl.text.trim()) ?? 0;
              final g = double.tryParse(gramsCtrl.text.trim().replaceAll(',', '.')) ?? 0;
              if (n > 0 && g > 0) await settings.calibrate(beans: n, grams: g);
              if (context.mounted) Navigator.pop(context);
            },
            child: const Text('Save'),
          ),
        ],
      );
    },
  );
}

// look.dart
// ----------
// Colors and wording shared by the photo and live screens.

import 'package:flutter/material.dart';

const Color kBrand = Color(0xFF2F4A24); // same deep green as the app icon

/// Below this confidence the photo screen asks the user to retake the photo.
const double kLowConfidence = 0.60;

/// One color per class, so results can be read at a glance.
const Map<String, Color> kClassColors = {
  'defect': Color(0xFFC0392B), // red: remove from the lot
  'premium': Color(0xFF2E7D32), // green: good bean
  'peaberry': Color(0xFFB7791F), // amber
  'longberry': Color(0xFF3B6EA8), // blue
};

const Color kNotBeanColor = Color(0xFF7E57C2); // purple: unusual or not a coffee bean
const Color kTouchingColor = Color(0xFFEF6C00); // orange: beans touching
const Color kAnalyzingColor = Color(0xFFFFFFFF); // white: not classified yet

const Map<String, String> kClassDescriptions = {
  'peaberry': 'Single rounded bean that forms when only one seed develops in the cherry.',
  'longberry': 'Elongated bean shape.',
  'premium': 'Normal, well-formed bean with no visible defects.',
  'defect': 'Visible defect such as broken, black, or insect-damaged. Remove from the lot.',
};

Color classColor(String label) => kClassColors[label] ?? kBrand;

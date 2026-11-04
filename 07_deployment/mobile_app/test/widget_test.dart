import 'package:flutter_test/flutter_test.dart';
import 'package:kapeklasipika_app/classifier.dart';

void main() {
  test('displayName capitalizes class labels', () {
    expect(displayName('peaberry'), 'Peaberry');
    expect(displayName('defect'), 'Defect');
  });
}

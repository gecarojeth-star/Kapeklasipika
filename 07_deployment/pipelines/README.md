# Deployment pipeline

1. **Notebook 04** writes the name of the best model (chosen on validation) to
   `06_evaluation/metrics/best_model.txt`.
2. **Notebook 05** converts that model to `05_modeling/models/kapeklasipika.tflite` (float16)
   plus `labels.txt`, checks it against the Keras model and copies both into
   `07_deployment/mobile_app/assets/`.
3. **Notebook 06** rebuilds the phone model with a second output, the not-a-bean ratio (above 1.0
   means "not a coffee bean or unclear"), and overwrites the asset. The single-output version is
   kept as `kapeklasipika_v1.tflite`.

## Phone model contract
- Input: 1 x 224 x 224 x 3, float32, raw RGB pixels 0-255 (centre-cropped square).
- Output 1: 4 probabilities in the order `defect, longberry, peaberry, premium`.
- Output 2: anomaly ratio (squared Mahalanobis distance / threshold).

## Android app notes (from `android/app/build.gradle.kts`)
- `minSdk = 26` → Android 8.0 and later. ✅ Matches the paper.
- `applicationId = com.example.kapeklasipika_app`: fine for a school demo, but it must be changed
  before publishing (the Play Store rejects `com.example`).
- Release builds are signed with the debug key: fine for demos, not for publishing.

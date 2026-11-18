# KapeKlasipika

An offline Android app that looks at a photo of **one green (unroasted) Arabica coffee bean**
and says whether it is **Defect, Longberry, Peaberry or Premium**. Behind it is a data mining
project that follows **CRISP-DM**, a standard six-step recipe for data projects: business
understanding → data understanding → data preparation → modeling → evaluation → deployment.

> Personal details (authors, school, contact) are intentionally left out of these files for now.

## Project status (updated 2026-11-04)

| CRISP-DM phase | Status | Where |
|---|---|---|
| 1. Business understanding | Drafted | `01_business_understanding/` |
| 2. Data understanding | Analysis done (notebook 01); write-up pending | `03_exploration/` |
| 3. Data preparation | Done (notebook 02); write-up pending | `04_preparation/`, `02_data/interim/` |
| 4. Modeling | Done (notebooks 03, 03b, 06) | `05_modeling/` |
| 5. Evaluation | Done on dataset (notebook 04); **real phone photos still missing** | `06_evaluation/` |
| 6. Deployment | TFLite model in the Flutter app (notebooks 05, 06) | `07_deployment/` |

## Results so far (USK-Coffee test set, 1,599 images)

| Item | Result | Target |
|---|---|---|
| Test accuracy | 85.43% | > 81.31% (published benchmark) ✅ |
| Macro F1 | 0.852 | ≥ 0.85 ✅ |
| Defect recall | 0.833 | ≥ 0.90 ❌ |
| Phone model size | 4.69 MB | < 15 MB ✅ |
| Accuracy on real phone photos | not measured yet | — |

Full details: `01_business_understanding/success_metrics.md`.

## How the folders are organised

```
00_admin/                    charter, decision log, meeting notes
01_business_understanding/   problem, success metrics, assumptions and risks
02_data/
  raw/usk_coffee/            original dataset - NEVER edited
  external/<class>/          your own phone photos of REAL beans (test only)
  external_non_beans/        phone photos of non-bean objects (test only)
  interim/                   inventory, duplicate checks, exclusion list (made by notebooks)
  processed/                 reserved; images are prepared on the fly, so it stays empty
  data_dictionary.md
03_exploration/              EDA notebooks (01) and findings.md
04_preparation/              notes on cleaning (02) and augmentation
05_modeling/                 modeling notebooks (03, 03b, 06), saved models, experiments_log.md
06_evaluation/               metrics files and validation_report.md
07_deployment/               export notes (pipelines/) and the Flutter app (mobile_app/)
src/                         shared Python code used by every notebook
tests/                       quick automatic checks of src/ (run: python -m pytest tests)
reports/                     figures for the paper and final_report.md
config/config.yaml           every setting in one place (seed, image size, epochs, paths)
```

## How to run (Google Colab, Runtime → T4 GPU)

Run the notebooks in this order. Each one starts with the same SETUP cell.

1. `01_data_understanding` - inventory, class balance, image quality, colour statistics
2. `02_data_preparation` - duplicate and leakage checks, exclusion list, augmentation preview
3. `03_modeling` - baseline CNN, MobileNetV2 frozen, MobileNetV2 fine-tuned
4. `03b_extended_finetuning` - continues fine-tuning (this is the model the app uses)
5. `04_evaluation` - picks the best model on validation, then tests it once
6. `05_export_tflite` - converts to TensorFlow Lite for the phone
7. `06_not_a_bean_detector` - adds the "is this even a bean?" check to the phone model

Suggested (optional) tidy-up: keep 01-02 in `03_exploration/notebooks/` and 03-06 in
`05_modeling/notebooks/`. Moving them is safe: in Colab the SETUP cell uses the fixed Drive
path, and on a laptop it searches upward for `config/config.yaml`.

## Scope

**In:** single-bean classification from an uploaded photo or a photo taken in the app; offline
on Android 8.0+; a "not a coffee bean" check.
**Out:** YOLO / webcam object detection, live multi-bean scanning (removed from the app),
saving a history to storage (recent scans exist only while the app is open), roasted beans,
splitting Defect into defect types.

## Glossary (plain language)

- **Transfer learning:** start from a network already trained on millions of everyday photos
  (ImageNet) and teach it the new task, instead of starting from zero.
- **Fine-tuning:** after the new last layer is trained, let the top layers of the pretrained
  network adjust slightly, with a very small learning rate.
- **Epoch:** one full pass over all training images.
- **Training / validation / test set:** the model learns from training images, we choose
  settings with validation images, and we measure the final score once on test images.
- **Precision:** of the beans the model called X, how many really were X.
- **Recall:** of the beans that really were X, how many the model found.
- **F1-score:** one number that balances precision and recall; **macro** = averaged over classes.
- **Confusion matrix:** table of true class vs predicted class; off-diagonal cells are mistakes.
- **Data leakage:** when test images (or near copies) also appear in training, inflating scores.
- **Data augmentation:** randomly rotating, flipping, zooming and re-lighting training images
  so the model learns the bean, not the exact photo.
- **TensorFlow Lite (TFLite):** the small model format that runs on phones.
- **Float16 quantization:** storing weights as 16-bit numbers to halve the file size.
- **Anomaly / out-of-distribution detection:** recognising inputs unlike anything in training
  (for example a coin).
- **Domain shift:** when the photos the app sees in real use differ from the training photos
  (camera, light, background, printing), so accuracy drops.

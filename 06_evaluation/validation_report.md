# Validation Report (notebook 04, 2026-10-22)

**Final model:** `mobilenetv2_finetuned_long` (experiment 3), chosen by highest validation
accuracy (86.56%) *before* the test set was used.
**Test set:** 1,599 images (USK-Coffee test split after removing 17 exact copies and 1 image
duplicated from training).

## 1. Test results
| Model | Accuracy | Macro F1 | Defect recall | Beats 81.31%? |
|---|---|---|---|---|
| Febriana et al. 2022, ResNet-18 | 81.31% | – | – | (benchmark) |
| Baseline CNN | 67.29% | 0.587 | 0.730 | No |
| MobileNetV2, frozen | 75.30% | 0.752 | 0.655 | No |
| MobileNetV2, fine-tuned (exp. 2) | 85.93% | 0.859 | 0.813 | Yes |
| **MobileNetV2, extended (exp. 3, selected)** | **85.43%** | **0.852** | **0.833** | **Yes** |

95% confidence interval for 85.43% on 1,599 images: about 83.7%–87.2%. The lower end is still
above 81.31%, so the improvement is not a fluke of this particular test set. Exp. 2 vs exp. 3
differ by 0.5 points, well inside that interval: statistically the same.

## 2. Success criteria (from the proposal)
| Criterion | Result | Met? |
|---|---|---|
| Test accuracy > 81.31% | 85.43% | Yes |
| Macro F1 ≥ 0.85 | 0.852 | Yes (just) |
| Defect recall ≥ 0.90 | 0.833 | **No** |
| TFLite size < 15 MB | 4.53 MB | Yes |

## 3. Per-class results (selected model)
| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| Defect | 0.822 | 0.833 | 0.827 | 400 |
| Longberry | 0.873 | 0.928 | 0.899 | 400 |
| Peaberry | 0.842 | 0.932 | 0.885 | 399 |
| Premium | 0.887 | 0.725 | 0.798 | 400 |

## 4. Weak spots (233 mistakes of 1,599)
- **Premium is the weakest class (72.5% recall).** Its 110 errors: 49 → Defect, 34 → Peaberry,
  27 → Longberry.
- **67 Defect beans missed:** 26 → Peaberry, 23 → Longberry, 18 → Premium.
- The most confident mistakes include "Premium" beans with visible cracks, chipped edges and
  blemishes (predicted Defect at 99–100%) and "Defect" beans whose flaw is small. The
  Premium/Defect boundary appears partly ambiguous in the labels themselves.

## 5. Overfitting
Train–validation gap 3.5 points (selected model) vs 17.5 points in the original paper.
Curves: `reports/figures/03b_history_mobilenetv2_full.png`.

## 6. On-device model (notebook 05)
- `kapeklasipika.tflite`, float16: **4.53 MB**.
- Agrees with the Keras model on 99.4% of the first 160 test images (differences = rounding
  on borderline cases).
- Full test accuracy of the .tflite file: **85.62%** on 1,599 images (Keras: 85.43%).

## 6b. Real-world photos
Not collected. All results are on USK-Coffee images only (see section 7).

## 7. What these results do and do not prove
- **Do:** on USK-Coffee images, MobileNetV2 transfer learning classifies the four classes
  better than the published ResNet-18 result, with far less overfitting.
- **Do not:** show performance on phone photos or Philippine beans (no field test was done),
  or that the app can replace a trained sorter. Defect recall of 83% means roughly 1 in 6
  defective beans would still be missed, so the app is a second opinion, not a gatekeeper.

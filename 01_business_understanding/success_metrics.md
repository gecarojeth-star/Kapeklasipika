# Success metrics

How we decide whether the project worked. Each metric says **when it was set**. Targets set
*before* training are the honest yardstick; targets added *after* seeing results are marked as
such, because setting a target once you already know the answer is not a real test.

Results are from the USK-Coffee test set (1,599 images after cleaning), for the model chosen on
the validation set (`mobilenetv2_finetuned_long`). "95% CI" (confidence interval) is the range
the true value probably lies in, given that the test set is a sample of limited size.

## Model metrics

| Metric | Plain meaning | Target | Set | Result | Status | Source |
|---|---|---|---|---|---|---|
| Test accuracy | Share of all test beans classified correctly | > 81.31% | Before training | **85.43%** (95% CI about 83.7-87.2%) | ✅ Met | `test_comparison.csv` |
| Macro F1 | Balance of precision and recall, averaged over the 4 classes | ≥ 0.85 | Before training | **0.852** | ✅ Met (barely) | `test_report_mobilenetv2_finetuned_long.json` |
| Defect recall | Share of truly defective beans the model catches | ≥ 0.90 | Before training | **0.833** (333 of 400; 95% CI about 0.80-0.87) | ❌ Not met | same |
| Train-validation gap | Train accuracy minus validation accuracy; large = overfitting | Much smaller than the original paper's 17.5 points | Before training | **3.5 points** (90.08% vs 86.56%) | ✅ Met | `val_summary.csv` |

## Deployment metrics

| Metric | Target | Set | Result | Status |
|---|---|---|---|---|
| Phone model size | < 15 MB | Before training | 4.69 MB (float16, includes the not-a-bean output) | ✅ Met |
| TFLite agrees with the Keras model | ≈ 100% | Before training | 99.4% on the first 160 test images; TFLite test accuracy 85.62% | ⚠️ Re-check on all 1,599 images |
| Time per prediction on a phone | Report it (suggest < 1 s) | After results | First readings on one phone: 0.47 s (upload), 1.07-1.45 s (camera photo) | ⚠️ Preliminary: measure 20+ photos per source and record the phone model |
| Runs offline on Android 8.0+ | Yes | Before training | `minSdk = 26` (= Android 8.0) in build.gradle.kts | ✅ Confirmed in code; test on a device |

## Not-a-bean check (added after the coin problem, so all targets here are post-hoc)

| Metric | Result | Note |
|---|---|---|
| Real test beans wrongly flagged | 3.2% | Expected about 2.5% by design |
| Non-bean images correctly flagged | 83% flowers, 87% CIFAR-10, 86% synthetic coins | AUROC about 0.98 for all three (1.0 = perfect separation) |
| **Defect beans wrongly flagged** | **12% (48 of 400)** | 48 of the 51 flagged test beans were Defect. Works against Q2; see proposal P02 in the decision log |

## Real-world metric (Q4)

| Metric | Target | Result |
|---|---|---|
| Accuracy and Defect recall on real phone photos | No pass/fail target: report it with its confidence interval and compare with the test set | ⏳ No photos yet |

A fixed target would be misleading because the real-world set will be small (with 200 photos,
the uncertainty is still about ±6 points).

# Assumptions and risks

## Assumptions (things we take as true; if one fails, results may not hold)
1. USK-Coffee labels are correct. *Doubtful for a few images:* some "Premium" beans in the
   misclassified examples show cracks or chipped skin.
2. One photo of one side is enough to judge a bean. A flaw on the hidden side cannot be seen.
3. Users photograph a single bean on a plain, light background, roughly like the dataset.
4. Local beans are Arabica and fit the same four categories.
5. The four classes are equally common (true in the dataset). In a real lot most beans are
   probably Premium, which changes how often each mistake happens in practice.

## Risk register

| # | Risk | Likelihood | Impact | Evidence so far | Mitigation | Status |
|---|---|---|---|---|---|---|
| R1 | **Domain shift:** phone photos differ from dataset photos (camera, light, background, distance) | High | High | Photos of printed dataset images were called Defect | Collect real bean photos with a fixed protocol (`02_data/external/README.md`); report the drop honestly; consider adding blur, noise, colour and JPEG augmentation and retraining | **Observed** |
| R2 | Defect recall below target | Happened | High | 0.833 vs 0.90 | Tune a Defect threshold on validation (P03); report as not met if still short | Open |
| R3 | Not-a-bean check rejects real defective beans | Happened | Medium-High | 12% of Defect test beans flagged | Show "check by hand" instead of rejecting (P02), or use a separate spread per class | Open |
| R4 | Real-world test set too small to trust | High | Medium | No photos yet | Aim for ≥ 50 per class; always report confidence intervals | Open |
| R5 | Local beans are not Arabica (most Philippine coffee is Robusta or Liberica) | Medium | High | - | Confirm variety with the seller; record it per photo | Open |
| R6 | Label noise in the dataset or our own labels | Medium | Medium | Some Premium beans look damaged | Two people label independently; report their agreement; mention it in the paper | Open |
| R7 | Results cannot be exactly reproduced | Medium | Low | GPU training is not perfectly deterministic; notebook 03 ran before the cleaning fix (4,804 training images) | Fixed seed and settings in config.yaml; note the 4,804 in the paper or re-run | Known |
| R8 | Benchmark not exactly comparable | Low | Low | Our test set is cleaned (1,599 vs the authors' set) | State it in the paper | Known |
| R11 | App crashes when taking photos | Happened | High | Reported by team, 2026-11-04 | Fixes in D20; retest on the phones you will demo with | Fix delivered, needs testing |
| R9 | Tool deprecation: `tf.lite.Interpreter` is scheduled for removal | Medium | Low | Warning in notebooks 05 and 06 | Keep TensorFlow pinned at 2.21.0 (requirements.txt) | Known |
| R10 | Users trust the app too much | Medium | Medium | - | Show confidence and all four probabilities; ask for a retake below 60% (confirmed: `kLowConfidence = 0.60` in `look.dart`); describe it as decision support | Designed in |

## Privacy and ethics
- **USK-Coffee** contains only bean photos: no people, faces, names or IDs.
- **Own phone photos:** keep people, hands and faces out of the frame. Phone photos can carry
  GPS location in their hidden metadata (EXIF), so strip it before sharing photos or the dataset.
- **App:** runs offline and keeps no history, so no user data is collected or sent.
- **Fair use:** cite the USK-Coffee authors; check the dataset's licence before redistributing images.

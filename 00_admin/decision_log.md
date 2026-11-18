# Decision log

Every important choice, why it was made, and what else was considered. When someone asks
"why did you do X?", the answer should be here.

Entries D01-D15 were made before 2026-11-04 and are back-filled from the notebooks and the draft
paper; later entries are dated when made.

| ID | Decision | Why | Alternatives considered | Evidence |
|---|---|---|---|---|
| D01 | Follow CRISP-DM | Standard, well-known structure; matches the course | Ad-hoc workflow | - |
| D02 | Keep the dataset authors' train/val/test split | Lets us compare fairly with their 81.31% test accuracy | Re-splitting randomly | config.yaml |
| D03 | Exclude problem files through a list instead of deleting them | Raw data stays untouched; anyone can re-run and get the same result | Deleting files | notebook 02, `excluded_files.csv` |
| D04 | Confirm hash-flagged near duplicates with a pixel check | The hash flagged 184 pairs, 95 with different labels, which were clearly different beans; pixel check confirmed only 1 | Trusting the hash alone (would wrongly drop ~180 images) | notebook 02 |
| D05 | Centre-crop to a square and resize to 224 x 224 | MobileNetV2's native size; cropping avoids stretching beans | Resizing without cropping | src/data_loading.py |
| D06 | Augment with flips, rotation up to 180°, zoom ±15%, brightness and contrast ±20% | A bean has no "up"; mimics different phone distances and light; fights the overfitting seen in the original paper | No augmentation | src/features.py |
| D07 | Train a small CNN from scratch as a baseline | Shows how much the pretrained network actually adds | No baseline | notebook 03 |
| D08 | Use MobileNetV2 transfer learning | Built for phones (about 2.3 M parameters), 4.7 MB after conversion; also tested by the dataset authors | ResNet-18 (larger), EfficientNet | notebook 03 |
| D09 | Fine-tune the last 40 layers with a 100x smaller learning rate, BatchNorm frozen | Adapts high-level features to beans without destroying pretrained ones; standard for small datasets | Fine-tuning everything | src/models.py |
| D10 | Run an extended fine-tuning (up to 20 more epochs) | Validation loss was still at its lowest on the last epoch of notebook 03 | Stopping at 15 epochs | notebook 03b |
| D11 | Choose the final model on validation accuracy only | Choosing on test would make the test score optimistic. The chosen model (finetuned_long) scored 85.43% on test, the shorter one 85.93%; the 0.5-point gap (8 images) is within noise | Picking the best test score | notebook 04 |
| D12 | Export to TFLite with float16 weights | Halves the size; TFLite accuracy 85.62% vs Keras 85.43% | float32 (about 9 MB) | notebooks 05, 06 |
| D13 | Add a Mahalanobis-distance "not a bean" detector; threshold keeps 97.5% of validation beans | A coin was labelled Defect at 100% confidence; confidence alone cannot catch unknown objects | Confidence threshold only; a separate "other" class (needs many non-bean photos) | notebook 06 |
| D14 | ~~App keeps no classification history~~ **Changed 2026-11-04:** the app shows up to 12 recent scans with a Clear button; they live in memory only and disappear when the app closes | Lets a sorter compare a few beans; nothing is stored on the phone or sent anywhere | No history (original spec); saving history to storage | team, `photo_page.dart` |
| D15 | Local beans are labelled by the team with a written grading standard | Consistent labels that others can check | Labelling by eye without a standard | spec |
| D16 | 2026-11-04: No YOLO; the app only classifies an uploaded or newly taken photo | Team decision; keeps scope realistic. `src/live_detector.py` and the app's live scanner are out of scope | Web YOLO + webcam tool; live scanner | team |
| D17 | 2026-11-04: Merge the CRISP-DM folder structure into the existing project; never move or overwrite files | Notebooks keep working; nothing is lost | Starting a fresh folder | team |
| D18 | 2026-11-04: Leave personal details out of documents until the end | Team request | - | team |
| D19 | 2026-11-04: Remove the Live scan mode completely (screens, `lib/live/`, weight estimate, `camera` and `shared_preferences` packages) | Focus on upload / take photo; fewer parts that can break; the camera package was a likely source of crashes | Hiding the tab only | team |
| D20 | 2026-11-04: Camera crash fixes: double-tap guard, error messages instead of silent failures, recovery of a photo when Android closes the app, safety downscale of huge images | The app crashed sometimes when taking a photo | - | `photo_page.dart`, `classifier.dart` |

## Proposed, waiting for team approval

| ID | Proposal | Why |
|---|---|---|
| P01 | *Status: in development until physical beans are available.* Do not use photos of **printed** dataset images as real-world evidence | Printing and re-photographing adds ink dots, colour shifts, paper texture and glare that real beans do not have; the app called such photos Defect. See `00_admin/meeting_notes/2026-11-04_project_review.md` |
| P02 | ✅ *Already done in the app:* flagged photos show "Unusual or not a bean ... Check it by hand" with the class bars. When the "not a bean" check fires, show "unclear, check by hand" instead of rejecting | 48 of the 51 test beans it flagged were real Defect beans (12% of all Defect beans) |
| P03 | Tune a Defect decision threshold on the validation set | Could raise Defect recall toward 0.90 without retraining; cost: more Premium beans flagged |
| P04 | Add `extended_epochs: 20` to config.yaml | Notebook 03b currently hard-codes the 20 |

## Open questions
- Where the real green Arabica beans will come from, and confirming they are Arabica.

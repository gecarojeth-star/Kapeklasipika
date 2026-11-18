"""
setup_project.py - adds the CRISP-DM folder structure and starter documents to the EXISTING
KapeKlasipika project.

Safe by design:
- It only CREATES folders and files that are missing.
- It never deletes, moves or overwrites anything. If a file with the same name already exists
  and differs, the new version is saved under 00_admin/_setup_suggestions/ for you to compare.
- Running it twice changes nothing the second time.

In Google Colab (after mounting Drive), upload this file to the project folder and run:
    !python /content/drive/MyDrive/kapeklasipika/setup_project.py --dry-run   # preview only
    !python /content/drive/MyDrive/kapeklasipika/setup_project.py             # do it
On a laptop, run it from anywhere inside the project:  python setup_project.py
You can also pass the project folder explicitly:       python setup_project.py --project PATH
"""

import argparse
from pathlib import Path

# Folders of the CRISP-DM layout. YOLO, webcam and dashboard folders are left out on purpose
# (decision D16: the app only classifies an uploaded or newly taken photo).
FOLDERS = [
    "00_admin/meeting_notes",
    "01_business_understanding",
    "02_data/raw",
    "02_data/external/defect",
    "02_data/external/longberry",
    "02_data/external/peaberry",
    "02_data/external/premium",
    "02_data/external_non_beans",
    "02_data/interim",
    "02_data/processed",
    "03_exploration/notebooks",
    "04_preparation/cleaning",
    "04_preparation/features",
    "05_modeling/notebooks",
    "05_modeling/models",
    "06_evaluation/metrics",
    "07_deployment/pipelines",
    "src",
    "tests",
    "reports/figures",
    "config",
]

FILES = {
    '.gitignore': r'''# --- Data (large, or the dataset authors' property; download it instead of committing) ---
02_data/raw/
02_data/external/**/*.jpg
02_data/external/**/*.jpeg
02_data/external/**/*.png
02_data/external_non_beans/

# --- Trained models (large; keep them in Drive) ---
05_modeling/models/*.keras
05_modeling/models/*.h5

# --- Python / Jupyter ---
__pycache__/
*.pyc
.ipynb_checkpoints/
.pytest_cache/
.venv/
venv/

# --- Flutter / Android build output and secrets ---
07_deployment/mobile_app/build/
07_deployment/mobile_app/.dart_tool/
07_deployment/mobile_app/.flutter-plugins*
07_deployment/mobile_app/android/.gradle/
07_deployment/mobile_app/android/local.properties
*.jks
*.keystore
key.properties

# --- OS / editor clutter ---
.DS_Store
Thumbs.db
.vscode/
.idea/
.env
''',
    '00_admin/decision_log.md': r'''# Decision log

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
''',
    '00_admin/meeting_notes/2026-11-04_project_review.md': r'''# 2026-11-04: Project review with Claude

## Discussed
- Reviewed notebooks 01-06, the src/ code, config.yaml, the Android build file and paper draft 2.
- Results on the dataset: test accuracy 85.43%, macro F1 0.852, Defect recall 0.833 (target 0.90
  not met), phone model 4.69 MB.
- The not-a-bean detector rejects non-bean images well (83-87% of flowers, CIFAR-10 images and
  synthetic coins), but most of the real beans it flags are Defect beans.
- Android minimum version is SDK 26 = Android 8.0, which matches the paper.
- **Printed-photo test.** Dataset images were printed and photographed with the phone. The app
  called them Defect, while uploading the same original files gave the correct class. Non-bean
  objects were still rejected correctly.

## Why the printed photos fail (summary)
The model only ever saw clean digital photos from one camera. A photo of a print changes
exactly the things it uses to judge beans:
1. **Colour and brightness:** printer ink and paper shift and darken colours; dataset backgrounds
   are very bright (average brightness about 206-212 out of 255).
2. **Texture:** printers build images from tiny ink dots, and paper has grain. Up close this looks
   like a rough, spotted surface, which is what Defect beans look like.
3. **Glare and blur:** shiny paper reflects light; re-photographing softens edges.
4. **Size in the frame:** dataset beans fill roughly half the picture. If the phone photo shows
   the whole page, the bean becomes a small blob after resizing to 224 x 224.
Defect is the class with the most visual variety, so "strange-looking bean" tends to land there.
This is a **domain shift** problem, not a bug in the app.

## Decided
- No YOLO; upload / take-photo only (D16).
- Merge the new structure into the existing folder (D17).
- No personal details in documents for now (D18).
- Remove Live scan completely (D19); keep Recent scans with a Clear button (D14 changed).
- P01 stays in development until physical beans are available.

## Action items
| What | Who | By when |
|---|---|---|
| Buy or borrow real green Arabica beans; follow `02_data/external/README.md` | Team | TBD |
| Send 2-3 pairs (original dataset file + phone photo of its print), plus `kapeklasipika.tflite`, so the exact app input can be analysed | Team | Next session |
| Run `setup_project.py` in Colab (dry run first) | Team | Next session |
| Review Stage 1-2 documents | Team | Next session |
| Install the updated app (`flutter clean`, `flutter pub get`, `flutter analyze`, `flutter run`) and retest taking photos | Team | Next session |
''',
    '00_admin/meeting_notes/_template.md': r'''# Meeting YYYY-MM-DD: <topic>

**Present:** (roles only for now)

## Discussed
-

## Decided (copy each one into decision_log.md)
-

## Action items
| What | Who | By when |
|---|---|---|
| | | |
''',
    '00_admin/project_charter.md': r'''# Project charter: KapeKlasipika

*Draft, 2026-11-04. Team names, school and adviser are left out on purpose and will be added
near the end of the project.*

## Purpose
Give coffee sorters a consistent, phone-based second opinion on the category of a single green
Arabica coffee bean, without needing internet or special hardware.

## Deliverables
1. A trained image classifier (MobileNetV2 transfer learning) and its evaluation.
2. An offline Android app (Flutter): upload a photo or take one, get the class, the confidence
   and all four probabilities, and a warning when the photo does not look like a coffee bean.
3. An IEEE-format paper and the supporting documents in this folder.

## Scope
| In scope | Out of scope (decided) |
|---|---|
| Four classes: Defect, Longberry, Peaberry, Premium | YOLO or webcam object detection |
| One bean per photo, uploaded or taken in the app | Live multi-bean scanning (removed) |
| Offline inference on Android 8.0+ | Saving a history to storage (recent scans stay in memory only, with a Clear button) |
| "Not a coffee bean" warning | Roasted beans; naming the specific defect type |
| Test on phone photos of real local beans | Replacing trained human sorters |

## Data
- **USK-Coffee** (public): single green Arabica beans photographed in Banda Aceh, Indonesia,
  pre-split into train / validation / test.
- **Own phone photos** of real green beans, used for testing only (not collected yet).

## Method
CRISP-DM, all experiments in Google Colab (T4 GPU) with TensorFlow/Keras; settings in
`config/config.yaml`; every decision recorded in `00_admin/decision_log.md`.

## Milestones
| Milestone | Status |
|---|---|
| Models trained and evaluated on the dataset | Done |
| Phone model exported, app runs it | Done |
| Project documents organised (this structure) | In progress |
| Real phone photos collected and labelled | **Not started** |
| Real-world evaluation | Waiting for photos |
| Paper final draft | In progress; deadline to be added |
''',
    '01_business_understanding/assumptions_risks.md': r'''# Assumptions and risks

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
''',
    '01_business_understanding/problem_statement.md': r'''# Problem statement

## Background
Before roasting, green coffee beans are sorted by shape, size and visible defects, because a
lot's grade (and price) depends on it. On many small farms and processing centres this is still
done by eye. Hand sorting is slow and tiring, and results vary from one sorter to another and
with fatigue, so defective beans can slip into a lot and lower its grade.

## The problem in plain words
Sorters need a quick, consistent second opinion on what kind of bean they are holding, using
something they already own (a phone), without depending on internet access.

## Who it is for
- **Primary users:** green-coffee sorters and small processors.
- **Other readers:** the course instructor and panel, who judge whether the method is sound.

## Business objective
Build an offline Android app that classifies a photo of one green Arabica bean as Defect,
Longberry, Peaberry or Premium, accurately enough to be a useful sorting aid. It supports a
sorter; it does not replace one.

## Data mining questions

| # | Question | Problem type | Why this type |
|---|---|---|---|
| Q1 | Can a MobileNetV2 transfer-learning model classify a single-bean photo into the four classes with test accuracy above the 81.31% reported by the dataset's authors? | **Multi-class classification** (supervised) | Every training image already has one of four known labels; we learn to predict that label for new images. |
| Q2 | How reliably does the model catch Defect beans (target recall ≥ 0.90), which classes does it confuse, and can a Defect decision threshold improve recall at an acceptable cost? | **Cost-sensitive classification** + error analysis | Mistakes do not cost the same: a missed Defect bean lowers the lot's grade, while a good bean set aside by mistake only costs a second look. So we weight Defect recall above plain accuracy. |
| Q3 | Can the app tell when a photo is not a coffee bean at all, while still accepting real beans? | **Anomaly (out-of-distribution) detection** | We cannot collect examples of "everything that is not a bean", so instead we model what normal beans look like and flag whatever is too far from that. |
| Q4 | How much does performance drop on phone photos of real local beans compared with the dataset? | **Generalisation test** of the Q1 classifier (evaluation, not a new model) | The dataset comes from one camera setup in Indonesia; this measures whether the results hold in real use. **Blocked until real photos exist.** |

## What a good answer looks like
See `success_metrics.md` for the numbers and their current status.

## What this project will not claim
- That the app can replace trained sorters.
- That results on USK-Coffee images hold for other varieties, cameras or lighting, unless Q4
  shows it.
- That it can name the specific defect type (the dataset has one Defect label).
''',
    '01_business_understanding/success_metrics.md': r'''# Success metrics

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
''',
    '02_data/data_dictionary.md': r'''# Data dictionary

*To be written in Stage 3 (data understanding).* For each data file and table it will list:
column name, meaning, type, example values and possible issues. Planned entries:

- `02_data/raw/usk_coffee/` folder layout (split / class / image)
- `02_data/interim/inventory.csv` (one row per image, made by notebook 01)
- `02_data/interim/color_stats.csv`
- `02_data/interim/exact_duplicates.csv`, `near_duplicates.csv`, `near_duplicates_checked.csv`
- `02_data/interim/excluded_files.csv`
- `02_data/external/labels.csv` (real-world photos)
- `06_evaluation/metrics/*` (history logs, reports, comparison tables)
''',
    '02_data/external/README.md': r'''# Real-world test photos: collection protocol

These photos answer data mining question Q4: does the model still work on real phone photos?
They are used **only for testing**, never for training.

## Rule 1: real beans only
Do **not** photograph printed pictures or screens. Prints add ink dots, paper grain, colour
shifts and glare; screens add moiré stripes and glow. The model reads those as bean texture, so
results say nothing about real use. This already happened once: printed dataset images were
classified as Defect.

## Where the files go
```
02_data/external/
  defect/      longberry/      peaberry/      premium/
  labels.csv
```
Notebook 04 reads the class from the folder name.

## How to take each photo (match the dataset as closely as possible)
1. One bean per photo, centred, filling **about half** of the frame. Do not photograph the
   bean from far away and rely on cropping later.
2. Plain, matte, white or very light background (bond paper works). No patterns or shadows from
   your hand.
3. Soft daylight near a window, or an evenly lit room. **No flash.**
4. Hold the phone parallel to the table and tap to focus on the bean. No digital zoom.
5. Use the normal camera app at default settings (no filters, no beauty mode, no HDR if possible).
6. If you photograph both sides of a bean, give both files the same bean ID, so the analysis
   counts the bean once.

## How many
Aim for **at least 50 beans per class (200 in total)**. With about 100 photos, the accuracy
estimate is still uncertain by roughly ±9 percentage points.

## Labelling
1. Use the team's written grading standard; save a copy in `00_admin/`.
2. Two team members label every bean **independently**, without seeing each other's answers.
3. Write both labels into `labels.csv`. Settle disagreements together and record the final
   label. The agreement rate (or Cohen's kappa, an agreement score that corrects for lucky
   guesses) goes in the paper.

`labels.csv` columns:

| column | example | meaning |
|---|---|---|
| file_name | `bean_017_a.jpg` | photo file |
| bean_id | `017` | same bean = same ID |
| label_1 | `premium` | first labeller |
| label_2 | `longberry` | second labeller |
| final_label | `premium` | agreed label (must match the folder) |
| source_place | `province / market` | where the beans came from (no seller names) |
| variety | `Arabica` | as stated by the seller |
| phone_model | `brand model` | camera used |
| notes | `slight shadow` | anything unusual |

## Privacy
No people, faces or hands in the frame. Remove GPS location from the photos (most phones can
turn location tagging off in the camera settings) before sharing them.

## Optional: non-bean photos
Photos of coins, rice, corn kernels, pebbles, peanuts or roasted coffee beans, taken the same
way, go in `02_data/external_non_beans/` (no subfolders). Notebook 06 uses them to test the
"not a bean" check on realistic objects.
''',
    '03_exploration/findings.md': r'''# Data understanding findings

*To be written in Stage 3 from notebook 01 and 02 outputs:* dataset size and balance, file
quality, what each class looks like, colour and brightness per class, duplicates and leakage,
surprising patterns and data quality problems, and the privacy check.
''',
    '04_preparation/cleaning/README.md': r'''# Cleaning

Cleaning happens in **notebook 02** with functions from `src/preprocessing.py`. Raw images are
never changed; problem files are listed in `02_data/interim/excluded_files.csv`, and every later
notebook skips them automatically (`src/data_loading.py`, `clean_split_files`).

Rules:
1. Byte-identical copies in the same split and class: keep one, exclude the rest.
2. The same photo in two splits: exclude the copy in the later split (val or test), so the model
   is never tested on an image it trained on.
3. Copies with conflicting labels: exclude all of them, because the label cannot be trusted.

The full write-up (with numbers) comes in Stage 3 (data preparation).
''',
    '04_preparation/features/README.md': r'''# Features

A CNN learns its own features (edges, curves, shape, surface texture) from the pixels, so there
is no hand-made feature table such as "bean length" or "roundness".

What we do control:
- **Input preparation** (`src/data_loading.py`): centre-crop to a square, resize to 224 x 224;
  the model itself rescales pixels to -1...1, so the phone app passes raw pixels.
- **Data augmentation** (`src/features.py`), during training only: random flips, rotation up to
  180°, zoom ±15%, brightness ±20%, contrast ±20%.
- **Deep features for the not-a-bean check** (`src/ood.py`): the 1,280 numbers MobileNetV2
  produces just before its last layer, compressed to 64 with PCA (principal component analysis,
  which keeps the main directions of variation).
''',
    '05_modeling/experiments_log.md': r'''# Experiments log

*To be written in Stage 4 (modeling):* one entry per experiment (baseline CNN, MobileNetV2
frozen, fine-tuned, extended fine-tuning, not-a-bean detector) with its settings, epochs run,
best epoch, training time, validation results and what we learned.
''',
    '06_evaluation/validation_report.md': r'''# Validation report

*To be written in Stage 5 (evaluation):* test results for every model, the success-criteria
check, confusion matrices, error analysis, the not-a-bean results, the real-world photo test
(once photos exist), and what the results do and do not prove.
''',
    '07_deployment/pipelines/README.md': r'''# Deployment pipeline

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
''',
    'README.md': r'''# KapeKlasipika

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
''',
    'reports/final_report.md': r'''# Final report

*Assembled in Stage 6 from the documents in this project:* summary, CRISP-DM walkthrough,
results, limitations and next steps. The IEEE paper is written separately and uses the same numbers.
''',
    'requirements.txt': r'''# Python packages used by the notebooks and src/.
# TensorFlow is pinned to the version the reported results were produced with (Colab, Nov 2026).
# Colab already has most of these; there you only need: pip install imagehash
tensorflow==2.21.0
tensorflow-datasets      # notebook 06 only (flowers and CIFAR-10 as non-bean test images)
numpy
pandas
scikit-learn
matplotlib
seaborn
pillow
imagehash                # perceptual hashes for the near-duplicate check (notebook 02)
pyyaml                   # reads config/config.yaml
pytest                   # runs tests/
''',
    'tests/conftest.py': r'''"""Lets the tests import `src.*` when pytest is run from the project folder."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
''',
    'tests/test_data_pipeline.py': r'''"""
Quick automatic checks of the data code in src/. They build a tiny fake dataset in a temporary
folder, so they need neither the real images nor TensorFlow, and finish in seconds.

Run from the project folder:   python -m pytest tests -q
"""
import numpy as np
import pandas as pd
import pytest
from PIL import Image

from src.data_loading import (CLASS_NAMES, build_inventory, clean_split_files,
                              list_files, relative_key)
from src.evaluate import PAPER_BENCHMARK_ACC, metrics_report
from src.preprocessing import build_exclusions


def _save(path, color, size=32):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (size, size), color).save(path)


@pytest.fixture
def fake_dataset(tmp_path):
    """3 splits x 4 classes x 2 images, plus one corrupt file and one copied image."""
    root = tmp_path / "usk_coffee"
    for s, split in enumerate(["train", "val", "test"]):
        for c, label in enumerate(CLASS_NAMES):
            for i in range(2):
                _save(root / split / label / f"img_{i}.jpg", (40 * c + i, 20 * s, 10 * i))
    (root / "train" / "defect" / "broken.jpg").write_bytes(b"not an image")
    # an exact copy of a training image hiding in the test split (leakage)
    (root / "test" / "defect" / "copy.jpg").write_bytes(
        (root / "train" / "defect" / "img_0.jpg").read_bytes())
    return root


def _cfg(root, tmp_path):
    return {"paths": {"train": root / "train", "val": root / "val", "test": root / "test",
                      "exclusions": tmp_path / "no_exclusions_yet.csv"}}


def test_relative_key_ignores_where_the_dataset_lives():
    assert relative_key("/content/drive/x/train/peaberry/a.jpg") == "train/peaberry/a.jpg"
    assert relative_key("/content/usk_coffee/train/peaberry/a.jpg") == "train/peaberry/a.jpg"


def test_inventory_counts_files_and_flags_unreadable(fake_dataset):
    inv = build_inventory(fake_dataset)
    assert len(inv) == 3 * 4 * 2 + 2           # 24 normal + corrupt + copy
    assert (~inv["readable"]).sum() == 1
    assert set(inv["label"]) == set(CLASS_NAMES)


def test_list_files_skips_excluded_and_uses_class_order(fake_dataset):
    paths, labels = list_files(fake_dataset / "val", exclude={"val/defect/img_0.jpg"})
    assert len(paths) == 7
    assert labels == sorted(labels)             # folders read in CLASS_NAMES order
    assert not any(p.endswith("val/defect/img_0.jpg") for p in paths)


def test_clean_split_files_removes_copy_from_later_split(fake_dataset, tmp_path):
    (fake_dataset / "train" / "defect" / "broken.jpg").unlink()
    files = clean_split_files(_cfg(fake_dataset, tmp_path), verbose=False)
    assert len(files["train"][0]) == 8
    assert not any(p.endswith("copy.jpg") for p in files["test"][0])


def test_exclusion_rules():
    exact = pd.DataFrame({
        "file_path": ["/d/train/defect/a.jpg", "/d/test/defect/a2.jpg",      # same label
                      "/d/train/premium/b.jpg", "/d/val/peaberry/b2.jpg"],   # conflicting labels
        "split": ["train", "test", "train", "val"],
        "label": ["defect", "defect", "premium", "peaberry"],
        "md5": ["m1", "m1", "m2", "m2"]})
    near = pd.DataFrame({
        "file_a": ["/d/train/longberry/c.jpg"], "file_b": ["/d/test/longberry/c2.jpg"],
        "split_a": ["train"], "split_b": ["test"],
        "label_a": ["longberry"], "label_b": ["longberry"], "confirmed": [True]})
    excluded = set(build_exclusions(exact, near)["relative_path"])
    assert "test/defect/a2.jpg" in excluded and "train/defect/a.jpg" not in excluded
    assert {"train/premium/b.jpg", "val/peaberry/b2.jpg"} <= excluded
    assert "test/longberry/c2.jpg" in excluded and "train/longberry/c.jpg" not in excluded


def test_metrics_report_on_known_predictions():
    y_true = np.array([0, 0, 1, 1, 2, 2, 3, 3])
    y_pred = np.array([0, 1, 1, 1, 2, 2, 3, 3])   # one Defect bean missed
    rep = metrics_report(y_true, y_pred)
    assert rep["accuracy"] == 0.875
    assert rep["per_class"]["defect"]["recall"] == 0.5
    assert rep["beats_paper_benchmark"] == (0.875 > PAPER_BENCHMARK_ACC)


def test_config_matches_code():
    from src.config import load_config
    cfg = load_config()
    assert cfg["classes"] == CLASS_NAMES        # model output order = labels.txt order
    assert cfg["img_size"] == 224
''',
}


def find_project(explicit):
    if explicit:
        return Path(explicit).resolve()
    for start in (Path.cwd(), Path(__file__).resolve().parent):
        for folder in (start, *start.parents):
            if (folder / "config" / "config.yaml").exists():
                return folder
    raise SystemExit("Could not find the project (a folder containing config/config.yaml). "
                     "Use --project PATH.")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--project", help="project folder (default: search for config/config.yaml)")
    ap.add_argument("--dry-run", action="store_true", help="only show what would happen")
    args = ap.parse_args()
    root = find_project(args.project)
    verb = "would" if args.dry_run else "did"
    print(f"Project folder: {root}{'   (DRY RUN: nothing is written)' if args.dry_run else ''}\n")

    report = {"folder": [], "new": [], "same": [], "suggestion": []}

    for rel in FOLDERS:
        d = root / rel
        if not d.exists():
            report["folder"].append(rel)
            if not args.dry_run:
                d.mkdir(parents=True, exist_ok=True)
        # empty folders are not kept by git, so mark them with a .gitkeep - except inside
        # 02_data/, where notebook 04 treats ANY file in external/<class>/ as a photo
        if (not args.dry_run and d.exists() and not any(d.iterdir())
                and not rel.startswith("02_data/")):
            (d / ".gitkeep").touch()

    for rel, text in FILES.items():
        target = root / rel
        if not target.exists():
            report["new"].append(rel)
            dest = target
        elif target.read_text(encoding="utf-8", errors="replace") == text:
            report["same"].append(rel)
            continue
        else:
            dest = root / "00_admin" / "_setup_suggestions" / rel
            if dest.exists() and dest.read_text(encoding="utf-8", errors="replace") == text:
                report["same"].append(f"{rel}  (suggestion already saved)")
                continue
            report["suggestion"].append(f"{rel}  ->  00_admin/_setup_suggestions/{rel}")
        if not args.dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="utf-8")

    labels = {"folder": f"Folders I {verb} create",
              "new": f"Files I {verb} create",
              "same": "Already up to date (skipped)",
              "suggestion": f"You already have these files, so I {verb} NOT touch them; "
                            "the new version goes here instead"}
    for key, title in labels.items():
        print(f"{title}: {len(report[key])}")
        for item in report[key]:
            print("   ", item)
        print()
    print("Nothing was deleted, moved or overwritten.")


if __name__ == "__main__":
    main()

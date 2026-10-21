"""
setup_project.py
----------------
Creates the full folder structure and starter documents for:

    KapeKlasipika: A Mobile-Based System for Green Coffee Bean
    Classification and Defect Identification

HOW TO RUN (from the folder where you want the project to live):
    python setup_project.py

It will NOT overwrite files that already exist, so it is safe to re-run.
"""

from pathlib import Path
from datetime import date

ROOT = Path("kapeklasipika")
TODAY = date.today().isoformat()
CLASSES = ["defect", "longberry", "peaberry", "premium"]

# ---------------------------------------------------------------------------
# 1. Folders
# ---------------------------------------------------------------------------
FOLDERS = [
    "00_admin/meeting_notes",
    "01_business_understanding",
    # Raw data: unzip the USK-Coffee download here, one folder per class.
    *[f"02_data/raw/usk_coffee/{c}" for c in CLASSES],
    "02_data/external",          # e.g. your own phone photos of beans for a real-world test
    "02_data/interim",           # temporary outputs (e.g. duplicate-check results)
    # Processed data: the train/val/test split, one folder per class inside each.
    *[f"02_data/processed/{s}/{c}" for s in ["train", "val", "test"] for c in CLASSES],
    "03_exploration/notebooks",
    "04_preparation/cleaning",
    "04_preparation/features",
    "05_modeling/notebooks",
    "05_modeling/models",        # saved .keras models and exported .tflite files
    "06_evaluation/metrics",
    "07_deployment/pipelines",
    "07_deployment/mobile_app",  # Flutter project goes here (created later with `flutter create`)
    "src",
    "tests",
    "reports/figures",
    "config",
]

# ---------------------------------------------------------------------------
# 2. Starter files (path -> content)
# ---------------------------------------------------------------------------
FILES = {}

FILES["README.md"] = f"""# KapeKlasipika

A mobile-based system that classifies images of green Arabica coffee beans into
**Peaberry, Longberry, Premium, or Defect** using a CNN (MobileNetV2, transfer learning).

## Project structure
| Folder | What goes in it |
|---|---|
| `00_admin/` | Project charter, decision log, meeting notes |
| `01_business_understanding/` | Problem statement, success metrics, assumptions and risks |
| `02_data/raw/` | Original USK-Coffee images. **Never edit these.** |
| `02_data/processed/` | Train/val/test split produced by code |
| `03_exploration/` | EDA notebooks and findings |
| `04_preparation/` | Cleaning and preprocessing work |
| `05_modeling/` | Training notebooks, saved models, experiment log |
| `06_evaluation/` | Metrics, confusion matrices, validation report |
| `07_deployment/` | TFLite export pipeline and Flutter mobile app |
| `src/` | Reusable Python code moved out of notebooks |
| `reports/` | Final report and presentation figures |

## How to rerun everything
1. `pip install -r requirements.txt`
2. Download USK-Coffee (https://coffee.comvislab-usk.org/) and put each class folder in
   `02_data/raw/usk_coffee/` (defect, longberry, peaberry, premium).
3. Run the notebooks in order: `03_exploration/notebooks/01_...`, then `05_modeling/notebooks/02_...`, etc.
4. Export the best model to TFLite (`07_deployment/pipelines/`) and copy it into the Flutter app.

## Dataset citation
Febriana, A., Muchtar, K., Dawood, R., Lin, C.-Y. (2022). USK-COFFEE Dataset: A Multi-class
Green Arabica Coffee Bean Dataset for Deep Learning. IEEE CyberneticsCom 2022.
"""

FILES["requirements.txt"] = """tensorflow>=2.15
numpy
pandas
matplotlib
seaborn
scikit-learn
pillow
imagehash        # finds near-duplicate images (data leakage check)
jupyter
"""

FILES[".gitignore"] = """# Data and models are too large for git
02_data/raw/
02_data/interim/
02_data/processed/
05_modeling/models/*.keras
05_modeling/models/*.h5
*.zip

# Python / Jupyter
__pycache__/
*.pyc
.ipynb_checkpoints/
.venv/
venv/

# Flutter build outputs
07_deployment/mobile_app/build/
07_deployment/mobile_app/.dart_tool/

# OS
.DS_Store
Thumbs.db
"""

FILES["00_admin/project_charter.md"] = f"""# Project Charter — KapeKlasipika
_Drafted {TODAY}. Update as decisions change._

**Title:** KapeKlasipika: A Mobile-Based System for Green Coffee Bean Classification and Defect Identification

**Objective:** Build a mobile-friendly app that takes a photo of a green Arabica coffee bean
and predicts its category (Peaberry, Longberry, Premium, Defect), to support consistent,
image-based coffee sorting.

**Data mining task:** Classification (supervised, 4 classes)

**Method:** CNN using transfer learning with MobileNetV2 (pretrained on ImageNet)

**Tools:** Python, TensorFlow/Keras, pandas, NumPy, Flutter (mobile app), TensorFlow Lite (on-device model)

**Dataset:** USK-Coffee — 8,000 images, 2,000 per class, 256×256 px

**Process:** CRISP-DM (business understanding → data understanding → preparation → modeling → evaluation → deployment)

**Deliverables:** _TBD — confirm with instructor_ (report, trained model, working app, presentation)

**Deadline:** _TBD_

**Team / roles:** _TBD_
"""

FILES["00_admin/decision_log.md"] = f"""# Decision Log
Record every important choice so you can defend it later.

| Date | Decision | Why | Alternatives considered |
|---|---|---|---|
| {TODAY} | Use MobileNetV2 with transfer learning | Small and fast enough to run on a phone; pretrained weights work well with only 2,000 images per class | ResNet-18 (used in the original paper, heavier), training a CNN from scratch (needs much more data) |
| {TODAY} | Run the model on the phone (TensorFlow Lite) instead of a server | Works offline (useful on farms), no hosting cost, images never leave the device | Server API (FastAPI) — easier to update, but needs internet and hosting |
| | | | |
"""

FILES["00_admin/meeting_notes/.gitkeep"] = ""

FILES["01_business_understanding/problem_statement.md"] = """# Problem Statement

## Background
Green coffee beans are sorted by hand in many farms and processing centers. Manual visual
sorting is slow, tiring, and inconsistent between workers, which can lower coffee quality.

## Problem
There is no simple, accessible tool that sorters can use to check a bean's category
consistently from an image.

## Proposed solution
A mobile app where the user captures or uploads a photo of a single green bean and gets a
predicted category (Peaberry, Longberry, Premium, Defect) with a confidence score.

## Data mining questions (draft — to be finalized in Step 2)
1. Can a CNN trained on bean images classify the 4 categories accurately enough to assist sorters? (classification)
2. How reliably does the model separate **Defect** beans from good beans? (binary view of the same classifier)
3. Which categories get confused with each other most, and why? (error analysis on the confusion matrix)
4. Does accuracy hold up on photos taken with a phone, not just the dataset images? (generalization test)
"""

FILES["01_business_understanding/success_metrics.md"] = """# Success Metrics (draft)

| Metric | Target | Why it matters |
|---|---|---|
| Test accuracy (4 classes) | > 81.3% | Beats the original USK-Coffee paper's reported test accuracy (ResNet-18) |
| Macro F1-score | ≥ 0.85 | Balances precision and recall across all 4 classes equally |
| Defect recall | ≥ 0.90 | Missing a defective bean is the costliest error for sorting |
| TFLite model size | < 15 MB | Must fit comfortably in a mobile app |
| Prediction time on phone | < 1 second | Feels instant to the user |

_Targets are proposals. Confirm with your instructor whether specific numbers are required._

**Plain-language definitions**
- *Accuracy*: share of all predictions that are correct.
- *Precision*: of the beans the model called X, how many really were X.
- *Recall*: of the beans that really were X, how many the model caught.
- *F1-score*: a single number that balances precision and recall.
"""

FILES["01_business_understanding/assumptions_risks.md"] = """# Assumptions and Risks

## Assumptions
- Each image shows **one bean**, as in the dataset.
- The dataset labels (assigned by the dataset authors) are correct.
- Users will photograph beans in conditions reasonably close to the dataset (clear, centered, decent light).

## Risks and mitigations
| Risk | Impact | Mitigation |
|---|---|---|
| **Domain shift**: dataset photos were taken with a digital camera in controlled conditions; real phone photos will differ in lighting, background, and focus | Accuracy in the app may be much lower than on the test set | Data augmentation (brightness, rotation, blur); test on your own phone photos in `02_data/external/`; show in-app photo tips |
| **Overfitting**: the original paper reached 98.8% training but 81.3% test accuracy | Model memorizes training images | Augmentation, dropout, early stopping, monitor validation curves |
| **Near-duplicate images** across train and test | Inflated, misleading test score | Perceptual-hash duplicate check before splitting |
| **Class confusion** (e.g. Premium vs Longberry look similar) | Systematic errors | Confusion matrix analysis, Grad-CAM to see what the model looks at |
| Dataset is from Indonesian Arabica | May not generalize to Philippine beans | State this as a limitation; test on local samples if available |
| Defect class mixes many defect types | One label hides different problems | Note as a limitation; defect sub-types are future work |
"""

FILES["02_data/data_dictionary.md"] = """# Data Dictionary — USK-Coffee

Image dataset: each **file** is one record; the **folder name** is the label.

| Field | Meaning | Type | Example | Possible issues |
|---|---|---|---|---|
| file_path | Location of the image file | text | `raw/usk_coffee/peaberry/0001.jpg` | Check exact file names/format after download |
| label | Bean category (from folder name) | categorical (4 values) | `peaberry` | Labels assumed correct; spot-check a sample |
| width, height | Image size in pixels | integer | 256, 256 | Dataset says 256×256; verify all images match |
| channels | Color channels | integer | 3 (RGB) | Check for grayscale or RGBA files |
| file_size_kb | File size | number | — | Very small files may be corrupt |

**Class meanings (to confirm against the dataset README / paper):**
- **Peaberry** — a single rounded bean that forms when only one seed develops in the coffee cherry.
- **Longberry** — elongated bean shape.
- **Premium** — normal, well-formed, defect-free bean.
- **Defect** — beans with visible defects (broken, black, insect-damaged, etc.).

_To be completed in Step 3 after profiling the actual files._
"""

FILES["03_exploration/findings.md"] = "# EDA Findings\n\n_Filled in during Step 3._\n"
FILES["03_exploration/notebooks/.gitkeep"] = ""
FILES["04_preparation/cleaning/.gitkeep"] = ""
FILES["04_preparation/features/.gitkeep"] = ""
FILES["05_modeling/notebooks/.gitkeep"] = ""
FILES["05_modeling/models/.gitkeep"] = ""

FILES["05_modeling/experiments_log.md"] = """# Experiments Log
Log every training run, even failed ones.

| # | Date | Model | Key settings | Train acc | Val acc | Val macro F1 | Notes |
|---|---|---|---|---|---|---|---|
| 0 | | Baseline (e.g. simple small CNN or frozen MobileNetV2 + logistic regression) | | | | | |
| 1 | | MobileNetV2, frozen base, new classifier head | | | | | |
| 2 | | MobileNetV2, fine-tune top layers | | | | | |
| 3 | | | | | | | |
"""

FILES["06_evaluation/metrics/.gitkeep"] = ""
FILES["06_evaluation/validation_report.md"] = "# Validation Report\n\n_Filled in during Step 6: test metrics, confusion matrix, weak spots, real-photo test._\n"
FILES["07_deployment/pipelines/.gitkeep"] = ""
FILES["07_deployment/mobile_app/README.md"] = """# Mobile App (Flutter)

Created later in Step 7 with `flutter create kapeklasipika_app` inside this folder.
The exported `model.tflite` and `labels.txt` go into the app's `assets/` folder.
"""

FILES["src/__init__.py"] = ""
FILES["src/data_loading.py"] = '''"""Load the USK-Coffee images into TensorFlow datasets. (Filled in during Step 4.)"""
CLASS_NAMES = ["defect", "longberry", "peaberry", "premium"]
IMG_SIZE = (224, 224)  # MobileNetV2's standard input size
'''
FILES["src/preprocessing.py"] = '"""Image resizing, normalization and augmentation. (Step 4.)"""\n'
FILES["src/features.py"] = '"""Not much manual feature engineering for CNNs; holds augmentation layers and helpers. (Step 4.)"""\n'
FILES["src/models.py"] = '"""Model builders: baseline and MobileNetV2 transfer learning. (Step 5.)"""\n'
FILES["tests/.gitkeep"] = ""
FILES["reports/figures/.gitkeep"] = ""
FILES["reports/final_report.md"] = """# KapeKlasipika — Final Report

1. Introduction and problem
2. Data
3. Method (CRISP-DM)
4. Results
5. Discussion and limitations
6. Recommendations and next steps
7. References
"""

FILES["config/config.yaml"] = """# Central settings so every notebook uses the same values
seed: 42
img_size: 224
batch_size: 32
classes: [defect, longberry, peaberry, premium]
split:
  train: 0.70
  val: 0.15
  test: 0.15
paths:
  raw: 02_data/raw/usk_coffee
  processed: 02_data/processed
  models: 05_modeling/models
"""

# ---------------------------------------------------------------------------
# 3. Create everything
# ---------------------------------------------------------------------------
def main():
    for folder in FOLDERS:
        (ROOT / folder).mkdir(parents=True, exist_ok=True)

    created, skipped = 0, 0
    for rel_path, content in FILES.items():
        path = ROOT / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            skipped += 1
            continue
        path.write_text(content, encoding="utf-8")
        created += 1

    print(f"Project created at: {ROOT.resolve()}")
    print(f"Files created: {created}, skipped (already existed): {skipped}")


if __name__ == "__main__":
    main()

# KapeKlasipika

**KapeKlasipika: An Offline Android Application for Classifying Green Arabica Coffee Beans into Peaberry, Longberry, Premium, and Defect Using MobileNetV2 Transfer Learning**

An offline Android app that classifies a photo of a single green Arabica coffee bean into
**Peaberry, Longberry, Premium, or Defect** using a CNN (MobileNetV2, transfer learning),
trained on Google Colab and deployed with TensorFlow Lite + Flutter.

## Project structure
| Folder | What goes in it |
|---|---|
| `00_admin/` | Project charter, decision log, meeting notes |
| `01_business_understanding/` | Problem statement, success metrics, assumptions and risks |
| `02_data/raw/` | Original USK-Coffee images. **Never edit these.** |
| `02_data/processed/` | Outputs produced by code (e.g. duplicate-check results, resized copies) |
| `02_data/external/` | Your own phone photos of local green beans (real-world test only) |
| `03_exploration/` | EDA notebooks and findings |
| `04_preparation/` | Cleaning and preprocessing work |
| `05_modeling/` | Training notebooks, saved models, experiment log |
| `06_evaluation/` | Metrics, confusion matrices, validation report |
| `07_deployment/` | TFLite export pipeline and Flutter mobile app |
| `src/` | Reusable Python code moved out of notebooks |
| `reports/` | Final report and presentation figures |

## The notebooks (run in this order)
| # | Notebook | CRISP-DM step | Where to run |
|---|---|---|---|
| 01 | `03_exploration/notebooks/01_data_understanding.ipynb` | Data understanding | Colab (CPU) or laptop |
| 02 | `04_preparation/02_data_preparation.ipynb` | Data preparation (duplicate check) | Colab (CPU) or laptop |
| 03 | `05_modeling/notebooks/03_modeling.ipynb` | Modeling: baseline, frozen, fine-tuned | **Colab T4 GPU** |
| 03b | `05_modeling/notebooks/03b_extended_finetuning.ipynb` | Modeling: extended fine-tuning (final model) | **Colab T4 GPU** |
| 04 | `06_evaluation/04_evaluation.ipynb` | Evaluation on the test set | Colab T4 GPU |
| 05 | `07_deployment/pipelines/05_export_tflite.ipynb` | Deployment: v1 phone model | Colab (CPU) |
| 06 | `06_evaluation/06_not_a_bean_detector.ipynb` | Anomaly detection + v2 phone model (replaces v1 in the app) | Colab (GPU helps) |
| 07 | `07_deployment/pipelines/07_live_test_sheets.ipynb` | Printable test sheets + live-scanner accuracy | Colab (CPU) or laptop |

Each notebook saves its tables to `02_data/interim/` or `06_evaluation/metrics/`,
its figures to `reports/figures/`, and its models to `05_modeling/models/`.
All reusable code lives in `src/` (`live_detector.py` is the tested Python reference of the app's
live bean finder and tracker); all settings live in `config/config.yaml`.

## How to rerun everything
1. Download USK-Coffee (https://coffee.comvislab-usk.org/). It comes already split.
   Put its `train/`, `val/` and `test/` folders in `02_data/raw/usk_coffee/`.
   Each contains four class folders: defect, longberry, peaberry, premium.
   (The dataset is not stored on GitHub; it is shared separately via a Google Drive link: _add link_.)
2. Put your own phone photos in `02_data/external/<class>/` (optional, for the real-world test).
3. Upload the whole `kapeklasipika` folder to Google Drive as `MyDrive/kapeklasipika`.
4. In Colab: File → Open notebook → Google Drive → open notebook 01.
   For notebook 03, set Runtime → Change runtime type → **T4 GPU** first.
   Run every cell from top to bottom (Runtime → Run all). The first cell connects your Drive.
5. Run notebooks 01 → 05 in order. Notebook 05 copies the model into the Flutter app.
6. Build the app: see `07_deployment/mobile_app/README.md`.

To run notebooks 01–02 on your laptop instead: `pip install -r requirements.txt`, then open
them in VS Code or Jupyter.

## Dataset citation
Febriana, A., Muchtar, K., Dawood, R., Lin, C.-Y. (2022). USK-COFFEE Dataset: A Multi-class
Green Arabica Coffee Bean Dataset for Deep Learning. IEEE CyberneticsCom 2022.

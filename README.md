# KapeKlasipika

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

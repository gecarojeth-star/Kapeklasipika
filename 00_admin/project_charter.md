# Project charter: KapeKlasipika

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

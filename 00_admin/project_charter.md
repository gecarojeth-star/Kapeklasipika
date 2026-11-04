# Project Charter — KapeKlasipika
_Drafted 2026-10-21. Update as decisions change._

**Title:** KapeKlasipika: An Offline Android Application for Classifying Green Arabica Coffee Beans into Peaberry, Longberry, Premium, and Defect Using MobileNetV2 Transfer Learning

**Student:** Jeth Sander S. Gecaro (solo project) — CS333

**Objective:** Build a mobile-friendly app that takes a photo of a green Arabica coffee bean
and predicts its category (Peaberry, Longberry, Premium, Defect), to support consistent,
image-based coffee sorting.

**Data mining task:** Classification (supervised, 4 classes)

**Method:** CNN using transfer learning with MobileNetV2 (pretrained on ImageNet)

**Tools:** Python, TensorFlow/Keras, pandas, NumPy, Flutter (mobile app), TensorFlow Lite (on-device model)

**Dataset:** USK-Coffee — 8,000 images, 2,000 per class, 256×256 px, pre-split into train/val/test (1,200 / 400 / 400 per class). Plus ~50–100 phone photos of locally sourced green beans for a real-world test.

**Training environment:** Google Colab (free GPU); laptop (Intel Iris Xe, CPU-only training) as backup

**Process:** CRISP-DM (business understanding → data understanding → preparation → modeling → evaluation → deployment)

**Deliverables (CS333):** project proposal (1–2 pages, ≥4 related papers, timeline); dataset; IEEE-format paper (6–10 pages, ≥6 references); trained model; source code; 20–30 min oral presentation

**Deadline:** _TBD_


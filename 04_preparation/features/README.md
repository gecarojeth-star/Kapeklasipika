# Features

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

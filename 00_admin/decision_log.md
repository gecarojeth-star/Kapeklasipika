# Decision Log
Record every important choice so you can defend it later.

| Date | Decision | Why | Alternatives considered |
|---|---|---|---|
| 2026-10-21 | Use MobileNetV2 with transfer learning | Small and fast enough to run on a phone; pretrained weights work well with only 2,000 images per class | ResNet-18 (used in the original paper, heavier), training a CNN from scratch (needs much more data) |
| 2026-10-21 | Run the model on the phone (TensorFlow Lite) instead of a server | Works offline (useful on farms), no hosting cost, images never leave the device | Server API (FastAPI) — easier to update, but needs internet and hosting |
| | | | |

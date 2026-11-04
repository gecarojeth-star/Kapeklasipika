# Experiments Log
Log every training run, even failed ones. Fill the numbers from notebook 03's
validation summary (`06_evaluation/metrics/val_summary.csv`).

All runs: same provided train/val split, 224×224 input, batch 32, Adam, seed 42,
early stopping on val loss (patience 5), augmentation as in `src/features.py`.

| # | Date | Model | Key settings | Trainable params | Epochs run | Train acc | Val acc | Gap | Notes |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 2026-10-22 | Baseline CNN (from scratch) | 3 conv blocks (32/64/128), dropout 0.3, lr 0.001, max 30 epochs | 94,212 | 12 (best 7) | 63.49% | 57.31% | 6.2 pts | Validation accuracy very unstable (22%–57% between epochs); early-stopped. ~4 min on T4 |
| 1 | 2026-10-22 | MobileNetV2, frozen base + new head | ImageNet weights, dropout 0.3, lr 0.001, max 15 epochs | 5,124 | 15 (best 15) | 77.85% | 75.44% | 2.4 pts | Steady but plateauing around 74–75%. 3.7 min |
| 2 | 2026-10-22 | MobileNetV2, fine-tuned | last 40 layers unfrozen (BatchNorm frozen), lr 0.00001, max 15 more epochs | 1,668,484 | 15 (best: last) | 88.72% | 84.25% | 4.5 pts | Best so far. Val loss still falling at the last epoch (0.403) → not converged; see experiment 3. 4.2 min |
| 3 | 2026-10-22 | MobileNetV2, extended fine-tuning (notebook 03b) | continue exp. 2, up to 20 more epochs, same lr, early stopping | 1,668,484 | 14 (best: 9th, epoch 39) | 90.08% | **86.56%** | 3.5 pts | Val loss bottomed at 0.381, then rose → early stop. Highest val accuracy → **selected final model**. 3.5 min |

**Gap** = train accuracy − validation accuracy. Above about 0.10 suggests overfitting.

Note: notebook 03's first run trained on 4,804 images (4 exact duplicate copies inside the
training set were not yet removed because of a loader bug, fixed 2026-10-22). Duplicates
within training only repeat 4 images out of 4,800, and validation was unaffected, so these
results stand; notebook 03b and later runs use the fully cleaned 4,800.

# Success Metrics (draft)

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

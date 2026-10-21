# Assumptions and Risks

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

# Problem statement

## Background
Before roasting, green coffee beans are sorted by shape, size and visible defects, because a
lot's grade (and price) depends on it. On many small farms and processing centres this is still
done by eye. Hand sorting is slow and tiring, and results vary from one sorter to another and
with fatigue, so defective beans can slip into a lot and lower its grade.

## The problem in plain words
Sorters need a quick, consistent second opinion on what kind of bean they are holding, using
something they already own (a phone), without depending on internet access.

## Who it is for
- **Primary users:** green-coffee sorters and small processors.
- **Other readers:** the course instructor and panel, who judge whether the method is sound.

## Business objective
Build an offline Android app that classifies a photo of one green Arabica bean as Defect,
Longberry, Peaberry or Premium, accurately enough to be a useful sorting aid. It supports a
sorter; it does not replace one.

## Data mining questions

| # | Question | Problem type | Why this type |
|---|---|---|---|
| Q1 | Can a MobileNetV2 transfer-learning model classify a single-bean photo into the four classes with test accuracy above the 81.31% reported by the dataset's authors? | **Multi-class classification** (supervised) | Every training image already has one of four known labels; we learn to predict that label for new images. |
| Q2 | How reliably does the model catch Defect beans (target recall ≥ 0.90), which classes does it confuse, and can a Defect decision threshold improve recall at an acceptable cost? | **Cost-sensitive classification** + error analysis | Mistakes do not cost the same: a missed Defect bean lowers the lot's grade, while a good bean set aside by mistake only costs a second look. So we weight Defect recall above plain accuracy. |
| Q3 | Can the app tell when a photo is not a coffee bean at all, while still accepting real beans? | **Anomaly (out-of-distribution) detection** | We cannot collect examples of "everything that is not a bean", so instead we model what normal beans look like and flag whatever is too far from that. |
| Q4 | How much does performance drop on phone photos of real local beans compared with the dataset? | **Generalisation test** of the Q1 classifier (evaluation, not a new model) | The dataset comes from one camera setup in Indonesia; this measures whether the results hold in real use. **Blocked until real photos exist.** |

## What a good answer looks like
See `success_metrics.md` for the numbers and their current status.

## What this project will not claim
- That the app can replace trained sorters.
- That results on USK-Coffee images hold for other varieties, cameras or lighting, unless Q4
  shows it.
- That it can name the specific defect type (the dataset has one Defect label).

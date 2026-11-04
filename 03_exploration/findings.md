# EDA Findings (notebook 01, run on Colab, 2026-10-21)

## 1. Size and balance
| Split | Defect | Longberry | Peaberry | Premium | Total |
|---|---|---|---|---|---|
| train | 1,203 | 1,200 | 1,200 | 1,201 | 4,804 |
| val | 400 | 400 | 400 | 400 | 1,600 |
| test | 400 | 401 | 416 | 400 | 1,617 |
| **Total** | 2,003 | 2,001 | 2,016 | 2,001 | **8,021** |

- **21 more images than the 8,000 the dataset page states.** Extras: 3 in train/defect,
  1 in train/premium, 1 in test/longberry, 16 in test/peaberry.
  **Confirmed by notebook 02:** these are exact byte-for-byte copies (42 files in 21 pairs),
  so each extra file is excluded and the dataset is back to its intended size.
- Even with the extras, classes stay balanced (largest class is under 1% bigger than the
  smallest), so accuracy remains a fair headline metric and no resampling is needed.

## 2. File quality
- Unreadable files: **0**.
- All 8,021 images are **256 × 256 RGB**. No grayscale, transparency, or odd sizes.
- File size 4.9–12.8 KB (mean 8.3 KB). No suspiciously tiny files.

## 3. What the classes look like (`reports/figures/01_samples_per_class.png`)
- One bean per image, on a white or light gray background, under similar lighting.
- Beans are not always centered; some sit near the edge of the frame. Random zoom and
  rotation in augmentation should help the model handle this.
- The classes are hard to tell apart by eye. Several Premium and Longberry samples
  show cracks, and some Peaberry samples look elongated. This visual overlap is a
  likely reason the original paper reached only 81.31% test accuracy.
- Defect beans range from obvious (black, broken, insect-damaged) to subtle (small spots).

## 4. Color and brightness (`reports/figures/01_color_brightness.png`)
| Class | Mean brightness | Std |
|---|---|---|
| Defect | 211.3 | 12.4 |
| Longberry | 210.1 | 9.9 |
| Peaberry | 211.7 | 9.7 |
| Premium | 206.0 | 13.8 |

- Brightness is dominated by the white background, so averages are very close across
  classes; Premium is slightly darker and more varied.
- In the red-vs-green scatter, all four classes overlap almost completely.
- **Meaning:** whole-image color cannot separate the classes. The model has to learn
  **shape and surface texture** of the bean, which is what CNNs are good at. A simple
  color-based classifier would not work here.
- Lighting varies (brightness roughly 150–240), which supports using brightness and
  contrast augmentation.

## 5. Privacy
Images contain only coffee beans. No people, faces, names, or IDs. No action needed.

## 6. Implications for the next steps
1. ~~Resolve the 21 extra files~~ Done: exact copies, excluded (section 8).
2. Keep shape-preserving augmentation (rotation, flips, zoom) and lighting augmentation.
3. Expect the hardest confusions among Premium, Longberry, and Peaberry; check this in the
   confusion matrix (notebook 04).

## 7. Duplicate check (notebook 02, first run)
- **Exact duplicates:** 42 files in 21 identical pairs; they account for the 21 extra images.
- **Perceptual-hash check across splits:** 184 flagged pairs (95 train–test, 67 train–val,
  22 val–test). Visual review showed most were *different* beans that just look similar
  (a dark oval on white), and 95 of the pairs even had different labels. At least one
  train–test Peaberry pair did look like the same photo.
- **Decision:** confirm each flagged pair with a pixel-difference test and exclude only
  confirmed duplicates (see decision log).

## 8. Duplicate check (notebook 02, final run)
- Pixel check on the 184 hash-flagged pairs: **1 confirmed duplicate** (pixel difference 0.0,
  the same Peaberry photo in train and test). The next-closest pair differs by 4.9, and the
  histogram shows a clear gap between 0 and ~5, so the threshold of 3.0 is not borderline.
  The closest rejected pairs are visibly different beans.
- **22 files excluded** (`02_data/interim/excluded_files.csv`): 21 exact copies (17 in test,
  4 in train) + 1 test image duplicated from train. No conflicting-label duplicates.

| Split | Defect | Longberry | Peaberry | Premium | Total |
|---|---|---|---|---|---|
| train | 1,200 | 1,200 | 1,200 | 1,200 | 4,800 |
| val | 400 | 400 | 400 | 400 | 1,600 |
| test | 400 | 400 | 399 | 400 | 1,599 |
| **Total** | 2,000 | 2,000 | 1,999 | 2,000 | **7,999** |

- Takeaway for the paper: the provided split is essentially leak-free (1 of 1,600 test
  images), so test results compare fairly with the original paper.

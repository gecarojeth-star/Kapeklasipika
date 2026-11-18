# Real-world test photos: collection protocol

These photos answer data mining question Q4: does the model still work on real phone photos?
They are used **only for testing**, never for training.

## Rule 1: real beans only
Do **not** photograph printed pictures or screens. Prints add ink dots, paper grain, colour
shifts and glare; screens add moiré stripes and glow. The model reads those as bean texture, so
results say nothing about real use. This already happened once: printed dataset images were
classified as Defect.

## Where the files go
```
02_data/external/
  defect/      longberry/      peaberry/      premium/
  labels.csv
```
Notebook 04 reads the class from the folder name.

## How to take each photo (match the dataset as closely as possible)
1. One bean per photo, centred, filling **about half** of the frame. Do not photograph the
   bean from far away and rely on cropping later.
2. Plain, matte, white or very light background (bond paper works). No patterns or shadows from
   your hand.
3. Soft daylight near a window, or an evenly lit room. **No flash.**
4. Hold the phone parallel to the table and tap to focus on the bean. No digital zoom.
5. Use the normal camera app at default settings (no filters, no beauty mode, no HDR if possible).
6. If you photograph both sides of a bean, give both files the same bean ID, so the analysis
   counts the bean once.

## How many
Aim for **at least 50 beans per class (200 in total)**. With about 100 photos, the accuracy
estimate is still uncertain by roughly ±9 percentage points.

## Labelling
1. Use the team's written grading standard; save a copy in `00_admin/`.
2. Two team members label every bean **independently**, without seeing each other's answers.
3. Write both labels into `labels.csv`. Settle disagreements together and record the final
   label. The agreement rate (or Cohen's kappa, an agreement score that corrects for lucky
   guesses) goes in the paper.

`labels.csv` columns:

| column | example | meaning |
|---|---|---|
| file_name | `bean_017_a.jpg` | photo file |
| bean_id | `017` | same bean = same ID |
| label_1 | `premium` | first labeller |
| label_2 | `longberry` | second labeller |
| final_label | `premium` | agreed label (must match the folder) |
| source_place | `province / market` | where the beans came from (no seller names) |
| variety | `Arabica` | as stated by the seller |
| phone_model | `brand model` | camera used |
| notes | `slight shadow` | anything unusual |

## Privacy
No people, faces or hands in the frame. Remove GPS location from the photos (most phones can
turn location tagging off in the camera settings) before sharing them.

## Optional: non-bean photos
Photos of coins, rice, corn kernels, pebbles, peanuts or roasted coffee beans, taken the same
way, go in `02_data/external_non_beans/` (no subfolders). Notebook 06 uses them to test the
"not a bean" check on realistic objects.

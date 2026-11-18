# 2026-11-04: Project review with Claude

## Discussed
- Reviewed notebooks 01-06, the src/ code, config.yaml, the Android build file and paper draft 2.
- Results on the dataset: test accuracy 85.43%, macro F1 0.852, Defect recall 0.833 (target 0.90
  not met), phone model 4.69 MB.
- The not-a-bean detector rejects non-bean images well (83-87% of flowers, CIFAR-10 images and
  synthetic coins), but most of the real beans it flags are Defect beans.
- Android minimum version is SDK 26 = Android 8.0, which matches the paper.
- **Printed-photo test.** Dataset images were printed and photographed with the phone. The app
  called them Defect, while uploading the same original files gave the correct class. Non-bean
  objects were still rejected correctly.

## Why the printed photos fail (summary)
The model only ever saw clean digital photos from one camera. A photo of a print changes
exactly the things it uses to judge beans:
1. **Colour and brightness:** printer ink and paper shift and darken colours; dataset backgrounds
   are very bright (average brightness about 206-212 out of 255).
2. **Texture:** printers build images from tiny ink dots, and paper has grain. Up close this looks
   like a rough, spotted surface, which is what Defect beans look like.
3. **Glare and blur:** shiny paper reflects light; re-photographing softens edges.
4. **Size in the frame:** dataset beans fill roughly half the picture. If the phone photo shows
   the whole page, the bean becomes a small blob after resizing to 224 x 224.
Defect is the class with the most visual variety, so "strange-looking bean" tends to land there.
This is a **domain shift** problem, not a bug in the app.

## Decided
- No YOLO; upload / take-photo only (D16).
- Merge the new structure into the existing folder (D17).
- No personal details in documents for now (D18).
- Remove Live scan completely (D19); keep Recent scans with a Clear button (D14 changed).
- P01 stays in development until physical beans are available.

## Action items
| What | Who | By when |
|---|---|---|
| Buy or borrow real green Arabica beans; follow `02_data/external/README.md` | Team | TBD |
| Send 2-3 pairs (original dataset file + phone photo of its print), plus `kapeklasipika.tflite`, so the exact app input can be analysed | Team | Next session |
| Run `setup_project.py` in Colab (dry run first) | Team | Next session |
| Review Stage 1-2 documents | Team | Next session |
| Install the updated app (`flutter clean`, `flutter pub get`, `flutter analyze`, `flutter run`) and retest taking photos | Team | Next session |

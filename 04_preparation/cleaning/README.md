# Cleaning

Cleaning happens in **notebook 02** with functions from `src/preprocessing.py`. Raw images are
never changed; problem files are listed in `02_data/interim/excluded_files.csv`, and every later
notebook skips them automatically (`src/data_loading.py`, `clean_split_files`).

Rules:
1. Byte-identical copies in the same split and class: keep one, exclude the rest.
2. The same photo in two splits: exclude the copy in the later split (val or test), so the model
   is never tested on an image it trained on.
3. Copies with conflicting labels: exclude all of them, because the label cannot be trusted.

The full write-up (with numbers) comes in Stage 3 (data preparation).

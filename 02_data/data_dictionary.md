# Data Dictionary — USK-Coffee

Image dataset: each **file** is one record; the **folder name** is the label.

| Field | Meaning | Type | Example | Possible issues |
|---|---|---|---|---|
| file_path | Location of the image file | text | `raw/usk_coffee/peaberry/0001.jpg` | Check exact file names/format after download |
| label | Bean category (from folder name) | categorical (4 values) | `peaberry` | Labels assumed correct; spot-check a sample |
| width, height | Image size in pixels | integer | 256, 256 | Dataset says 256×256; verify all images match |
| channels | Color channels | integer | 3 (RGB) | Check for grayscale or RGBA files |
| file_size_kb | File size | number | — | Very small files may be corrupt |

**Class meanings (to confirm against the dataset README / paper):**
- **Peaberry** — a single rounded bean that forms when only one seed develops in the coffee cherry.
- **Longberry** — elongated bean shape.
- **Premium** — normal, well-formed, defect-free bean.
- **Defect** — beans with visible defects (broken, black, insect-damaged, etc.).

_To be completed in Step 3 after profiling the actual files._

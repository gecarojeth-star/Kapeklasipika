# KapeKlasipika mobile app (Flutter, Android) · v2

Two modes, switched with the bottom bar. Everything runs on the phone, offline.

- **Live scan:** point the camera at green beans on a plain light surface. Each bean gets a
  box, an ID (#1, #2, ...) and a label that settles over a few frames. The panel shows the
  count per class, beans that are touching, objects that are not beans, and an estimated
  weight. A banner guides the camera ("Too far, move closer", "Too dark", ...).
  **Freeze** pauses the view and opens a per-bean list.
- **Photo:** one bean per photo, with detailed probabilities and timing. Objects that don't
  look like coffee beans are shown as "Not a coffee bean?".

## What's here
| File | Purpose |
|---|---|
| `pubspec.yaml` | Packages, model assets, icon and splash settings |
| `lib/main.dart` | App shell: loads the model and settings once; bottom navigation |
| `lib/live/live_page.dart` | Live scan screen: camera, overlay, counts, guidance, freeze/details |
| `lib/live/detector.dart` | Bean finder (Otsu threshold + connected components) and camera guidance |
| `lib/live/tracker.dart` | IDs per bean and label voting |
| `lib/live/frame.dart` | Camera frame (YUV) → 224×224 RGB crop per bean |
| `lib/photo_page.dart` | Photo mode screen |
| `lib/classifier.dart` | Loads the model (v1 or v2), preprocessing and inference in background isolates |
| `lib/settings.dart` | Weight estimate: default 0.155 g/bean, or your own calibration |
| `lib/look.dart` | Shared colors and wording |
| `assets/kapeklasipika.tflite`, `assets/labels.txt` | The model. **v2** (with the not-a-bean detector) comes from notebook 06; the older v1 from notebook 05 still works |
| `assets/icon/` | App icon, adaptive-icon foreground, splash image |

The live bean finder and tracker were first written and tested in Python:
`src/live_detector.py` (same settings and steps).

## First-time setup (Windows, run everything INSIDE this folder)
```
cd C:\Users\Admin\kapeklasipika\07_deployment\mobile_app
flutter create --platforms=android --project-name kapeklasipika_app .
flutter pub get
dart run flutter_launcher_icons
dart run flutter_native_splash:create
```
Then make these one-time edits to the generated Android files:
1. `android\app\build.gradle.kts` → `minSdk = 26` (tflite_flutter needs Android 8.0+).
2. `android\app\src\main\AndroidManifest.xml` → `android:label="KapeKlasipika"`.
3. `android\gradle.properties` → add `kotlin.jvm.target.validation.mode=warning`.

If you already did these for v1, just run `flutter pub get` (new packages: `camera`,
`shared_preferences`) and copy the v2 model from Drive into `assets\`.

## Run on your phone
```
flutter run
```
Keep the phone unlocked and tap **Install** if it asks. The first time you open Live scan,
allow camera access. Installable file: `flutter build apk --release` →
`build\app\outputs\flutter-apk\app-release.apk`.

## Using Live scan well
- Plain white paper or a light tray, even light, beans **not touching**.
- Hold the phone so beans look at least about a fingernail wide on screen; the banner tells
  you if you're too far or too close.
- Labels start white ("...") and settle after a few looks; touching beans are orange,
  non-beans purple.
- Weight: tap the scale icon to calibrate with your own beans (weigh e.g. 100 beans).

## Troubleshooting (problems we already hit)
| Error | Fix |
|---|---|
| `did not install NDK 28.2...` | Android Studio → Settings → Android SDK → SDK Tools → Show Package Details → NDK (Side by side) 28.2.13676358 → Apply |
| `No file or variants found for asset: assets/kapeklasipika.tflite` | Download `kapeklasipika.tflite` and `labels.txt` from Drive into `assets\` |
| `Inconsistent JVM-target compatibility ... (11) and (25)` | `flutter config --jdk-dir "C:\Program Files\Android\Android Studio\jbr"` + the gradle.properties line above, then `flutter clean` |
| Build files appear in `C:\Users\Admin` | You ran Flutter outside this folder; `cd` here first |
| `INSTALL_FAILED_USER_RESTRICTED` (Xiaomi/Redmi) | Unlock the phone and tap Install on the popup; or Developer options → Install via USB + USB debugging (Security settings) |
| Live boxes are shifted or rotated | Tell Claude your phone model; the frame rotation depends on the camera sensor |
| Camera error on Live scan | Settings → Apps → KapeKlasipika → Permissions → Camera → Allow |

## How images are prepared (must match training)
Photo mode: rotate upright (EXIF) → center-crop to a square → resize to 224×224 → raw RGB
0–255. Live mode: square crop around each bean, twice the bean's length (like the dataset's
framing) → 224×224 → raw RGB. The model normalizes pixels itself.

## Known limitations
- The live bean finder needs a light, plain background; touching beans are flagged, not classified.
- Weight is an estimate (count × average bean weight), not a measurement.
- The not-a-bean check was tested on flowers, CIFAR-10 and synthetic coins; unusual real
  objects may still pass.

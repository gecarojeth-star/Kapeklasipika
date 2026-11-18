# KapeKlasipika app 2.1.0: what changed

## How to install (inside 07_deployment/mobile_app/)
1. **Delete** `lib/live/` and `lib/settings.dart` (they are no longer used).
2. Replace `lib/main.dart`, `lib/photo_page.dart`, `lib/classifier.dart`, `lib/look.dart`
   and `pubspec.yaml` with the files from this zip.
3. Run:
   ```
   flutter clean
   flutter pub get
   flutter analyze      # should report no errors
   flutter run
   ```
`assets/`, `android/` and the model files do not change.

## Removed: Live scan
- No bottom navigation bar; the app opens straight on the photo screen.
- Deleted the live scanner (`lib/live/`), the weight estimate (`lib/settings.dart`), and the
  `camera` and `shared_preferences` packages. The app now asks for no camera permission
  itself: "Take photo" uses the phone's own camera app.

## Fixed: crashes when taking a photo
| Problem | Fix |
|---|---|
| Tapping "Take photo" twice could open the camera twice | Both buttons are disabled while the camera or gallery is open |
| Camera or permission errors were not handled | They are caught and shown as a message on screen |
| On low-memory phones, Android may close the app while the camera is open, and the photo is lost | The photo is recovered when the app restarts, and classified once the model is loaded |
| Very large photos used a lot of memory | The picker now limits both width and height to 1024 px; a safety step shrinks anything over 1600 px before processing |
| Updating the screen after it was closed | Every update checks first that the screen still exists |
| The live camera and the camera app competing for the camera | Gone with Live scan |

If it still crashes, run `flutter run` with the phone connected and send the red error text.

## Added: Clear button for Recent scans
A small "Clear" button next to "Recent scans". It asks for confirmation, then removes all
recent scans and the current result. Scans are kept in memory only: nothing is saved on the
phone, and closing the app clears them.

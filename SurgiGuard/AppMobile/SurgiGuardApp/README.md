# SurgiGuard AI — mobile app (React Native)

*Smarter Recovery. Safer Care.* This is the patient and caregiver mobile app for the HackCure project. It is a React Native 0.87 (CLI, TypeScript) port of the Figma Make prototype in `../SurgiGuard AI mobile app UI`, using the screenshots in `../Maquette` as the visual reference.

## Run (Windows → Android)

Requirements:
- Node ≥ 22
- JDK 17 (`JAVA_HOME`)
- Android SDK (`ANDROID_HOME`, with `platform-tools` on `PATH`)
- An emulator or a USB phone with USB debugging enabled

```powershell
npm install
npm start                      # Metro, keep it open
cd android; .\gradlew.bat app:installDebug   # build + install (or: npm run android)
```

> `npx react-native run-android` can fail because the project path contains a space ("Nouveau dossier"). Calling `gradlew.bat` directly works.

For the AI assistant, start the backend (see `../backend/README.md`).

iOS: the code is cross-platform. To build it you need a Mac (`cd ios && pod install && npx react-native run-ios`).

## Structure

```
src/
  theme/        design tokens ported from the Figma CSS (light + dark), ThemeContext
  i18n/         en.ts / fr.ts — every UI string, device language by default
  components/   T (text), ui (Button, Card, Chip, TopBar, Switch…), Icon, charts, figures,
                CameraPreview (vision-camera v5), twin/Twin3D (three.js in a WebView)
  context/      AppState (role, onboarding, backend URL, demo cross-role acknowledgement)
  navigation/   RootNavigator (role → onboarding → tabs), custom BottomNav
  screens/      onboarding/, patient/, family/, SettingsScreen
  services/     api.ts (chat → FastAPI → Mistral)
  data/         mock.ts — fictional patient (Sarah Miller)
twin-src/       3D twin source (three.js); `npm run build:twin` regenerates src/components/twin/twinHtml.ts
```

## Screens

- **Patient**: role selection, welcome, upload reports, AI protocol, home, daily check-in, 3D recovery twin + knee detail, wound scan (live camera), sensing request, knee rehab (live camera), clinical alert with the closed follow-up loop, medications, AI assistant, reports & appointments, profile, family access, consent, settings.
- **Family**: join by QR or code, family home (assistance tasks, observations), updates, recovery (shared data only), profile & notifications, lock-screen previews, and the info / needs-attention / urgent alert details.

Demo tip: on the patient's *Clinical alert* screen, tap **Family notified** to reset the acknowledgement. Then switch role (Settings → Switch role). As the family member, acknowledge the alert, switch back, and the patient sees "Ahmed has seen your alert".

## Notes

- Small Figma sizes (5–9px) are scaled up by `fs()` in `theme/tokens.ts` so they're readable on a device. The layout and hierarchy are unchanged.
- All patient data is fictional. Simulated IoT measurements carry a **SIMULATED** tag.
- 3D model: *Cesium Man* from the Khronos glTF Sample Assets, © Cesium, licensed CC-BY 4.0. It is rendered with a custom glass material, so the logo texture is not used. If WebGL is unavailable, the twin falls back to the 2D glass SVG body from the prototype.

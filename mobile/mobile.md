# Mobile Cheat Sheet

Flutter and Expo each own a different slice of the mobile build pipeline — the native build system versus the (classic) Expo remote build service. Knowing which one you're actually invoking saves a round trip through the wrong docs.

---

## Flutter — Build

**Native Android packaging goes through `flutter build`, not a bare `flutter` verb.**

```bash
# Build the Android app from a Flutter project
flutter build android app
```

> **Uncertain — preserved verbatim.** `flutter build android app` is not a documented `flutter` subcommand; the standard forms are `flutter build apk` or `flutter build appbundle`. This may be a custom script or shell alias on the source system rather than the bare Flutter CLI. Copied as run — verify against your own `flutter` before relying on it.

---

## Expo — Build

**The classic Expo build service compiles native binaries remotely — no local Xcode/Android SDK toolchain required.**

```bash
# Build an Android binary using the (classic) Expo build service
npx expo build:android

# Build an iOS binary using the (classic) Expo build service
npx expo build:ios
```

---

## Key Patterns

| Symptom | Move |
|---|---|
| Need an installable Android binary from a Flutter project | `flutter build android app` (verify — non-standard form, see note above) |
| Need a native binary without a local native toolchain | `npx expo build:android` / `npx expo build:ios` |

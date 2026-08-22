# Web Cheat Sheet

## NPM / React Native — Dev Server

Metro won't hot-reload anything until it's actually running — every other command in this project (`ios`, `android`, `web`) assumes this server is already up in another terminal.

```bash
# Start the React Native/Expo development (Metro) server
npm start
```

## NPM / React Native — Run

`ios` and `android` compile a native shell around the JS bundle and launch it on a simulator/emulator or attached device; `web` skips the native shell entirely and serves the same app straight to a browser through the dev server.

```bash
# Build and run the app on an iOS simulator or device
npm run ios

# Build and run the app on an Android emulator or device
npm run android

# Run the app in a web browser via the dev server
npm run web
```

## NPM / React Native — Build

The dev server is fine for iteration but never ships — `build:web` is the one command that produces static output fit to deploy.

```bash
# Produce a production web build
npm run build:web
```

## Key Patterns

| Symptom | Move |
|---|---|
| `ios`/`android`/`web` run commands hang or can't connect | Start the Metro dev server first (`npm start`) |
| Need the app in a browser for quick iteration | `npm run web` |
| Need a deployable static bundle, not a dev server | `npm run build:web` |

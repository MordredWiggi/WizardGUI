# Wizard Flutter – Android Score Tracker

Android port of the Wizard card game score tracker, built with Flutter/Dart.
Shares the same JSON save format as the desktop app.

## Setup

1. Install [Flutter](https://docs.flutter.dev/get-started/install/windows/mobile) (SDK 3.32+)
2. Install [Android Studio](https://developer.android.com/studio) to get the Android SDK
3. Copy `android/local.properties.template` to `android/local.properties` and fill in your SDK paths
4. Accept SDK licenses: `flutter doctor --android-licenses`

```bash
cd wizard_flutter
flutter pub get
flutter run           # run on connected device / emulator
```

## Build

```bash
flutter build apk --release           # APK for sideloading
flutter build appbundle               # AAB for Play Store
```

Release APK: `build/app/outputs/flutter-apk/app-release.apk`

## Architecture

| File / folder | Responsibility |
|---|---|
| `lib/main.dart` | Entry point, Provider wiring |
| `lib/domain/` | Game model — full Dart port of `game_control.py` |
| `lib/i18n/translations.dart` | All UI strings in de / en / fr / hi |
| `lib/persistence/app_settings.dart` | Language, theme, leaderboard URL via `SharedPreferences` |
| `lib/persistence/save_manager.dart` | JSON save / load / delete, desktop-compatible schema |
| `lib/services/leaderboard_service.dart` | HTTP client for the leaderboard API (groups, leaderboards, game submission) |
| `lib/state/game_notifier.dart` | `ChangeNotifier` owning `GameControl` + active group, exposes all game actions |
| `lib/theme/app_theme.dart` | Dark and light `ThemeData`, colour palette |
| `lib/screens/setup_screen.dart` | Player setup — group selection/creation, player name entry |
| `lib/screens/game_screen.dart` | Gameplay — bids tab, chart tab, groups LB tab, my group LB tab |
| `lib/screens/settings_screen.dart` | Language, theme, leaderboard URL settings |
| `lib/screens/podium_screen.dart` | End-of-game podium |
| `lib/widgets/player_entry_card.dart` | Per-player card with bid / made spinners |
| `lib/widgets/score_chart.dart` | Score progression line chart (`fl_chart`) |
| `lib/widgets/event_overlay.dart` | Animated celebration toast |

## Key dependencies

| Package | Purpose |
|---|---|
| `provider` | State management (`GameNotifier`, `AppSettings`) |
| `shared_preferences` | Persist language, theme, leaderboard URL |
| `path_provider` | Locate the app documents directory for save files |
| `fl_chart` | Score progression line chart |
| `crypto` | SHA-256 game hash for deduplication |
| `intl` | Date formatting |

## Groups & Leaderboard

Before starting a game, players must join or create a group:

- **Join** — search public groups by name, then enter the 4-digit code to confirm.
- **Create** — choose a name, a 4-digit code, and public/hidden visibility.

During a game, the bottom tab bar shows:

| Tab | Content |
|---|---|
| Bids | Player bid/made entry (main gameplay) |
| Chart | Score progression line chart |
| Groups | Global groups leaderboard |
| My Group | Player leaderboard for the active group |

The leaderboard URL is configured in **Settings**. It points to the shared FastAPI backend.

## Minimum Android version

Android 8.0 (API 26) — covers ~98 % of active Android devices.

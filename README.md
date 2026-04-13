# 🃏 Wizard – Score Tracker

A score tracker for the **Wizard** card game, available in two independent versions that share the same save file format.

| Version | Platform | Language | Location |
|---|---|---|---|
| **Desktop** | Windows / macOS / Linux | Python + PyQt6 | `wizard_desktop/` |
| **Android** | Android 8.0+ | Flutter / Dart | `wizard_flutter/` |
| **Leaderboard** | Web (hosted) | Python + FastAPI | `wizard_backend/` |

---

## Repository layout

```
Wizard/
│
├── wizard_desktop/          ─┐
│   ├── main.py               │
│   ├── main_window.py        │
│   ├── setup_view.py         │  Desktop app (Python/PyQt6)
│   ├── game_view.py          │
│   ├── game_control.py       │
│   ├── save_manager.py       │
│   ├── leaderboard_client.py │
│   ├── translations.py       │
│   ├── app_settings.py       │
│   ├── style.py              │
│   ├── dialogs.py            │
│   └── sounds/              ─┘
│
├── wizard_flutter/          ─┐
│   ├── lib/                  │
│   │   ├── main.dart         │
│   │   ├── domain/           │
│   │   ├── i18n/             │  Android app (Flutter/Dart)
│   │   ├── persistence/      │
│   │   ├── state/            │
│   │   ├── theme/            │
│   │   ├── screens/          │
│   │   └── widgets/          │
│   └── android/             ─┘
│
└── wizard_backend/          ─┐
    ├── main.py               │
    ├── database.py           │  Leaderboard server (FastAPI)
    ├── templates/            │
    └── requirements.txt     ─┘
```

---

## Desktop app (Python / PyQt6)

### Setup

```bash
cd wizard_desktop
pip install PyQt6 matplotlib numpy
python main.py
```

### Architecture

| File | Responsibility |
|---|---|
| `wizard_desktop/main.py` | Entry point |
| `wizard_desktop/game_control.py` | Game model — scoring, undo, serialisation (`RoundResult`, `Player`, `GameControl`, `RoundEvents`) |
| `wizard_desktop/save_manager.py` | JSON save / load / plot export |
| `wizard_desktop/translations.py` | All UI strings in de / en / fr / hi |
| `wizard_desktop/app_settings.py` | Language, theme, leaderboard URL (`~/.wizard_gui_settings.json`) |
| `wizard_desktop/main_window.py` | Main window, screen transitions, celebration logic |
| `wizard_desktop/setup_view.py` | Player setup screen |
| `wizard_desktop/game_view.py` | Gameplay screen — point entry, Matplotlib chart |
| `wizard_desktop/dialogs.py` | All dialog classes |
| `wizard_desktop/style.py` | Central design system (colours, stylesheet) |

### Save location

```
~/.wizard_gui/games/*.json
```

---

## Android app (Flutter / Dart)

### Setup

1. Install [Flutter](https://docs.flutter.dev/get-started/install/windows/mobile) (SDK 3.x)
2. Install [Android Studio](https://developer.android.com/studio) to get the Android SDK
3. Copy `wizard_flutter/android/local.properties.template` to `wizard_flutter/android/local.properties` and fill in your SDK paths
4. Accept SDK licenses: `flutter doctor --android-licenses`

```bash
cd wizard_flutter
flutter pub get
flutter run           # run on connected device / emulator
```

### Build

```bash
flutter build apk --release           # APK for sideloading
flutter build appbundle               # AAB for Play Store
```

Release APK output: `wizard_flutter/build/app/outputs/flutter-apk/app-release.apk`

### Architecture

| File / folder | Responsibility |
|---|---|
| `lib/main.dart` | Entry point, Provider wiring |
| `lib/domain/` | Game model — full Dart port of `game_control.py` |
| `lib/i18n/translations.dart` | All UI strings in de / en / fr / hi |
| `lib/persistence/app_settings.dart` | Language, theme, and leaderboard URL via `SharedPreferences` |
| `lib/persistence/save_manager.dart` | JSON save / load / delete, desktop-compatible schema |
| `lib/state/game_notifier.dart` | `ChangeNotifier` owning `GameControl` + active group, exposes all game actions |
| `lib/theme/app_theme.dart` | Dark and light `ThemeData`, colour palette |
| `lib/services/leaderboard_service.dart` | HTTP client for groups, leaderboards, and game submission |
| `lib/screens/setup_screen.dart` | Player setup — group selection/creation, player name entry |
| `lib/screens/game_screen.dart` | Gameplay — bids, chart, groups LB, my group LB via 4-tab `TabBarView` |
| `lib/screens/settings_screen.dart` | Language, theme, and leaderboard URL settings |
| `lib/screens/podium_screen.dart` | End-of-game podium |
| `lib/widgets/player_entry_card.dart` | Per-player card with bid / made spinners |
| `lib/widgets/score_chart.dart` | Score progression line chart (`fl_chart`) |
| `lib/widgets/event_overlay.dart` | Animated celebration toast |

### Minimum Android version

Android 8.0 (API 26). Covers ~98% of active Android devices.

---

## Leaderboard (Backend)

A central leaderboard server collects finished games from all clients. It runs as a FastAPI app with SQLite on an Oracle Cloud VM.

- **Live leaderboard:** http://158.180.32.188:8000
- **API docs:** http://158.180.32.188:8000/docs

### How it works

1. Before starting a game, players select or create a **group** (name + 4-digit code).
2. When a game finishes, results are automatically submitted to the server under the active group.
3. Games are deduplicated via SHA-256 hash so re-submitting the same game is safe.
4. On first launch after the update, the desktop app offers a one-time migration of all previously saved games.

### Groups

- Players create **groups** with a name and a unique 4-digit code.
- Groups can be **public** (visible in the global ranking) or **hidden** (accessible by code only).
- Each group has its own **player leaderboard** per game mode.
- A separate **global groups leaderboard** ranks all public groups by games played, average score, and hit rate.

### Player leaderboard criteria

Separate boards for **Standard** and **Multiplicative** game modes, sortable by:

| Criterion | Description |
|---|---|
| Wins | Total games won |
| Win rate | Wins / games played |
| Avg score | Average final score |
| Hit rate | Percentage of rounds where bid = made |
| Highest score | Best single-game score |
| Win streak | Longest consecutive win streak |

### Architecture

| File | Responsibility |
|---|---|
| `wizard_backend/main.py` | FastAPI app, all API endpoints, HTML leaderboard page |
| `wizard_backend/database.py` | SQLite layer — groups, games, player results, leaderboards |
| `wizard_backend/templates/leaderboard.html` | Responsive dark-themed web leaderboard |
| `wizard_desktop/leaderboard_client.py` | Desktop HTTP client, game hash, QThread workers |
| `wizard_flutter/lib/services/leaderboard_service.dart` | Flutter HTTP client, game hash, submission builder |

---

## Shared save format

Both versions read and write the same JSON schema (`1.1`), so saves are cross-compatible — a game saved on desktop can be loaded on mobile and vice versa.

```json
{
  "schema_version": "1.1",
  "meta": {
    "name": "Spieleabend_Freitag",
    "saved_at": "2025-04-12T20:15:30"
  },
  "game": {
    "round_number": 5,
    "game_mode": "standard",
    "initial_dealer_index": 2,
    "players": [
      {
        "name": "Alice",
        "avatar": "🧙‍♀️",
        "rounds": [
          { "said": 2, "achieved": 2 },
          { "said": 1, "achieved": 0 }
        ]
      }
    ]
  }
}
```

Desktop save location: `~/.wizard_gui/games/`  
Android save location: `<app documents>/wizard_gui/games/`

---

## Working on only one version

The two versions are fully independent codebases. They share no source files — only the save file format.

### If you are working on the desktop app only

The following files are **irrelevant** to you and should not be modified:

```
wizard_flutter/          ← entire folder, ignore it
```

### If you are working on the Android app only

The following files are **irrelevant** to you and should not be modified:

```
wizard_desktop/          ← entire folder, ignore it
```

### If you change the save format

Both versions must be updated together whenever the JSON schema changes. The schema version string lives in:
- Desktop: `wizard_desktop/save_manager.py` → `SCHEMA_VERSION = "1.1"`
- Android: `wizard_flutter/lib/persistence/save_manager.dart` → `const _schemaVersion = '1.1'`

Bump both in the same commit and update the example above.

---

## Features

| Feature | Desktop | Android |
|---|---|---|
| Player setup with avatars | ✅ | ✅ |
| Standard scoring | ✅ | ✅ |
| Multiplicative scoring mode | ✅ | ✅ |
| Bid / made entry per player | ✅ | ✅ |
| Bid-warning banner | ✅ | ✅ |
| Auto-fill made from bid | ✅ | ✅ |
| Score progression chart | ✅ Matplotlib | ✅ fl_chart |
| Undo last round | ✅ | ✅ |
| Save / load games (JSON) | ✅ | ✅ |
| Delete saved games | — | ✅ |
| Round event celebrations | ✅ | ✅ |
| Tobi easter egg | ✅ | ✅ |
| End-of-game podium | ✅ | ✅ |
| Dark / light theme | ✅ | ✅ |
| 4 languages (de/en/fr/hi) | ✅ | ✅ |
| Plot image export | ✅ | — |
| Group selection / creation | ✅ | ✅ |
| Global groups leaderboard | ✅ | ✅ |
| Group player leaderboard | ✅ | ✅ |
| Game submission to backend | ✅ | ✅ |
| Legacy game migration | ✅ | — |
| Cross-compatible saves | ✅ | ✅ |

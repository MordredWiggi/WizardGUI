### 🎯 Objective
Rework the group selection logic and offline play capabilities for both the Desktop (Python) and Mobile (Flutter) applications. The goal is to ensure no default group is selected on startup, support intentional offline play, and provide robust local save/migration to the server later.

### 🛠️ Context
- **Desktop App:** Located in `wizard_backend/` (Wait, no, desktop is in `wizard_desktop/` using Python). Key files: `app_settings.py`, `setup_view.py`, `save_manager.py`, `dialogs.py`, `WizardGUI.py`, `main_window.py`.
- **Mobile App:** Located in `wizard_flutter/` (using Flutter/Dart). Key files: `lib/persistence/app_settings.dart`, `lib/screens/setup_screen.dart`, `lib/persistence/save_manager.dart`, `lib/screens/podium_screen.dart`.

### 🚀 Implementation Plan

#### Part 1: Desktop Application (`wizard_desktop/`)

**Step 1.1: Remove Default Group Selection**
- **Files to check:** `app_settings.py`, `save_manager.py`, `main_window.py`, `setup_view.py`.
- **Action:** Ensure that upon fresh startup or if no group was explicitly saved by the user, the app boots without attempting to auto-join or auto-select a default group. The initial state should be strictly `None` or `unselected`.

**Step 1.2: UI Updates for Group Selection & Offline Mode**
- **Files:** `setup_view.py`, relevant dialogs in `dialogs.py`.
- **Action:** 
  - Update the group selection UI to clearly show "No Group Selected".
  - Add a visible option/button: "Play Offline / Skip Group Selection".
  - Ensure the user can still join/create a group if they have an internet connection.
  - **Bug Fix:** When the user explicitly clears the group selection, make sure the UI fully resets. Currently, there is a bug where it still displays information about whether a name is in the group. Clear the underlying state models and trigger UI repaints correctly.

**Step 1.3: End-of-Game Offline Reminder**
- **Files:** `game_view.py`, `dialogs.py`, `main_window.py` (wherever game conclusion occurs).
- **Action:** When a game concludes, check the connection state and selected group.
- If no group is selected or it's offline mode, pop up a dialog emphasizing: "This game is not uploaded to a group."
- Provide a button in this dialog to "Save Manually to Device". Update `save_manager.py` if needed to gracefully store these pending uploads locally.

**Step 1.4: Startup Migration for Offline Games**
- **Files:** `WizardGUI.py` or `main_window.py` (boot sequence).
- **Action:** On startup, if an internet connection is established, query the local `save_manager` for any un-uploaded local games.
- If un-uploaded games exist, show a "Migration Dialog" prompting the user to upload their offline game(s) to a group.

---

#### Part 2: Mobile Application (`wizard_flutter/`)

**Step 2.1: Remove Default Group Selection**
- **Files:** `lib/persistence/app_settings.dart`, `lib/state/game_notifier.dart`, `lib/main.dart`.
- **Action:** Similar to desktop, initialize the app state with a nullable group concept. Prevent it from defaulting to a fallback group.

**Step 2.2: Setup Screen & Offline Play Mechanism**
- **Files:** `lib/screens/setup_screen.dart`, `lib/screens/settings_screen.dart`.
- **Action:** 
  - In the Setup Screen, represent the "No Group" state intuitively.
  - Provide a "Continue Offline" / "Skip Group" workflow.
  - Require internet validation only when actively trying to Create or Join a group.
  - **Bug Fix:** When clearing the group in the settings or setup screen, clear all associated state variables completely so that UI elements (like name presence indicators) instantly disappear. Use standard state invalidation (`notifyListeners()` or `setState()` depending on the state management used).

**Step 2.3: End of Game Flow**
- **Files:** `lib/screens/podium_screen.dart`, `lib/widgets/event_overlay.dart`.
- **Action:** When the game finishes, evaluate the group status.
- Show an alert dialog if no group is bound: "Game not uploaded."
- Provide an action button to save the game locally via `lib/persistence/save_manager.dart`.

**Step 2.4: Migration Flow on Startup**
- **Files:** `lib/main.dart` or an initial splash screen logic.
- **Action:** Check for locally cached games that are flagged as `unuploaded`.
- Ping the server to verify connectivity.
- If connected and pending games exist, present a bottom sheet or dialog to map and upload these games to a group.
# Wizard Game Update Plan

### **Phase 1: Core Architecture & Data State Updates**
This phase focuses on the underlying data structures, settings, and offline capabilities needed across both the Python desktop app and the Flutter mobile app.

*   **Step 1: Offline Mode & Caching**
    *   **Desktop:** Update `group_cache.py` and `save_manager.py` to securely store group names and codes locally. 
    *   **Flutter:** Update persistence layers to cache group credentials locally.
    *   **Both:** Modify the game start logic to allow selecting a local group when the network is unreachable. Add offline game queuing: mark games completed offline as "pending sync".
*   **Step 2: Sync Hook for Unassigned Games**
    *   Implement a check on startup/network restore that scans for "unsynced" games.
    *   If an unsynced game lacks an assigned group, prompt the user with a UI hook (similar to the old game migration tool) to assign a group and push it to the leaderboard.
*   **Step 3: New Settings Data Models**
    *   Add a `message_display_duration` property (integer/float) to the app settings configuration on both platforms.
    *   Create a schema for `custom_event_messages` that maps basic game events (e.g., "round won", "zero tricks bid") to user-defined string messages.

### **Phase 2: Desktop UI Refinements (`wizard_desktop/`)**
These steps cover the visual and interaction fixes specific to the Python application.

*   **Step 4: Fix Transparent Messages & Timers**
    *   Locate the event display message overlay/toast implementation (likely in `game_view.py` or `main_window.py`).
    *   Update styling (in `style.py` or directly in the widget) to ensure the background opacity is solid (e.g., 255 alpha) and text color contrasts correctly.
    *   Wire the message visibility timer to use the new `message_display_duration` from user settings.
*   **Step 5: Add Custom Message Settings UI**
    *   Add a new dialog/tab in the settings view (`setup_view.py` or `dialogs.py`) allowing users to map their own text strings to specific game events.
    *   Integrate these mapped messages into the game loop events.
*   **Step 6: Fix Plot Tooltip Clipping**
    *   Inspect hover events on the plot canvas (likely in `leaderboard_widget.py` or where the graph is drawn).
    *   Add boundary clamping logic to the tooltip's X-coordinate so if `cursor_x + tooltip_width > window_width`, the tooltip is bumped to the left of the cursor instead of floating out of bounds.
*   **Step 7: Re-style the "Tricks Made" Button**
    *   Find the button responsible for matching tricks made to tricks bid. Remove the text/style causing it to look ugly.
    *   Change the button label to be a large, clearly visible `=` sign, and ensure sizing aligns well with the adjacent input fields.
*   **Step 8: Audit Desktop Translation Updates**
    *   Check the language switching callback in `translations.py` and `main_window.py`.
    *   Ensure all static labels, button texts, and plot legends are explicitly redrawn/re-translated when a language toggle occurs, rather than requiring an app restart.

### **Phase 3: Flutter App Fixes (`wizard_flutter/`)**
These steps address behavioral and UI bugs inside the Flutter client.

*   **Step 9: Fix Chart Interpolation & Hover Bugs**
    *   *Interpolation:* Change the line chart configuration to map point-to-point directly (e.g., if using `fl_chart`, set `isCurved: false`).
    *   *Hover state:* Fix the touch mapping/hover logic. Ensure the touched spot correctly updates the state with the point data instead of breaking, and verify no default "white-out" styling overriding the hover state unprompted.
*   **Step 10: Correct the Round Counter**
    *   Locate the game state logic providing the round number to the UI (inside `lib/state/` or `lib/screens/`).
    *   Shift the index logic to display the *current* round being actively played instead of relying on the last completed round index.
*   **Step 11: Message Durations & Custom Messages**
    *   Update `ScaffoldMessenger.showSnackBar()` or custom toast durations to reference the user's `message_display_duration` setting.
    *   Implement the Flutter UI components in the settings screen for defining custom messages for the new event system, and apply them dynamically during the game.
*   **Step 12: Audit Flutter Translation Updates**
    *   Verify the `i18n` implementation (e.g., `flutter_localizations` or custom provider). 
    *   Ensure UI elements are properly wrapped in `Builder` or consume the localization context so they actively rebuild when `Locale` changes. Ensure no hardcoded strings bypass the locale state.

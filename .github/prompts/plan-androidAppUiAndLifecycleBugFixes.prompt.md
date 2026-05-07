## Plan: Android App UI and Lifecycle Bug Fixes

This plan outlines the specific steps needed to implement the stretched header buttons, update the layout of player points in the 'Bid' section, and address the app lifecycle save bug.

**Steps**
1. Update `TabBar` settings to make the header span left-to-right.
2. Modify the `PlayerEntryCard` layout to place the score next to the player's name instead of beneath it.
3. Update `GameNotifier` to store the current file name during manual save / loading to prevent duplicate game save files.
4. Add an `autoSave()` method to `GameNotifier` and invoke it round completion.
5. Hook into Flutter's app lifecycle within the game screen to trigger the existing `savePaused()` logic when the app enters a paused or detached state.

**Relevant files**
- `wizard_flutter/lib/screens/game_screen.dart` — 
  - In the `_buildUI` (or similar) method, update the `TabBar` configuration by changing `isScrollable` to `false` and removing or adapting the `tabAlignment` property.
  - Implement `WidgetsBindingObserver` on `_GameScreenState`. Add the observer in `initState` and remove it in `dispose`.
  - Override `didChangeAppLifecycleState` to call `notifier.savePaused()` when the lifecycle state changes to `AppLifecycleState.paused` or `AppLifecycleState.detached`.
  - After `notifier.submitRound()` is called in `_completeRound()`, add a call to `notifier.autoSave()`.
- `wizard_flutter/lib/widgets/player_entry_card.dart` — 
  - Update the `build` method layout. Change the vertical `Column` that currently wraps the player's name `Row` and the score `Row` into a single `Row` layout. Use a `Spacer()` to align the current score (`player.currentScore`) and its delta badge directly to the right side of the player's name.
- `wizard_flutter/lib/state/game_notifier.dart` — 
  - Add a state variable (e.g., `String? currentSaveName`) to retain the active game's filename.
  - Update `loadFromFile()` and `saveGame()` to properly set `currentSaveName` whenever a game is loaded or a new save file is generated.
  - Add an `autoSave()` method that delegates to `saveGame(name: currentSaveName)` if it exists, mitigating unnecessary duplicate file creation.

**Verification**
1. Open a game, and verify that the "Bid", "Chart", "Groups", "My Group" header buttons stretch fully across the screen without horizontal scrolling.
2. Check the Game Screen ('Bid' phase) and confirm the player's score and point delta are on the same line to the right of the player name.
3. Complete a single round in a game, verify that a save file of the game is updated automatically without manual intervention.
4. Minimize the application mid-game (forcing `AppLifecycleState.paused`), then kill the app completely. Reopen the app and verify the "paused game" overlay appears, allowing the player to resume accurately from the partial state — identical to using the mid-game "Home" button.

**Decisions**
- Implemented `WidgetsBindingObserver` strictly within `GameScreen` so the app is only monitored for mid-game pauses while actually in game mode.
- Tracking `currentSaveName` in `GameNotifier` ensures that round-by-round autosaves do not endlessly spawn new save slots for the same session.
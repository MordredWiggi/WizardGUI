## Plan: Flutter Android Two-Layer Migration

Rebuild the desktop PyQt app as an Android Flutter app while preserving gameplay rules, save/load behavior, and the main menu flow. Use existing Python modules as behavioral source-of-truth, then implement equivalent Dart logic plus two gameplay layers:
1. Layer 1: players list and point entry
2. Layer 2: points-over-rounds plot

### Steps
1. Phase 1 - Scope lock and architecture baseline: keep desktop app unchanged, define a parallel Flutter Android app area in this repo, and lock parity goals from current flow (startup -> menu/setup -> gameplay -> round submit -> podium/new game).
2. Phase 2 - Domain model port (blocks UI): port core logic from [game_control.py](game_control.py#L1) into Dart with parity for standard/multiplicative scoring, dealer rotation, total rounds, event detection, undo, and serialization behavior matching [game_control.py](game_control.py#L262) and [game_control.py](game_control.py#L309).
3. Phase 3 - Persistence and i18n foundation (parallel with UI shell after contracts exist): implement local storage and metadata behavior equivalent to [save_manager.py](save_manager.py#L1), and preserve translation key coverage from [translations.py](translations.py#L1).
4. Phase 4 - Navigation and main menu shell (depends on 1, can start once interfaces are defined): implement menu/setup behavior based on [setup_view.py](setup_view.py#L1), including new game, saved games list, load action, settings, and game mode selection.
5. Phase 5 - Gameplay Layer 1 (depends on 2): implement players list plus point-entry interactions from [game_view.py](game_view.py#L1), including announced/achieved entry, totals validation, complete round, undo/save/new game actions, and score delta/leader display.
6. Phase 6 - Gameplay Layer 2 (depends on 2, parallel with 5 after shared state exists): implement score progression chart layer with per-player lines, average line, current-round highlighting, and score-sorted legend based on intent from [game_view.py](game_view.py#L66).
7. Phase 7 - Two-layer integration (depends on 5 and 6): wire both layers to shared game state (tab switch or pager), ensure round submission on Layer 1 immediately updates Layer 2, and preserve expected input/state continuity.
8. Phase 8 - Endgame and event feedback (depends on 5): port round-event-driven feedback and podium/game-over flow from [main_window.py](main_window.py#L95), adapted to mobile-safe overlays/animations.
9. Phase 9 - Android packaging and handoff verification: produce reproducible Android build/test flow (debug + release), emulator and device checks, and signing-ready artifacts.

### Relevant files
- [main.py](main.py#L1): startup responsibilities reference.
- [main_window.py](main_window.py#L1): state transitions, event handling, endgame flow.
- [setup_view.py](setup_view.py#L1): menu/setup behavior to preserve.
- [game_view.py](game_view.py#L1): player entry and chart behavior baseline.
- [game_control.py](game_control.py#L1): authoritative gameplay and scoring rules.
- [save_manager.py](save_manager.py#L1): save/load metadata and payload structure.
- [translations.py](translations.py#L1): localization key source.
- [app_settings.py](app_settings.py#L1): settings behavior reference.

### Verification
1. Domain parity tests: validate Dart outputs against expected scenarios from [game_control.py](game_control.py#L262) for both game modes, including edge cases (perfect rounds, large misses, undo chains, game-over boundary).
2. Persistence tests: verify saved payload schema/version/metadata and full reconstruction parity with [save_manager.py](save_manager.py#L20) and [game_control.py](game_control.py#L318).
3. UI integration tests: menu -> start game -> Layer 1 input -> Layer 2 chart update -> endgame podium -> return to menu.
4. Manual device checks: phone/tablet, portrait/landscape, touch targets, keyboard behavior for numeric entry, layer switching usability.
5. Performance checks: long-game simulation with max players and responsive chart redraw.
6. Release checks: debug/release APK or AAB build, install/update path, storage access for save/load and chart export/share.

### Decisions
- Chosen implementation stack: Flutter (Dart), Android-first.
- In scope: preserve main menu concept, implement two gameplay layers, preserve rules and save/load semantics, preserve language/theme behavior.
- Out of scope for this pass: scoring-rule redesign, cloud sync/backend, networking/multiplayer, desktop refactor.

### Further considerations
1. Layer navigation choice: tab switch vs swipe pager. Recommendation: swipe pager with visible tab indicator.
2. Chart approach: library first vs custom painter. Recommendation: use a chart library first, switch only if parity gaps appear.
3. Save compatibility: desktop JSON import now vs later. Recommendation: support desktop JSON import in initial mobile release.
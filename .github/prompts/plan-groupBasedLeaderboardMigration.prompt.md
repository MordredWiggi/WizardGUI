You are implementing a major cross-platform leaderboard migration in this repository.
Work end-to-end across backend, desktop app, Flutter/mobile app, database/server hosting, and documentation.

### Objective
Replace the current global player leaderboard model with a group-based leaderboard system:

1. Players can create groups.
2. Global leaderboard should become a global groups leaderboard (group-level metrics only).
3. Each group keeps its own player leaderboard (name mapping remains inside group).
4. In setup flow, users must choose the target group before entering player names:
   - select existing group (searchable dropdown) plus mandatory 4-digit code validation
   - or create new group (name + visibility in global groups leaderboard)
5. Setup and in-game navigation must support:
   - saved games
   - global groups leaderboard
   - selected-group leaderboard
6. Legacy game import must be updated:
   - dialog to create/select groups
   - each imported old game must be explicitly assigned to a group
7. Implement for desktop and Android/mobile (Flutter), plus backend API/database/server hosting updates.
8. Update documentation (root + backend + Flutter README) accordingly.
9. Validate each step thoroughly before moving on.

### Required Decisions (already finalized)
1. Group code format: exactly 4 digits.
2. Hidden group behavior: excluded from global groups leaderboard, but accessible with valid code.
3. Legacy import behavior: explicit per-game group assignment required.

### Required Tools and How to Use Them
Use these tools actively and in parallel where possible:

1. Discovery and architecture mapping:
   - runSubagent (Explore)
   - read_file
   - file_search
   - grep_search
   - list_dir
2. Clarifications when ambiguity appears:
   - vscode_askQuestions
3. Change safety and validation:
   - get_changed_files
   - get_errors
   - test/terminal commands if available in your environment
4. Efficiency:
   - multi_tool_use.parallel for independent read/search operations

### Primary Files to Touch
Backend:
- wizard_backend/main.py
- wizard_backend/database.py
- wizard_backend/templates/leaderboard.html
- wizard_backend/README.md

Desktop:
- wizard_desktop/setup_view.py
- wizard_desktop/game_view.py
- wizard_desktop/leaderboard_widget.py
- wizard_desktop/leaderboard_client.py
- wizard_desktop/dialogs.py
- wizard_desktop/game_control.py
- wizard_desktop/save_manager.py

Flutter/mobile:
- wizard_flutter/lib/screens/setup_screen.dart
- wizard_flutter/lib/screens/game_screen.dart
- wizard_flutter/lib/state/game_notifier.dart
- wizard_flutter/lib/persistence/save_manager.dart
- wizard_flutter/lib/domain/game_control.dart
- wizard_flutter/lib/main.dart
- wizard_flutter/README.md

Repo docs:
- README.md

### Implementation Requirements by Phase

1. Backend schema and migration
1. Add group entities and membership/linking to games.
2. Enforce unique 4-digit group code.
3. Make migration idempotent and safe for existing data.
4. Preserve backward compatibility for old game submissions where possible.

2. Backend API and aggregation
1. Add endpoints for group create/list/select/verify-code.
2. Add selected-group player leaderboard endpoint.
3. Add global groups leaderboard endpoint with metrics like:
   - total games played in group
   - average points per round in group
4. Keep legacy behavior stable or provide explicit compatibility mode.
5. Add robust error handling for invalid code/group/not found.

3. Desktop setup flow
1. Insert group selection/create UI before player-name input.
2. Existing group selection requires successful code validation.
3. New group creation includes name and visibility toggle.
4. Block game start until group state is valid.

4. Desktop navigation and runtime
1. Setup bottom area: saved games, global groups leaderboard, selected-group leaderboard.
2. In-game view switching: graph, global groups leaderboard, selected-group leaderboard.
3. Ensure selected group is carried into gameplay and submissions.

5. Desktop import migration
1. Extend import dialog to create/select groups.
2. Require explicit per-imported-game mapping to a group.
3. Support progress reporting and failure messaging.

6. Flutter/mobile setup and runtime
1. Mirror desktop group selection/create/code flow in setup.
2. Add runtime switching between chart, global groups leaderboard, and selected-group leaderboard.
3. Ensure state propagation and persistence consistency.

7. Flutter/mobile import migration
1. If import exists, update it to explicit per-game group mapping.
2. If import does not exist, add equivalent migration/import flow aligned with desktop behavior.

8. Documentation and hosting
1. Update API docs, payload examples, and migration notes.
2. Document operational DB migration/hosting rollout steps.
3. Document UX behavior for group visibility and code-protected access.

### Quality Gates (must pass)
1. Functional
1. Create group, validate code, submit game to group, retrieve group leaderboard.
2. Global groups leaderboard aggregates correctly.
3. Hidden groups are excluded globally but accessible via code.

2. Security and abuse resistance
1. Wrong code blocks access and group assignment.
2. Repeated invalid code handling is explicit and safe.

3. Regression
1. Old saves and legacy submission paths are not broken unexpectedly.
2. Existing non-group workflows still work or are intentionally migrated with clear UX.

4. Cross-platform parity
1. Desktop and Flutter behavior is aligned for group creation/selection, navigation, and import mapping.

5. Documentation
1. README updates match real behavior and endpoint contracts.

### Execution Rules
1. Do not do a shallow partial update.
2. Implement all layers in one coherent migration path.
3. After each phase, run relevant checks and fix before proceeding.
4. Keep changes atomic and reviewable.
5. Provide a final report including:
   - changed files
   - endpoint/schema changes
   - migration notes
   - test results
   - known risks and follow-ups
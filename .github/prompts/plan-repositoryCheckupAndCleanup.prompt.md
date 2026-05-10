## Plan: Repository Checkup and Cleanup

This plan outlines a comprehensive cleanup of temporary artifacts, unused files, and a general health check (linting, formatting, dependencies) across the Python and Flutter sub-projects.

**Steps**

**Phase 1: Artifact & Temporary File Cleanup**
1. Delete merge-conflict or backup artifacts: Remove all `.orig` files in `wizard_desktop/` (`game_control.py.orig`, `game_view.py.orig`, `main_window.py.orig`).
2. Clean Python build artifacts: Safely remove the `build/` directory at the root and `wizard_desktop/build/`.
3. Clean Flutter build artifacts: Run `flutter clean` inside the `wizard_flutter/` directory to clear out `wizard_flutter/build/` and `.dart_tool/`.

**Phase 2: Python Sub-projects Checkup (Backend & Desktop)**
1. *Depends on Phase 1.* Format Python code: Run a formatter like `black` or `autopep8` over `wizard_backend/` and `wizard_desktop/`.
2. Lint Python code: Run `flake8` or `pylint` on both Python directories to detect potential errors or styling issues.
3. Check dependencies: Review `wizard_backend/requirements.txt` and `wizard_desktop/requirements.txt` for severely outdated packages. 

**Phase 3: Flutter Sub-project Checkup**
1. *Depends on Phase 1.* Format Dart code: Run `dart format .` inside `wizard_flutter/`.
2. Lint Dart code: Run `flutter analyze` inside `wizard_flutter/` to identify issues.
3. Check dependencies: Run `flutter pub outdated` in `wizard_flutter/` to check for package updates.

**Relevant files**
- `wizard_desktop/*.orig` — temporary files to delete.
- `build/` and `wizard_desktop/build/` — build artifacts to delete.
- `wizard_backend/` and `wizard_desktop/` — target directories for Python linting/formatting.
- `wizard_flutter/` — target directory for Flutter cleanup/linting/formatting.

**Verification**
1. Verify no `.orig` files remain in the workspace.
2. Verify `flutter analyze` returns no errors.
3. Verify Python linting reports are clean or have minimal ignorable warnings.
4. Verify the application apps (backend, desktop, flutter) still build/run successfully after cleanup.

**Decisions**
- Excluded automatic major dependency upgrades to prevent breaking changes; they will only be reported.
- Excluded deletion of `WizardGUI.spec` as it might be a customized PyInstaller configuration.
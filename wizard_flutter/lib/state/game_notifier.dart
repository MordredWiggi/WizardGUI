import 'package:flutter/foundation.dart';
import '../domain/game_control.dart';
import '../domain/game_mode.dart';
import '../domain/round_result.dart';
import '../domain/round_events.dart';
import '../persistence/save_manager.dart';

/// Central Provider notifier – owns the active GameControl, the active group,
/// and exposes all mutations the UI needs.
/// Mirrors the role of MainWindow._game in the Python desktop app.
class GameNotifier extends ChangeNotifier {
  GameControl? _game;
  final SaveManager _saveManager;

  /// The currently selected group dict (id, name, code, visibility), or null.
  Map<String, dynamic>? _activeGroup;

  GameNotifier({SaveManager? saveManager})
      : _saveManager = saveManager ?? SaveManager();

  GameControl? get game => _game;
  bool get hasGame => _game != null;
  Map<String, dynamic>? get activeGroup => _activeGroup;

  // ── Group management ────────────────────────────────────────────────────────

  void setGroup(Map<String, dynamic>? group) {
    _activeGroup = group;
    notifyListeners();
  }

  void clearGroup() {
    _activeGroup = null;
    notifyListeners();
  }

  // ── Game lifecycle ─────────────────────────────────────────────────────────

  void startGame(List<Map<String, dynamic>> playerData, String gameMode) {
    _game = GameControl(
      playerData: playerData,
      gameMode: gameMode == 'multiplicative'
          ? GameMode.multiplicative
          : GameMode.standard,
    );
    notifyListeners();
  }

  void loadGame(GameControl game) {
    _game = game;
    notifyListeners();
  }

  void endGame() {
    _game = null;
    notifyListeners();
  }

  // ── Round actions ──────────────────────────────────────────────────────────

  /// Submit results; returns RoundEvents for the UI to react to.
  RoundEvents submitRound(List<RoundResult> results) {
    assert(_game != null);
    final (:game, :events) = _game!.submitRound(results);
    _game = game;
    notifyListeners();
    return events;
  }

  bool undoRound() {
    if (_game == null || _game!.roundNumber == 0) return false;
    _game = _game!.undoRound();
    notifyListeners();
    return true;
  }

  // ── Persistence ────────────────────────────────────────────────────────────

  Future<String> saveGame({String? name}) async {
    assert(_game != null);
    return _saveManager.saveGame(_game!.toJson(), gameName: name);
  }

  /// Persist the current finished game with pending_sync=true so it can be
  /// uploaded on a later launch (mirrors desktop SaveManager.save_game).
  Future<String> savePendingGame({String? groupCode}) async {
    assert(_game != null);
    return _saveManager.saveGame(
      _game!.toJson(),
      pendingSync: true,
      groupCode: groupCode,
    );
  }

  Future<void> loadFromFile(String filePath) async {
    final data = await _saveManager.loadGame(filePath);
    _game = GameControl.fromJson(data);
    notifyListeners();
  }

  Future<List<SavedGameMeta>> listSavedGames() =>
      _saveManager.listSavedGames();

  Future<List<PendingSyncGame>> listPendingSyncGames() =>
      _saveManager.listPendingSyncGames();

  Future<void> markSynced(String filePath) =>
      _saveManager.markSynced(filePath);

  Future<void> updatePendingGroupCode(String filePath, String? groupCode) =>
      _saveManager.updatePendingGroupCode(filePath, groupCode);

  Future<void> deleteSavedGame(String filePath) =>
      _saveManager.deleteGame(filePath);

  // ── Paused-game (Home button) ──────────────────────────────────────────────

  Future<void> savePaused() async {
    if (_game == null) return;
    await _saveManager.savePaused(_game!.toJson(), group: _activeGroup);
  }

  Future<bool> hasPaused() => _saveManager.hasPaused();

  /// Returns the raw paused payload (`{'game': ..., 'group': ...}`) without
  /// restoring it — used by the UI to render the resume banner.
  Future<Map<String, dynamic>?> peekPaused() => _saveManager.loadPaused();

  /// Restore a paused game; on success the game + group are re-bound and the
  /// paused file is cleared. Returns true when a paused game was loaded.
  Future<bool> resumePaused() async {
    final data = await _saveManager.loadPaused();
    if (data == null) return false;
    try {
      _game = GameControl.fromJson(
        Map<String, dynamic>.from(data['game'] as Map),
      );
    } catch (_) {
      await _saveManager.clearPaused();
      return false;
    }
    final group = data['group'];
    _activeGroup = group is Map ? Map<String, dynamic>.from(group) : null;
    await _saveManager.clearPaused();
    notifyListeners();
    return true;
  }

  Future<void> clearPaused() => _saveManager.clearPaused();
}

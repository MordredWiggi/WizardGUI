import 'package:flutter/foundation.dart';
import '../domain/game_control.dart';
import '../domain/game_mode.dart';
import '../domain/round_result.dart';
import '../domain/round_events.dart';
import '../persistence/save_manager.dart';

/// Central Provider notifier – owns the active GameControl and exposes
/// all mutations the UI needs.  Mirrors the role of MainWindow._game in the
/// Python desktop app.
class GameNotifier extends ChangeNotifier {
  GameControl? _game;
  final SaveManager _saveManager;

  GameNotifier({SaveManager? saveManager})
      : _saveManager = saveManager ?? SaveManager();

  GameControl? get game => _game;
  bool get hasGame => _game != null;

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

  Future<void> loadFromFile(String filePath) async {
    final data = await _saveManager.loadGame(filePath);
    _game = GameControl.fromJson(data);
    notifyListeners();
  }

  Future<List<SavedGameMeta>> listSavedGames() =>
      _saveManager.listSavedGames();

  Future<void> deleteSavedGame(String filePath) =>
      _saveManager.deleteGame(filePath);
}

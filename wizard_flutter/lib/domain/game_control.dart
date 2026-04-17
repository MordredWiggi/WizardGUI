import 'dart:math';
import 'game_mode.dart';
import 'player.dart';
import 'round_result.dart';
import 'round_events.dart';

/// Central model holding the complete state of one game.
/// Mirrors Python GameControl class with immutable-style mutation.
class GameControl {
  final GameMode gameMode;
  final List<Player> players;
  final int roundNumber;
  final int initialDealerIndex;

  GameControl({
    required List<Map<String, dynamic>> playerData,
    int? initialDealerIndex,
    this.gameMode = GameMode.standard,
  })  : roundNumber = 0,
        initialDealerIndex = initialDealerIndex ??
            (playerData.isEmpty ? 0 : Random().nextInt(playerData.length)),
        players = playerData
            .map((p) => Player(
                  name: p['name'] as String,
                  avatar: (p['avatar'] as String?) ?? '🧙‍♂️',
                  initialScore: gameMode == GameMode.multiplicative ? 100 : 0,
                ))
            .toList();

  GameControl._raw({
    required this.gameMode,
    required this.players,
    required this.roundNumber,
    required this.initialDealerIndex,
  });

  // --- derived properties --------------------------------------------------

  int get numPlayers => players.length;
  List<String> get playerNames => players.map((p) => p.name).toList();

  /// Total rounds = 60 ÷ num_players (Wizard rule).
  int get totalRounds => numPlayers == 0 ? 0 : 60 ~/ numPlayers;

  bool get isGameOver => roundNumber >= totalRounds;

  int get currentDealerIndex =>
      numPlayers == 0 ? 0 : (initialDealerIndex + roundNumber) % numPlayers;

  Player? get currentDealer =>
      players.isEmpty ? null : players[currentDealerIndex];

  /// Cards dealt this round = round number + 1 (1-indexed).
  int get cardsThisRound => roundNumber + 1;

  /// 1-indexed number of the round currently being played.
  /// Equals `roundNumber + 1` while the game is active (players are entering
  /// bids for the next round), and `totalRounds` once the last round has been
  /// submitted — so the UI never shows a round number greater than the total.
  int get currentRoundDisplay =>
      isGameOver ? totalRounds : roundNumber + 1;

  List<int> get roundIndices => List.generate(roundNumber + 1, (i) => i);

  List<List<int>> get allScores => players.map((p) => p.scores).toList();

  List<double> get averages => List.generate(roundNumber + 1, (r) {
        final total = players.fold(0, (sum, p) => sum + p.scores[r]);
        return total / numPlayers;
      });

  Player? get leader => players.isEmpty
      ? null
      : players.reduce((a, b) => a.currentScore >= b.currentScore ? a : b);

  List<Player> get leaders {
    if (players.isEmpty) return [];
    final maxScore = players.map((p) => p.currentScore).reduce(max);
    return players.where((p) => p.currentScore == maxScore).toList();
  }

  List<int> lastDeltas() {
    if (roundNumber == 0) return List.filled(numPlayers, 0);
    return players.map((p) => p.scores.last - p.scores[p.scores.length - 2]).toList();
  }

  // --- game actions --------------------------------------------------------

  /// Apply round results; returns event info so the UI can show effects.
  ({GameControl game, RoundEvents events}) submitRound(
      List<RoundResult> results) {
    final oldLeader = leader;

    var newPlayers = <Player>[];
    for (var i = 0; i < players.length; i++) {
      final result = results[i];
      newPlayers.add(
        gameMode == GameMode.multiplicative
            ? players[i].applyRoundMultiplicative(result)
            : players[i].applyRound(result),
      );
    }

    final updated = GameControl._raw(
      gameMode: gameMode,
      players: newPlayers,
      roundNumber: roundNumber + 1,
      initialDealerIndex: initialDealerIndex,
    );

    final newLeader = updated.leader;
    final deltas = updated.lastDeltas();

    final maxDelta = deltas.reduce(max);
    final minDelta = deltas.reduce(min);
    final maxPlayer = newPlayers[deltas.indexOf(maxDelta)];
    final minPlayer = newPlayers[deltas.indexOf(minDelta)];

    final hugeLossPlayer = minDelta <= -40 ? minPlayer : null;

    final events = RoundEvents(
      newLeader: newLeader != oldLeader ? newLeader : null,
      bigScorer: maxDelta >= 50 ? maxPlayer : null,
      bigScoreDelta: maxDelta,
      firePlayer: newPlayers
          .where((p) => p.consecutivePerfect >= 3)
          .firstOrNull,
      negativePlayer: minDelta < 0 ? minPlayer : null,
      gameOver: updated.isGameOver,
      bowPlayers: newPlayers
          .where((p) => p.consecutiveLosses == 3)
          .toList(),
      revengePlayers: newPlayers
          .where((p) => p.revengeTriggered)
          .toList(),
      hugeLossPlayer: hugeLossPlayer,
      hugeLossDelta: hugeLossPlayer != null ? minDelta : 0,
    );

    return (game: updated, events: events);
  }

  /// Returns updated game with last round reversed, or same game if no rounds.
  GameControl undoRound() {
    if (roundNumber <= 0) return this;
    return GameControl._raw(
      gameMode: gameMode,
      players: players.map((p) => p.undoRound()).toList(),
      roundNumber: roundNumber - 1,
      initialDealerIndex: initialDealerIndex,
    );
  }

  // --- serialisation -------------------------------------------------------

  Map<String, dynamic> toJson() => {
        'players': players.map((p) => p.toJson()).toList(),
        'round_number': roundNumber,
        'initial_dealer_index': initialDealerIndex,
        'game_mode': gameMode.toJson(),
      };

  factory GameControl.fromJson(Map<String, dynamic> json) {
    final gameMode =
        GameMode.fromJson((json['game_mode'] as String?) ?? 'standard');
    final playersJson = json['players'] as List;

    final loadedPlayers = playersJson
        .map((p) => Player.fromJson(p as Map<String, dynamic>, gameMode: gameMode))
        .toList();

    return GameControl._raw(
      gameMode: gameMode,
      players: loadedPlayers,
      roundNumber: json['round_number'] as int,
      initialDealerIndex: json['initial_dealer_index'] as int,
    );
  }
}

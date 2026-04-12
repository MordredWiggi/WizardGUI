import 'player.dart';

/// Mirrors Python RoundEvents dataclass.
/// Returned by GameControl.submitRound so the UI can trigger effects.
class RoundEvents {
  final Player? newLeader;       // null → no leadership change
  final Player? bigScorer;       // gained ≥ 50 pts
  final int bigScoreDelta;
  final Player? firePlayer;      // ≥ 3 consecutive perfect rounds
  final Player? negativePlayer;  // biggest loss this round
  final bool gameOver;
  final List<Player> bowPlayers;     // exactly 3 consecutive losses
  final List<Player> revengePlayers; // 2 gains after ≥2 losses
  final Player? hugeLossPlayer;      // lost ≥ 40 pts
  final int hugeLossDelta;           // the actual negative delta

  const RoundEvents({
    this.newLeader,
    this.bigScorer,
    this.bigScoreDelta = 0,
    this.firePlayer,
    this.negativePlayer,
    this.gameOver = false,
    this.bowPlayers = const [],
    this.revengePlayers = const [],
    this.hugeLossPlayer,
    this.hugeLossDelta = 0,
  });
}

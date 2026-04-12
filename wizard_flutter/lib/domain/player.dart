import 'round_result.dart';
import 'game_mode.dart';

/// Mirrors Python Player dataclass.
class Player {
  final String name;
  final String avatar;

  // scores[0] = initial score; scores[i] = cumulative score after round i
  final List<int> scores;
  final List<RoundResult> roundResults;

  Player({
    required this.name,
    this.avatar = '🧙‍♂️',
    int initialScore = 0,
  })  : scores = [initialScore],
        roundResults = [];

  Player._raw({
    required this.name,
    required this.avatar,
    required List<int> scores,
    required List<RoundResult> roundResults,
  })  : scores = scores,
        roundResults = roundResults;

  int get currentScore => scores.last;

  /// Number of consecutive perfect rounds at end of history.
  int get consecutivePerfect {
    int count = 0;
    for (final r in roundResults.reversed) {
      if (r.isPerfect) {
        count++;
      } else {
        break;
      }
    }
    return count;
  }

  /// Number of consecutive negative-delta rounds at end of history.
  int get consecutiveLosses {
    int count = 0;
    for (final r in roundResults.reversed) {
      if (r.scoreDelta < 0) {
        count++;
      } else {
        break;
      }
    }
    return count;
  }

  /// True if gained 2 rounds in a row after losing 2+ rounds in a row before.
  bool get revengeTriggered {
    if (roundResults.length < 4) return false;
    final r = roundResults;
    return r[r.length - 1].scoreDelta > 0 &&
        r[r.length - 2].scoreDelta > 0 &&
        r[r.length - 3].scoreDelta < 0 &&
        r[r.length - 4].scoreDelta < 0;
  }

  // --- mutating copies (immutable-style) ------------------------------------

  Player applyRound(RoundResult result) {
    final newResults = [...roundResults, result];
    final newScores = [...scores, currentScore + result.scoreDelta];
    return Player._raw(
      name: name,
      avatar: avatar,
      scores: newScores,
      roundResults: newResults,
    );
  }

  Player applyRoundMultiplicative(RoundResult result) {
    final newResults = [...roundResults, result];
    final double newScore;
    if (result.said == result.achieved) {
      newScore = currentScore * (2 + result.achieved).toDouble();
    } else {
      newScore = currentScore / (1 + (result.achieved - result.said).abs());
    }
    final newScores = [...scores, newScore.round()];
    return Player._raw(
      name: name,
      avatar: avatar,
      scores: newScores,
      roundResults: newResults,
    );
  }

  Player undoRound() {
    if (roundResults.isEmpty) return this;
    return Player._raw(
      name: name,
      avatar: avatar,
      scores: scores.sublist(0, scores.length - 1),
      roundResults: roundResults.sublist(0, roundResults.length - 1),
    );
  }

  // --- serialisation --------------------------------------------------------

  Map<String, dynamic> toJson() => {
        'name': name,
        'avatar': avatar,
        'rounds': roundResults.map((r) => r.toJson()).toList(),
      };

  factory Player.fromJson(Map<String, dynamic> json,
      {GameMode gameMode = GameMode.standard}) {
    final int initialScore =
        gameMode == GameMode.multiplicative ? 100 : 0;
    var p = Player(
      name: json['name'] as String,
      avatar: (json['avatar'] as String?) ?? '🧙‍♂️',
      initialScore: initialScore,
    );
    for (final rd in (json['rounds'] as List)) {
      final result = RoundResult.fromJson(rd as Map<String, dynamic>);
      if (gameMode == GameMode.multiplicative) {
        p = p.applyRoundMultiplicative(result);
      } else {
        p = p.applyRound(result);
      }
    }
    return p;
  }
}

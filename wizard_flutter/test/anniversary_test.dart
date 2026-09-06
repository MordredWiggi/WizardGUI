import 'package:flutter_test/flutter_test.dart';
import 'package:wizard_flutter/domain/game_control.dart';
import 'package:wizard_flutter/domain/game_mode.dart';
import 'package:wizard_flutter/domain/round_result.dart';
import 'package:wizard_flutter/services/leaderboard_service.dart';

void main() {
  test('RoundResult cloud adjusts scoring', () {
    const hit = RoundResult(said: 2, achieved: 3, cloud: 1);
    expect(hit.effectiveSaid, 3);
    expect(hit.isPerfect, isTrue);
    expect(hit.scoreDelta, 50);

    const miss = RoundResult(said: 2, achieved: 2, cloud: 1);
    expect(miss.isPerfect, isFalse);
    expect(miss.scoreDelta, -10);

    const zero = RoundResult(said: 1, achieved: 0, cloud: -1);
    expect(zero.scoreDelta, 20);

    expect(const RoundResult(said: 1, achieved: 1).toJson().containsKey('cloud'),
        isFalse);
    expect(RoundResult.fromJson({'said': 1, 'achieved': 2}).cloud, 0);
  });

  test('anniversary game flow with bomb + cloud, undo and serialisation', () {
    var game = GameControl(
      playerData: [
        {'name': 'A'},
        {'name': 'B'},
        {'name': 'C'},
      ],
      initialDealerIndex: 0,
      gameMode: GameMode.anniversary,
    );

    // Round 1 (1 card), bomb played → 0 tricks distributed.
    var res = game.submitRound(const [
      RoundResult(said: 0, achieved: 0),
      RoundResult(said: 1, achieved: 0),
      RoundResult(said: 0, achieved: 0),
    ], bombPlayed: true);
    game = res.game;
    expect(game.bombs, [true]);
    expect(game.players.map((p) => p.currentScore).toList(), [20, -10, 20]);

    // Round 2 (2 cards), cloud +1 on B: said 0 → effective 1, achieved 1.
    res = game.submitRound(const [
      RoundResult(said: 1, achieved: 1),
      RoundResult(said: 0, achieved: 1, cloud: 1),
      RoundResult(said: 0, achieved: 0),
    ]);
    game = res.game;
    expect(game.bombs, [true, false]);
    expect(game.players.map((p) => p.currentScore).toList(), [50, 20, 40]);

    // Serialisation round-trip keeps bombs + cloud.
    final json = game.toJson();
    expect(json['bombs'], [true, false]);
    final restored = GameControl.fromJson(json);
    expect(restored.bombs, [true, false]);
    expect(
        restored.players.map((p) => p.currentScore).toList(), [50, 20, 40]);
    expect(restored.players[1].roundResults[1].cloud, 1);

    // Undo pops the bombs list too.
    final undone = restored.undoRound();
    expect(undone.bombs, [true]);
    expect(undone.roundNumber, 1);

    // Classic games serialise without a bombs key.
    final std = GameControl(
      playerData: [
        {'name': 'A'},
        {'name': 'B'},
      ],
    );
    expect(std.toJson().containsKey('bombs'), isFalse);

    // Submission: cloud round counts as a hit, scores match the app.
    final payload = buildGameSubmission(game.toJson());
    final byName = {
      for (final p in payload['players'] as List) p['name']: p,
    };
    expect(byName['A']['final_score'], 50);
    expect(byName['B']['final_score'], 20);
    expect(byName['C']['final_score'], 40);
    expect(byName['B']['correct_bids'], 1);
    expect(byName['A']['rank'], 1);
    expect(payload['game_mode'], 'anniversary');

    // The cloud changes the game hash.
    final noCloud = game.toJson();
    (((noCloud['players'] as List)[1] as Map)['rounds'] as List)[1] = {
      'said': 0,
      'achieved': 1,
    };
    expect(computeGameHash(game.toJson()) == computeGameHash(noCloud), isFalse);
  });
}

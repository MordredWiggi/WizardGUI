/// Mirrors Python RoundResult dataclass.
class RoundResult {
  final int said;
  final int achieved;

  /// Wolke (Jubiläumsedition): forced bid change of ±1 for this player.
  /// 0 in every other mode / when the cloud wasn't in this player's tricks.
  final int cloud;

  const RoundResult({
    required this.said,
    required this.achieved,
    this.cloud = 0,
  });

  /// Bid that counts for scoring: announcement plus cloud adjustment.
  int get effectiveSaid => said + cloud;

  /// Standard scoring: +20+10*bid on match, -10*|diff| on miss — judged on
  /// the effective bid (announcement plus cloud adjustment).
  int get scoreDelta {
    if (effectiveSaid == achieved) return 20 + effectiveSaid * 10;
    return -10 * (effectiveSaid - achieved).abs();
  }

  bool get isPerfect => effectiveSaid == achieved;

  Map<String, dynamic> toJson() => {
    'said': said,
    'achieved': achieved,
    if (cloud != 0) 'cloud': cloud,
  };

  factory RoundResult.fromJson(Map<String, dynamic> json) => RoundResult(
    said: json['said'] as int,
    achieved: json['achieved'] as int,
    cloud: (json['cloud'] as int?) ?? 0,
  );
}

/// Mirrors Python RoundResult dataclass.
class RoundResult {
  final int said;
  final int achieved;

  const RoundResult({required this.said, required this.achieved});

  /// Standard scoring: +20+10*said on match, -10*|diff| on miss.
  int get scoreDelta {
    if (said == achieved) return 20 + said * 10;
    return -10 * (said - achieved).abs();
  }

  bool get isPerfect => said == achieved;

  Map<String, dynamic> toJson() => {'said': said, 'achieved': achieved};

  factory RoundResult.fromJson(Map<String, dynamic> json) =>
      RoundResult(said: json['said'] as int, achieved: json['achieved'] as int);
}

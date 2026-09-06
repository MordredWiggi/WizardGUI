enum GameMode {
  standard,
  multiplicative,

  /// Jubiläumsedition (25 Jahre): standard scoring plus the special cards.
  /// Scoring-relevant are the bomb (its trick counts for nobody, so one trick
  /// fewer in the round) and the cloud (forces one player's bid ±1).
  anniversary;

  String toJson() => name;

  static GameMode fromJson(String value) => switch (value) {
    'multiplicative' => GameMode.multiplicative,
    'anniversary' => GameMode.anniversary,
    _ => GameMode.standard,
  };
}

enum GameMode {
  standard,
  multiplicative,
  anniversary;

  String toJson() => name;

  static GameMode fromJson(String value) => switch (value) {
    'multiplicative' => GameMode.multiplicative,
    'anniversary' => GameMode.anniversary,
    _ => GameMode.standard,
  };
}

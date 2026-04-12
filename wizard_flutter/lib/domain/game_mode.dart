enum GameMode {
  standard,
  multiplicative;

  String toJson() => name;

  static GameMode fromJson(String value) => switch (value) {
        'multiplicative' => GameMode.multiplicative,
        _ => GameMode.standard,
      };
}

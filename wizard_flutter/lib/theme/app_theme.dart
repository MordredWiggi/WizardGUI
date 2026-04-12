import 'package:flutter/material.dart';

// ── Colour palette (mirrors desktop style.py) ─────────────────────────────────
const Color kAccent = Color(0xFFC9A84C);       // gold
const Color kAccentDim = Color(0xFF8A6E30);
const Color kBgBase = Color(0xFF0D0D1A);
const Color kBgPanel = Color(0xFF12122B);
const Color kBgCard = Color(0xFF1A1A3A);
const Color kTextMain = Color(0xFFE8E8FF);
const Color kTextDim = Color(0xFF888AAA);
const Color kSuccess = Color(0xFF4CAF7D);
const Color kDanger = Color(0xFFE53935);
const Color kLeader = Color(0xFFFFD700);

// Per-player line colours – matches Python PLAYER_COLORS list
const List<Color> kPlayerColors = [
  Color(0xFF4FC3F7), // light blue
  Color(0xFFAED581), // light green
  Color(0xFFFFB74D), // orange
  Color(0xFFCE93D8), // purple
  Color(0xFFEF9A9A), // pink
  Color(0xFF80DEEA), // cyan
  Color(0xFFFFF176), // yellow
  Color(0xFFA5D6A7), // green
];

// ── Dark theme ────────────────────────────────────────────────────────────────
final ThemeData darkTheme = ThemeData(
  brightness: Brightness.dark,
  scaffoldBackgroundColor: kBgBase,
  colorScheme: const ColorScheme.dark(
    primary: kAccent,
    secondary: kAccentDim,
    surface: kBgPanel,
    onPrimary: kBgBase,
    onSurface: kTextMain,
    error: kDanger,
  ),
  appBarTheme: const AppBarTheme(
    backgroundColor: kBgPanel,
    foregroundColor: kTextMain,
    elevation: 0,
    titleTextStyle: TextStyle(
      color: kAccent,
      fontSize: 18,
      fontWeight: FontWeight.bold,
      letterSpacing: 1.5,
    ),
  ),
  cardTheme: CardThemeData(
    color: kBgCard,
    elevation: 2,
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
  ),
  inputDecorationTheme: InputDecorationTheme(
    filled: true,
    fillColor: kBgCard,
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(8),
      borderSide: const BorderSide(color: kAccentDim),
    ),
    focusedBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(8),
      borderSide: const BorderSide(color: kAccent, width: 2),
    ),
    hintStyle: const TextStyle(color: kTextDim),
    labelStyle: const TextStyle(color: kTextDim),
  ),
  elevatedButtonTheme: ElevatedButtonThemeData(
    style: ElevatedButton.styleFrom(
      backgroundColor: kAccent,
      foregroundColor: kBgBase,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      textStyle: const TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1),
      minimumSize: const Size(0, 44),
    ),
  ),
  textButtonTheme: TextButtonThemeData(
    style: TextButton.styleFrom(foregroundColor: kAccent),
  ),
  dividerColor: kBgCard,
  textTheme: const TextTheme(
    bodyLarge: TextStyle(color: kTextMain),
    bodyMedium: TextStyle(color: kTextMain),
    titleLarge: TextStyle(
        color: kAccent, fontWeight: FontWeight.bold, letterSpacing: 1.5),
    titleMedium: TextStyle(color: kTextMain, fontWeight: FontWeight.w600),
    labelSmall: TextStyle(color: kTextDim),
  ),
);

// ── Light theme ───────────────────────────────────────────────────────────────
final ThemeData lightTheme = ThemeData(
  brightness: Brightness.light,
  scaffoldBackgroundColor: const Color(0xFFF0F0F5),
  colorScheme: const ColorScheme.light(
    primary: Color(0xFF7B5E1A),
    secondary: Color(0xFF9B7A1E),
    surface: Color(0xFFE4E4EE),
    onPrimary: Colors.white,
    onSurface: Color(0xFF222244),
    error: Color(0xFFB71C1C),
  ),
  appBarTheme: const AppBarTheme(
    backgroundColor: Color(0xFFE4E4EE),
    foregroundColor: Color(0xFF222244),
    elevation: 0,
    titleTextStyle: TextStyle(
      color: Color(0xFF7B5E1A),
      fontSize: 18,
      fontWeight: FontWeight.bold,
      letterSpacing: 1.5,
    ),
  ),
  cardTheme: CardThemeData(
    color: Colors.white,
    elevation: 1,
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
  ),
  inputDecorationTheme: InputDecorationTheme(
    filled: true,
    fillColor: Colors.white,
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(8),
      borderSide: const BorderSide(color: Color(0xFFCCCCDD)),
    ),
    focusedBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(8),
      borderSide: const BorderSide(color: Color(0xFF7B5E1A), width: 2),
    ),
  ),
  elevatedButtonTheme: ElevatedButtonThemeData(
    style: ElevatedButton.styleFrom(
      backgroundColor: const Color(0xFF7B5E1A),
      foregroundColor: Colors.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      textStyle: const TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1),
      minimumSize: const Size(0, 44),
    ),
  ),
);

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../i18n/translations.dart';

/// Mirrors Python app_settings.py – persists language, theme, and leaderboard URL.
class AppSettings extends ChangeNotifier {
  static const _keyLanguage = 'language';
  static const _keyTheme = 'theme';
  static const _keyLeaderboardUrl = 'leaderboard_url';

  String _language = 'de';
  String _theme = 'dark'; // 'dark' | 'light'
  String _leaderboardUrl = '';

  String get language => _language;
  String get theme => _theme;
  String get leaderboardUrl => _leaderboardUrl;
  bool get isDark => _theme == 'dark';
  ThemeMode get themeMode => isDark ? ThemeMode.dark : ThemeMode.light;

  /// Shorthand translate using current language.
  String t(String key, [Map<String, String> args = const {}]) =>
      translate(_language, key, args);

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    _language = prefs.getString(_keyLanguage) ?? 'de';
    _theme = prefs.getString(_keyTheme) ?? 'dark';
    _leaderboardUrl = prefs.getString(_keyLeaderboardUrl) ?? '';
    notifyListeners();
  }

  Future<void> setLanguage(String lang) async {
    _language = lang;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyLanguage, lang);
    notifyListeners();
  }

  Future<void> setTheme(String theme) async {
    _theme = theme;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyTheme, theme);
    notifyListeners();
  }

  Future<void> setLeaderboardUrl(String url) async {
    _leaderboardUrl = url.trim();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyLeaderboardUrl, _leaderboardUrl);
    notifyListeners();
  }
}

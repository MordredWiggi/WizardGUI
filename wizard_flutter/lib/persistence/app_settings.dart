import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../i18n/translations.dart';

/// Keys used by the event overlay – mirrors EVENT_KEYS in the desktop app.
const List<String> kEventKeys = <String>[
  'huge_loss',
  'bow_stretched',
  'revenge_lever',
  'tobi_message',
  'fire',
  'new_leader',
  'big_scorer',
];

const int _kDefaultMessageDurationMs = 2200;
const int _kMinMessageDurationMs = 500;
const int _kMaxMessageDurationMs = 10000;

/// Mirrors Python app_settings.py – persists language and theme. The
/// leaderboard URL is a compile-time constant, matching the desktop app, so
/// end users never configure or see it.
class AppSettings extends ChangeNotifier {
  static const _keyLanguage = 'language';
  static const _keyTheme = 'theme';
  static const _keyMessageDuration = 'message_display_duration_ms';
  static const _keyCustomMessages = 'custom_event_messages';

  // Kept in sync with wizard_desktop/app_settings.py::_LEADERBOARD_URL.
  static const String _leaderboardUrl = 'http://158.180.32.188:8000';

  String _language = 'de';
  String _theme = 'dark'; // 'dark' | 'light'
  int _messageDurationMs = _kDefaultMessageDurationMs;
  Map<String, String> _customMessages = {
    for (final k in kEventKeys) k: '',
  };

  String get language => _language;
  String get theme => _theme;
  String get leaderboardUrl => _leaderboardUrl;
  bool get isDark => _theme == 'dark';
  ThemeMode get themeMode => isDark ? ThemeMode.dark : ThemeMode.light;

  int get messageDurationMs => _messageDurationMs;
  Duration get messageDuration => Duration(milliseconds: _messageDurationMs);
  Map<String, String> get customMessages => Map.unmodifiable(_customMessages);

  /// Shorthand translate using current language.
  String t(String key, [Map<String, String> args = const {}]) =>
      translate(_language, key, args);

  /// Returns the override (with {placeholders} substituted) if set,
  /// otherwise falls back to the translated default for ``key``.
  String resolveEventMessage(String key, [Map<String, String> args = const {}]) {
    final override = _customMessages[key] ?? '';
    if (override.isNotEmpty) {
      return _format(override, args);
    }
    return translate(_language, key, args);
  }

  String _format(String template, Map<String, String> args) {
    var out = template;
    args.forEach((k, v) {
      out = out.replaceAll('{$k}', v);
    });
    return out;
  }

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    _language = prefs.getString(_keyLanguage) ?? 'de';
    _theme = prefs.getString(_keyTheme) ?? 'dark';
    _messageDurationMs = _clampDuration(
      prefs.getInt(_keyMessageDuration) ?? _kDefaultMessageDurationMs,
    );
    final raw = prefs.getString(_keyCustomMessages);
    if (raw != null && raw.isNotEmpty) {
      try {
        final decoded = jsonDecode(raw);
        if (decoded is Map) {
          _customMessages = {
            for (final k in kEventKeys)
              k: (decoded[k] ?? '').toString(),
          };
        }
      } catch (_) {/* ignore malformed */}
    }
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

  Future<void> setMessageDurationMs(int ms) async {
    _messageDurationMs = _clampDuration(ms);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_keyMessageDuration, _messageDurationMs);
    notifyListeners();
  }

  Future<void> setCustomMessages(Map<String, String> mapping) async {
    _customMessages = {
      for (final k in kEventKeys) k: (mapping[k] ?? '').trim(),
    };
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyCustomMessages, jsonEncode(_customMessages));
    notifyListeners();
  }

  Future<void> setCustomMessage(String key, String value) async {
    if (!kEventKeys.contains(key)) return;
    await setCustomMessages({..._customMessages, key: value});
  }

  int _clampDuration(int ms) {
    if (ms < _kMinMessageDurationMs) return _kMinMessageDurationMs;
    if (ms > _kMaxMessageDurationMs) return _kMaxMessageDurationMs;
    return ms;
  }
}

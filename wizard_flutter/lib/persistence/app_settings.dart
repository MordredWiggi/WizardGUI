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

class CustomMessageRule {
  final String type; // 'points', 'win_streak', 'loss_streak'
  final int value;
  final String message;

  CustomMessageRule({
    required this.type,
    required this.value,
    required this.message,
  });

  Map<String, dynamic> toJson() => {
        'type': type,
        'value': value,
        'message': message,
      };

  factory CustomMessageRule.fromJson(Map<String, dynamic> json) =>
      CustomMessageRule(
        type: json['type'] as String,
        value: json['value'] as int,
        message: json['message'] as String,
      );
}

/// Mirrors Python app_settings.py – persists language and theme. The
/// leaderboard URL is a compile-time constant, matching the desktop app, so
/// end users never configure or see it.
class AppSettings extends ChangeNotifier {
  static const _keyLanguage = 'language';
  static const _keyTheme = 'theme';
  static const _keyMessageDuration = 'message_display_duration_ms';
  static const _keyCustomMessages = 'custom_event_messages';
  static const _keyCustomRules = 'custom_rules';
  // Persisted list of every group the user has previously joined or created.
  // Used to autofill the code in the join dialog when they reselect that
  // group — never to pre-select a group at app startup.
  static const _keyKnownGroups = 'known_groups';
  // Legacy single-group key from the previous version, migrated on load.
  static const _keyLastGroup = 'last_group';

  // Kept in sync with wizard_desktop/app_settings.py::_LEADERBOARD_URL.
  static const String _leaderboardUrl = 'https://play-wizard.de';

  String _language = 'de';
  String _theme = 'dark'; // 'dark' | 'light'
  int _messageDurationMs = _kDefaultMessageDurationMs;
  Map<String, String> _customMessages = {
    for (final k in kEventKeys) k: '',
  };
  List<CustomMessageRule> _customRules = [];
  // Most-recent-first list of groups the user has previously joined or
  // created. Each entry is a map with at least {id, name, code, visibility}.
  List<Map<String, dynamic>> _knownGroups = [];

  String get language => _language;
  String get theme => _theme;
  String get leaderboardUrl => _leaderboardUrl;
  bool get isDark => _theme == 'dark';
  ThemeMode get themeMode => isDark ? ThemeMode.dark : ThemeMode.light;

  int get messageDurationMs => _messageDurationMs;
  Duration get messageDuration => Duration(milliseconds: _messageDurationMs);
  Map<String, String> get customMessages => Map.unmodifiable(_customMessages);
  List<CustomMessageRule> get customRules => List.unmodifiable(_customRules);

  /// All groups the user has previously joined or created, most-recent-first.
  /// The setup screen does NOT auto-restore these on startup — they're only
  /// used by the join dialog to autofill the 4-digit code when the user
  /// reselects a group they've played in before.
  List<Map<String, dynamic>> get knownGroups =>
      List.unmodifiable(_knownGroups);

  /// Look up a previously-joined group by name (case-insensitive). Returns
  /// null if the user has never played in a group with that name.
  Map<String, dynamic>? findKnownGroupByName(String name) {
    final needle = name.trim().toLowerCase();
    if (needle.isEmpty) return null;
    for (final g in _knownGroups) {
      if ((g['name'] as String? ?? '').toLowerCase() == needle) return g;
    }
    return null;
  }

  /// Look up a previously-joined group by its server id. Returns null if
  /// the group is not in the local known-groups list.
  Map<String, dynamic>? findKnownGroupById(int? id) {
    if (id == null) return null;
    for (final g in _knownGroups) {
      if (g['id'] == id) return g;
    }
    return null;
  }

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
    
    final rawRules = prefs.getString(_keyCustomRules);
    if (rawRules != null && rawRules.isNotEmpty) {
      try {
        final decoded = jsonDecode(rawRules);
        if (decoded is List) {
          _customRules = decoded
              .map((e) => CustomMessageRule.fromJson(e as Map<String, dynamic>))
              .toList();
        }
      } catch (_) {/* ignore malformed */}
    }

    final rawKnown = prefs.getString(_keyKnownGroups);
    if (rawKnown != null && rawKnown.isNotEmpty) {
      try {
        final decoded = jsonDecode(rawKnown);
        if (decoded is List) {
          _knownGroups = decoded
              .whereType<Map>()
              .map((e) => Map<String, dynamic>.from(e))
              .toList();
        }
      } catch (_) {/* ignore malformed */}
    }

    // One-shot migration from the previous `last_group` single-entry key.
    if (_knownGroups.isEmpty) {
      final legacy = prefs.getString(_keyLastGroup);
      if (legacy != null && legacy.isNotEmpty) {
        try {
          final decoded = jsonDecode(legacy);
          if (decoded is Map) {
            _knownGroups = [Map<String, dynamic>.from(decoded)];
            await prefs.setString(_keyKnownGroups, jsonEncode(_knownGroups));
          }
        } catch (_) {/* ignore malformed */}
        await prefs.remove(_keyLastGroup);
      }
    }

    notifyListeners();
  }

  /// Remember a group the user just joined or created so its 4-digit code
  /// can be autofilled the next time they reselect that group. The most
  /// recently used group moves to the front of the list. Calling this
  /// purposely does NOT make the group "active" for the next session —
  /// the setup screen still starts with no group selected.
  Future<void> addKnownGroup(Map<String, dynamic> group) async {
    final code = group['code'] as String?;
    final id = group['id'];
    if (code == null || code.isEmpty) return;

    bool sameGroup(Map<String, dynamic> g) {
      if (id != null && g['id'] == id) return true;
      return g['code'] == code;
    }

    final next = [
      Map<String, dynamic>.from(group),
      ..._knownGroups.where((g) => !sameGroup(g)),
    ];
    _knownGroups = next;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyKnownGroups, jsonEncode(_knownGroups));
    notifyListeners();
  }

  /// Remove a saved group code (e.g. if the server reports the group
  /// no longer exists). No-op if the code wasn't known.
  Future<void> forgetKnownGroupByCode(String code) async {
    final filtered =
        _knownGroups.where((g) => g['code'] != code).toList();
    if (filtered.length == _knownGroups.length) return;
    _knownGroups = filtered;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyKnownGroups, jsonEncode(_knownGroups));
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

  Future<void> addCustomRule(CustomMessageRule rule) async {
    _customRules = [..._customRules, rule];
    await _saveCustomRules();
  }

  Future<void> removeCustomRule(int index) async {
    final list = List<CustomMessageRule>.from(_customRules);
    list.removeAt(index);
    _customRules = list;
    await _saveCustomRules();
  }

  Future<void> _saveCustomRules() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      _keyCustomRules,
      jsonEncode(_customRules.map((e) => e.toJson()).toList()),
    );
    notifyListeners();
  }

  int _clampDuration(int ms) {
    if (ms < _kMinMessageDurationMs) return _kMinMessageDurationMs;
    if (ms > _kMaxMessageDurationMs) return _kMaxMessageDurationMs;
    return ms;
  }
}

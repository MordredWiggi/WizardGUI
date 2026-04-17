import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../persistence/app_settings.dart';
import '../i18n/translations.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final Map<String, TextEditingController> _controllers = {};
  double _durationSec = 2.2;

  @override
  void initState() {
    super.initState();
    final settings = context.read<AppSettings>();
    _durationSec = settings.messageDurationMs / 1000.0;
    for (final key in kEventKeys) {
      _controllers[key] =
          TextEditingController(text: settings.customMessages[key] ?? '');
    }
  }

  @override
  void dispose() {
    for (final c in _controllers.values) {
      c.dispose();
    }
    super.dispose();
  }

  String _eventLabel(String key, String Function(String) t) =>
      t('event_$key');

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<AppSettings>();
    final t = settings.t;

    return Scaffold(
      appBar: AppBar(title: Text(t('settings_title'))),
      body: ListView(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
        children: [
          // ── Theme ──────────────────────────────────────────────────────
          Text(t('settings_theme'),
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          SegmentedButton<String>(
            segments: [
              ButtonSegment(
                  value: 'dark', label: Text(t('settings_theme_dark'))),
              ButtonSegment(
                  value: 'light', label: Text(t('settings_theme_light'))),
            ],
            selected: {settings.theme},
            onSelectionChanged: (s) => settings.setTheme(s.first),
          ),

          const SizedBox(height: 28),

          // ── Language ───────────────────────────────────────────────────
          Text(t('settings_language'),
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          RadioGroup<String>(
            groupValue: settings.language,
            onChanged: (v) => settings.setLanguage(v!),
            child: Column(
              children: kLanguageNames.entries.map(
                (e) => RadioListTile<String>(
                  value: e.key,
                  title: Text(e.value),
                  activeColor: Theme.of(context).colorScheme.primary,
                  dense: true,
                ),
              ).toList(),
            ),
          ),

          const SizedBox(height: 28),

          // ── Messages ───────────────────────────────────────────────────
          Text(t('settings_messages'),
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: Text(t('settings_message_duration')),
              ),
              SizedBox(
                width: 60,
                child: Text(
                  t('settings_message_duration_sec', {
                    's': _durationSec.toStringAsFixed(1),
                  }),
                  textAlign: TextAlign.end,
                ),
              ),
            ],
          ),
          Slider(
            min: 0.5,
            max: 10.0,
            divisions: 95,
            value: _durationSec,
            label: t('settings_message_duration_sec', {
              's': _durationSec.toStringAsFixed(1),
            }),
            onChanged: (v) => setState(() => _durationSec = v),
            onChangeEnd: (v) =>
                settings.setMessageDurationMs((v * 1000).round()),
          ),

          const SizedBox(height: 20),

          // ── Custom event messages ──────────────────────────────────────
          Text(t('settings_custom_messages'),
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 4),
          Text(
            t('settings_custom_messages_hint'),
            style: TextStyle(
                fontSize: 12,
                color: Theme.of(context).textTheme.bodySmall?.color),
          ),
          const SizedBox(height: 12),
          ...kEventKeys.map((key) {
            final defaultText = settings.t(key, _placeholderArgs(key));
            return Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: TextField(
                controller: _controllers[key],
                decoration: InputDecoration(
                  labelText: _eventLabel(key, t),
                  hintText: defaultText,
                  border: const OutlineInputBorder(),
                  isDense: true,
                ),
                onChanged: (v) => settings.setCustomMessage(key, v),
              ),
            );
          }),
        ],
      ),
    );
  }

  /// Preview args so the hint shows a realistic-looking default instead of
  /// literal `{name}` placeholders.
  Map<String, String> _placeholderArgs(String key) {
    switch (key) {
      case 'huge_loss':
        return const {'name': '…', 'delta': '…'};
      case 'bow_stretched':
      case 'revenge_lever':
      case 'tobi_message':
      case 'fire':
      case 'new_leader':
        return const {'name': '…'};
      default:
        return const {};
    }
  }
}

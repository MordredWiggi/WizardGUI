import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../persistence/app_settings.dart';
import '../i18n/translations.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

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
        ],
      ),
    );
  }
}

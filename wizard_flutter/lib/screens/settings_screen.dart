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
  late TextEditingController _urlCtrl;

  @override
  void initState() {
    super.initState();
    final url = context.read<AppSettings>().leaderboardUrl;
    _urlCtrl = TextEditingController(text: url);
  }

  @override
  void dispose() {
    _urlCtrl.dispose();
    super.dispose();
  }

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

          // ── Leaderboard URL ────────────────────────────────────────────
          Text(t('leaderboard_url_label'),
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          TextField(
            controller: _urlCtrl,
            decoration: InputDecoration(
              hintText: t('leaderboard_url_placeholder'),
              border: const OutlineInputBorder(),
              isDense: true,
              suffixIcon: IconButton(
                icon: const Icon(Icons.check, size: 20),
                tooltip: t('apply'),
                onPressed: () {
                  settings.setLeaderboardUrl(_urlCtrl.text);
                  FocusScope.of(context).unfocus();
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text(t('ok'))),
                  );
                },
              ),
            ),
            keyboardType: TextInputType.url,
            autocorrect: false,
            onSubmitted: (v) {
              settings.setLeaderboardUrl(v);
              FocusScope.of(context).unfocus();
            },
          ),
        ],
      ),
    );
  }
}

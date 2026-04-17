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
  double _durationSec = 2.2;

  @override
  void initState() {
    super.initState();
    final settings = context.read<AppSettings>();
    _durationSec = settings.messageDurationMs / 1000.0;
  }

  @override
  void dispose() {
    super.dispose();
  }

  void _showAddRuleDialog() {
    showDialog(
      context: context,
      builder: (ctx) => const _AddRuleDialog(),
    );
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
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                t('settings_custom_messages'),
                style: Theme.of(context).textTheme.titleMedium,
              ),
              IconButton(
                icon: const Icon(Icons.add),
                onPressed: _showAddRuleDialog,
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            t('settings_custom_messages_hint'),
            style: TextStyle(
                fontSize: 12,
                color: Theme.of(context).textTheme.bodySmall?.color),
          ),
          const SizedBox(height: 12),
          ...settings.customRules.asMap().entries.map((req) {
            final idx = req.key;
            final rule = req.value;
            return Card(
              margin: const EdgeInsets.only(bottom: 8),
              child: ListTile(
                title: Text(rule.message),
                subtitle: Text('${rule.type}: ${rule.value}'),
                trailing: IconButton(
                  icon: const Icon(Icons.delete),
                  onPressed: () => settings.removeCustomRule(idx),
                ),
              ),
            );
          }).toList(),
        ],
      ),
    );
  }
}

class _AddRuleDialog extends StatefulWidget {
  const _AddRuleDialog();

  @override
  State<_AddRuleDialog> createState() => _AddRuleDialogState();
}

class _AddRuleDialogState extends State<_AddRuleDialog> {
  String _type = 'points';
  final _amountController = TextEditingController();
  final _messageController = TextEditingController();

  @override
  void dispose() {
    _amountController.dispose();
    _messageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<AppSettings>();
    final t = settings.t;

    return AlertDialog(
      title: Text(t('settings_custom_messages')),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          DropdownButtonFormField<String>(
            value: _type,
            isExpanded: true,
            items: const [
              DropdownMenuItem(value: 'points', child: Text('Points in Round')),
              DropdownMenuItem(value: 'win_streak', child: Text('Win Streak')),
              DropdownMenuItem(value: 'loss_streak', child: Text('Loss Streak')),
            ],
            onChanged: (v) => setState(() => _type = v!),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _amountController,
            decoration: const InputDecoration(labelText: 'Amount / Target Value'),
            keyboardType: TextInputType.number,
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _messageController,
            decoration: const InputDecoration(
              labelText: 'Message template',
              hintText: 'e.g. {name} got absolutely crushed',
            ),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(t('cancel')),
        ),
        ElevatedButton(
          onPressed: () {
            final val = int.tryParse(_amountController.text) ?? 0;
            final msg = _messageController.text.trim();
            if (msg.isEmpty) return;
            context.read<AppSettings>().addCustomRule(CustomMessageRule(
                  type: _type,
                  value: val,
                  message: msg,
                ));
            Navigator.pop(context);
          },
          child: Text(t('btn_add')),
        ),
      ],
    );
  }
}

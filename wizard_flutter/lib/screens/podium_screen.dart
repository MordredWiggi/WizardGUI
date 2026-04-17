import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../persistence/app_settings.dart';
import '../state/game_notifier.dart';
import '../theme/app_theme.dart';
import 'setup_screen.dart';

/// Podium dialog shown when the game ends – mirrors Python PodiumDialog.
class PodiumScreen extends StatefulWidget {
  /// sorted descending by score: [(name, score), ...]
  final List<(String, int)> podium;

  /// When true, the game finished without a group – show a reminder dialog
  /// once the screen is visible and let the user save locally or discard.
  final bool offlineReminder;

  const PodiumScreen({
    super.key,
    required this.podium,
    this.offlineReminder = false,
  });

  @override
  State<PodiumScreen> createState() => _PodiumScreenState();
}

class _PodiumScreenState extends State<PodiumScreen> {
  bool _reminderShown = false;

  @override
  void initState() {
    super.initState();
    if (widget.offlineReminder) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _showOfflineDialog());
    }
  }

  Future<void> _showOfflineDialog() async {
    if (_reminderShown) return;
    _reminderShown = true;
    final settings = context.read<AppSettings>();
    final notifier = context.read<GameNotifier>();
    final t = settings.t;

    final save = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        title: Row(children: [
          const Icon(Icons.wifi_off, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text(t('offline_reminder_title'))),
        ]),
        content: Text(t('offline_reminder_message')),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: Text(t('offline_discard')),
          ),
          ElevatedButton.icon(
            onPressed: () => Navigator.pop(ctx, true),
            icon: const Icon(Icons.save_outlined, size: 18),
            label: Text(t('offline_save_device')),
          ),
        ],
      ),
    );
    if (save == true && notifier.game != null) {
      try {
        await notifier.savePendingGame();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text(t('offline_saved_ok')),
            duration: settings.messageDuration,
          ));
        }
      } catch (_) {/* ignore */}
    }
  }

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<AppSettings>();
    final t = settings.t;
    final theme = Theme.of(context);

    final podiumKeys = [
      ('podium_1st', '🥇'),
      ('podium_2nd', '🥈'),
      ('podium_3rd', '🥉'),
    ];

    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(t('game_over_title'),
                  style: theme.textTheme.titleLarge
                      ?.copyWith(fontSize: 28, letterSpacing: 2)),
              const SizedBox(height: 8),
              Text(t('podium_title'),
                  style: theme.textTheme.titleMedium
                      ?.copyWith(color: kLeader, fontSize: 20)),
              const SizedBox(height: 40),

              // Podium entries
              ...List.generate(
                widget.podium.length.clamp(0, 3),
                (i) {
                  final (name, score) = widget.podium[i];
                  final (_, emoji) = podiumKeys[i];
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    child: Row(children: [
                      Text(emoji, style: const TextStyle(fontSize: 32)),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Text(name,
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                              color: i == 0
                                  ? kLeader
                                  : theme.textTheme.bodyLarge?.color,
                            )),
                      ),
                      Text(
                        t('podium_points', {'pts': score.toString()}),
                        style: TextStyle(
                          fontSize: 16,
                          color: i == 0 ? kLeader : kAccentDim,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ]),
                  );
                },
              ),

              // Extra players beyond podium
              if (widget.podium.length > 3) ...[
                const SizedBox(height: 16),
                const Divider(),
                const SizedBox(height: 8),
                ...widget.podium.skip(3).toList().asMap().entries.map((e) {
                  final (name, score) = e.value;
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    child: Row(children: [
                      Text('${e.key + 4}.',
                          style: const TextStyle(
                              fontSize: 16, color: kTextDim)),
                      const SizedBox(width: 12),
                      Expanded(
                          child: Text(name,
                              style: const TextStyle(fontSize: 15))),
                      Text('$score',
                          style: const TextStyle(
                              fontSize: 15, color: kAccentDim)),
                    ]),
                  );
                }),
              ],

              const SizedBox(height: 48),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () => Navigator.of(context).pushAndRemoveUntil(
                    MaterialPageRoute(builder: (_) => const SetupScreen()),
                    (_) => false,
                  ),
                  child: Text(t('podium_close'),
                      style: const TextStyle(fontSize: 16)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

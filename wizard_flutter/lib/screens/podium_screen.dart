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
  bool _savedAfterFinish = false;

  Future<void> _onSaveAfterFinish() async {
    final settings = context.read<AppSettings>();
    final notifier = context.read<GameNotifier>();
    if (notifier.game == null) return;
    try {
      await notifier.saveGame();
      if (mounted) {
        setState(() => _savedAfterFinish = true);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(settings.t('offline_saved_ok')),
          duration: settings.messageDuration,
        ));
      }
    } catch (_) {/* ignore */}
  }

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

    // Compute competition ranks (1224) so multiple players with identical
    // scores share the same place — and the same emoji.
    final ranks = <int>[];
    int? lastScore;
    int currentRank = 1;
    for (var i = 0; i < widget.podium.length; i++) {
      final score = widget.podium[i].$2;
      if (lastScore == null || score != lastScore) {
        currentRank = i + 1;
        lastScore = score;
      }
      ranks.add(currentRank);
    }

    String rankEmoji(int r) {
      if (r == 1) return '🥇';
      if (r == 2) return '🥈';
      if (r == 3) return '🥉';
      return '$r.';
    }

    // Split into "podium" (rank ≤ 3) and "rest" so ties can extend the podium
    // beyond three rows (e.g. two co-winners both get gold and appear on top).
    final topEntries = <int>[];
    final restEntries = <int>[];
    for (var i = 0; i < widget.podium.length; i++) {
      if (ranks[i] <= 3) {
        topEntries.add(i);
      } else {
        restEntries.add(i);
      }
    }

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

              // Podium entries (rank ≤ 3, may include ties)
              ...topEntries.map((i) {
                final (name, score) = widget.podium[i];
                final r = ranks[i];
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  child: Row(children: [
                    Text(rankEmoji(r), style: const TextStyle(fontSize: 32)),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Text(name,
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                            color: r == 1
                                ? kLeader
                                : theme.textTheme.bodyLarge?.color,
                          )),
                    ),
                    Text(
                      t('podium_points', {'pts': score.toString()}),
                      style: TextStyle(
                        fontSize: 16,
                        color: r == 1 ? kLeader : kAccentDim,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ]),
                );
              }),

              // Extra players beyond podium
              if (restEntries.isNotEmpty) ...[
                const SizedBox(height: 16),
                const Divider(),
                const SizedBox(height: 8),
                ...restEntries.map((i) {
                  final (name, score) = widget.podium[i];
                  final r = ranks[i];
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    child: Row(children: [
                      Text('$r.',
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
              // Always offer to save the finished game locally so it can be
              // re-opened later via the Setup screen's "saved games" list,
              // mirroring the desktop app.
              if (!widget.offlineReminder)
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    onPressed: _savedAfterFinish ? null : _onSaveAfterFinish,
                    icon: Icon(
                      _savedAfterFinish
                          ? Icons.check_circle_outline
                          : Icons.save_outlined,
                      size: 18,
                    ),
                    label: Text(_savedAfterFinish
                        ? t('offline_saved_ok')
                        : t('offline_save_device')),
                  ),
                ),
              if (!widget.offlineReminder) const SizedBox(height: 12),
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

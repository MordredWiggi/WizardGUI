import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../persistence/app_settings.dart';
import '../theme/app_theme.dart';
import 'setup_screen.dart';

/// Podium dialog shown when the game ends – mirrors Python PodiumDialog.
class PodiumScreen extends StatelessWidget {
  /// sorted descending by score: [(name, score), ...]
  final List<(String, int)> podium;

  const PodiumScreen({super.key, required this.podium});

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
                podium.length.clamp(0, 3),
                (i) {
                  final (name, score) = podium[i];
                  final (key, emoji) = podiumKeys[i];
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
              if (podium.length > 3) ...[
                const SizedBox(height: 16),
                const Divider(),
                const SizedBox(height: 8),
                ...podium.skip(3).toList().asMap().entries.map((e) {
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

import 'dart:math';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../domain/game_control.dart';
import '../domain/round_result.dart';
import '../domain/round_events.dart';
import '../persistence/app_settings.dart';
import '../services/leaderboard_service.dart';
import '../state/game_notifier.dart';
import '../theme/app_theme.dart';
import '../widgets/player_entry_card.dart';
import '../widgets/score_chart.dart';
import '../widgets/event_overlay.dart';
import '../widgets/leaderboard_tabs.dart';
import '../main.dart' show rootScaffoldMessengerKey;
import 'setup_screen.dart';
import 'podium_screen.dart';
import 'settings_screen.dart';

class GameScreen extends StatefulWidget {
  const GameScreen({super.key});

  @override
  State<GameScreen> createState() => _GameScreenState();
}

class _GameScreenState extends State<GameScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  // Per-player bid/made values, owned by the parent so they survive ListView
  // recycling as cards scroll off-screen.
  final List<int> _bids = [];
  final List<int> _mades = [];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  void _ensureCapacity(int n) {
    while (_bids.length < n) _bids.add(0);
    while (_mades.length < n) _mades.add(0);
  }

  void _resetEntries() {
    for (var i = 0; i < _bids.length; i++) {
      _bids[i] = 0;
      _mades[i] = 0;
    }
  }

  // ── Actions ────────────────────────────────────────────────────────────────

  void _completeRound(BuildContext context, GameControl game) {
    final settings = context.read<AppSettings>();
    final t = settings.t;
    _ensureCapacity(game.numPlayers);

    // Gather results
    final results = List<RoundResult>.generate(
      game.numPlayers,
      (i) => RoundResult(said: _bids[i], achieved: _mades[i]),
    );

    // Validate: sum of made == cards this round
    final madeTot = results.fold(0, (s, r) => s + r.achieved);
    if (madeTot != game.cardsThisRound) {
      final settings = context.read<AppSettings>();
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(t('made_tricks_warning', {
          'made': madeTot.toString(),
          'total': game.cardsThisRound.toString(),
        })),
        backgroundColor: kDanger,
        duration: settings.messageDuration,
      ));
      return;
    }

    final events = context.read<GameNotifier>().submitRound(results);
    _resetEntries();
    _handleEvents(context, events);
  }

  void _handleEvents(BuildContext context, RoundEvents events) {
    final settings = context.read<AppSettings>();
    final t = settings.t;
    final game = context.read<GameNotifier>().game!;

    // ── Evaluate Custom Rules (Highest Priority) ──
    final customPool = <(String, String, String, Color)>[];
    final deltas = game.lastDeltas();
    for (int i = 0; i < game.players.length; i++) {
      final p = game.players[i];
      final delta = deltas[i];
      for (final rule in settings.customRules) {
        bool matched = false;
        if (rule.type == 'points' && delta == rule.value) {
          matched = true;
        } else if (rule.type == 'win_streak' && p.consecutivePerfect == rule.value) {
          matched = true;
        } else if (rule.type == 'loss_streak' && p.consecutiveLosses == rule.value) {
          matched = true;
        }
        
        if (matched) {
          customPool.add((
            '✨',
            rule.message.replaceAll('{name}', p.name).replaceAll('{value}', rule.value.toString()),
            '',
            Colors.purpleAccent
          ));
        }
      }
    }

    if (customPool.isNotEmpty) {
      final pick = customPool[Random().nextInt(customPool.length)];
      EventOverlay.show(
        context,
        emoji: pick.$1,
        title: pick.$2,
        subtitle: pick.$3,
        color: pick.$4,
        duration: settings.messageDuration,
      );
      if (events.gameOver) _scheduleGameOver(context);
      return;
    }

    // Tobi easter egg
    if (_checkTobi(context, game)) return;

    // Huge loss (priority 2)
    if (events.hugeLossPlayer != null) {
      EventOverlay.show(
        context,
        emoji: '💥',
        title: settings.resolveEventMessage('huge_loss', {
          'name': events.hugeLossPlayer!.name,
          'delta': events.hugeLossDelta.abs().toString(),
        }),
        color: kDanger,
        duration: settings.messageDuration,
      );
      if (events.gameOver) _scheduleGameOver(context);
      return;
    }

    // Build random pool (priority 3)
    final pool = <(String, String, String, Color)>[];

    if (events.firePlayer != null) {
      pool.add((
        '🔥',
        settings.resolveEventMessage('fire', {'name': events.firePlayer!.name}),
        settings.t('fire_subtitle'),
        const Color(0xFFFF6B35),
      ));
    }
    if (events.newLeader != null) {
      pool.add((
        '👑',
        settings.resolveEventMessage(
            'new_leader', {'name': events.newLeader!.name}),
        settings.t('new_leader_subtitle',
            {'score': events.newLeader!.currentScore.toString()}),
        kLeader,
      ));
    }
    if (events.bigScorer != null && events.bigScoreDelta >= 50) {
      pool.add((
        '🎯',
        settings.resolveEventMessage('big_scorer'),
        settings.t('big_scorer_subtitle', {
          'delta': events.bigScoreDelta.toString(),
          'name': events.bigScorer!.name,
        }),
        kSuccess,
      ));
    }
    for (final p in events.bowPlayers) {
      pool.add(('🏹',
          settings.resolveEventMessage('bow_stretched', {'name': p.name}),
          '',
          kDanger));
    }
    for (final p in events.revengePlayers) {
      pool.add(('⚡',
          settings.resolveEventMessage('revenge_lever', {'name': p.name}),
          '',
          const Color(0xFFFF9900)));
    }

    if (pool.isNotEmpty) {
      final pick = pool[Random().nextInt(pool.length)];
      EventOverlay.show(
        context,
        emoji: pick.$1,
        title: pick.$2,
        subtitle: pick.$3,
        color: pick.$4,
        duration: settings.messageDuration,
      );
    }

    if (events.gameOver) _scheduleGameOver(context);
  }

  bool _checkTobi(BuildContext context, GameControl game) {
    final roundsAt60 = (game.totalRounds * 0.6).toInt();
    if (game.roundNumber != roundsAt60) return false;

    final tobi = game.players
        .where((p) => p.name.toLowerCase() == 'tobi')
        .firstOrNull;
    if (tobi == null) return false;

    final sorted = [...game.players]
      ..sort((a, b) => b.currentScore.compareTo(a.currentScore));
    final pos = sorted.indexOf(tobi);
    if (pos < sorted.length - 2) return false;

    final settings = context.read<AppSettings>();
    EventOverlay.show(
      context,
      emoji: '💪',
      title: settings.resolveEventMessage('tobi_message', {'name': tobi.name}),
      color: const Color(0xFF4FC3F7),
      duration: settings.messageDuration,
    );
    return true;
  }

  void _scheduleGameOver(BuildContext context) {
    // Kick off leaderboard submission in parallel with the podium delay —
    // mirrors the desktop flow where the QThread worker runs alongside the
    // UI transition. Result is surfaced via a global SnackBar so it still
    // appears after we've navigated to the podium screen.
    _submitToLeaderboard(context);

    Future.delayed(const Duration(milliseconds: 3200), () {
      if (!mounted) return;
      final notifier = context.read<GameNotifier>();
      final game = notifier.game;
      if (game == null) return;
      final podium = [...game.players]
        ..sort((a, b) => b.currentScore.compareTo(a.currentScore));
      final entries = podium.map((p) => (p.name, p.currentScore)).toList();
      // When no group was bound, the podium shows the "game not uploaded"
      // reminder and offers to save locally.
      final noGroup = notifier.activeGroup == null;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
            builder: (_) => PodiumScreen(
                  podium: entries,
                  offlineReminder: noGroup,
                )),
      );
    });
  }

  void _submitToLeaderboard(BuildContext context) {
    final notifier = context.read<GameNotifier>();
    final settings = context.read<AppSettings>();
    final game = notifier.game;
    if (game == null || !game.isGameOver) return;

    final t = settings.t;

    // No group bound → the end-of-game offline reminder is shown on the
    // podium screen instead. Nothing to upload here.
    if (notifier.activeGroup == null) return;

    final url = settings.leaderboardUrl;
    if (url.isEmpty) return;

    final groupCode = notifier.activeGroup?['code'] as String?;
    final payload = buildGameSubmission(
      game.toJson(),
      groupCode: groupCode,
    );

    LeaderboardService(url).submitGame(payload).then((success) async {
      if (!success) {
        // Persist offline so the next launch can retry.
        try {
          await notifier.savePendingGame(groupCode: groupCode);
        } catch (_) {/* ignore */}
      }
      final messenger = rootScaffoldMessengerKey.currentState;
      if (messenger == null) return;
      messenger.showSnackBar(SnackBar(
        content: Text(success
            ? t('leaderboard_submit_ok')
            : t('leaderboard_submit_fail')),
        duration: settings.messageDuration,
      ));
    });
  }

  Future<void> _onUndo(BuildContext context) async {
    final settings = context.read<AppSettings>();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(settings.t('warning_title')),
        content: Text(settings.t('undo_confirm')),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: Text(settings.t('cancel'))),
          TextButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: Text(settings.t('undo'))),
        ],
      ),
    );
    if (confirmed == true && mounted) {
      context.read<GameNotifier>().undoRound();
      _resetEntries();
    }
  }

  Future<void> _onSave(BuildContext context) async {
    final settings = context.read<AppSettings>();
    final notifier = context.read<GameNotifier>();
    final game = notifier.game;
    if (game == null) return;

    final nameCtrl = TextEditingController(
        text: game.playerNames.join('_'));
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(settings.t('save_game_title')),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(settings.t('save_game_label')),
            const SizedBox(height: 8),
            TextField(
              controller: nameCtrl,
              decoration: InputDecoration(
                  hintText: settings.t('save_game_placeholder')),
              autofocus: true,
            ),
          ],
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: Text(settings.t('cancel'))),
          TextButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: Text(settings.t('save'))),
        ],
      ),
    );
    if (confirmed == true && mounted) {
      try {
        final path = await notifier.saveGame(name: nameCtrl.text.trim());
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                  '${settings.t('save')} ✓  ${path.split('/').last}'),
              duration: settings.messageDuration,
            ),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text('${settings.t('save')}: $e'),
            duration: settings.messageDuration,
          ));
        }
      }
    }
  }

  Future<void> _onNewGame(BuildContext context) async {
    final settings = context.read<AppSettings>();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(settings.t('warning_title')),
        content: Text(settings.t('new_game_confirm')),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: Text(settings.t('cancel'))),
          TextButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: Text(settings.t('new'))),
        ],
      ),
    );
    if (confirmed == true && mounted) {
      // Starting fresh discards any paused state — otherwise resume would
      // silently bring it back later.
      final notifier = context.read<GameNotifier>();
      await notifier.clearPaused();
      notifier.endGame();
      if (!mounted) return;
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => const SetupScreen()),
        (_) => false,
      );
    }
  }

  Future<void> _onHome(BuildContext context) async {
    final notifier = context.read<GameNotifier>();
    if (notifier.game == null) return;
    try {
      await notifier.savePaused();
    } catch (_) {/* ignore – fall through to navigation */}
    notifier.endGame();
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const SetupScreen()),
      (_) => false,
    );
  }

  // ── UI ─────────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<AppSettings>();
    final t = settings.t;
    final notifier = context.watch<GameNotifier>();
    final game = notifier.game;

    if (game == null) {
      return Scaffold(
        body: Center(child: Text(t('no_saved_games'))),
      );
    }

    _ensureCapacity(game.numPlayers);
    final deltas = game.lastDeltas();
    final leaderSet = game.leaders.map((p) => p.name).toSet();

    // Bid sum tracking for the bid-warning banner
    final bidSum = _bids
        .take(game.numPlayers)
        .fold<int>(0, (s, b) => s + b);
    final bidWarning = bidSum == game.cardsThisRound;

    return Scaffold(
      appBar: AppBar(
        automaticallyImplyLeading: false,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(t('round_header', {
              'n': game.currentRoundDisplay.toString(),
              'total': game.totalRounds.toString(),
            })),
            Text(
              t('dealer_badge', {
                'n': game.cardsThisRound.toString(),
              }) + '  —  ${game.currentDealer?.name ?? ''}',
              style: const TextStyle(fontSize: 12, color: kAccentDim),
            ),
          ],
        ),
        bottom: TabBar(
          controller: _tabController,
          isScrollable: true,
          tabAlignment: TabAlignment.start,
          tabs: [
            Tab(icon: const Icon(Icons.people_outlined, size: 18), text: t('announced')),
            Tab(icon: const Icon(Icons.show_chart, size: 18), text: t('tab_chart')),
            Tab(icon: const Icon(Icons.leaderboard, size: 18), text: t('tab_groups_lb')),
            Tab(icon: const Icon(Icons.group, size: 18), text: t('tab_group_lb')),
          ],
          labelColor: kAccent,
          unselectedLabelColor: kTextDim,
          indicatorColor: kAccent,
          labelStyle: const TextStyle(fontSize: 11),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.undo, size: 22),
            tooltip: t('undo'),
            onPressed: game.roundNumber > 0 ? () => _onUndo(context) : null,
          ),
          IconButton(
            icon: const Icon(Icons.save_outlined, size: 22),
            tooltip: t('save'),
            onPressed: () => _onSave(context),
          ),
          IconButton(
            icon: const Icon(Icons.home_outlined, size: 22),
            tooltip: t('tooltip_home'),
            onPressed: () => _onHome(context),
          ),
          IconButton(
            icon: const Icon(Icons.settings_outlined, size: 22),
            tooltip: t('settings_title'),
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const SettingsScreen()),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.refresh, size: 22),
            tooltip: t('new'),
            onPressed: () => _onNewGame(context),
          ),
        ],
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          // ── Tab 0: Player cards + submit ───────────────────────────────
          _Layer1(
            game: game,
            bids: _bids,
            mades: _mades,
            deltas: deltas,
            leaderSet: leaderSet,
            bidWarning: bidWarning,
            bidSum: bidSum,
            onAutoFill: () {
              setState(() {
                for (var i = 0; i < game.numPlayers; i++) {
                  _mades[i] = _bids[i];
                }
              });
            },
            onCompleteRound: () => _completeRound(context, game),
            onEntryChanged: (index, bid, made) {
              setState(() {
                _bids[index] = bid;
                _mades[index] = made;
              });
            },
            t: t,
          ),

          // ── Tab 1: Score chart ─────────────────────────────────────────
          ScoreChart(game: game),

          // ── Tab 2: Global groups leaderboard ───────────────────────────
          const GroupsLeaderboardTab(),

          // ── Tab 3: My group player leaderboard ─────────────────────────
          const MyGroupLeaderboardTab(),
        ],
      ),
    );
  }
}

// ── Layer 1 widget ─────────────────────────────────────────────────────────────

class _Layer1 extends StatelessWidget {
  final GameControl game;
  final List<int> bids;
  final List<int> mades;
  final List<int> deltas;
  final Set<String> leaderSet;
  final bool bidWarning;
  final int bidSum;
  final VoidCallback onAutoFill;
  final VoidCallback onCompleteRound;
  final void Function(int index, int bid, int made) onEntryChanged;
  final String Function(String, [Map<String, String>]) t;

  const _Layer1({
    required this.game,
    required this.bids,
    required this.mades,
    required this.deltas,
    required this.leaderSet,
    required this.bidWarning,
    required this.bidSum,
    required this.onAutoFill,
    required this.onCompleteRound,
    required this.onEntryChanged,
    required this.t,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Bid counter banner
        Container(
          color: bidWarning ? kDanger.withOpacity(0.15) : Colors.transparent,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  bidWarning
                      ? t('bid_warning')
                      : t('bid_total', {
                          'bid': bidSum.toString(),
                          'total': game.cardsThisRound.toString(),
                        }),
                  style: TextStyle(
                    fontSize: 13,
                    color: bidWarning ? kDanger : kTextDim,
                    fontWeight:
                        bidWarning ? FontWeight.bold : FontWeight.normal,
                  ),
                ),
              ),
              TextButton.icon(
                onPressed: onAutoFill,
                icon: const Icon(Icons.auto_fix_high, size: 16),
                label: Text(t('auto_fill'), style: const TextStyle(fontSize: 12)),
                style: TextButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                  visualDensity: VisualDensity.compact,
                ),
              ),
            ],
          ),
        ),

        // Player cards
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.symmetric(vertical: 8),
            itemCount: game.numPlayers,
            itemBuilder: (_, i) {
              final p = game.players[i];
              return PlayerEntryCard(
                player: p,
                color: kPlayerColors[i % kPlayerColors.length],
                playerIndex: i,
                maxBid: game.cardsThisRound,
                isDealer: game.currentDealerIndex == i,
                isLeader: leaderSet.contains(p.name),
                scoreDelta: game.roundNumber > 0 ? deltas[i] : 0,
                bid: bids[i],
                made: mades[i],
                onChanged: (b, m) => onEntryChanged(i, b, m),
              );
            },
          ),
        ),

        // Complete round button
        SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
            child: SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: bidWarning ? null : onCompleteRound,
                style: ElevatedButton.styleFrom(
                  backgroundColor: bidWarning ? kDanger.withOpacity(0.3) : null,
                ),
                child: Text(t('complete_round'),
                    style: const TextStyle(fontSize: 16)),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

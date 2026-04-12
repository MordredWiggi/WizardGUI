import 'dart:math';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../domain/game_control.dart';
import '../domain/round_result.dart';
import '../domain/round_events.dart';
import '../persistence/app_settings.dart';
import '../state/game_notifier.dart';
import '../theme/app_theme.dart';
import '../widgets/player_entry_card.dart';
import '../widgets/score_chart.dart';
import '../widgets/event_overlay.dart';
import 'setup_screen.dart';
import 'podium_screen.dart';

class GameScreen extends StatefulWidget {
  const GameScreen({super.key});

  @override
  State<GameScreen> createState() => _GameScreenState();
}

class _GameScreenState extends State<GameScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  // One GlobalKey per player card so we can read bid/made values
  final List<GlobalKey<PlayerEntryCardState>> _cardKeys = [];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  // ── Build per-player card keys when player count changes ───────────────────

  List<GlobalKey<PlayerEntryCardState>> _keysFor(int n) {
    while (_cardKeys.length < n) {
      _cardKeys.add(GlobalKey<PlayerEntryCardState>());
    }
    return _cardKeys.sublist(0, n);
  }

  // ── Actions ────────────────────────────────────────────────────────────────

  void _completeRound(BuildContext context, GameControl game) {
    final settings = context.read<AppSettings>();
    final t = settings.t;
    final keys = _keysFor(game.numPlayers);

    // Gather results
    final results = keys
        .map((k) => k.currentState?.result ?? const RoundResult(said: 0, achieved: 0))
        .toList();

    // Validate: sum of made == cards this round
    final madeTot = results.fold(0, (s, r) => s + r.achieved);
    if (madeTot != game.cardsThisRound) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(t('made_tricks_warning', {
          'made': madeTot.toString(),
          'total': game.cardsThisRound.toString(),
        })),
        backgroundColor: kDanger,
      ));
      return;
    }

    final events = context.read<GameNotifier>().submitRound(results);
    _handleEvents(context, events);
  }

  void _handleEvents(BuildContext context, RoundEvents events) {
    final settings = context.read<AppSettings>();
    final t = settings.t;
    final game = context.read<GameNotifier>().game!;

    // Tobi easter egg
    if (_checkTobi(context, game)) return;

    // Huge loss (priority 2)
    if (events.hugeLossPlayer != null) {
      EventOverlay.show(
        context,
        emoji: '💥',
        title: t('huge_loss', {
          'name': events.hugeLossPlayer!.name,
          'delta': events.hugeLossDelta.abs().toString(),
        }),
        color: kDanger,
      );
      if (events.gameOver) _scheduleGameOver(context);
      return;
    }

    // Build random pool (priority 3)
    final pool = <(String, String, String, Color)>[];

    if (events.firePlayer != null) {
      pool.add(('🔥', '${events.firePlayer!.name}!', '3× perfect', const Color(0xFFFF6B35)));
    }
    if (events.newLeader != null) {
      pool.add(('👑', '${events.newLeader!.name}',
          '${events.newLeader!.currentScore} pts', kLeader));
    }
    if (events.bigScorer != null && events.bigScoreDelta >= 50) {
      pool.add(('🎯', 'Meisterschuss!',
          '+${events.bigScoreDelta} für ${events.bigScorer!.name}', kSuccess));
    }
    for (final p in events.bowPlayers) {
      pool.add(('🏹', t('bow_stretched', {'name': p.name}), '', kDanger));
    }
    for (final p in events.revengePlayers) {
      pool.add(('⚡', t('revenge_lever', {'name': p.name}), '', const Color(0xFFFF9900)));
    }

    if (pool.isNotEmpty) {
      final pick = pool[Random().nextInt(pool.length)];
      EventOverlay.show(
        context,
        emoji: pick.$1,
        title: pick.$2,
        subtitle: pick.$3,
        color: pick.$4,
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
      title: settings.t('tobi_message', {'name': tobi.name}),
      color: const Color(0xFF4FC3F7),
    );
    return true;
  }

  void _scheduleGameOver(BuildContext context) {
    Future.delayed(const Duration(milliseconds: 3200), () {
      if (!mounted) return;
      final game = context.read<GameNotifier>().game;
      if (game == null) return;
      final podium = [...game.players]
        ..sort((a, b) => b.currentScore.compareTo(a.currentScore));
      final entries = podium.map((p) => (p.name, p.currentScore)).toList();
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => PodiumScreen(podium: entries)),
      );
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
                    '${settings.t('save')} ✓  ${path.split('/').last}')),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context)
              .showSnackBar(SnackBar(content: Text('Save failed: $e')));
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
      context.read<GameNotifier>().endGame();
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => const SetupScreen()),
        (_) => false,
      );
    }
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

    final keys = _keysFor(game.numPlayers);
    final deltas = game.lastDeltas();
    final leaderSet = game.leaders.map((p) => p.name).toSet();

    // Bid sum tracking for the bid-warning banner
    // (read from card keys; 0 at round start before any card changes)
    final bidSum = keys.fold(0,
        (s, k) => s + (k.currentState?.bid ?? 0));
    final bidWarning = bidSum == game.cardsThisRound;

    return Scaffold(
      appBar: AppBar(
        automaticallyImplyLeading: false,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(t('round_header', {
              'n': game.roundNumber.toString(),
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
          tabs: [
            Tab(icon: const Icon(Icons.people_outlined), text: t('announced')),
            Tab(icon: const Icon(Icons.show_chart), text: t('points')),
          ],
          labelColor: kAccent,
          unselectedLabelColor: kTextDim,
          indicatorColor: kAccent,
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
            icon: const Icon(Icons.refresh, size: 22),
            tooltip: t('new'),
            onPressed: () => _onNewGame(context),
          ),
        ],
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          // ── Layer 1: Player cards + submit ─────────────────────────────
          _Layer1(
            game: game,
            keys: keys,
            deltas: deltas,
            leaderSet: leaderSet,
            bidWarning: bidWarning,
            bidSum: bidSum,
            onAutoFill: () {
              for (final k in keys) {
                k.currentState?.fillMadeFromBid();
              }
              setState(() {});
            },
            onCompleteRound: () => _completeRound(context, game),
            onBidChanged: () => setState(() {}),
            t: t,
          ),

          // ── Layer 2: Score chart ────────────────────────────────────────
          ScoreChart(game: game),
        ],
      ),
    );
  }
}

// ── Layer 1 widget ─────────────────────────────────────────────────────────────

class _Layer1 extends StatelessWidget {
  final GameControl game;
  final List<GlobalKey<PlayerEntryCardState>> keys;
  final List<int> deltas;
  final Set<String> leaderSet;
  final bool bidWarning;
  final int bidSum;
  final VoidCallback onAutoFill;
  final VoidCallback onCompleteRound;
  final VoidCallback onBidChanged;
  final String Function(String, [Map<String, String>]) t;

  const _Layer1({
    required this.game,
    required this.keys,
    required this.deltas,
    required this.leaderSet,
    required this.bidWarning,
    required this.bidSum,
    required this.onAutoFill,
    required this.onCompleteRound,
    required this.onBidChanged,
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
                key: keys[i],
                player: p,
                color: kPlayerColors[i % kPlayerColors.length],
                playerIndex: i,
                maxBid: game.cardsThisRound,
                isDealer: game.currentDealerIndex == i,
                isLeader: leaderSet.contains(p.name),
                scoreDelta: game.roundNumber > 0 ? deltas[i] : 0,
                onChanged: (_, __) => onBidChanged(),
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

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
import '../main.dart' show rootScaffoldMessengerKey;
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
    _tabController = TabController(length: 4, vsync: this);
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

  void _submitToLeaderboard(BuildContext context) {
    final notifier = context.read<GameNotifier>();
    final settings = context.read<AppSettings>();
    final game = notifier.game;
    if (game == null || !game.isGameOver) return;

    final url = settings.leaderboardUrl;
    if (url.isEmpty) return;

    final groupCode = notifier.activeGroup?['code'] as String?;
    final payload = buildGameSubmission(
      game.toJson(),
      groupCode: groupCode,
    );
    final t = settings.t;

    LeaderboardService(url).submitGame(payload).then((success) {
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

          // ── Tab 1: Score chart ─────────────────────────────────────────
          ScoreChart(game: game),

          // ── Tab 2: Global groups leaderboard ───────────────────────────
          const _GroupsLeaderboardTab(),

          // ── Tab 3: My group player leaderboard ─────────────────────────
          const _MyGroupLeaderboardTab(),
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

// ── Global groups leaderboard tab ──────────────────────────────────────────────

class _GroupsLeaderboardTab extends StatefulWidget {
  const _GroupsLeaderboardTab();

  @override
  State<_GroupsLeaderboardTab> createState() => _GroupsLeaderboardTabState();
}

class _GroupsLeaderboardTabState extends State<_GroupsLeaderboardTab> {
  List<Map<String, dynamic>>? _data;
  bool _loading = false;
  bool _hasError = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_data == null && !_loading) _load();
  }

  Future<void> _load() async {
    final url = context.read<AppSettings>().leaderboardUrl;
    if (url.isEmpty) {
      setState(() { _data = null; _hasError = false; _loading = false; });
      return;
    }
    setState(() { _loading = true; _hasError = false; });
    try {
      final svc = LeaderboardService(url);
      final result = await svc.getGlobalGroupsLeaderboard();
      if (mounted) setState(() { _data = result; _loading = false; });
    } catch (_) {
      if (mounted) setState(() { _loading = false; _hasError = true; });
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.watch<AppSettings>().t;
    final url = context.watch<AppSettings>().leaderboardUrl;

    if (_loading) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const CircularProgressIndicator(),
            const SizedBox(height: 12),
            Text(t('lb_loading'), style: const TextStyle(color: kTextDim)),
          ],
        ),
      );
    }

    if (url.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(t('leaderboard_url_label') + ' ' + t('leaderboard_url_placeholder'),
              textAlign: TextAlign.center,
              style: const TextStyle(color: kTextDim)),
        ),
      );
    }

    if (_hasError) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_off, size: 40, color: kTextDim),
            const SizedBox(height: 8),
            Text(t('glb_error'), style: const TextStyle(color: kTextDim)),
            const SizedBox(height: 12),
            ElevatedButton(onPressed: _load, child: Text(t('btn_refresh'))),
          ],
        ),
      );
    }

    if (_data == null || _data!.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.leaderboard, size: 40, color: kTextDim),
            const SizedBox(height: 8),
            Text(t('glb_no_data'), style: const TextStyle(color: kTextDim)),
            const SizedBox(height: 12),
            ElevatedButton(onPressed: _load, child: Text(t('btn_refresh'))),
          ],
        ),
      );
    }

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(t('tab_groups_lb'),
                  style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.bold,
                      color: kTextDim,
                      letterSpacing: 1.1)),
              IconButton(
                icon: const Icon(Icons.refresh, size: 20),
                tooltip: t('btn_refresh'),
                onPressed: _load,
                padding: EdgeInsets.zero,
                visualDensity: VisualDensity.compact,
              ),
            ],
          ),
        ),
        Expanded(
          child: SingleChildScrollView(
            scrollDirection: Axis.vertical,
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 8),
              child: DataTable(
                columnSpacing: 16,
                headingRowHeight: 36,
                dataRowMinHeight: 40,
                dataRowMaxHeight: 40,
                headingTextStyle: const TextStyle(
                    fontSize: 11, color: kTextDim, fontWeight: FontWeight.w600),
                dataTextStyle: const TextStyle(fontSize: 12),
                columns: [
                  const DataColumn(label: Text('#')),
                  DataColumn(label: Text(t('lb_col_name'))),
                  DataColumn(label: Text(t('lb_col_games')), numeric: true),
                  DataColumn(label: Text(t('lb_col_avg')), numeric: true),
                  DataColumn(label: Text(t('lb_col_hit_pct')), numeric: true),
                ],
                rows: _data!.map((row) {
                  final rank = row['rank'] as int? ?? 0;
                  final name = row['name'] as String? ?? '';
                  final games = row['total_games'] as int? ?? 0;
                  final avg = (row['avg_score'] as num?)?.toDouble() ?? 0.0;
                  final hit = (row['avg_hit_rate'] as num?)?.toDouble() ?? 0.0;
                  return DataRow(cells: [
                    DataCell(Text(_rankBadge(rank),
                        style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.bold,
                            color: _rankColor(rank)))),
                    DataCell(Text(name,
                        style: const TextStyle(fontWeight: FontWeight.w500),
                        overflow: TextOverflow.ellipsis)),
                    DataCell(Text(games.toString())),
                    DataCell(Text(avg.toStringAsFixed(0))),
                    DataCell(Text('${(hit * 100).toStringAsFixed(0)}%')),
                  ]);
                }).toList(),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

// ── My group player leaderboard tab ────────────────────────────────────────────

class _MyGroupLeaderboardTab extends StatefulWidget {
  const _MyGroupLeaderboardTab();

  @override
  State<_MyGroupLeaderboardTab> createState() => _MyGroupLeaderboardTabState();
}

class _MyGroupLeaderboardTabState extends State<_MyGroupLeaderboardTab> {
  List<Map<String, dynamic>>? _data;
  bool _loading = false;
  bool _hasError = false;
  String _mode = 'standard';
  String? _lastGroupCode;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final group = context.read<GameNotifier>().activeGroup;
    final code = group?['code'] as String?;
    if (code != null && (code != _lastGroupCode || _data == null && !_loading)) {
      _lastGroupCode = code;
      _load(code);
    }
  }

  Future<void> _load(String code) async {
    final url = context.read<AppSettings>().leaderboardUrl;
    if (url.isEmpty) return;
    setState(() { _loading = true; _hasError = false; });
    try {
      final svc = LeaderboardService(url);
      final result = await svc.getGroupPlayerLeaderboard(code, _mode);
      if (mounted) setState(() { _data = result; _loading = false; });
    } catch (_) {
      if (mounted) setState(() { _loading = false; _hasError = true; });
    }
  }

  void _switchMode(String mode) {
    if (mode == _mode) return;
    setState(() { _mode = mode; _data = null; });
    final code = context.read<GameNotifier>().activeGroup?['code'] as String?;
    if (code != null) _load(code);
  }

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<AppSettings>();
    final t = settings.t;
    final group = context.watch<GameNotifier>().activeGroup;
    final url = settings.leaderboardUrl;

    if (group == null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(t('group_required'),
              textAlign: TextAlign.center,
              style: const TextStyle(color: kTextDim)),
        ),
      );
    }

    if (url.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(t('leaderboard_url_label') + ' ' + t('leaderboard_url_placeholder'),
              textAlign: TextAlign.center,
              style: const TextStyle(color: kTextDim)),
        ),
      );
    }

    return Column(
      children: [
        // Group name header + mode toggle + refresh
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  group['name'] as String? ?? '',
                  style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.bold,
                      color: kAccent,
                      letterSpacing: 1.0),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              IconButton(
                icon: const Icon(Icons.refresh, size: 20),
                tooltip: t('btn_refresh'),
                onPressed: () => _load(group['code'] as String),
                padding: EdgeInsets.zero,
                visualDensity: VisualDensity.compact,
              ),
            ],
          ),
        ),
        // Mode toggle
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
          child: Row(
            children: [
              _ModeChip(
                label: t('game_mode_standard'),
                selected: _mode == 'standard',
                onTap: () => _switchMode('standard'),
              ),
              const SizedBox(width: 8),
              _ModeChip(
                label: t('game_mode_multiplicative'),
                selected: _mode == 'multiplicative',
                onTap: () => _switchMode('multiplicative'),
              ),
            ],
          ),
        ),

        if (_loading)
          const Expanded(child: Center(child: CircularProgressIndicator()))
        else if (_hasError)
          Expanded(
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.cloud_off, size: 40, color: kTextDim),
                  const SizedBox(height: 8),
                  Text(t('lb_error'), style: const TextStyle(color: kTextDim)),
                  const SizedBox(height: 12),
                  ElevatedButton(
                      onPressed: () => _load(group['code'] as String),
                      child: Text(t('btn_refresh'))),
                ],
              ),
            ),
          )
        else if (_data == null || _data!.isEmpty)
          Expanded(
            child: Center(
              child: Text(t('lb_no_data'),
                  style: const TextStyle(color: kTextDim)),
            ),
          )
        else
          Expanded(
            child: SingleChildScrollView(
              scrollDirection: Axis.vertical,
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                child: DataTable(
                  columnSpacing: 12,
                  headingRowHeight: 36,
                  dataRowMinHeight: 40,
                  dataRowMaxHeight: 40,
                  headingTextStyle: const TextStyle(
                      fontSize: 10, color: kTextDim, fontWeight: FontWeight.w600),
                  dataTextStyle: const TextStyle(fontSize: 12),
                  columns: [
                    const DataColumn(label: Text('#')),
                    DataColumn(label: Text(t('lb_col_name'))),
                    DataColumn(label: Text(t('lb_col_games')), numeric: true),
                    DataColumn(label: Text(t('lb_col_avg')), numeric: true),
                    DataColumn(label: Text(t('lb_col_best')), numeric: true),
                    DataColumn(label: Text(t('lb_col_hit_pct')), numeric: true),
                    DataColumn(label: Text(t('lb_col_streak')), numeric: true),
                  ],
                  rows: _data!.map((row) {
                    final rank = row['rank'] as int? ?? 0;
                    final name = row['name'] as String? ?? '';
                    final games = row['games_played'] as int? ?? 0;
                    final avg = (row['avg_score'] as num?)?.toDouble() ?? 0.0;
                    final best = row['best_score'] as int? ?? 0;
                    final hitPct = (row['avg_correct_bids_pct'] as num?)?.toDouble() ?? 0.0;
                    final streak = row['current_streak'] as int? ?? 0;
                    return DataRow(cells: [
                      DataCell(Text(_rankBadge(rank),
                          style: TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.bold,
                              color: _rankColor(rank)))),
                      DataCell(Text(name,
                          style: const TextStyle(fontWeight: FontWeight.w500),
                          overflow: TextOverflow.ellipsis)),
                      DataCell(Text(games.toString())),
                      DataCell(Text(avg.toStringAsFixed(0))),
                      DataCell(Text(best.toString())),
                      DataCell(Text('${(hitPct * 100).toStringAsFixed(0)}%')),
                      DataCell(Text(streak > 0 ? '🔥$streak' : streak.toString())),
                    ]);
                  }).toList(),
                ),
              ),
            ),
          ),
      ],
    );
  }
}

// ── Mode chip helper ────────────────────────────────────────────────────────────

class _ModeChip extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _ModeChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
        decoration: BoxDecoration(
          color: selected ? kAccent.withOpacity(0.2) : Colors.transparent,
          border: Border.all(color: selected ? kAccent : kTextDim, width: 1),
          borderRadius: BorderRadius.circular(20),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 11,
            color: selected ? kAccent : kTextDim,
            fontWeight: selected ? FontWeight.bold : FontWeight.normal,
          ),
        ),
      ),
    );
  }
}

// ── Helpers ─────────────────────────────────────────────────────────────────────

String _rankBadge(int rank) {
  if (rank == 1) return '🥇';
  if (rank == 2) return '🥈';
  if (rank == 3) return '🥉';
  return rank.toString();
}

Color _rankColor(int rank) {
  if (rank == 1) return const Color(0xFFFFD700);
  if (rank == 2) return const Color(0xFFC0C0C0);
  if (rank == 3) return const Color(0xFFCD7F32);
  return kTextDim;
}

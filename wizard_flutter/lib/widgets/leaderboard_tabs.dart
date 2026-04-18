import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../persistence/app_settings.dart';
import '../services/leaderboard_service.dart';
import '../state/game_notifier.dart';
import '../theme/app_theme.dart';

// ── Global groups leaderboard tab ──────────────────────────────────────────────

class GroupsLeaderboardTab extends StatefulWidget {
  const GroupsLeaderboardTab({super.key});

  @override
  State<GroupsLeaderboardTab> createState() => _GroupsLeaderboardTabState();
}

class _GroupsLeaderboardTabState extends State<GroupsLeaderboardTab> {
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
          child: Text('${t('leaderboard_url_label')} ${t('leaderboard_url_placeholder')}',
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

class MyGroupLeaderboardTab extends StatefulWidget {
  const MyGroupLeaderboardTab({super.key});

  @override
  State<MyGroupLeaderboardTab> createState() => _MyGroupLeaderboardTabState();
}

class _MyGroupLeaderboardTabState extends State<MyGroupLeaderboardTab> {
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
    if (code != null && (code != _lastGroupCode || (_data == null && !_loading))) {
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
          child: Text('${t('leaderboard_url_label')} ${t('leaderboard_url_placeholder')}',
              textAlign: TextAlign.center,
              style: const TextStyle(color: kTextDim)),
        ),
      );
    }

    return Column(
      children: [
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

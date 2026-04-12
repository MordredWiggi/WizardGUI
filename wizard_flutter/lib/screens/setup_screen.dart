import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';

import '../persistence/app_settings.dart';
import '../persistence/save_manager.dart';
import '../state/game_notifier.dart';
import '../theme/app_theme.dart';
import 'game_screen.dart';
import 'settings_screen.dart';

const List<String> _kAvatars = [
  '🧙‍♂️', '🧙‍♀️', '🧚‍♂️', '🧚‍♀️',
  '🧞‍♂️', '🧞‍♀️', '🧝‍♂️', '🧝‍♀️',
  '🧛‍♂️', '🧛‍♀️',
];

class SetupScreen extends StatefulWidget {
  const SetupScreen({super.key});

  @override
  State<SetupScreen> createState() => _SetupScreenState();
}

class _SetupScreenState extends State<SetupScreen> {
  final _nameController = TextEditingController();
  final _nameFocus = FocusNode();
  int _avatarIndex = 0;
  final List<Map<String, dynamic>> _players = [];
  String _gameMode = 'standard'; // 'standard' | 'multiplicative'

  List<SavedGameMeta> _savedGames = [];
  bool _loadingSaved = false;

  @override
  void initState() {
    super.initState();
    _refreshSaved();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _nameFocus.dispose();
    super.dispose();
  }

  Future<void> _refreshSaved() async {
    setState(() => _loadingSaved = true);
    final notifier = context.read<GameNotifier>();
    final games = await notifier.listSavedGames();
    if (mounted) setState(() { _savedGames = games; _loadingSaved = false; });
  }

  void _addPlayer() {
    final name = _nameController.text.trim();
    if (name.isEmpty) return;
    if (_players.any((p) => p['name'] == name)) return;
    if (_players.length >= kPlayerColors.length) return;
    setState(() {
      _players.add({'name': name, 'avatar': _kAvatars[_avatarIndex]});
      _avatarIndex = (_avatarIndex + 1) % _kAvatars.length;
      _nameController.clear();
    });
    _nameFocus.requestFocus();
  }

  void _removePlayer(String name) =>
      setState(() => _players.removeWhere((p) => p['name'] == name));

  void _startGame() {
    if (_players.length < 2) return;
    context.read<GameNotifier>().startGame(List.from(_players), _gameMode);
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (_) => const GameScreen()),
    );
  }

  Future<void> _loadGame(SavedGameMeta meta) async {
    try {
      await context.read<GameNotifier>().loadFromFile(meta.filePath);
      if (mounted) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (_) => const GameScreen()),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Load failed: $e')),
        );
      }
    }
  }

  Future<void> _deleteGame(SavedGameMeta meta) async {
    final settings = context.read<AppSettings>();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(settings.t('warning_title')),
        content: Text(settings.t('delete_game_confirm')),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: Text(settings.t('cancel'))),
          TextButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: Text(settings.t('delete_game'))),
        ],
      ),
    );
    if (confirmed == true) {
      await context.read<GameNotifier>().deleteSavedGame(meta.filePath);
      await _refreshSaved();
    }
  }

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<AppSettings>();
    final t = settings.t;
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(t('app_title'),
            style: const TextStyle(fontSize: 22, letterSpacing: 3)),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.settings_outlined),
            tooltip: t('settings_title'),
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const SettingsScreen()),
            ),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // ── Subtitle ──────────────────────────────────────────────────
            Text(t('subtitle'),
                textAlign: TextAlign.center,
                style: theme.textTheme.bodyMedium
                    ?.copyWith(color: theme.colorScheme.onSurface.withOpacity(0.6),
                        letterSpacing: 1.5)),

            const SizedBox(height: 28),

            // ── Add players panel ─────────────────────────────────────────
            _SectionCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _SectionHeader(t('add_players_header')),
                  const SizedBox(height: 12),
                  Row(children: [
                    // Avatar picker
                    GestureDetector(
                      onTap: () => setState(() =>
                          _avatarIndex = (_avatarIndex + 1) % _kAvatars.length),
                      child: Container(
                        width: 48,
                        height: 48,
                        alignment: Alignment.center,
                        decoration: BoxDecoration(
                          color: theme.colorScheme.surface,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                              color:
                                  theme.colorScheme.primary.withOpacity(0.5)),
                        ),
                        child: Text(_kAvatars[_avatarIndex],
                            style: const TextStyle(fontSize: 24)),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: TextField(
                        controller: _nameController,
                        focusNode: _nameFocus,
                        decoration: InputDecoration(
                            hintText: t('player_name_placeholder')),
                        onSubmitted: (_) => _addPlayer(),
                        textInputAction: TextInputAction.done,
                      ),
                    ),
                    const SizedBox(width: 8),
                    ElevatedButton(
                      onPressed: _addPlayer,
                      child: Text(t('btn_add')),
                    ),
                  ]),

                  // Player chips
                  if (_players.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: _players.asMap().entries.map((e) {
                        final color = kPlayerColors[e.key % kPlayerColors.length];
                        return _PlayerChip(
                          avatar: e.value['avatar'] as String,
                          name: e.value['name'] as String,
                          color: color,
                          onRemove: () => _removePlayer(e.value['name'] as String),
                        );
                      }).toList(),
                    ),
                  ],

                  const SizedBox(height: 10),
                  Text(
                    _players.isEmpty
                        ? t('hint_min_players')
                        : t('hint_players_selected',
                            {'n': _players.length.toString()}),
                    style: theme.textTheme.bodySmall
                        ?.copyWith(fontStyle: FontStyle.italic),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 16),

            // ── Game mode panel ────────────────────────────────────────────
            _SectionCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _SectionHeader(t('game_mode_label')),
                  const SizedBox(height: 10),
                  RadioGroup<String>(
                    groupValue: _gameMode,
                    onChanged: (v) => setState(() => _gameMode = v!),
                    child: Row(children: [
                      Expanded(
                        child: RadioListTile<String>(
                          value: 'standard',
                          title: Text(t('game_mode_standard')),
                          dense: true,
                          contentPadding: EdgeInsets.zero,
                        ),
                      ),
                      Expanded(
                        child: RadioListTile<String>(
                          value: 'multiplicative',
                          title: Text(t('game_mode_multiplicative')),
                          dense: true,
                          contentPadding: EdgeInsets.zero,
                        ),
                      ),
                    ]),
                  ),
                  const SizedBox(height: 8),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: _players.length >= 2 ? _startGame : null,
                      child: Text(t('start_game')),
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 16),

            // ── Saved games panel ──────────────────────────────────────────
            _SectionCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      _SectionHeader(t('saved_games_header')),
                      IconButton(
                        icon: const Icon(Icons.refresh, size: 20),
                        tooltip: t('btn_refresh'),
                        onPressed: _refreshSaved,
                        visualDensity: VisualDensity.compact,
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  if (_loadingSaved)
                    const Center(child: CircularProgressIndicator())
                  else if (_savedGames.isEmpty)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      child: Text(t('no_saved_games'),
                          style: theme.textTheme.bodySmall
                              ?.copyWith(fontStyle: FontStyle.italic)),
                    )
                  else
                    ListView.separated(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: _savedGames.length,
                      separatorBuilder: (_, __) => const Divider(height: 1),
                      itemBuilder: (_, i) {
                        final g = _savedGames[i];
                        String dateStr = '–';
                        try {
                          final dt = DateTime.parse(g.savedAt);
                          dateStr =
                              DateFormat('dd.MM.yyyy HH:mm').format(dt.toLocal());
                        } catch (_) {}
                        return ListTile(
                          dense: true,
                          title: Text(g.name,
                              style: theme.textTheme.bodyMedium
                                  ?.copyWith(fontWeight: FontWeight.w600)),
                          subtitle: Text(
                              '$dateStr  ·  ${g.players.join(', ')}  ·  ${t('saved_round')} ${g.rounds}',
                              style: theme.textTheme.bodySmall),
                          trailing: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              IconButton(
                                icon: const Icon(Icons.folder_open_outlined, size: 20),
                                tooltip: t('load'),
                                onPressed: () => _loadGame(g),
                              ),
                              IconButton(
                                icon: const Icon(Icons.delete_outline, size: 20),
                                tooltip: t('delete_game'),
                                onPressed: () => _deleteGame(g),
                              ),
                            ],
                          ),
                          onTap: () => _loadGame(g),
                        );
                      },
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Shared sub-widgets ─────────────────────────────────────────────────────────

class _SectionCard extends StatelessWidget {
  final Widget child;
  const _SectionCard({required this.child});

  @override
  Widget build(BuildContext context) => Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: child,
        ),
      );
}

class _SectionHeader extends StatelessWidget {
  final String text;
  const _SectionHeader(this.text);

  @override
  Widget build(BuildContext context) => Text(
        text,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
              letterSpacing: 1.5,
              fontWeight: FontWeight.bold,
              color: Theme.of(context).colorScheme.primary,
            ),
      );
}

class _PlayerChip extends StatelessWidget {
  final String avatar;
  final String name;
  final Color color;
  final VoidCallback onRemove;

  const _PlayerChip({
    required this.avatar,
    required this.name,
    required this.color,
    required this.onRemove,
  });

  @override
  Widget build(BuildContext context) => Container(
        decoration: BoxDecoration(
          border: Border.all(color: color),
          borderRadius: BorderRadius.circular(20),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(avatar, style: const TextStyle(fontSize: 16)),
            const SizedBox(width: 4),
            Text(name,
                style: TextStyle(
                    color: color, fontWeight: FontWeight.w600, fontSize: 13)),
            const SizedBox(width: 4),
            GestureDetector(
              onTap: onRemove,
              child: Icon(Icons.close, size: 14, color: color),
            ),
          ],
        ),
      );
}

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';

import '../persistence/app_settings.dart';
import '../persistence/save_manager.dart';
import '../services/leaderboard_service.dart';
import '../state/game_notifier.dart';
import '../theme/app_theme.dart';
import '../widgets/leaderboard_tabs.dart';
import 'game_screen.dart';
import 'settings_screen.dart';
import 'pending_sync_dialog.dart';

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
  String _gameMode = 'standard';

  List<SavedGameMeta> _savedGames = [];
  bool _loadingSaved = false;

  // Index of the active bottom tab: 0 = Saved Games, 1 = Groups LB, 2 = My Group LB
  int _bottomTab = 0;

  // ── Group state ──────────────────────────────────────────────────────────
  // No group = offline by default. The user can always start a game without
  // picking a group.
  Map<String, dynamic>? _selectedGroup;

  @override
  void initState() {
    super.initState();
    _refreshSaved();
    // On first build, check for offline-queued games and offer to sync.
    WidgetsBinding.instance.addPostFrameCallback((_) => _checkPendingSync());
  }

  Future<void> _checkPendingSync() async {
    if (!mounted) return;
    final notifier = context.read<GameNotifier>();
    final settings = context.read<AppSettings>();
    final pending = await notifier.listPendingSyncGames();
    if (!mounted || pending.isEmpty) return;

    final url = settings.leaderboardUrl;
    if (url.isEmpty) return;

    final service = LeaderboardService(url);
    // Probe connectivity before prompting – if the server is unreachable we
    // just leave the games flagged and try again next launch.
    final probe = await service.listGroups(search: '');
    if (!mounted || probe == null) return;

    await showPendingSyncDialog(
      context: context,
      pending: pending,
      service: service,
    );
    if (mounted) _refreshSaved();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _nameFocus.dispose();
    super.dispose();
  }

  LeaderboardService? _getService() {
    final url = context.read<AppSettings>().leaderboardUrl;
    if (url.isEmpty) return null;
    return LeaderboardService(url);
  }

  Future<void> _refreshSaved() async {
    setState(() => _loadingSaved = true);
    final notifier = context.read<GameNotifier>();
    final games = await notifier.listSavedGames();
    if (mounted) setState(() { _savedGames = games; _loadingSaved = false; });
  }

  // ── Group actions ──────────────────────────────────────────────────────────

  Future<void> _joinGroup() async {
    final svc = _getService();
    if (svc == null) {
      _showNoUrlSnackbar();
      return;
    }
    final group = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (_) => _GroupSelectDialog(service: svc),
    );
    if (group != null && mounted) {
      setState(() => _selectedGroup = group);
      context.read<GameNotifier>().setGroup(group);
    }
  }

  Future<void> _createGroup() async {
    final svc = _getService();
    if (svc == null) {
      _showNoUrlSnackbar();
      return;
    }
    final group = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (_) => _GroupCreateDialog(service: svc),
    );
    if (group != null && mounted) {
      setState(() => _selectedGroup = group);
      context.read<GameNotifier>().setGroup(group);
    }
  }

  void _clearGroup() {
    // Return fully to the default offline state — no lingering group.
    setState(() {
      _selectedGroup = null;
      // If the user was viewing the My-Group tab, bounce back to saved games.
      if (_bottomTab == 2) _bottomTab = 0;
    });
    context.read<GameNotifier>().clearGroup();
  }

  void _showNoUrlSnackbar() {
    final t = context.read<AppSettings>().t;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(t('leaderboard_url_label') + ' – not configured in Settings')),
    );
  }

  // ── Player actions ─────────────────────────────────────────────────────────

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
    // No group selected is a valid, offline-by-default way to play.
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
        final settings = context.read<AppSettings>();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
                settings.t('load_failed', {'error': e.toString()})),
            duration: settings.messageDuration,
          ),
        );
      }
    }
  }

  Widget _buildSavedGames(BuildContext context, String Function(String, [Map<String, String>]) t, ThemeData theme) {
    if (_loadingSaved) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_savedGames.isEmpty) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Align(
            alignment: Alignment.centerRight,
            child: IconButton(
              icon: const Icon(Icons.refresh, size: 20),
              tooltip: t('btn_refresh'),
              onPressed: _refreshSaved,
              visualDensity: VisualDensity.compact,
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 16),
            child: Text(
              t('no_saved_games'),
              textAlign: TextAlign.center,
              style: theme.textTheme.bodySmall?.copyWith(fontStyle: FontStyle.italic),
            ),
          ),
        ],
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Align(
          alignment: Alignment.centerRight,
          child: IconButton(
            icon: const Icon(Icons.refresh, size: 20),
            tooltip: t('btn_refresh'),
            onPressed: _refreshSaved,
            visualDensity: VisualDensity.compact,
          ),
        ),
        Expanded(
          child: ListView.separated(
            itemCount: _savedGames.length,
            separatorBuilder: (_, __) => const Divider(height: 1),
            itemBuilder: (_, i) {
              final g = _savedGames[i];
              String dateStr = '–';
              try {
                final dt = DateTime.parse(g.savedAt);
                dateStr = DateFormat('dd.MM.yyyy HH:mm').format(dt.toLocal());
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
        ),
      ],
    );
  }

  Future<void> _deleteGame(SavedGameMeta meta) async {
    final settings = context.read<AppSettings>();
    final t = settings.t;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(t('warning_title')),
        content: Text(t('delete_game_confirm')),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: Text(t('cancel'))),
          TextButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: Text(t('delete_game'))),
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
    final canStart = _players.length >= 2;

    return Scaffold(
      appBar: AppBar(
        title: Text(t('app_title'),
            style: const TextStyle(fontSize: 22, letterSpacing: 3)),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.language),
            tooltip: 'Online Leaderboard',
            onPressed: () => launchUrl(Uri.parse('https://play-wizard.de')),
          ),
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
                style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.onSurface.withOpacity(0.6),
                    letterSpacing: 1.5)),

            const SizedBox(height: 24),

            // ── Step 1: Group ─────────────────────────────────────────────
            _SectionCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _SectionHeader(t('group_header')),
                  const SizedBox(height: 10),

                  // Current group status
                  if (_selectedGroup != null) ...[
                    Row(children: [
                      const Icon(Icons.group, size: 18),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          t('group_selected', {
                            'name': _selectedGroup!['name'] as String,
                            'code': _selectedGroup!['code'] as String,
                          }),
                          style: theme.textTheme.bodyMedium?.copyWith(
                              color: kSuccess, fontWeight: FontWeight.w600),
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.close, size: 18),
                        onPressed: _clearGroup,
                        tooltip: 'Clear',
                        padding: EdgeInsets.zero,
                        visualDensity: VisualDensity.compact,
                      ),
                    ]),
                    const SizedBox(height: 8),
                  ] else ...[
                    Text(t('group_not_selected'),
                        style: theme.textTheme.bodySmall?.copyWith(
                            fontStyle: FontStyle.italic,
                            color: theme.colorScheme.onSurface.withOpacity(0.6))),
                    const SizedBox(height: 10),
                  ],

                  // Action buttons
                  Row(children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _joinGroup,
                        icon: const Icon(Icons.login, size: 18),
                        label: Text(t('group_select_label')),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _createGroup,
                        icon: const Icon(Icons.add, size: 18),
                        label: Text(t('group_create_btn')),
                      ),
                    ),
                  ]),
                ],
              ),
            ),

            const SizedBox(height: 16),

            // ── Step 2: Add players ───────────────────────────────────────
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
                              color: theme.colorScheme.primary.withOpacity(0.5)),
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

            // ── Game mode + Start ─────────────────────────────────────────
            _SectionCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _SectionHeader(t('game_mode_label')),
                  const SizedBox(height: 10),
                  Row(children: [
                    Expanded(
                      child: RadioListTile<String>(
                        value: 'standard',
                        groupValue: _gameMode,
                        onChanged: (v) => setState(() => _gameMode = v!),
                        title: Text(t('game_mode_standard')),
                        dense: true,
                        contentPadding: EdgeInsets.zero,
                      ),
                    ),
                    Expanded(
                      child: RadioListTile<String>(
                        value: 'multiplicative',
                        groupValue: _gameMode,
                        onChanged: (v) => setState(() => _gameMode = v!),
                        title: Text(t('game_mode_multiplicative')),
                        dense: true,
                        contentPadding: EdgeInsets.zero,
                      ),
                    ),
                  ]),
                  const SizedBox(height: 8),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: canStart ? _startGame : null,
                      child: Text(t('start_game')),
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 16),

            // ── Bottom tabs: Saved games | Groups LB | My Group LB ────────
            _SectionCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: [
                      _TabChip(
                        label: t('saved_games_header'),
                        selected: _bottomTab == 0,
                        onTap: () => setState(() => _bottomTab = 0),
                      ),
                      _TabChip(
                        label: t('tab_groups_lb'),
                        selected: _bottomTab == 1,
                        onTap: () => setState(() => _bottomTab = 1),
                      ),
                      _TabChip(
                        label: t('tab_group_lb'),
                        selected: _bottomTab == 2,
                        // Only enabled once a group is selected
                        onTap: _selectedGroup == null
                            ? null
                            : () => setState(() => _bottomTab = 2),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  SizedBox(
                    height: 340,
                    child: IndexedStack(
                      index: _bottomTab,
                      children: [
                        _buildSavedGames(context, t, theme),
                        const GroupsLeaderboardTab(),
                        const MyGroupLeaderboardTab(),
                      ],
                    ),
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

// ── Group Select Dialog ────────────────────────────────────────────────────────

class _GroupSelectDialog extends StatefulWidget {
  final LeaderboardService service;
  const _GroupSelectDialog({required this.service});

  @override
  State<_GroupSelectDialog> createState() => _GroupSelectDialogState();
}

class _GroupSelectDialogState extends State<_GroupSelectDialog> {
  final _searchController = TextEditingController();
  final _codeController = TextEditingController();
  final _codeFocusNode = FocusNode();
  List<Map<String, dynamic>> _groups = [];
  bool _loading = false;
  bool _connectionFailed = false;
  String? _codeStatus; // null | 'ok' | 'error'
  Map<String, dynamic>? _validatedGroup;

  @override
  void initState() {
    super.initState();
    _doSearch('');
  }

  @override
  void dispose() {
    _searchController.dispose();
    _codeController.dispose();
    _codeFocusNode.dispose();
    super.dispose();
  }

  Future<void> _doSearch(String q) async {
    setState(() => _loading = true);
    final result = await widget.service.listGroups(search: q);
    if (mounted) {
      setState(() {
        _groups = result ?? [];
        _connectionFailed = result == null;
        _loading = false;
      });
    }
  }

  Future<void> _validateCode() async {
    final code = _codeController.text.trim();
    if (code.length != 4 || int.tryParse(code) == null) {
      setState(() { _codeStatus = 'error'; _validatedGroup = null; });
      return;
    }
    final group = await widget.service.getGroupByCode(code);
    if (mounted) {
      setState(() {
        _validatedGroup = group;
        _codeStatus = group != null ? 'ok' : 'error';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final settings = context.read<AppSettings>();
    final t = settings.t;
    final theme = Theme.of(context);

    return AlertDialog(
      title: Text(t('group_select_label')),
      content: SizedBox(
        width: 380,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Search
            TextField(
              controller: _searchController,
              decoration: InputDecoration(hintText: t('group_search_placeholder')),
              onChanged: (v) => _doSearch(v),
            ),
            const SizedBox(height: 8),

            // Groups list
            if (_loading)
              const LinearProgressIndicator()
            else if (_connectionFailed)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: Text(t('group_connection_error'),
                    style: theme.textTheme.bodySmall?.copyWith(color: kDanger)),
              )
            else if (_groups.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: Text(t('no_groups'),
                    style: theme.textTheme.bodySmall
                        ?.copyWith(fontStyle: FontStyle.italic)),
              )
            else
              SizedBox(
                height: 140,
                child: ListView.builder(
                  itemCount: _groups.length,
                  itemBuilder: (_, i) {
                    final g = _groups[i];
                    final n = (g['player_count'] as num?)?.toInt() ?? 0;
                    return ListTile(
                      dense: true,
                      leading: const Icon(Icons.group_outlined, size: 20),
                      title: Text(g['name'] as String),
                      subtitle: Text(
                          t('group_players_count', {'n': n.toString()}),
                          style: theme.textTheme.bodySmall),
                      onTap: () {
                        _searchController.text = g['name'] as String;
                        _doSearch(g['name'] as String);
                        _codeFocusNode.requestFocus();
                      },
                    );
                  },
                ),
              ),

            const Divider(),

            // Code validation
            Text(t('group_code_label'),
                style: theme.textTheme.bodySmall
                    ?.copyWith(fontWeight: FontWeight.w600)),
            const SizedBox(height: 6),
            Row(children: [
              Expanded(
                child: TextField(
                  controller: _codeController,
                  focusNode: _codeFocusNode,
                  decoration: InputDecoration(
                      hintText: t('group_code_placeholder')),
                  keyboardType: TextInputType.number,
                  maxLength: 4,
                  onChanged: (_) => setState(() { _codeStatus = null; _validatedGroup = null; }),
                ),
              ),
              const SizedBox(width: 8),
              ElevatedButton(
                onPressed: _validateCode,
                child: Text(t('group_code_validate')),
              ),
            ]),

            if (_codeStatus == 'ok')
              Text(
                t('group_code_correct',
                    {'name': _validatedGroup?['name'] ?? ''}),
                style: theme.textTheme.bodySmall?.copyWith(color: kSuccess),
              )
            else if (_codeStatus == 'error')
              Text(t('group_code_invalid'),
                  style: theme.textTheme.bodySmall?.copyWith(color: kDanger)),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(t('cancel')),
        ),
        ElevatedButton(
          onPressed:
              _validatedGroup != null ? () => Navigator.pop(context, _validatedGroup) : null,
          child: Text(t('load')),
        ),
      ],
    );
  }
}

// ── Group Create Dialog ────────────────────────────────────────────────────────

class _GroupCreateDialog extends StatefulWidget {
  final LeaderboardService service;
  const _GroupCreateDialog({required this.service});

  @override
  State<_GroupCreateDialog> createState() => _GroupCreateDialogState();
}

class _GroupCreateDialogState extends State<_GroupCreateDialog> {
  final _nameController = TextEditingController();
  final _codeController = TextEditingController();
  String _visibility = 'public';
  String? _statusMsg;
  bool _isError = false;
  bool _creating = false;

  @override
  void dispose() {
    _nameController.dispose();
    _codeController.dispose();
    super.dispose();
  }

  Future<void> _create() async {
    final t = context.read<AppSettings>().t;
    final name = _nameController.text.trim();
    final code = _codeController.text.trim();
    if (name.isEmpty) {
      setState(() { _statusMsg = t('group_name_placeholder') + ' required'; _isError = true; });
      return;
    }
    if (code.length != 4 || int.tryParse(code) == null) {
      setState(() { _statusMsg = t('group_code_invalid'); _isError = true; });
      return;
    }
    setState(() => _creating = true);
    final result = await widget.service.createGroup(
        name: name, code: code, visibility: _visibility);
    if (!mounted) return;
    setState(() => _creating = false);
    if (result.isOk) {
      setState(() {
        _statusMsg = t('group_created_ok', {'name': name, 'code': code});
        _isError = false;
      });
      await Future.delayed(const Duration(milliseconds: 800));
      if (mounted) Navigator.pop(context, result.group);
    } else if (result.taken) {
      setState(() {
        _statusMsg = t('group_code_taken', {'code': code});
        _isError = true;
      });
    } else {
      setState(() {
        _statusMsg = t('group_connection_error');
        _isError = true;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final settings = context.read<AppSettings>();
    final t = settings.t;
    final theme = Theme.of(context);

    return AlertDialog(
      title: Text(t('group_create_label')),
      content: SizedBox(
        width: 340,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              controller: _nameController,
              decoration: InputDecoration(hintText: t('group_name_placeholder')),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _codeController,
              decoration: InputDecoration(hintText: t('group_code_placeholder')),
              keyboardType: TextInputType.number,
              maxLength: 4,
            ),
            const SizedBox(height: 6),
            // Visibility
            Row(children: [
              Expanded(
                child: RadioListTile<String>(
                  value: 'public',
                  groupValue: _visibility,
                  onChanged: (v) => setState(() => _visibility = v!),
                  title: Text(t('group_visibility_public'),
                      style: const TextStyle(fontSize: 13)),
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                ),
              ),
              Expanded(
                child: RadioListTile<String>(
                  value: 'hidden',
                  groupValue: _visibility,
                  onChanged: (v) => setState(() => _visibility = v!),
                  title: Text(t('group_visibility_hidden'),
                      style: const TextStyle(fontSize: 13)),
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                ),
              ),
            ]),
            if (_statusMsg != null)
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Text(_statusMsg!,
                    style: theme.textTheme.bodySmall?.copyWith(
                        color: _isError ? kDanger : kSuccess)),
              ),
            if (_creating) const LinearProgressIndicator(),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(t('cancel')),
        ),
        ElevatedButton(
          onPressed: _creating ? null : _create,
          child: Text(t('group_create_btn')),
        ),
      ],
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

class _TabChip extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback? onTap;
  const _TabChip({required this.label, required this.selected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final enabled = onTap != null;
    final color = !enabled
        ? theme.colorScheme.onSurface.withOpacity(0.3)
        : selected
            ? theme.colorScheme.onPrimary
            : theme.colorScheme.onSurface.withOpacity(0.7);
    final bg = selected
        ? theme.colorScheme.primary
        : theme.colorScheme.surface;
    final borderColor = !enabled
        ? theme.dividerColor
        : selected
            ? theme.colorScheme.primary
            : theme.colorScheme.onSurface.withOpacity(0.2);
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(6),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(
            color: bg,
            border: Border.all(color: borderColor, width: 1),
            borderRadius: BorderRadius.circular(6),
          ),
          child: Text(
            label,
            style: TextStyle(
              fontSize: 12,
              fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
              color: color,
            ),
          ),
        ),
      ),
    );
  }
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

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../main.dart' show rootScaffoldMessengerKey;
import '../persistence/app_settings.dart';
import '../persistence/save_manager.dart';
import '../services/leaderboard_service.dart';
import '../state/game_notifier.dart';

/// Top-level entry point: shows the pending-sync dialog as a bottom sheet.
///
/// Lets the user assign groups to each offline-queued game (or leave them
/// ungrouped), then uploads them and clears the pending_sync flag on success.
Future<void> showPendingSyncDialog({
  required BuildContext context,
  required List<PendingSyncGame> pending,
  required LeaderboardService service,
}) async {
  await showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    builder: (_) => _PendingSyncSheet(pending: pending, service: service),
  );
}

class _PendingSyncSheet extends StatefulWidget {
  final List<PendingSyncGame> pending;
  final LeaderboardService service;

  const _PendingSyncSheet({required this.pending, required this.service});

  @override
  State<_PendingSyncSheet> createState() => _PendingSyncSheetState();
}

class _PendingSyncSheetState extends State<_PendingSyncSheet> {
  // filePath → group code (or null for "no group")
  late final Map<String, String?> _assignments;
  bool _uploading = false;

  @override
  void initState() {
    super.initState();
    _assignments = {
      for (final p in widget.pending) p.filePath: p.groupCode,
    };
  }

  Future<void> _pickGroup(PendingSyncGame p) async {
    final code = await showDialog<String?>(
      context: context,
      builder: (_) => _GroupPickerDialog(service: widget.service),
    );
    if (code != null) {
      setState(() => _assignments[p.filePath] = code.isEmpty ? null : code);
    }
  }

  Future<void> _uploadAll() async {
    final settings = context.read<AppSettings>();
    final notifier = context.read<GameNotifier>();
    final t = settings.t;
    setState(() => _uploading = true);

    int synced = 0;
    for (final p in widget.pending) {
      final code = _assignments[p.filePath];
      // Persist group-code changes first so the file reflects the user's choice
      if (code != p.groupCode) {
        await notifier.updatePendingGroupCode(p.filePath, code);
      }
      final payload = buildGameSubmission(
        p.game,
        playedAt: p.savedAt.isNotEmpty ? p.savedAt : null,
        groupCode: code,
      );
      try {
        if (await widget.service.submitGame(payload)) {
          await notifier.markSynced(p.filePath);
          synced++;
        }
      } catch (_) {/* ignore individual failures */}
    }

    if (!mounted) return;
    Navigator.pop(context);
    if (synced > 0) {
      rootScaffoldMessengerKey.currentState?.showSnackBar(SnackBar(
        content: Text(t('pending_sync_success', {'n': synced.toString()})),
        duration: settings.messageDuration,
      ));
    }
  }

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<AppSettings>();
    final t = settings.t;
    final theme = Theme.of(context);
    final mq = MediaQuery.of(context);

    return Padding(
      padding: EdgeInsets.only(bottom: mq.viewInsets.bottom),
      child: ConstrainedBox(
        constraints: BoxConstraints(maxHeight: mq.size.height * 0.8),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(children: [
                Icon(Icons.cloud_upload_outlined,
                    size: 22, color: theme.colorScheme.primary),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(t('pending_sync_title'),
                      style: theme.textTheme.titleMedium
                          ?.copyWith(fontWeight: FontWeight.bold)),
                ),
              ]),
              const SizedBox(height: 8),
              Text(
                t('pending_sync_message',
                    {'n': widget.pending.length.toString()}),
                style: theme.textTheme.bodySmall,
              ),
              const SizedBox(height: 12),
              Flexible(
                child: ListView.separated(
                  shrinkWrap: true,
                  itemCount: widget.pending.length,
                  separatorBuilder: (_, __) => const Divider(height: 1),
                  itemBuilder: (_, i) {
                    final p = widget.pending[i];
                    final code = _assignments[p.filePath];
                    return ListTile(
                      dense: true,
                      contentPadding: EdgeInsets.zero,
                      title: Text(p.name,
                          style: theme.textTheme.bodyMedium
                              ?.copyWith(fontWeight: FontWeight.w600)),
                      subtitle: Text(
                        code == null
                            ? t('pending_sync_no_group')
                            : '${t('group_header')}: $code',
                        style: theme.textTheme.bodySmall,
                      ),
                      trailing: TextButton(
                        onPressed:
                            _uploading ? null : () => _pickGroup(p),
                        child: Text(t('pending_sync_assign_group')),
                      ),
                    );
                  },
                ),
              ),
              if (_uploading) const LinearProgressIndicator(),
              const SizedBox(height: 12),
              Row(children: [
                TextButton(
                  onPressed:
                      _uploading ? null : () => Navigator.pop(context),
                  child: Text(t('pending_sync_skip')),
                ),
                const Spacer(),
                ElevatedButton.icon(
                  onPressed: _uploading ? null : _uploadAll,
                  icon: const Icon(Icons.cloud_upload, size: 18),
                  label: Text(t('pending_sync_upload')),
                ),
              ]),
            ],
          ),
        ),
      ),
    );
  }
}

class _GroupPickerDialog extends StatefulWidget {
  final LeaderboardService service;
  const _GroupPickerDialog({required this.service});

  @override
  State<_GroupPickerDialog> createState() => _GroupPickerDialogState();
}

class _GroupPickerDialogState extends State<_GroupPickerDialog> {
  final _codeController = TextEditingController();
  List<Map<String, dynamic>> _groups = [];
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    _search('');
  }

  @override
  void dispose() {
    _codeController.dispose();
    super.dispose();
  }

  Future<void> _search(String q) async {
    setState(() => _loading = true);
    final res = await widget.service.listGroups(search: q);
    if (mounted) {
      setState(() {
        _groups = res ?? [];
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.read<AppSettings>().t;
    final theme = Theme.of(context);
    return AlertDialog(
      title: Text(t('pending_sync_assign_group')),
      content: SizedBox(
        width: 360,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              decoration:
                  InputDecoration(hintText: t('group_search_placeholder')),
              onChanged: _search,
            ),
            const SizedBox(height: 8),
            if (_loading)
              const LinearProgressIndicator()
            else if (_groups.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Text(t('no_groups'),
                    style: theme.textTheme.bodySmall
                        ?.copyWith(fontStyle: FontStyle.italic)),
              )
            else
              SizedBox(
                height: 180,
                child: ListView.builder(
                  itemCount: _groups.length,
                  itemBuilder: (_, i) {
                    final g = _groups[i];
                    return ListTile(
                      dense: true,
                      leading: const Icon(Icons.group_outlined, size: 20),
                      title: Text(g['name'] as String),
                      subtitle: Text('#${g['code']}',
                          style: theme.textTheme.bodySmall),
                      onTap: () => Navigator.pop(context, g['code'] as String),
                    );
                  },
                ),
              ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(t('cancel')),
        ),
        TextButton(
          // empty string = explicit "no group"
          onPressed: () => Navigator.pop(context, ''),
          child: Text(t('pending_sync_no_group')),
        ),
      ],
    );
  }
}

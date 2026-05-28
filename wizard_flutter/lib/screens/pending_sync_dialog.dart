import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../main.dart' show rootScaffoldMessengerKey;
import '../persistence/app_settings.dart';
import '../persistence/save_manager.dart';
import '../services/leaderboard_service.dart';
import '../state/game_notifier.dart';
import '../theme/app_theme.dart';

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
    _assignments = {for (final p in widget.pending) p.filePath: p.groupCode};
  }

  Future<void> _pickGroup(PendingSyncGame p) async {
    // Show the picker as another bottom sheet on top of this one. Nesting a
    // dialog over a modal bottom sheet was unreliable on some devices — taps
    // on the group list never reached the ListTile callback. Bottom sheets
    // stack predictably and accept input from the user.
    final code = await showModalBottomSheet<String?>(
      context: context,
      isScrollControlled: true,
      builder: (_) => const _GroupPickerSheet(),
    );
    if (!mounted || code == null) return;
    setState(() => _assignments[p.filePath] = code.isEmpty ? null : code);
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
        // A non-null response means the server accepted (created or duplicate).
        if (await widget.service.submitGame(payload) != null) {
          await notifier.markSynced(p.filePath);
          synced++;
        }
      } catch (_) {
        /* ignore individual failures */
      }
    }

    if (!mounted) return;
    Navigator.pop(context);
    if (synced > 0) {
      rootScaffoldMessengerKey.currentState?.showSnackBar(
        SnackBar(
          content: Text(t('pending_sync_success', {'n': synced.toString()})),
          duration: settings.messageDuration,
        ),
      );
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
              Row(
                children: [
                  Icon(
                    Icons.cloud_upload_outlined,
                    size: 22,
                    color: theme.colorScheme.primary,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      t('pending_sync_title'),
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                t('pending_sync_message', {
                  'n': widget.pending.length.toString(),
                }),
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
                      title: Text(
                        p.name,
                        style: theme.textTheme.bodyMedium?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      subtitle: Text(
                        code == null
                            ? t('pending_sync_no_group')
                            : '${t('group_header')}: $code',
                        style: theme.textTheme.bodySmall,
                      ),
                      trailing: TextButton(
                        onPressed: _uploading ? null : () => _pickGroup(p),
                        child: Text(t('pending_sync_assign_group')),
                      ),
                    );
                  },
                ),
              ),
              if (_uploading) const LinearProgressIndicator(),
              const SizedBox(height: 12),
              Row(
                children: [
                  TextButton(
                    onPressed: _uploading ? null : () => Navigator.pop(context),
                    child: Text(t('pending_sync_skip')),
                  ),
                  const Spacer(),
                  ElevatedButton.icon(
                    onPressed: _uploading ? null : _uploadAll,
                    icon: const Icon(Icons.cloud_upload, size: 18),
                    label: Text(t('pending_sync_upload')),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Bottom-sheet group picker for the pending-sync flow.
///
/// Pops with:
///   • a 4-digit group code (group selected),
///   • an empty string (user explicitly chose "no group"),
///   • null (user dismissed without choosing).
///
/// The list of selectable groups comes from [AppSettings.knownGroups] — the
/// groups the user has previously joined or created on this device. The
/// public `/api/groups` endpoint deliberately strips the 4-digit `code` from
/// its response (it's a shared secret), so the only reliable place to look
/// up codes for the upload payload is the local known-groups cache.
class _GroupPickerSheet extends StatefulWidget {
  const _GroupPickerSheet();

  @override
  State<_GroupPickerSheet> createState() => _GroupPickerSheetState();
}

class _GroupPickerSheetState extends State<_GroupPickerSheet> {
  final _codeController = TextEditingController();

  @override
  void dispose() {
    _codeController.dispose();
    super.dispose();
  }

  bool get _codeValid {
    final s = _codeController.text.trim();
    return s.length == 4 && int.tryParse(s) != null;
  }

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<AppSettings>();
    final t = settings.t;
    final theme = Theme.of(context);
    final mq = MediaQuery.of(context);
    final groups = settings.knownGroups;

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
              Row(
                children: [
                  Icon(
                    Icons.group_outlined,
                    size: 22,
                    color: theme.colorScheme.primary,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      t('pending_sync_assign_group'),
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),

              // Known groups list — these have codes locally, so tapping one
              // is sufficient to assign the upload.
              if (groups.isEmpty)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  child: Text(
                    t('no_groups'),
                    style: theme.textTheme.bodySmall?.copyWith(
                      fontStyle: FontStyle.italic,
                    ),
                  ),
                )
              else
                Flexible(
                  child: ListView.separated(
                    shrinkWrap: true,
                    itemCount: groups.length,
                    separatorBuilder: (_, __) => const Divider(height: 1),
                    itemBuilder: (_, i) {
                      final g = groups[i];
                      final name = (g['name'] as String?) ?? '';
                      final code = (g['code'] as String?) ?? '';
                      return ListTile(
                        dense: true,
                        contentPadding: EdgeInsets.zero,
                        leading: const Icon(Icons.group_outlined, size: 20),
                        title: Text(
                          name,
                          style: theme.textTheme.bodyMedium?.copyWith(
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        subtitle: Text(
                          '#$code',
                          style: theme.textTheme.bodySmall,
                        ),
                        onTap: code.isEmpty
                            ? null
                            : () => Navigator.pop(context, code),
                      );
                    },
                  ),
                ),

              const Divider(height: 24),

              // Manual code entry — for groups the user knows the code for
              // but hasn't joined on this device. We don't validate against
              // the server here; the upload itself will succeed or fail.
              Text(
                t('group_code_label'),
                style: theme.textTheme.bodySmall?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 6),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _codeController,
                      decoration: InputDecoration(
                        hintText: t('group_code_placeholder'),
                        counterText: '',
                      ),
                      keyboardType: TextInputType.number,
                      maxLength: 4,
                      onChanged: (_) => setState(() {}),
                    ),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton(
                    onPressed: _codeValid
                        ? () => Navigator.pop(
                            context,
                            _codeController.text.trim(),
                          )
                        : null,
                    child: Text(t('btn_add')),
                  ),
                ],
              ),

              const SizedBox(height: 12),
              Row(
                children: [
                  TextButton(
                    onPressed: () => Navigator.pop(context),
                    child: Text(t('cancel')),
                  ),
                  const Spacer(),
                  TextButton(
                    // Empty string = explicit "no group" choice.
                    onPressed: () => Navigator.pop(context, ''),
                    child: Text(
                      t('pending_sync_no_group'),
                      style: const TextStyle(color: kTextDim),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

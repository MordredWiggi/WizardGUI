import 'dart:convert';
import 'dart:io';
import 'package:path_provider/path_provider.dart';
import 'package:intl/intl.dart';

/// Mirrors Python SaveManager.
/// Save dir: <appDocumentsDir>/wizard_gui/games/
/// Schema version matches desktop: "1.1"
const _schemaVersion = '1.1';

/// Reserved filename for the auto-paused game (Home button mid-round).
/// Stored alongside regular saves but excluded from listings.
const _pausedFilename = '__paused__.json';

class SavedGameMeta {
  final String name;
  final String savedAt;
  final List<String> players;
  final int rounds;
  final String filePath;
  final bool pendingSync;
  final String? groupCode;

  const SavedGameMeta({
    required this.name,
    required this.savedAt,
    required this.players,
    required this.rounds,
    required this.filePath,
    this.pendingSync = false,
    this.groupCode,
  });
}

/// A pending-sync game as returned by [SaveManager.listPendingSyncGames].
class PendingSyncGame {
  final String filePath;
  final String name;
  final String savedAt;
  final String? groupCode;
  final Map<String, dynamic> game;

  const PendingSyncGame({
    required this.filePath,
    required this.name,
    required this.savedAt,
    required this.groupCode,
    required this.game,
  });
}

class SaveManager {
  /// Cached so [savePausedSync] can run without async path lookup. Filled the
  /// first time [_saveDir] is awaited (e.g. on app launch from listSavedGames
  /// or on startGame).
  Directory? _cachedSaveDir;

  Future<Directory> get _saveDir async {
    if (_cachedSaveDir != null) return _cachedSaveDir!;
    final docs = await getApplicationDocumentsDirectory();
    final dir = Directory('${docs.path}/wizard_gui/games');
    if (!await dir.exists()) {
      await dir.create(recursive: true);
    }
    _cachedSaveDir = dir;
    return dir;
  }

  /// Atomic write: write to a sibling .tmp file, fsync, then rename over the
  /// target. Prevents the destination from being left half-written if the OS
  /// kills the process mid-write (common on Android backgrounding).
  Future<void> _writeAtomic(File target, String contents) async {
    final tmp = File('${target.path}.tmp');
    await tmp.writeAsString(contents, encoding: utf8, flush: true);
    if (await target.exists()) {
      await target.delete();
    }
    await tmp.rename(target.path);
  }

  void _writeAtomicSync(File target, String contents) {
    final tmp = File('${target.path}.tmp');
    tmp.writeAsStringSync(contents, encoding: utf8, flush: true);
    if (target.existsSync()) {
      target.deleteSync();
    }
    tmp.renameSync(target.path);
  }

  // ---------------------------------------------------------------- save

  /// Persist game_data JSON; returns saved file path.
  ///
  /// Set [pendingSync] to true for games completed without a network so they
  /// can be picked up on the next launch and uploaded. [groupCode] is the
  /// target group (if any) for that later upload.
  Future<String> saveGame(
    Map<String, dynamic> gameData, {
    String? gameName,
    bool pendingSync = false,
    String? groupCode,
  }) async {
    final now = DateTime.now();
    String name = gameName ?? _defaultName(now, gameData);

    // sanitise: keep alphanumeric + '-' + '_'
    final safe = name.replaceAll(RegExp(r'[^\w\-]'), '_');

    final dir = await _saveDir;
    final filepath = '${dir.path}/$safe.json';

    final payload = {
      'schema_version': _schemaVersion,
      'meta': {
        'name': name,
        'saved_at': now.toIso8601String(),
        'pending_sync': pendingSync,
        'group_code': groupCode,
      },
      'game': gameData,
    };

    await _writeAtomic(
      File(filepath),
      const JsonEncoder.withIndent('  ').convert(payload),
    );
    return filepath;
  }

  String _defaultName(DateTime now, Map<String, dynamic> gameData) {
    final ts = DateFormat('yyyyMMdd_HHmmss').format(now);
    final players =
        (gameData['players'] as List?)
            ?.map((p) => (p as Map)['name'] as String)
            .join('_') ??
        '';
    return players.isNotEmpty ? '${ts}_$players' : 'game_$ts';
  }

  // ---------------------------------------------------------------- load

  /// Load JSON file and return the inner game dict.
  Future<Map<String, dynamic>> loadGame(String filePath) async {
    final content = await File(filePath).readAsString(encoding: utf8);
    final payload = jsonDecode(content) as Map<String, dynamic>;
    return payload['game'] as Map<String, dynamic>;
  }

  // --------------------------------------------------------- paused game

  Future<File> _pausedFile() async {
    final dir = await _saveDir;
    return File('${dir.path}/$_pausedFilename');
  }

  Map<String, dynamic> _pausedPayload(
    Map<String, dynamic> gameData,
    Map<String, dynamic>? group,
  ) => {
    'schema_version': _schemaVersion,
    'meta': {
      'saved_at': DateTime.now().toIso8601String(),
      'paused': true,
      'group': group,
    },
    'game': gameData,
  };

  /// Persist the in-progress game so it can be resumed from the menu.
  Future<String> savePaused(
    Map<String, dynamic> gameData, {
    Map<String, dynamic>? group,
  }) async {
    final file = await _pausedFile();
    await _writeAtomic(
      file,
      const JsonEncoder.withIndent(
        '  ',
      ).convert(_pausedPayload(gameData, group)),
    );
    return file.path;
  }

  /// Synchronous variant for use from app-lifecycle callbacks where the OS
  /// may kill the process before any async Future completes. Requires
  /// [_cachedSaveDir] to be populated; if it isn't, falls back to scheduling
  /// the async write (best-effort).
  void savePausedSync(
    Map<String, dynamic> gameData, {
    Map<String, dynamic>? group,
  }) {
    final dir = _cachedSaveDir;
    if (dir == null) {
      savePaused(gameData, group: group);
      return;
    }
    final file = File('${dir.path}/$_pausedFilename');
    try {
      _writeAtomicSync(
        file,
        const JsonEncoder.withIndent(
          '  ',
        ).convert(_pausedPayload(gameData, group)),
      );
    } catch (_) {
      /* best-effort during shutdown */
    }
  }

  /// Returns `{'game': ..., 'group': ...}` or `null` when nothing is paused.
  ///
  /// If the canonical file is missing but a `.tmp` sibling exists (write was
  /// interrupted *after* deleting the target but *before* the rename), we
  /// recover from the temp file rather than reporting "no paused game".
  Future<Map<String, dynamic>?> loadPaused() async {
    final file = await _pausedFile();
    File source = file;
    if (!await source.exists()) {
      final tmp = File('${file.path}.tmp');
      if (!await tmp.exists()) return null;
      source = tmp;
    }
    try {
      final payload =
          jsonDecode(await source.readAsString(encoding: utf8))
              as Map<String, dynamic>;
      final meta = (payload['meta'] as Map?) ?? const {};
      return {
        'game': Map<String, dynamic>.from(payload['game'] as Map? ?? {}),
        'group': meta['group'] == null
            ? null
            : Map<String, dynamic>.from(meta['group'] as Map),
      };
    } catch (_) {
      return null;
    }
  }

  Future<bool> hasPaused() async {
    final file = await _pausedFile();
    if (await file.exists()) return true;
    final tmp = File('${file.path}.tmp');
    return tmp.exists();
  }

  Future<void> clearPaused() async {
    try {
      final file = await _pausedFile();
      if (await file.exists()) await file.delete();
      final tmp = File('${file.path}.tmp');
      if (await tmp.exists()) await tmp.delete();
    } catch (_) {
      /* ignore */
    }
  }

  /// Synchronous variant of [clearPaused], for use after a final-round
  /// submission where we want the file gone before the function returns
  /// (so a process kill during the post-game UI delay can't leave a
  /// resumeable snapshot of an already-finished game). Falls back to the
  /// async version when the save dir hasn't been resolved yet.
  void clearPausedSync() {
    final dir = _cachedSaveDir;
    if (dir == null) {
      clearPaused();
      return;
    }
    try {
      final file = File('${dir.path}/$_pausedFilename');
      if (file.existsSync()) file.deleteSync();
      final tmp = File('${file.path}.tmp');
      if (tmp.existsSync()) tmp.deleteSync();
    } catch (_) {
      /* ignore */
    }
  }

  // ----------------------------------------------------------- list games

  /// Return metadata for all saved games, newest first.
  Future<List<SavedGameMeta>> listSavedGames() async {
    final dir = await _saveDir;
    final files =
        dir
            .listSync()
            .whereType<File>()
            .where((f) => f.path.endsWith('.json'))
            .where((f) => f.uri.pathSegments.last != _pausedFilename)
            .where((f) => !f.path.endsWith('.tmp'))
            .toList()
          ..sort(
            (a, b) => b.path.compareTo(a.path),
          ); // reverse alphabetical ≈ newest first

    final result = <SavedGameMeta>[];
    for (final file in files) {
      try {
        final content = await file.readAsString(encoding: utf8);
        final payload = jsonDecode(content) as Map<String, dynamic>;
        final meta = (payload['meta'] as Map?) ?? {};
        final game = (payload['game'] as Map?) ?? {};
        final players =
            (game['players'] as List?)
                ?.map((p) => (p as Map)['name'] as String)
                .toList() ??
            [];
        result.add(
          SavedGameMeta(
            name: (meta['name'] as String?) ?? file.uri.pathSegments.last,
            savedAt: (meta['saved_at'] as String?) ?? '',
            players: players,
            rounds: (game['round_number'] as int?) ?? 0,
            filePath: file.path,
            pendingSync: (meta['pending_sync'] as bool?) ?? false,
            groupCode: meta['group_code'] as String?,
          ),
        );
      } catch (_) {
        // skip corrupt files
      }
    }
    return result;
  }

  // -------------------------------------------------------- pending sync

  /// Return every saved game that is still flagged as needing sync.
  Future<List<PendingSyncGame>> listPendingSyncGames() async {
    final dir = await _saveDir;
    final files = dir
        .listSync()
        .whereType<File>()
        .where((f) => f.path.endsWith('.json'))
        .where((f) => f.uri.pathSegments.last != _pausedFilename)
        .where((f) => !f.path.endsWith('.tmp'))
        .toList();

    final result = <PendingSyncGame>[];
    for (final file in files) {
      try {
        final content = await file.readAsString(encoding: utf8);
        final payload = jsonDecode(content) as Map<String, dynamic>;
        final meta = (payload['meta'] as Map?) ?? {};
        if ((meta['pending_sync'] as bool?) != true) continue;
        result.add(
          PendingSyncGame(
            filePath: file.path,
            name: (meta['name'] as String?) ?? file.uri.pathSegments.last,
            savedAt: (meta['saved_at'] as String?) ?? '',
            groupCode: meta['group_code'] as String?,
            game: Map<String, dynamic>.from(payload['game'] as Map? ?? {}),
          ),
        );
      } catch (_) {
        // skip corrupt files
      }
    }
    return result;
  }

  /// Clear the pending_sync flag on [filePath] after a successful upload.
  Future<void> markSynced(String filePath) async {
    final file = File(filePath);
    if (!await file.exists()) return;
    try {
      final payload =
          jsonDecode(await file.readAsString(encoding: utf8))
              as Map<String, dynamic>;
      final meta = Map<String, dynamic>.from(payload['meta'] as Map? ?? {});
      meta['pending_sync'] = false;
      payload['meta'] = meta;
      await file.writeAsString(
        const JsonEncoder.withIndent('  ').convert(payload),
        encoding: utf8,
      );
    } catch (_) {
      /* ignore */
    }
  }

  /// Attach / update the group code on a pending-sync game.
  Future<void> updatePendingGroupCode(
    String filePath,
    String? groupCode,
  ) async {
    final file = File(filePath);
    if (!await file.exists()) return;
    try {
      final payload =
          jsonDecode(await file.readAsString(encoding: utf8))
              as Map<String, dynamic>;
      final meta = Map<String, dynamic>.from(payload['meta'] as Map? ?? {});
      meta['group_code'] = groupCode;
      payload['meta'] = meta;
      await file.writeAsString(
        const JsonEncoder.withIndent('  ').convert(payload),
        encoding: utf8,
      );
    } catch (_) {
      /* ignore */
    }
  }

  // ---------------------------------------------------------------- delete

  Future<void> deleteGame(String filePath) async {
    final file = File(filePath);
    if (await file.exists()) {
      await file.delete();
    }
  }
}

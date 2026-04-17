import 'dart:convert';
import 'dart:io';
import 'package:path_provider/path_provider.dart';
import 'package:intl/intl.dart';

/// Mirrors Python SaveManager.
/// Save dir: <appDocumentsDir>/wizard_gui/games/
/// Schema version matches desktop: "1.1"
const _schemaVersion = '1.1';

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
  Future<Directory> get _saveDir async {
    final docs = await getApplicationDocumentsDirectory();
    final dir = Directory('${docs.path}/wizard_gui/games');
    if (!await dir.exists()) {
      await dir.create(recursive: true);
    }
    return dir;
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

    await File(filepath).writeAsString(
      const JsonEncoder.withIndent('  ').convert(payload),
      encoding: utf8,
    );
    return filepath;
  }

  String _defaultName(DateTime now, Map<String, dynamic> gameData) {
    final ts = DateFormat('yyyyMMdd_HHmmss').format(now);
    final players = (gameData['players'] as List?)
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

  // ----------------------------------------------------------- list games

  /// Return metadata for all saved games, newest first.
  Future<List<SavedGameMeta>> listSavedGames() async {
    final dir = await _saveDir;
    final files = dir
        .listSync()
        .whereType<File>()
        .where((f) => f.path.endsWith('.json'))
        .toList()
      ..sort((a, b) => b.path.compareTo(a.path)); // reverse alphabetical ≈ newest first

    final result = <SavedGameMeta>[];
    for (final file in files) {
      try {
        final content = await file.readAsString(encoding: utf8);
        final payload = jsonDecode(content) as Map<String, dynamic>;
        final meta = (payload['meta'] as Map?) ?? {};
        final game = (payload['game'] as Map?) ?? {};
        final players = (game['players'] as List?)
                ?.map((p) => (p as Map)['name'] as String)
                .toList() ??
            [];
        result.add(SavedGameMeta(
          name: (meta['name'] as String?) ?? file.uri.pathSegments.last,
          savedAt: (meta['saved_at'] as String?) ?? '',
          players: players,
          rounds: (game['round_number'] as int?) ?? 0,
          filePath: file.path,
        ));
      } catch (_) {
        // skip corrupt files
      }
    }
    return result;
  }

  // ---------------------------------------------------------------- delete

  Future<void> deleteGame(String filePath) async {
    final file = File(filePath);
    if (await file.exists()) {
      await file.delete();
    }
  }
}

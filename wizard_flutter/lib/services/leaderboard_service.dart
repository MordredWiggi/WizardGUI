import 'dart:convert';
import 'dart:io';
import 'package:crypto/crypto.dart';

/// HTTP client for the Wizard Leaderboard API.
/// Mirrors leaderboard_client.py from the desktop app.
class LeaderboardService {
  final String baseUrl;
  final Duration timeout;

  LeaderboardService(String url, {this.timeout = const Duration(seconds: 8)})
      : baseUrl = url.endsWith('/') ? url.substring(0, url.length - 1) : url;

  // ── Groups ──────────────────────────────────────────────────────────────

  Future<Map<String, dynamic>?> getGroupByCode(String code) async {
    try {
      final resp = await _get('/api/groups/$code');
      if (resp.statusCode == 200) return jsonDecode(resp.body) as Map<String, dynamic>;
      return null;
    } catch (_) {
      return null;
    }
  }

  Future<List<Map<String, dynamic>>?> listGroups({String search = ''}) async {
    try {
      final q = search.isNotEmpty ? '?search=${Uri.encodeComponent(search)}' : '';
      final resp = await _get('/api/groups$q');
      if (resp.statusCode == 200) {
        final decoded = jsonDecode(resp.body);
        if (decoded is List) {
          return decoded.cast<Map<String, dynamic>>();
        }
        return <Map<String, dynamic>>[];
      }
      return null;
    } catch (e) {
      // ignore: avoid_print
      print('listGroups failed: $e');
      return null;
    }
  }

  /// Create a group.  Returns:
  ///   • the new group on 201,
  ///   • CreateGroupResult.codeTaken on 409,
  ///   • CreateGroupResult.networkError for any connection/parse failure.
  Future<CreateGroupResult> createGroup({
    required String name,
    required String code,
    String visibility = 'public',
  }) async {
    try {
      final resp = await _post('/api/groups', {
        'name': name,
        'code': code,
        'visibility': visibility,
      });
      if (resp.statusCode == 201) {
        return CreateGroupResult.ok(
            jsonDecode(resp.body) as Map<String, dynamic>);
      }
      if (resp.statusCode == 409) {
        return CreateGroupResult.codeTaken();
      }
      return CreateGroupResult.networkError(
          'HTTP ${resp.statusCode}: ${resp.body}');
    } catch (e) {
      return CreateGroupResult.networkError(e.toString());
    }
  }

  // ── Leaderboards ────────────────────────────────────────────────────────

  Future<List<Map<String, dynamic>>?> getGlobalGroupsLeaderboard() async {
    try {
      final resp = await _get('/api/leaderboard/groups');
      if (resp.statusCode == 200) {
        return (jsonDecode(resp.body) as List).cast<Map<String, dynamic>>();
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  Future<List<Map<String, dynamic>>?> getGroupPlayerLeaderboard(
      String code, String mode) async {
    try {
      final resp = await _get(
          '/api/leaderboard/group/$code?mode=${Uri.encodeComponent(mode)}');
      if (resp.statusCode == 200) {
        return (jsonDecode(resp.body) as List).cast<Map<String, dynamic>>();
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  Future<List<Map<String, dynamic>>?> getPlayerLeaderboard(String mode) async {
    try {
      final resp =
          await _get('/api/leaderboard?mode=${Uri.encodeComponent(mode)}');
      if (resp.statusCode == 200) {
        return (jsonDecode(resp.body) as List).cast<Map<String, dynamic>>();
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  // ── Game submission ─────────────────────────────────────────────────────

  Future<bool> submitGame(Map<String, dynamic> payload) async {
    try {
      final resp = await _post('/api/games', payload);
      return resp.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // ── HTTP helpers ────────────────────────────────────────────────────────

  Future<_Response> _get(String path) async {
    final client = HttpClient();
    client.connectionTimeout = timeout;
    try {
      final req = await client.getUrl(Uri.parse('$baseUrl$path'));
      final resp = await req.close().timeout(timeout);
      final body = await resp.transform(utf8.decoder).join();
      return _Response(resp.statusCode, body);
    } finally {
      client.close();
    }
  }

  Future<_Response> _post(String path, Map<String, dynamic> data) async {
    final client = HttpClient();
    client.connectionTimeout = timeout;
    try {
      final req = await client.postUrl(Uri.parse('$baseUrl$path'));
      req.headers.contentType = ContentType.json;
      req.write(jsonEncode(data));
      final resp = await req.close().timeout(timeout);
      final body = await resp.transform(utf8.decoder).join();
      return _Response(resp.statusCode, body);
    } finally {
      client.close();
    }
  }
}

class _Response {
  final int statusCode;
  final String body;
  _Response(this.statusCode, this.body);
}

/// Result of a createGroup call — distinguishes a real 409 (code taken) from
/// a network/server failure so the UI can show an accurate message.
class CreateGroupResult {
  final Map<String, dynamic>? group;
  final bool taken;
  final String? errorMessage;

  const CreateGroupResult._({this.group, this.taken = false, this.errorMessage});

  factory CreateGroupResult.ok(Map<String, dynamic> group) =>
      CreateGroupResult._(group: group);
  factory CreateGroupResult.codeTaken() =>
      const CreateGroupResult._(taken: true);
  factory CreateGroupResult.networkError(String msg) =>
      CreateGroupResult._(errorMessage: msg);

  bool get isOk => group != null;
  bool get isNetworkError => errorMessage != null;
}

// ── Game submission builder ─────────────────────────────────────────────────

/// Compute SHA-256 hash (first 16 hex chars) of a canonical game representation.
String computeGameHash(Map<String, dynamic> gameData) {
  final canonical = {
    'mode': gameData['game_mode'] ?? 'standard',
    'players': (gameData['players'] as List? ?? [])
        .map((p) => {
              'n': p['name'],
              'r': (p['rounds'] as List? ?? [])
                  .map((r) => {'s': r['said'], 'a': r['achieved']})
                  .toList(),
            })
        .toList()
      ..sort((a, b) => (a['n'] as String).compareTo(b['n'] as String)),
  };
  final raw = jsonEncode(canonical);
  final digest = sha256.convert(utf8.encode(raw));
  return digest.toString().substring(0, 16);
}

/// Build the POST /api/games payload from local game data.
Map<String, dynamic> buildGameSubmission(
  Map<String, dynamic> gameData, {
  String? playedAt,
  String? groupCode,
}) {
  final players = (gameData['players'] as List? ?? []);
  final numPlayers = players.length;
  final gameMode = gameData['game_mode'] ?? 'standard';

  final playerResults = players.map<Map<String, dynamic>>((p) {
    final rounds = (p['rounds'] as List? ?? []);
    int score;
    if (gameMode == 'multiplicative') {
      double s = 100;
      for (final r in rounds) {
        if (r['said'] == r['achieved']) {
          s = s * (2 + (r['achieved'] as int));
        } else {
          s = s / (1 + ((r['achieved'] as int) - (r['said'] as int)).abs());
        }
      }
      score = s.round();
    } else {
      score = 0;
      for (final r in rounds) {
        if (r['said'] == r['achieved']) {
          score += 20 + (r['said'] as int) * 10;
        } else {
          score += -10 * ((r['said'] as int) - (r['achieved'] as int)).abs();
        }
      }
    }
    final correctBids =
        rounds.where((r) => r['said'] == r['achieved']).length;
    return {
      'name': p['name'],
      'final_score': score,
      'correct_bids': correctBids,
      'total_rounds': rounds.length,
    };
  }).toList();

  // Assign ranks (descending score). Players with the same score share the
  // same rank — competition (or "1224") ranking — so a tied first place
  // counts as a win for every tied player on the server's leaderboards
  // (which credit a win whenever rank == 1).
  playerResults
      .sort((a, b) => (b['final_score'] as int) - (a['final_score'] as int));
  int currentRank = 1;
  int? lastScore;
  for (int i = 0; i < playerResults.length; i++) {
    final score = playerResults[i]['final_score'] as int;
    if (lastScore == null || score != lastScore) {
      currentRank = i + 1;
      lastScore = score;
    }
    playerResults[i]['rank'] = currentRank;
  }

  final payload = <String, dynamic>{
    'game_hash': computeGameHash(gameData),
    'game_mode': gameMode,
    'num_players': numPlayers,
    'played_at': playedAt ?? DateTime.now().toIso8601String(),
    'players': playerResults,
  };
  if (groupCode != null) payload['group_code'] = groupCode;
  return payload;
}

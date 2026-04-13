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
        return (jsonDecode(resp.body) as List).cast<Map<String, dynamic>>();
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  Future<Map<String, dynamic>?> createGroup({
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
      if (resp.statusCode == 201) return jsonDecode(resp.body) as Map<String, dynamic>;
      return null; // 409 = code taken
    } catch (_) {
      return null;
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

  // Assign ranks (descending score)
  playerResults
      .sort((a, b) => (b['final_score'] as int) - (a['final_score'] as int));
  for (int i = 0; i < playerResults.length; i++) {
    playerResults[i]['rank'] = i + 1;
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

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:wizard_flutter/services/leaderboard_service.dart';

/// The setup screen colours a typed player name green when that player has
/// already played in the selected group. That question must be asked with
/// `/api/groups/{code}/players/check`, which is scoped to the group only.
///
/// It must NOT be answered from `/api/leaderboard/group/{code}?mode=…`, which
/// is scoped to one game mode: doing so hid every player whose games in the
/// group were multiplicative or Jubiläumsedition, and left groups that only
/// ever played those modes with no green names at all.
void main() {
  late HttpServer server;
  late String base;
  late List<Uri> requests;

  /// Stands in for the backend: mirrors the real endpoint's contract, and
  /// serves the group's roster regardless of game mode.
  const roster = {
    '5001': ['Anna', 'Clara', 'Emil'],
    '5002': ['Gustav'],
  };

  setUp(() async {
    requests = [];
    server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    base = 'http://127.0.0.1:${server.port}';
    server.listen((req) async {
      requests.add(req.uri);
      final code = req.uri.pathSegments.length >= 3
          ? req.uri.pathSegments[2]
          : '';
      final name = req.uri.queryParameters['name'] ?? '';
      final names = roster[code];
      if (names == null) {
        req.response.statusCode = 404;
      } else {
        final exists = names.any((n) => n.toLowerCase() == name.toLowerCase());
        req.response
          ..headers.contentType = ContentType.json
          ..write(jsonEncode({'name': name, 'code': code, 'exists': exists}));
      }
      await req.response.close();
    });
  });

  tearDown(() async => server.close(force: true));

  test('asks the group-scoped endpoint, with no game mode attached', () async {
    await LeaderboardService(base).checkGroupPlayer('5001', 'Anna');

    expect(requests, hasLength(1));
    expect(requests.single.path, '/api/groups/5001/players/check');
    expect(requests.single.queryParameters['name'], 'Anna');
    // A mode filter here is exactly what caused the bug.
    expect(requests.single.queryParameters.containsKey('mode'), isFalse);
  });

  test('reports membership regardless of which mode was played', () async {
    final svc = LeaderboardService(base);
    // Anna, Clara and Emil are in group 5001 through games in three different
    // modes; all three must come back as known players.
    expect(await svc.checkGroupPlayer('5001', 'Anna'), isTrue);
    expect(await svc.checkGroupPlayer('5001', 'Clara'), isTrue);
    expect(await svc.checkGroupPlayer('5001', 'Emil'), isTrue);
    // A group whose only games are Jubiläumsedition still has a roster.
    expect(await svc.checkGroupPlayer('5002', 'Gustav'), isTrue);
  });

  test('membership is per group and case-insensitive', () async {
    final svc = LeaderboardService(base);
    expect(await svc.checkGroupPlayer('5001', 'aNNa'), isTrue);
    expect(await svc.checkGroupPlayer('5001', 'Gustav'), isFalse);
    expect(await svc.checkGroupPlayer('5002', 'Anna'), isFalse);
    expect(await svc.checkGroupPlayer('5001', 'Zacharias'), isFalse);
  });

  test('surrounding whitespace does not hide a known player', () async {
    // The name field is trimmed before it is compared, so the request must be
    // trimmed too — the server matches the stored name exactly.
    await LeaderboardService(base).checkGroupPlayer('5001', '  Anna  ');
    expect(requests.single.queryParameters['name'], 'Anna');
  });

  test('an empty name is never looked up', () async {
    expect(
      await LeaderboardService(base).checkGroupPlayer('5001', '   '),
      isNull,
    );
    expect(requests, isEmpty);
  });

  test('unreachable server and unknown group answer null, not false', () async {
    // null keeps the field neutral; false would claim the name is new.
    final unreachable = LeaderboardService(
      'http://127.0.0.1:1',
      timeout: const Duration(milliseconds: 300),
    );
    expect(await unreachable.checkGroupPlayer('5001', 'Anna'), isNull);
    expect(
      await LeaderboardService(base).checkGroupPlayer('9999', 'Anna'),
      isNull,
    );
  });
}

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:wizard_flutter/domain/player.dart';
import 'package:wizard_flutter/persistence/app_settings.dart';
import 'package:wizard_flutter/widgets/player_entry_card.dart';

/// Logical widths of common Android phones (physical px ÷ device pixel ratio),
/// plus a deliberately cramped one. The Jubiläumsedition cloud control used to
/// share a row with the bid/made spinners, which squeezed their +/− buttons
/// into each other on the narrower of these — reported on a Galaxy S24 (360).
const _widths = <String, double>{
  'small phone': 320,
  'Galaxy S24': 360,
  'Pixel 7': 412,
  'Galaxy S24 Ultra': 384,
  'iPhone-class wide': 430,
  'cramped / split screen': 280,
};

Widget _harness(double width, {required bool showCloud, double textScale = 1}) {
  return MediaQuery(
    data: MediaQueryData(
      size: Size(width, 800),
      textScaler: TextScaler.linear(textScale),
    ),
    child: ChangeNotifierProvider<AppSettings>.value(
      value: AppSettings(),
      child: MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: width,
            child: PlayerEntryCard(
              player: Player(name: 'Spielerin', avatar: '🧙‍♀️'),
              color: Colors.teal,
              playerIndex: 0,
              maxBid: 13,
              isDealer: true,
              isLeader: true,
              scoreDelta: -30,
              bid: 10,
              made: 12,
              showCloud: showCloud,
              cloud: -1,
              onCloudChanged: (_) {},
              onChanged: (_, __) {},
            ),
          ),
        ),
      ),
    ),
  );
}

/// Left-to-right order the six spinner controls must always paint in, with no
/// two of them sharing horizontal space.
void _expectSpinnersDisjoint(WidgetTester tester, String label) {
  final minus = find.byIcon(Icons.remove);
  final plus = find.byIcon(Icons.add);
  expect(minus, findsNWidgets(2), reason: label);
  expect(plus, findsNWidgets(2), reason: label);

  final rects = <Rect>[
    tester.getRect(minus.at(0)),
    tester.getRect(find.text('10')),
    tester.getRect(plus.at(0)),
    tester.getRect(minus.at(1)),
    tester.getRect(find.text('12')),
    tester.getRect(plus.at(1)),
  ];

  for (var i = 1; i < rects.length; i++) {
    expect(
      rects[i].left,
      greaterThanOrEqualTo(rects[i - 1].right),
      reason: '$label: control $i overlaps control ${i - 1} '
          '(${rects[i - 1]} vs ${rects[i]})',
    );
  }
}

void main() {
  // A RenderFlex overflow logs a FlutterError, which fails the test on its own,
  // so pumping each width is already the no-overflow assertion; the rect checks
  // catch the subtler case of controls sliding on top of each other.
  for (final entry in _widths.entries) {
    testWidgets('bid/made controls stay apart with the cloud — ${entry.key}', (
      tester,
    ) async {
      await tester.pumpWidget(
        _harness(entry.value, showCloud: true),
      );
      _expectSpinnersDisjoint(tester, entry.key);
    });
  }

  testWidgets('bid/made controls stay apart without the cloud', (tester) async {
    await tester.pumpWidget(_harness(320, showCloud: false));
    _expectSpinnersDisjoint(tester, 'no cloud @320');
  });

  testWidgets('bid/made controls survive a large system font scale', (
    tester,
  ) async {
    await tester.pumpWidget(
      _harness(360, showCloud: true, textScale: 1.5),
    );
    _expectSpinnersDisjoint(tester, 'Galaxy S24 @1.5x text');
  });

  testWidgets('cloud control sits below the spinners, not beside them', (
    tester,
  ) async {
    await tester.pumpWidget(_harness(360, showCloud: true));
    final cloud = tester.getRect(find.text('−1'));
    final made = tester.getRect(find.text('12'));
    expect(cloud.top, greaterThanOrEqualTo(made.bottom));
  });
}

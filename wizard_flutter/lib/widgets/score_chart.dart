import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../domain/game_control.dart';
import '../persistence/app_settings.dart';
import '../theme/app_theme.dart';
import 'package:provider/provider.dart';

/// Layer 2 – score progression line chart.
/// Mirrors the Matplotlib chart from the Python desktop app.
class ScoreChart extends StatefulWidget {
  final GameControl game;
  const ScoreChart({super.key, required this.game});

  @override
  State<ScoreChart> createState() => _ScoreChartState();
}

class _ScoreChartState extends State<ScoreChart> {
  int? _touchedLineIndex;

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<AppSettings>();
    final t = settings.t;
    final game = widget.game;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    if (game.roundNumber == 0) {
      return Center(
        child: Text(t('round_header', {'n': '0', 'total': game.totalRounds.toString()}),
            style: Theme.of(context).textTheme.bodyMedium),
      );
    }

    // Build line chart data
    final lines = <LineChartBarData>[];

    // Player lines
    for (var i = 0; i < game.players.length; i++) {
      final p = game.players[i];
      final color = kPlayerColors[i % kPlayerColors.length];
      final isTouched = _touchedLineIndex == i;

      lines.add(LineChartBarData(
        spots: p.scores
            .asMap()
            .entries
            .map((e) => FlSpot(e.key.toDouble(), e.value.toDouble()))
            .toList(),
        isCurved: false,
        color: color,
        barWidth: isTouched ? 3.5 : 2,
        dotData: FlDotData(
          show: true,
          getDotPainter: (spot, pct, bar, idx) => FlDotCirclePainter(
            radius: idx == game.roundNumber
                ? 5
                : (isTouched ? 4 : 3),
            color: color,
            strokeWidth: isTouched ? 1.5 : 0,
            strokeColor: isDark ? Colors.white : Colors.black,
          ),
        ),
        belowBarData: BarAreaData(show: false),
      ));
    }

    // Average line (dashed)
    final avgs = game.averages;
    final avgLine = LineChartBarData(
      spots: avgs
          .asMap()
          .entries
          .map((e) => FlSpot(e.key.toDouble(), e.value))
          .toList(),
      isCurved: false,
      color: (isDark ? Colors.white : Colors.black).withOpacity(0.35),
      barWidth: 1.5,
      dashArray: [6, 4],
      dotData: const FlDotData(show: false),
      belowBarData: BarAreaData(show: false),
    );
    lines.add(avgLine);

    // Score-sorted legend (top of chart), separate from chart widget
    final sorted = game.players.toList()
      ..sort((a, b) => b.currentScore.compareTo(a.currentScore));

    final gridColor = isDark
        ? const Color(0xFF3a3a6a)
        : const Color(0xFFCCCCDD);
    final axisColor = isDark ? kTextDim : const Color(0xFF888899);

    return Column(
      children: [
        // ── Legend (score-sorted) ──────────────────────────────────────
        Padding(
          padding: const EdgeInsets.fromLTRB(8, 8, 8, 4),
          child: Wrap(
            spacing: 12,
            runSpacing: 4,
            children: sorted.asMap().entries.map((e) {
              final originalIndex =
                  game.players.indexWhere((p) => p.name == e.value.name);
              final color =
                  kPlayerColors[originalIndex % kPlayerColors.length];
              final isFirst = e.key == 0;
              return Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 16,
                    height: 3,
                    color: color,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    '${e.value.avatar} ${e.value.name} (${e.value.currentScore})',
                    style: TextStyle(
                      fontSize: 12,
                      color: isFirst ? kLeader : color,
                      fontWeight: isFirst
                          ? FontWeight.bold
                          : FontWeight.normal,
                    ),
                  ),
                ],
              );
            }).toList(),
          ),
        ),
        // Average legend entry
        Padding(
          padding: const EdgeInsets.fromLTRB(8, 0, 8, 8),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              SizedBox(
                width: 16,
                child: CustomPaint(
                  size: const Size(16, 3),
                  painter: _DashedLinePainter(
                    color: (isDark ? Colors.white : Colors.black)
                        .withOpacity(0.35),
                  ),
                ),
              ),
              const SizedBox(width: 4),
              Text(
                t('average'),
                style: TextStyle(
                  fontSize: 12,
                  color: axisColor,
                ),
              ),
            ],
          ),
        ),

        // ── Chart ───────────────────────────────────────────────────────
        Expanded(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(0, 0, 20, 12),
            child: LineChart(
              LineChartData(
                // Add a tiny bit of horizontal padding so the dots at round 0
                // and at the latest round aren't clipped by the chart border.
                minX: -0.25,
                maxX: game.roundNumber.toDouble() + 0.25,
                lineBarsData: lines,
                gridData: FlGridData(
                  show: true,
                  horizontalInterval: 100,
                  getDrawingHorizontalLine: (_) => FlLine(
                    color: gridColor,
                    strokeWidth: 0.8,
                    dashArray: [4, 4],
                  ),
                  getDrawingVerticalLine: (_) => FlLine(
                    color: gridColor,
                    strokeWidth: 0.8,
                    dashArray: [4, 4],
                  ),
                ),
                titlesData: FlTitlesData(
                  bottomTitles: AxisTitles(
                    axisNameWidget: Padding(
                      padding: const EdgeInsets.only(top: 4),
                      child: Text(t('round'),
                          style: TextStyle(
                              color: axisColor, fontSize: 12)),
                    ),
                    sideTitles: SideTitles(
                      showTitles: true,
                      interval: 1,
                      getTitlesWidget: (v, _) {
                        final n = v.toInt();
                        if (n == 0 ||
                            n > game.roundNumber ||
                            n % _labelStep(game.roundNumber) != 0) {
                          return const SizedBox.shrink();
                        }
                        return Text('$n',
                            style: TextStyle(
                                color: axisColor, fontSize: 11));
                      },
                    ),
                  ),
                  rightTitles: AxisTitles(
                    axisNameWidget: Padding(
                      padding: const EdgeInsets.only(bottom: 4),
                      child: Text(t('points'),
                          style: TextStyle(
                              color: axisColor, fontSize: 12)),
                    ),
                    sideTitles: SideTitles(
                      showTitles: true,
                      interval: 100,
                      reservedSize: 44,
                      getTitlesWidget: (v, _) => Text('${v.toInt()}',
                          style: TextStyle(
                              color: axisColor, fontSize: 11)),
                    ),
                  ),
                  leftTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false)),
                  topTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false)),
                ),
                borderData: FlBorderData(
                  show: true,
                  border: Border.all(color: gridColor, width: 0.8),
                ),
                lineTouchData: LineTouchData(
                  handleBuiltInTouches: true,
                  touchCallback: (event, response) {
                    // Clear the highlight whenever touch/pointer leaves the
                    // chart area, the gesture is released, or the response
                    // contains no spots. Picking only explicit "exit" events
                    // left the highlight stuck when the cursor slid off the
                    // side of the plot during a hover session.
                    final isEndEvent = event is FlTapUpEvent ||
                        event is FlTapCancelEvent ||
                        event is FlLongPressEnd ||
                        event is FlPanEndEvent ||
                        event is FlPanCancelEvent ||
                        event is FlPointerExitEvent;

                    final spots = response?.lineBarSpots;
                    final hasSpot = spots != null && spots.isNotEmpty;

                    if (isEndEvent || !hasSpot) {
                      if (_touchedLineIndex != null) {
                        setState(() => _touchedLineIndex = null);
                      }
                      return;
                    }

                    // Prefer the closest non-average line the user touched.
                    final touched = spots!.firstWhere(
                      (s) => s.barIndex < game.players.length,
                      orElse: () => spots.first,
                    );
                    if (touched.barIndex >= game.players.length) {
                      if (_touchedLineIndex != null) {
                        setState(() => _touchedLineIndex = null);
                      }
                      return;
                    }
                    if (_touchedLineIndex != touched.barIndex) {
                      setState(() => _touchedLineIndex = touched.barIndex);
                    }
                  },
                  touchTooltipData: LineTouchTooltipData(
                    // Auto-flip the tooltip below the marker when it would
                    // otherwise be clipped against the top edge of the chart
                    // (e.g. for the highest line in late rounds).
                    fitInsideVertically: true,
                    fitInsideHorizontally: true,
                    getTooltipItems: (spots) => spots.map((s) {
                      // Skip average line tooltip
                      if (s.barIndex >= game.players.length) {
                        return null;
                      }
                      final p = game.players[s.barIndex];
                      final color =
                          kPlayerColors[s.barIndex % kPlayerColors.length];
                      return LineTooltipItem(
                        '${p.avatar} ${p.name}\n${s.y.toInt()}',
                        TextStyle(color: color, fontSize: 12),
                      );
                    }).toList(),
                  ),
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  /// Reduce label density for long games.
  int _labelStep(int rounds) {
    if (rounds <= 10) return 1;
    if (rounds <= 20) return 2;
    return 5;
  }
}

class _DashedLinePainter extends CustomPainter {
  final Color color;
  const _DashedLinePainter({required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..strokeWidth = 1.5;
    const dashW = 4.0;
    const gapW = 3.0;
    double x = 0;
    while (x < size.width) {
      canvas.drawLine(
          Offset(x, size.height / 2), Offset(x + dashW, size.height / 2), paint);
      x += dashW + gapW;
    }
  }

  @override
  bool shouldRepaint(_DashedLinePainter old) => old.color != color;
}

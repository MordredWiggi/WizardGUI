import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../domain/player.dart';
import '../persistence/app_settings.dart';
import '../theme/app_theme.dart';

/// Layer 1 – input card for one player per round.
/// Controlled widget: bid/made values are owned by the parent so they survive
/// ListView recycling as players scroll off-screen.
class PlayerEntryCard extends StatelessWidget {
  final Player player;
  final Color color;
  final int playerIndex;
  final int maxBid;           // cards this round — upper bound on bid
  final bool isDealer;
  final bool isLeader;
  final int scoreDelta;       // delta from last round (0 before any round)
  final int bid;
  final int made;
  final void Function(int bid, int made) onChanged;

  const PlayerEntryCard({
    super.key,
    required this.player,
    required this.color,
    required this.playerIndex,
    required this.maxBid,
    required this.isDealer,
    required this.isLeader,
    required this.scoreDelta,
    required this.bid,
    required this.made,
    required this.onChanged,
  });

  void _setBid(int v) {
    if (v < 0 || v > maxBid) return;
    onChanged(v, made);
  }

  void _setMade(int v) {
    if (v < 0 || v > maxBid) return;
    onChanged(bid, v);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isLight = theme.brightness == Brightness.light;
    final cardBg = isLight ? Colors.white : kBgCard;
    final t = context.watch<AppSettings>().t;

    return Card(
      color: cardBg,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(
          color: isLeader ? kLeader : color.withOpacity(0.5),
          width: isLeader ? 2 : 1,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Header row ─────────────────────────────────────────────
            Row(children: [
              Text(player.avatar,
                  style: const TextStyle(fontSize: 26)),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(children: [
                      Text(player.name,
                          style: TextStyle(
                              color: color,
                              fontWeight: FontWeight.bold,
                              fontSize: 15)),
                      if (isDealer) ...[
                        const SizedBox(width: 6),
                        _Badge('🃏', kAccentDim),
                      ],
                      if (isLeader) ...[
                        const SizedBox(width: 4),
                        _Badge('👑', kLeader),
                      ],
                    ]),
                    const SizedBox(height: 2),
                    Row(children: [
                      Text(
                        player.currentScore.toString(),
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: color,
                        ),
                      ),
                      if (scoreDelta != 0) ...[
                        const SizedBox(width: 8),
                        _DeltaBadge(scoreDelta),
                      ],
                    ]),
                  ],
                ),
              ),
            ]),

            const SizedBox(height: 12),
            const Divider(height: 1),
            const SizedBox(height: 12),

            // ── Bid / Made spinners ────────────────────────────────────
            Row(children: [
              Expanded(
                child: _SpinnerField(
                  label: t('announced'),
                  value: bid,
                  max: maxBid,
                  color: color,
                  onDecrement: () => _setBid(bid - 1),
                  onIncrement: () => _setBid(bid + 1),
                  onChanged: (v) => _setBid(v),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _SpinnerField(
                  label: t('achieved'),
                  value: made,
                  max: maxBid,
                  color: color,
                  onDecrement: () => _setMade(made - 1),
                  onIncrement: () => _setMade(made + 1),
                  onChanged: (v) => _setMade(v),
                ),
              ),
            ]),
          ],
        ),
      ),
    );
  }
}

// ── Helper sub-widgets ─────────────────────────────────────────────────────────

class _Badge extends StatelessWidget {
  final String text;
  final Color color;
  const _Badge(this.text, this.color);

  @override
  Widget build(BuildContext context) => Text(text,
      style: TextStyle(fontSize: 13, color: color));
}

class _DeltaBadge extends StatelessWidget {
  final int delta;
  const _DeltaBadge(this.delta);

  @override
  Widget build(BuildContext context) {
    final positive = delta > 0;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
      decoration: BoxDecoration(
        color: (positive ? kSuccess : kDanger).withOpacity(0.15),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        positive ? '+$delta' : '$delta',
        style: TextStyle(
          color: positive ? kSuccess : kDanger,
          fontWeight: FontWeight.bold,
          fontSize: 12,
        ),
      ),
    );
  }
}

class _SpinnerField extends StatelessWidget {
  final String label;
  final int value;
  final int max;
  final Color color;
  final VoidCallback onDecrement;
  final VoidCallback onIncrement;
  final void Function(int) onChanged;

  const _SpinnerField({
    required this.label,
    required this.value,
    required this.max,
    required this.color,
    required this.onDecrement,
    required this.onIncrement,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label,
            style: theme.textTheme.labelSmall
                ?.copyWith(color: color, letterSpacing: 1)),
        const SizedBox(height: 4),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            _CircleIconBtn(
              icon: Icons.remove,
              onTap: value > 0 ? onDecrement : null,
              color: color,
            ),
            const SizedBox(width: 8),
            GestureDetector(
              onTap: () => _showPicker(context),
              child: Container(
                width: 52,
                height: 40,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: color.withOpacity(0.4)),
                ),
                child: Text(
                  '$value',
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                    color: color,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 8),
            _CircleIconBtn(
              icon: Icons.add,
              onTap: value < max ? onIncrement : null,
              color: color,
            ),
          ],
        ),
      ],
    );
  }

  void _showPicker(BuildContext context) {
    final ctrl = TextEditingController(text: '$value');
    final t = context.read<AppSettings>().t;
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: Text(label),
        content: TextField(
          controller: ctrl,
          keyboardType: TextInputType.number,
          autofocus: true,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context),
              child: Text(t('cancel'))),
          TextButton(
              onPressed: () {
                final v = int.tryParse(ctrl.text) ?? value;
                onChanged(v.clamp(0, max));
                Navigator.pop(context);
              },
              child: Text(t('ok'))),
        ],
      ),
    );
  }
}

class _CircleIconBtn extends StatelessWidget {
  final IconData icon;
  final VoidCallback? onTap;
  final Color color;
  const _CircleIconBtn(
      {required this.icon, required this.onTap, required this.color});

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(20),
        child: Container(
          width: 32,
          height: 32,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(
                color: onTap != null ? color : color.withOpacity(0.2)),
          ),
          child: Icon(icon,
              size: 16,
              color: onTap != null ? color : color.withOpacity(0.3)),
        ),
      );
}

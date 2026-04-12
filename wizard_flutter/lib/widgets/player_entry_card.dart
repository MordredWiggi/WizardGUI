import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../domain/player.dart';
import '../domain/round_result.dart';
import '../theme/app_theme.dart';

/// Layer 1 – input card for one player per round.
/// Shows avatar, name, current score, delta, bid/made spinners.
class PlayerEntryCard extends StatefulWidget {
  final Player player;
  final Color color;
  final int playerIndex;
  final int maxBid;           // cards this round — upper bound on bid
  final bool isDealer;
  final bool isLeader;
  final int scoreDelta;       // delta from last round (0 before any round)
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
    required this.onChanged,
  });

  @override
  State<PlayerEntryCard> createState() => PlayerEntryCardState();
}

class PlayerEntryCardState extends State<PlayerEntryCard> {
  late int _bid;
  late int _made;

  int get bid => _bid;
  int get made => _made;

  @override
  void initState() {
    super.initState();
    _bid = 0;
    _made = 0;
  }

  void fillMadeFromBid() => setState(() => _made = _bid);

  RoundResult get result => RoundResult(said: _bid, achieved: _made);

  void _setBid(int v) {
    if (v < 0 || v > widget.maxBid) return;
    setState(() => _bid = v);
    widget.onChanged(_bid, _made);
  }

  void _setMade(int v) {
    if (v < 0 || v > widget.maxBid) return;
    setState(() => _made = v);
    widget.onChanged(_bid, _made);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isLight = theme.brightness == Brightness.light;
    final cardBg = isLight ? Colors.white : kBgCard;

    return Card(
      color: cardBg,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(
          color: widget.isLeader ? kLeader : widget.color.withOpacity(0.5),
          width: widget.isLeader ? 2 : 1,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Header row ─────────────────────────────────────────────
            Row(children: [
              Text(widget.player.avatar,
                  style: const TextStyle(fontSize: 26)),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(children: [
                      Text(widget.player.name,
                          style: TextStyle(
                              color: widget.color,
                              fontWeight: FontWeight.bold,
                              fontSize: 15)),
                      if (widget.isDealer) ...[
                        const SizedBox(width: 6),
                        _Badge('🃏', kAccentDim),
                      ],
                      if (widget.isLeader) ...[
                        const SizedBox(width: 4),
                        _Badge('👑', kLeader),
                      ],
                    ]),
                    const SizedBox(height: 2),
                    Row(children: [
                      Text(
                        widget.player.currentScore.toString(),
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: widget.color,
                        ),
                      ),
                      if (widget.scoreDelta != 0) ...[
                        const SizedBox(width: 8),
                        _DeltaBadge(widget.scoreDelta),
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
                  label: 'Bid',
                  value: _bid,
                  max: widget.maxBid,
                  color: widget.color,
                  onDecrement: () => _setBid(_bid - 1),
                  onIncrement: () => _setBid(_bid + 1),
                  onChanged: (v) => _setBid(v),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _SpinnerField(
                  label: 'Made',
                  value: _made,
                  max: widget.maxBid,
                  color: widget.color,
                  onDecrement: () => _setMade(_made - 1),
                  onIncrement: () => _setMade(_made + 1),
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
              child: const Text('Cancel')),
          TextButton(
              onPressed: () {
                final v = int.tryParse(ctrl.text) ?? value;
                onChanged(v.clamp(0, max));
                Navigator.pop(context);
              },
              child: const Text('OK')),
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

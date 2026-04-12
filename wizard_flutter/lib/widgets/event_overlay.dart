import 'package:flutter/material.dart';

/// Animated celebration overlay – mirrors Python CelebrationOverlay.
/// Show it via EventOverlay.show(context, ...).
class EventOverlay extends StatefulWidget {
  final String emoji;
  final String title;
  final String subtitle;
  final Color color;

  const EventOverlay({
    super.key,
    required this.emoji,
    required this.title,
    required this.subtitle,
    required this.color,
  });

  /// Show a timed overlay anchored to [context]'s Overlay.
  static void show(
    BuildContext context, {
    required String emoji,
    required String title,
    String subtitle = '',
    required Color color,
    Duration duration = const Duration(seconds: 3),
  }) {
    final overlay = Overlay.of(context);
    late OverlayEntry entry;
    entry = OverlayEntry(
      builder: (_) => EventOverlay(
        emoji: emoji,
        title: title,
        subtitle: subtitle,
        color: color,
      ),
    );
    overlay.insert(entry);
    Future.delayed(duration, entry.remove);
  }

  @override
  State<EventOverlay> createState() => _EventOverlayState();
}

class _EventOverlayState extends State<EventOverlay>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _opacity;
  late Animation<double> _slide;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 400));
    _opacity = CurvedAnimation(parent: _ctrl, curve: Curves.easeOut);
    _slide = Tween<double>(begin: 40, end: 0)
        .animate(CurvedAnimation(parent: _ctrl, curve: Curves.easeOut));
    _ctrl.forward();
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Positioned(
      top: MediaQuery.of(context).padding.top + 20,
      left: 24,
      right: 24,
      child: AnimatedBuilder(
        animation: _ctrl,
        builder: (_, child) => Transform.translate(
          offset: Offset(0, -_slide.value),
          child: Opacity(opacity: _opacity.value, child: child),
        ),
        child: Material(
          elevation: 8,
          borderRadius: BorderRadius.circular(16),
          color: Colors.transparent,
          child: Container(
            decoration: BoxDecoration(
              color: widget.color.withOpacity(0.92),
              borderRadius: BorderRadius.circular(16),
            ),
            padding:
                const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
            child: Row(
              children: [
                Text(widget.emoji,
                    style: const TextStyle(fontSize: 36)),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(widget.title,
                          style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.bold,
                              fontSize: 16)),
                      if (widget.subtitle.isNotEmpty)
                        Text(widget.subtitle,
                            style: const TextStyle(
                                color: Colors.white70, fontSize: 13)),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

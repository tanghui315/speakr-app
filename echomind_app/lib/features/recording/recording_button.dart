import 'package:flutter/material.dart';

import '../../app/theme/app_colors.dart';
import '../../app/l10n/l10n.dart';

class RecordingButton extends StatefulWidget {
  const RecordingButton({super.key, this.onStart});

  final Future<void> Function()? onStart;

  @override
  State<RecordingButton> createState() => _RecordingButtonState();
}

class _RecordingButtonState extends State<RecordingButton>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  bool _isRecording = false;
  bool _isLaunching = false;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
      lowerBound: 0.0,
      upperBound: 1.0,
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _handleTap() async {
    if (_isLaunching) return;

    setState(() {
      _isRecording = true;
      _isLaunching = true;
      _controller.repeat(reverse: true);
    });

    try {
      if (widget.onStart != null) {
        await widget.onStart!();
      }
    } finally {
      if (!mounted) return;
      setState(() {
        _isRecording = false;
        _isLaunching = false;
        _controller.stop();
        _controller.reset();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Center(
      child: Stack(
        alignment: Alignment.center,
        children: [
          AnimatedBuilder(
            animation: _controller,
            builder: (context, child) {
              final scale = 1 + (_controller.value * 0.15);
              if (!_isRecording) {
                return const SizedBox.shrink();
              }
              return Transform.scale(
                scale: scale,
                child: Container(
                  width: 210,
                  height: 210,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: LinearGradient(
                      colors: [
                        AppColors.primary.withOpacity(0.28),
                        AppColors.accent.withOpacity(0.22),
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
          GestureDetector(
            onTap: _handleTap,
            child: Container(
              width: 160,
              height: 160,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: AppColors.primaryGradient,
                boxShadow: const [
                  BoxShadow(
                    color: Color(0x405840FF),
                    blurRadius: 30,
                    offset: Offset(0, 20),
                  ),
                ],
              ),
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      _isRecording ? Icons.stop : Icons.mic,
                      size: 48,
                      color: Colors.white,
                    ),
                    const SizedBox(height: 12),
                    Text(
                      _isRecording
                          ? l10n.recordButtonStop
                          : l10n.recordButtonStart,
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      l10n.recordButtonTagline,
                      style: const TextStyle(
                        color: Colors.white70,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

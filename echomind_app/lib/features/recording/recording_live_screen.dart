import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../app/theme/app_colors.dart';
import '../../app/l10n/l10n.dart';

class RecordingLiveScreen extends StatefulWidget {
  const RecordingLiveScreen({super.key});

  @override
  State<RecordingLiveScreen> createState() => _RecordingLiveScreenState();
}

class _RecordingLiveScreenState extends State<RecordingLiveScreen>
    with TickerProviderStateMixin {
  final ScrollController _scrollController = ScrollController();
  final List<String> _finalSegments = [];
  late final AnimationController _waveController;
  Timer? _transcriptTimer;
  Timer? _elapsedTimer;
  Duration _elapsed = Duration.zero;
  String? _inProgressSegment;
  int _scriptIndex = 0;

  static const _script = <({String text, bool isFinal})>[
    (
      text: 'Good afternoon team, thanks for dialing in on time.',
      isFinal: true,
    ),
    (
      text: 'First, quick updates on the EchoMind beta rollout…',
      isFinal: false,
    ),
    (
      text:
          'First, quick updates on the EchoMind beta rollout. Sign-ups crossed 1.2k this week.',
      isFinal: true,
    ),
    (
      text:
          'We are tracking streaming latency at roughly one hundred milliseconds.',
      isFinal: true,
    ),
    (
      text:
          'Next, marketing is preparing launch assets for the App Store feature list.',
      isFinal: true,
    ),
    (
      text:
          'Engineering focus this sprint is stabilising the faster-whisper gateway.',
      isFinal: true,
    ),
    (
      text: 'Please flag blockers on the shared board before tomorrow evening.',
      isFinal: true,
    ),
  ];

  @override
  void initState() {
    super.initState();
    _waveController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    )..repeat();
    _startMockStreams();
  }

  void _startMockStreams() {
    _elapsedTimer = Timer.periodic(
      const Duration(seconds: 1),
      (_) => setState(() => _elapsed += const Duration(seconds: 1)),
    );

    _transcriptTimer = Timer.periodic(const Duration(milliseconds: 1600), (
      timer,
    ) {
      if (_scriptIndex >= _script.length) {
        timer.cancel();
        setState(() => _inProgressSegment = null);
        return;
      }

      final entry = _script[_scriptIndex++];

      setState(() {
        if (!entry.isFinal) {
          _inProgressSegment = entry.text;
        } else {
          _finalSegments.add(entry.text);
          _inProgressSegment = null;
        }
      });

      _scheduleAutoScroll();
    });
  }

  void _scheduleAutoScroll() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) return;
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent + 80,
        duration: const Duration(milliseconds: 400),
        curve: Curves.easeOut,
      );
    });
  }

  @override
  void dispose() {
    _transcriptTimer?.cancel();
    _elapsedTimer?.cancel();
    _waveController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  String _elapsedLabel(BuildContext context) {
    final hours = _elapsed.inHours.remainder(24).toString().padLeft(2, '0');
    final minutes = _elapsed.inMinutes.remainder(60).toString().padLeft(2, '0');
    final seconds = _elapsed.inSeconds.remainder(60).toString().padLeft(2, '0');
    return context.l10n.recordingTimerLabel(
      hours: hours,
      minutes: minutes,
      seconds: seconds,
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final surface = theme.colorScheme.surface;
    final l10n = context.l10n;

    return Scaffold(
      backgroundColor: AppColors.backgroundDark,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        foregroundColor: Colors.white,
        title: Text(l10n.recordLiveTitle),
        actions: [
          TextButton.icon(
            onPressed: () {},
            icon: const Icon(Icons.cloud_done_outlined, color: Colors.white70),
            label: Text(l10n.recordLiveStreaming),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  _StatusChip(
                    icon: Icons.timer_outlined,
                    label: _elapsedLabel(context),
                  ),
                  _StatusChip(
                    icon: Icons.wifi_tethering,
                    label: l10n.recordLiveLatency(latency: '120'),
                  ),
                  _StatusChip(
                    icon: Icons.battery_charging_full,
                    label: l10n.recordLiveFreeMinutes(minutes: '179'),
                  ),
                ],
              ),
            ),
            _WaveformPlaceholder(controller: _waveController),
            Expanded(
              child: Container(
                margin: const EdgeInsets.fromLTRB(24, 16, 24, 0),
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: surface.withOpacity(0.95),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: ListView(
                  controller: _scrollController,
                  physics: const BouncingScrollPhysics(),
                  children: [
                    for (final segment in _finalSegments)
                      _TranscriptBubble(text: segment, isFinal: true),
                    if (_inProgressSegment != null)
                      _TranscriptBubble(
                        text: _inProgressSegment!,
                        isFinal: false,
                      ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
            _ControlBar(onStop: () => Navigator.of(context).maybePop()),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }
}

class _WaveformPlaceholder extends StatelessWidget {
  const _WaveformPlaceholder({required this.controller});

  final AnimationController controller;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 160,
      child: AnimatedBuilder(
        animation: controller,
        builder: (context, child) {
          final t = controller.value;
          return CustomPaint(
            painter: _WavePainter(progress: t),
            child: Container(
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [Color(0x6621C5E5), Color(0x225840FF)],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

class _WavePainter extends CustomPainter {
  const _WavePainter({required this.progress});

  final double progress;

  @override
  void paint(Canvas canvas, Size size) {
    final paint =
        Paint()
          ..color = AppColors.accent.withOpacity(0.7)
          ..strokeWidth = 3
          ..style = PaintingStyle.stroke;

    final path = Path();
    final midY = size.height / 2;
    const waves = 18;
    final amplitude = size.height / 2.2;
    final speed = progress * 2 * math.pi;

    path.moveTo(0, midY);
    for (int i = 0; i <= size.width.toInt(); i++) {
      final normalized = i / size.width;
      final y =
          midY +
          math.sin((normalized * waves * math.pi) + speed) *
              amplitude *
              (0.7 + 0.3 * math.sin(progress * math.pi));
      path.lineTo(i.toDouble(), y);
    }

    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant _WavePainter oldDelegate) {
    return oldDelegate.progress != progress;
  }
}

class _TranscriptBubble extends StatelessWidget {
  const _TranscriptBubble({required this.text, required this.isFinal});

  final String text;
  final bool isFinal;

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 250),
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: isFinal ? Colors.white : Colors.white10,
        borderRadius: BorderRadius.circular(16),
        border:
            isFinal
                ? Border.all(color: AppColors.primary.withOpacity(0.18))
                : null,
      ),
      child: Text(
        text,
        style: TextStyle(
          color: isFinal ? AppColors.textPrimary : Colors.white70,
          fontStyle: isFinal ? FontStyle.normal : FontStyle.italic,
          fontWeight: isFinal ? FontWeight.w500 : FontWeight.w400,
        ),
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0x3321C5E5),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 18, color: Colors.white70),
          const SizedBox(width: 6),
          Text(label, style: const TextStyle(color: Colors.white)),
        ],
      ),
    );
  }
}

class _ControlBar extends StatelessWidget {
  const _ControlBar({required this.onStop});

  final VoidCallback onStop;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: const Color(0xFF161B2B),
          borderRadius: BorderRadius.circular(20),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            _ControlButton(
              icon: Icons.pause_rounded,
              label: context.l10n.recordLivePause,
              onTap: () {},
            ),
            _ControlButton(
              icon: Icons.flag_outlined,
              label: context.l10n.recordLiveMark,
              onTap: () {},
            ),
            _ControlButton(
              icon: Icons.bookmark_outline,
              label: context.l10n.recordLiveTag,
              onTap: () {},
            ),
            ElevatedButton.icon(
              onPressed: onStop,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.highlight,
                foregroundColor: AppColors.textPrimary,
                padding: const EdgeInsets.symmetric(
                  horizontal: 20,
                  vertical: 12,
                ),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
              ),
              icon: const Icon(Icons.stop_circle_outlined),
              label: Text(context.l10n.recordLiveFinish),
            ),
          ],
        ),
      ),
    );
  }
}

class _ControlButton extends StatelessWidget {
  const _ControlButton({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: const Color(0x3321C5E5),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Icon(icon, color: Colors.white),
          ),
          const SizedBox(height: 6),
          Text(label, style: const TextStyle(color: Colors.white70)),
        ],
      ),
    );
  }
}

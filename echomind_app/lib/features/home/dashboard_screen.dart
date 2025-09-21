import 'package:flutter/material.dart';

import '../../app/theme/app_colors.dart';
import '../../app/l10n/l10n.dart';
import '../recording/recording_button.dart';
import '../recording/recording_live_screen.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = context.l10n;

    return CustomScrollView(
      slivers: [
        SliverAppBar(
          floating: true,
          title: Text(
            l10n.appTitle,
            style: theme.textTheme.titleLarge?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
          actions: const [
            _QuotaChip(remainingMinutes: 180),
            SizedBox(width: 16),
          ],
        ),
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                RecordingButton(
                  onStart:
                      () => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => const RecordingLiveScreen(),
                          settings: const RouteSettings(name: 'recording'),
                        ),
                      ),
                ),
                const SizedBox(height: 24),
                Text(
                  l10n.homeStatusTitle,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 12),
                _StatusCard(
                  title: l10n.homeLiveCaptionGateway,
                  subtitle: l10n.homeLiveCaptionStatus(latency: '120'),
                  statusColor: AppColors.accent,
                ),
                const SizedBox(height: 12),
                _StatusCard(
                  title: l10n.homeUploadQueue,
                  subtitle: l10n.homeUploadStatus(count: '0'),
                  statusColor: Colors.greenAccent,
                ),
                const SizedBox(height: 24),
                Text(
                  l10n.homeQuickActionsTitle,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 16,
                  runSpacing: 16,
                  children: [
                    _QuickActionCard(
                      icon: Icons.library_music,
                      title: l10n.homeQuickActionLibrary,
                    ),
                    _QuickActionCard(
                      icon: Icons.chat,
                      title: l10n.homeQuickActionAI,
                    ),
                    _QuickActionCard(
                      icon: Icons.workspace_premium,
                      title: l10n.homeQuickActionUpgrade,
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _QuotaChip extends StatelessWidget {
  const _QuotaChip({required this.remainingMinutes});

  final int remainingMinutes;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Chip(
      avatar: const Icon(Icons.timer, size: 18, color: AppColors.primary),
      backgroundColor: Colors.white,
      label: Text(
        l10n.homeQuotaLabel(minutes: '$remainingMinutes'),
        style: const TextStyle(color: AppColors.textPrimary),
      ),
    );
  }
}

class _StatusCard extends StatelessWidget {
  const _StatusCard({
    required this.title,
    required this.subtitle,
    required this.statusColor,
  });

  final String title;
  final String subtitle;
  final Color statusColor;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            offset: const Offset(0, 6),
            blurRadius: 16,
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 10,
            height: 10,
            decoration: BoxDecoration(
              color: statusColor,
              borderRadius: BorderRadius.circular(12),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: theme.textTheme.bodyLarge?.copyWith(
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  subtitle,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _QuickActionCard extends StatelessWidget {
  const _QuickActionCard({required this.icon, required this.title});

  final IconData icon;
  final String title;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      width: 150,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            offset: const Offset(0, 8),
            blurRadius: 20,
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              gradient: AppColors.primaryGradient,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: Colors.white),
          ),
          const SizedBox(height: 12),
          Text(
            title,
            style: theme.textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.w600,
              color: AppColors.textPrimary,
            ),
          ),
        ],
      ),
    );
  }
}

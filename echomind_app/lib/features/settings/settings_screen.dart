import 'package:flutter/material.dart';

import '../../app/theme/app_colors.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
        children: const [
          _SectionTitle('Account & Security'),
          _SettingsTile(
            icon: Icons.devices,
            title: 'Manage devices',
            subtitle: 'View active sessions and revoke access',
          ),
          _SettingsTile(
            icon: Icons.lock_reset,
            title: 'Reset password',
            subtitle: 'Update password or enable passkeys',
          ),
          _SectionTitle('Preferences'),
          _SettingsTile(
            icon: Icons.language,
            title: 'Language',
            subtitle: '中文 / English',
          ),
          _SettingsTile(
            icon: Icons.dark_mode,
            title: 'Appearance',
            subtitle: 'Light · Dark · System',
          ),
          _SettingsTile(
            icon: Icons.storage,
            title: 'Cache & downloads',
            subtitle: '540 MB · Tap to manage',
          ),
          _SectionTitle('Diagnostics'),
          _SettingsTile(
            icon: Icons.graphic_eq,
            title: 'ASR Gateway status',
            subtitle: 'Operational · 120ms avg latency',
          ),
          _SettingsTile(
            icon: Icons.info_outline,
            title: 'App info',
            subtitle: 'Version 0.1.0 (Build 1)',
          ),
          SizedBox(height: 24),
          _DangerZoneButton(),
        ],
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.label);

  final String label;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Padding(
      padding: const EdgeInsets.only(top: 24, bottom: 8),
      child: Text(
        label,
        style: theme.textTheme.titleSmall?.copyWith(
          fontWeight: FontWeight.w600,
          color: AppColors.textSecondary,
        ),
      ),
    );
  }
}

class _SettingsTile extends StatelessWidget {
  const _SettingsTile({
    required this.icon,
    required this.title,
    required this.subtitle,
  });

  final IconData icon;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      elevation: 0,
      color: Colors.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: ListTile(
        leading: Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            gradient: AppColors.primaryGradient,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(icon, color: Colors.white),
        ),
        title: Text(
          title,
          style: theme.textTheme.titleMedium?.copyWith(
            color: AppColors.textPrimary,
          ),
        ),
        subtitle: Text(
          subtitle,
          style: theme.textTheme.bodySmall?.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
        trailing: const Icon(
          Icons.chevron_right,
          color: AppColors.textSecondary,
        ),
        onTap: () {},
      ),
    );
  }
}

class _DangerZoneButton extends StatelessWidget {
  const _DangerZoneButton();

  @override
  Widget build(BuildContext context) {
    return OutlinedButton.icon(
      onPressed: () {},
      icon: const Icon(Icons.logout),
      label: const Text('Sign out of all devices'),
      style: OutlinedButton.styleFrom(
        foregroundColor: Colors.redAccent,
        side: const BorderSide(color: Colors.redAccent),
        padding: const EdgeInsets.symmetric(vertical: 14),
      ),
    );
  }
}

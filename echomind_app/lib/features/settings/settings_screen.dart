import 'package:flutter/material.dart';

import '../../app/theme/app_colors.dart';
import '../../app/l10n/l10n.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Scaffold(
      appBar: AppBar(title: Text(l10n.settingsTitle)),
      body: ListView(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
        children: [
          _SectionTitle(l10n.settingsAccountSection),
          _SettingsTile(
            icon: Icons.devices,
            title: l10n.settingsManageDevices,
            subtitle: l10n.settingsManageDevicesSubtitle,
          ),
          _SettingsTile(
            icon: Icons.lock_reset,
            title: l10n.settingsResetPassword,
            subtitle: l10n.settingsResetPasswordSubtitle,
          ),
          _SectionTitle(l10n.settingsPreferencesSection),
          _SettingsTile(
            icon: Icons.language,
            title: l10n.settingsLanguage,
            subtitle: l10n.settingsLanguageSubtitle,
          ),
          _SettingsTile(
            icon: Icons.dark_mode,
            title: l10n.settingsAppearance,
            subtitle: l10n.settingsAppearanceSubtitle,
          ),
          _SettingsTile(
            icon: Icons.storage,
            title: l10n.settingsCache,
            subtitle: l10n.settingsCacheSubtitle,
          ),
          _SectionTitle(l10n.settingsDiagnosticsSection),
          _SettingsTile(
            icon: Icons.graphic_eq,
            title: l10n.settingsAsrStatus,
            subtitle: l10n.settingsAsrStatusSubtitle,
          ),
          _SettingsTile(
            icon: Icons.info_outline,
            title: l10n.settingsAppInfo,
            subtitle: l10n.settingsAppInfoSubtitle,
          ),
          const SizedBox(height: 24),
          const _DangerZoneButton(),
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
    final l10n = context.l10n;
    return OutlinedButton.icon(
      onPressed: () {},
      icon: const Icon(Icons.logout),
      label: Text(l10n.settingsSignOutAll),
      style: OutlinedButton.styleFrom(
        foregroundColor: Colors.redAccent,
        side: const BorderSide(color: Colors.redAccent),
        padding: const EdgeInsets.symmetric(vertical: 14),
      ),
    );
  }
}

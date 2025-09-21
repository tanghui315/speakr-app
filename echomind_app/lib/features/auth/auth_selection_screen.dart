import 'package:flutter/material.dart';

import '../home/home_shell.dart';
import '../../app/theme/app_colors.dart';
import '../../app/l10n/l10n.dart';

class AuthSelectionScreen extends StatelessWidget {
  const AuthSelectionScreen({super.key});

  void _navigateToHome(BuildContext context) {
    Navigator.of(
      context,
    ).pushReplacement(MaterialPageRoute(builder: (_) => const HomeShell()));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = context.l10n;

    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                l10n.authWelcome,
                style: theme.textTheme.headlineMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                l10n.authSubtitle,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: 32),
              _AuthButton(
                icon: Icons.apple,
                label: l10n.authContinueApple,
                onTap: () => _navigateToHome(context),
              ),
              const SizedBox(height: 16),
              _AuthButton(
                icon: Icons.g_mobiledata,
                label: l10n.authContinueGoogle,
                onTap: () => _navigateToHome(context),
              ),
              const SizedBox(height: 16),
              _AuthButton(
                icon: Icons.mail_outline,
                label: l10n.authContinueEmail,
                onTap: () => _navigateToHome(context),
              ),
              const Spacer(),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  TextButton(onPressed: () {}, child: Text(l10n.authPrivacy)),
                  TextButton(
                    onPressed: () {},
                    child: Text(l10n.authLanguageToggle),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _AuthButton extends StatelessWidget {
  const _AuthButton({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton.icon(
        style: ElevatedButton.styleFrom(
          backgroundColor: Colors.white,
          foregroundColor: AppColors.textPrimary,
          elevation: 0,
          padding: const EdgeInsets.symmetric(vertical: 16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
        ),
        icon: Icon(icon, size: 24),
        label: Text(label),
        onPressed: onTap,
      ),
    );
  }
}

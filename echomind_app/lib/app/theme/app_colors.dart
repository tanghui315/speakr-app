import 'package:flutter/material.dart';

/// Brand color tokens used across EchoMind.
class AppColors {
  const AppColors._();

  static const Color primary = Color(0xFF5840FF);
  static const Color accent = Color(0xFF21C5E5);
  static const Color accentGradientEnd = Color(0xFF0AAEE0);
  static const Color highlight = Color(0xFFFFC857);

  static const Color backgroundLight = Color(0xFFF4F5F9);
  static const Color backgroundDark = Color(0xFF101321);

  static const Color textPrimary = Color(0xFF1F2430);
  static const Color textSecondary = Color(0xFF6B7280);

  static const LinearGradient primaryGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [primary, accent],
  );
}

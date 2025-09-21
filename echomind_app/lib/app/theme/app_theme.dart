import 'package:flutter/material.dart';

import 'app_colors.dart';

ThemeData buildLightTheme() {
  const textTheme = Typography.blackMountainView;

  return ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(
      seedColor: AppColors.primary,
      primary: AppColors.primary,
      secondary: AppColors.accent,
      surface: Colors.white,
      background: AppColors.backgroundLight,
      onPrimary: Colors.white,
      onSecondary: Colors.white,
      onSurface: AppColors.textPrimary,
      onBackground: AppColors.textPrimary,
    ),
    scaffoldBackgroundColor: AppColors.backgroundLight,
    textTheme: textTheme,
    fontFamilyFallback: const ['SF Pro', 'Noto Sans'],
    appBarTheme: const AppBarTheme(
      elevation: 0,
      scrolledUnderElevation: 0,
      backgroundColor: Colors.transparent,
      foregroundColor: AppColors.textPrimary,
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: Colors.white,
      indicatorColor: AppColors.primary.withOpacity(0.12),
      labelTextStyle: MaterialStateProperty.resolveWith(
        (states) => TextStyle(
          fontWeight:
              states.contains(MaterialState.selected)
                  ? FontWeight.w600
                  : FontWeight.w500,
          color: AppColors.textPrimary,
        ),
      ),
      iconTheme: MaterialStateProperty.resolveWith(
        (states) => IconThemeData(
          color:
              states.contains(MaterialState.selected)
                  ? AppColors.primary
                  : AppColors.textSecondary,
        ),
      ),
    ),
    chipTheme: ChipThemeData(
      backgroundColor: Colors.white,
      labelStyle: const TextStyle(color: AppColors.textSecondary),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      selectedColor: AppColors.primary.withOpacity(0.12),
    ),
    floatingActionButtonTheme: const FloatingActionButtonThemeData(
      backgroundColor: AppColors.primary,
      foregroundColor: Colors.white,
      shape: CircleBorder(),
    ),
  );
}

ThemeData buildDarkTheme() {
  const textTheme = Typography.whiteMountainView;

  return ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(
      brightness: Brightness.dark,
      seedColor: AppColors.primary,
      primary: AppColors.primary,
      secondary: AppColors.accent,
      surface: const Color(0xFF161A27),
      background: AppColors.backgroundDark,
      onPrimary: Colors.white,
      onSecondary: Colors.black,
      onSurface: Colors.white,
      onBackground: Colors.white,
    ),
    scaffoldBackgroundColor: AppColors.backgroundDark,
    textTheme: textTheme,
    fontFamilyFallback: const ['SF Pro', 'Noto Sans'],
    appBarTheme: const AppBarTheme(
      elevation: 0,
      scrolledUnderElevation: 0,
      backgroundColor: Colors.transparent,
      foregroundColor: Colors.white,
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: const Color(0xFF151926),
      indicatorColor: AppColors.primary.withOpacity(0.35),
      labelTextStyle: MaterialStateProperty.resolveWith(
        (states) => TextStyle(
          fontWeight:
              states.contains(MaterialState.selected)
                  ? FontWeight.w600
                  : FontWeight.w500,
          color:
              states.contains(MaterialState.selected)
                  ? Colors.white
                  : Colors.white70,
        ),
      ),
      iconTheme: MaterialStateProperty.resolveWith(
        (states) => IconThemeData(
          color:
              states.contains(MaterialState.selected)
                  ? Colors.white
                  : Colors.white70,
        ),
      ),
    ),
    chipTheme: ChipThemeData(
      backgroundColor: const Color(0xFF191E2A),
      labelStyle: const TextStyle(color: Colors.white70),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      selectedColor: AppColors.primary.withOpacity(0.24),
    ),
    floatingActionButtonTheme: const FloatingActionButtonThemeData(
      backgroundColor: AppColors.primary,
      foregroundColor: Colors.white,
      shape: CircleBorder(),
    ),
  );
}

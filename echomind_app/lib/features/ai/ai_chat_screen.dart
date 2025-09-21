import 'package:flutter/material.dart';

import '../../app/theme/app_colors.dart';
import '../../app/l10n/l10n.dart';

class AiChatScreen extends StatelessWidget {
  const AiChatScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = context.l10n;

    return GestureDetector(
      onTap: () => FocusScope.of(context).unfocus(),
      behavior: HitTestBehavior.translucent,
      child: Scaffold(
        appBar: AppBar(
          title: Text(l10n.aiTitle),
          actions: [
            IconButton(
              icon: const Icon(Icons.history_toggle_off),
              tooltip: l10n.aiHistory,
              onPressed: () {},
            ),
          ],
        ),
        body: Column(
          children: [
            Expanded(
              child: ListView(
                padding: const EdgeInsets.symmetric(
                  horizontal: 24,
                  vertical: 16,
                ),
                keyboardDismissBehavior:
                    ScrollViewKeyboardDismissBehavior.onDrag,
                children: const [
                  _AiMessage(
                    isUser: true,
                    message:
                        'Summarise yesterday\'s board meeting and list follow-ups?',
                  ),
                  _AiMessage(
                    isUser: false,
                    message:
                        'Here is a summary with next steps:\n1. Align on product pricing...\n2. Schedule follow-up with finance team...\nCitations: #Recording-024, #Recording-025',
                  ),
                ],
              ),
            ),
            _InputArea(theme: theme),
          ],
        ),
      ),
    );
  }
}

class _AiMessage extends StatelessWidget {
  const _AiMessage({required this.isUser, required this.message});

  final bool isUser;
  final String message;

  @override
  Widget build(BuildContext context) {
    final alignment = isUser ? Alignment.centerRight : Alignment.centerLeft;

    return Align(
      alignment: alignment,
      child: Container(
        constraints: const BoxConstraints(maxWidth: 320),
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: isUser ? Colors.transparent : Colors.white,
          gradient:
              isUser
                  ? const LinearGradient(
                    colors: [AppColors.primary, AppColors.accent],
                  )
                  : null,
          borderRadius: BorderRadius.circular(18),
        ),
        child: Text(
          message,
          style: TextStyle(
            color: isUser ? Colors.white : AppColors.textPrimary,
            height: 1.4,
          ),
        ),
      ),
    );
  }
}

class _InputArea extends StatelessWidget {
  const _InputArea({required this.theme});

  final ThemeData theme;

  @override
  Widget build(BuildContext context) {
    final keyboardInset = MediaQuery.viewInsetsOf(context).bottom;
    final isDark = theme.brightness == Brightness.dark;
    final l10n = context.l10n;

    return SafeArea(
      top: false,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: EdgeInsets.fromLTRB(20, 12, 20, 12 + keyboardInset * 0.02),
        decoration: BoxDecoration(
          color: theme.colorScheme.surface,
          boxShadow: const [
            BoxShadow(
              blurRadius: 20,
              offset: Offset(0, -4),
              color: Color(0x11000000),
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              children: [
                Expanded(
                  child: TextField(
                    minLines: 1,
                    maxLines: 4,
                    style: TextStyle(
                      color: isDark ? Colors.white : AppColors.textPrimary,
                    ),
                    cursorColor: AppColors.primary,
                    decoration: InputDecoration(
                      hintText: l10n.aiPlaceholder,
                      hintStyle: TextStyle(
                        color:
                            isDark ? Colors.white70 : AppColors.textSecondary,
                      ),
                      filled: true,
                      fillColor:
                          isDark ? const Color(0xFF191E2A) : Colors.white,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(20),
                        borderSide: BorderSide.none,
                      ),
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 14,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    shape: const CircleBorder(),
                    padding: const EdgeInsets.all(16),
                    backgroundColor: AppColors.primary,
                  ),
                  onPressed: () {
                    FocusScope.of(context).unfocus();
                  },
                  child: Semantics(
                    label: l10n.aiSend,
                    button: true,
                    child: const Icon(Icons.send, color: Colors.white),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            SizedBox(
              height: 36,
              child: ListView(
                scrollDirection: Axis.horizontal,
                keyboardDismissBehavior:
                    ScrollViewKeyboardDismissBehavior.onDrag,
                children: const [
                  _SuggestionChipIconized(kind: _SuggestionKind.decisions),
                  _SuggestionChipIconized(kind: _SuggestionKind.notes),
                  _SuggestionChipIconized(kind: _SuggestionKind.actions),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

enum _SuggestionKind { decisions, notes, actions }

class _SuggestionChipIconized extends StatelessWidget {
  const _SuggestionChipIconized({required this.kind});

  final _SuggestionKind kind;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final label = switch (kind) {
      _SuggestionKind.decisions => l10n.aiSuggestDecisions,
      _SuggestionKind.notes => l10n.aiSuggestNotes,
      _SuggestionKind.actions => l10n.aiSuggestActions,
    };
    return Padding(
      padding: const EdgeInsets.only(right: 12),
      child: ActionChip(
        label: Text(
          label,
          style: const TextStyle(color: AppColors.textPrimary),
        ),
        onPressed: () {},
        backgroundColor: Colors.white,
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'persistence/app_settings.dart';
import 'state/game_notifier.dart';
import 'theme/app_theme.dart';
import 'screens/setup_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final settings = AppSettings();
  await settings.load();

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider.value(value: settings),
        ChangeNotifierProvider(create: (_) => GameNotifier()),
      ],
      child: const WizardApp(),
    ),
  );
}

/// App-wide messenger key so background tasks (e.g. leaderboard submission
/// that finishes after we've navigated to the podium) can still surface a
/// SnackBar without holding a specific screen's context.
final GlobalKey<ScaffoldMessengerState> rootScaffoldMessengerKey =
    GlobalKey<ScaffoldMessengerState>();

class WizardApp extends StatelessWidget {
  const WizardApp({super.key});

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<AppSettings>();
    return MaterialApp(
      title: 'Wizard',
      debugShowCheckedModeBanner: false,
      theme: lightTheme,
      darkTheme: darkTheme,
      themeMode: settings.themeMode,
      scaffoldMessengerKey: rootScaffoldMessengerKey,
      home: const SetupScreen(),
    );
  }
}

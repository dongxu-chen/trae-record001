import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:device_info_plus/device_info_plus.dart';
import 'providers/auth_provider.dart';
import 'providers/book_provider.dart';
import 'providers/note_provider.dart';
import 'providers/progress_provider.dart';
import 'providers/bookmark_provider.dart';
import 'providers/sync_provider.dart';
import 'providers/ai_provider.dart';
import 'providers/stats_provider.dart';
import 'screens/home_screen.dart';
import 'screens/login_screen.dart';
import 'services/sync_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp(
    options: const FirebaseOptions(
      apiKey: 'your-api-key',
      appId: 'your-app-id',
      messagingSenderId: 'your-sender-id',
      projectId: 'your-project-id',
    ),
  );
  
  final deviceId = await _getDeviceId();
  final syncService = SyncService(deviceId);
  await syncService.init();

  runApp(MyApp(syncService: syncService));
}

Future<String> _getDeviceId() async {
  final deviceInfo = DeviceInfoPlugin();
  if (Theme.of(WidgetsBinding.instance.context).platform == TargetPlatform.iOS) {
    final iosInfo = await deviceInfo.iosInfo;
    return iosInfo.identifierForVendor ?? 'ios_device';
  } else if (Theme.of(WidgetsBinding.instance.context).platform == TargetPlatform.android) {
    final androidInfo = await deviceInfo.androidInfo;
    return androidInfo.id ?? 'android_device';
  } else {
    final webBrowserInfo = await deviceInfo.webBrowserInfo;
    return webBrowserInfo.userAgent ?? 'web_device';
  }
}

class MyApp extends StatelessWidget {
  final SyncService syncService;

  const MyApp({super.key, required this.syncService});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthProvider()),
        ChangeNotifierProvider(create: (_) => SyncProvider(syncService)),
        ChangeNotifierProxyProvider2<AuthProvider, SyncProvider, BookProvider>(
          create: (_) => BookProvider(),
          update: (_, auth, sync, previous) =>
              previous!..updateUser(auth.user, sync?.syncService),
        ),
        ChangeNotifierProxyProvider2<AuthProvider, SyncProvider, NoteProvider>(
          create: (_) => NoteProvider(),
          update: (_, auth, sync, previous) =>
              previous!..updateUser(auth.user, sync?.syncService),
        ),
        ChangeNotifierProxyProvider2<AuthProvider, SyncProvider, ProgressProvider>(
          create: (_) => ProgressProvider(),
          update: (_, auth, sync, previous) =>
              previous!..updateUser(auth.user, sync?.syncService),
        ),
        ChangeNotifierProxyProvider2<AuthProvider, SyncProvider, BookmarkProvider>(
          create: (_) => BookmarkProvider(),
          update: (_, auth, sync, previous) =>
              previous!..updateUser(auth.user, sync?.syncService),
        ),
        ChangeNotifierProvider(create: (_) => AIProvider()),
        ChangeNotifierProvider(create: (_) => StatsProvider()),
      ],
      child: MaterialApp(
        title: 'Ebook Sync',
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
          useMaterial3: true,
        ),
        darkTheme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: Colors.blue,
            brightness: Brightness.dark,
          ),
          useMaterial3: true,
        ),
        themeMode: ThemeMode.system,
        home: const AuthWrapper(),
        debugShowCheckedModeBanner: false,
      ),
    );
  }
}

class AuthWrapper extends StatelessWidget {
  const AuthWrapper({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<AuthProvider>(
      builder: (context, auth, _) {
        if (auth.isAuthenticated) {
          return const HomeScreen();
        }
        return const LoginScreen();
      },
    );
  }
}

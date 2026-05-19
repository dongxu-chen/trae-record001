import 'dart:math';
import 'package:flutter/foundation.dart';
import '../models/reading_stats.dart';
import '../services/local_storage_service.dart';
import 'package:uuid/uuid.dart';

class StatsProvider extends ChangeNotifier {
  final LocalDataManager _storage = LocalDataManager();
  ReadingStats? _stats;
  ReadingSession? _activeSession;

  ReadingStats? get stats => _stats;
  ReadingSession? get activeSession => _activeSession;
  bool get hasActiveSession => _activeSession != null;

  Future<void> loadStats() async {
    final sessions = _storage.readingSessions;
    final bookmarksCount = _storage.bookmarks.length;
    final booksCompleted = _storage.books.where((b) => b.isCompleted ?? false).length;

    _stats = ReadingStats.calculate(
      sessions,
      booksCompleted: booksCompleted,
      totalBookmarks: bookmarksCount,
    );
    notifyListeners();
  }

  Future<void> startReadingSession({
    required String bookId,
    required String bookTitle,
    int? startPage,
  }) async {
    if (_activeSession != null) {
      await endReadingSession();
    }

    _activeSession = ReadingSession(
      id: const Uuid().v4(),
      bookId: bookId,
      bookTitle: bookTitle,
      startTime: DateTime.now(),
      endTime: DateTime.now(),
      durationSeconds: 0,
      startPage: startPage,
    );
    notifyListeners();
  }

  Future<void> endReadingSession({int? endPage}) async {
    if (_activeSession == null) return;

    final endTime = DateTime.now();
    final duration = endTime.difference(_activeSession!.startTime).inSeconds;

    final updatedSession = ReadingSession(
      id: _activeSession!.id,
      bookId: _activeSession!.bookId,
      bookTitle: _activeSession!.bookTitle,
      startTime: _activeSession!.startTime,
      endTime: endTime,
      durationSeconds: max(duration, 10),
      startPage: _activeSession!.startPage,
      endPage: endPage,
    );

    await _storage.addReadingSession(updatedSession);
    _activeSession = null;
    await loadStats();
  }

  void cancelReadingSession() {
    _activeSession = null;
    notifyListeners();
  }

  int get currentSessionDuration {
    if (_activeSession == null) return 0;
    return DateTime.now().difference(_activeSession!.startTime).inSeconds;
  }

  void generateDemoData() {
    final now = DateTime.now();
    final random = Random();

    final demoSessions = <ReadingSession>[];

    for (int i = 30; i >= 0; i--) {
      final date = now.subtract(Duration(days: i));
      final sessionsPerDay = random.nextInt(3) + 1;

      for (int s = 0; s < sessionsPerDay; s++) {
        final hour = random.nextInt(12) + 8;
        final duration = random.nextInt(60) + 15;

        demoSessions.add(ReadingSession(
          id: const Uuid().v4(),
          bookId: 'demo_book_${random.nextInt(3)}',
          bookTitle: ['思考，快与慢', '原则', '人类简史'][random.nextInt(3)],
          startTime: DateTime(date.year, date.month, date.day, hour),
          endTime: DateTime(date.year, date.month, date.day, hour).add(Duration(minutes: duration)),
          durationSeconds: duration * 60,
          startPage: random.nextInt(300),
          endPage: random.nextInt(300) + 50,
        ));
      }
    }

    for (final session in demoSessions) {
      _storage.addReadingSession(session);
    }

    loadStats();
  }
}

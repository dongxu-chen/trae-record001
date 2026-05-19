import 'package:flutter/foundation.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../models/reading_progress.dart';
import '../services/firebase_service.dart';
import '../services/sync_service.dart';

class ProgressProvider extends ChangeNotifier {
  final FirebaseService _firebaseService = FirebaseService();
  SyncService? _syncService;
  User? _user;
  bool _isLoading = false;

  List<ReadingProgress> get progressList => _syncService?.getLocalProgress() ?? [];
  bool get isLoading => _isLoading;

  void updateUser(User? user, [SyncService? syncService]) {
    if (_user?.uid != user?.uid) {
      _user = user;
      _syncService = syncService;
      notifyListeners();
    } else if (syncService != null && _syncService == null) {
      _syncService = syncService;
      notifyListeners();
    }
  }

  ReadingProgress? getProgressForBook(String bookId) {
    try {
      return progressList.firstWhere((p) => p.bookId == bookId);
    } catch (e) {
      return null;
    }
  }

  Future<void> loadProgressForBook(String bookId) async {
    if (_user == null) return;
    notifyListeners();
  }

  Future<ReadingProgress?> updateProgress(
    String bookId,
    int currentPage,
    int totalPages,
    String? deviceInfo,
  ) async {
    try {
      final progress = ReadingProgress(
        id: getProgressForBook(bookId)?.id ?? '',
        bookId: bookId,
        userId: _user?.uid ?? '',
        currentPage: currentPage,
        progressPercentage: currentPage / totalPages,
        lastReadAt: DateTime.now(),
        deviceInfo: deviceInfo,
      );
      await _syncService?.updateProgress(progress);
      notifyListeners();
      return progress;
    } catch (e) {
      debugPrint('Error updating progress: $e');
      return null;
    }
  }
}

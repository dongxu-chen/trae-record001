import 'package:flutter/foundation.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../models/bookmark.dart';
import '../services/firebase_service.dart';
import '../services/sync_service.dart';
import '../utils/image_preprocessor.dart';

class BookmarkProvider extends ChangeNotifier {
  final FirebaseService _firebaseService = FirebaseService();
  SyncService? _syncService;
  User? _user;
  bool _isLoading = false;

  List<Bookmark> get bookmarks => _syncService?.getLocalBookmarks() ?? [];
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

  Future<void> loadBookmarks() async {
    if (_user == null) return;
    notifyListeners();
  }

  Future<Uint8List> preprocessImageForOCR(Uint8List imageData) async {
    return await OCRPreprocessingPipeline.processImage(imageData);
  }

  Future<Bookmark?> addBookmark(Bookmark bookmark) async {
    try {
      await _syncService?.createBookmark(bookmark);
      notifyListeners();
      return bookmark;
    } catch (e) {
      debugPrint('Error adding bookmark: $e');
      return null;
    }
  }

  Future<void> updateBookmark(Bookmark bookmark) async {
    try {
      await _syncService?.updateBookmark(bookmark);
      notifyListeners();
    } catch (e) {
      debugPrint('Error updating bookmark: $e');
    }
  }

  Future<void> deleteBookmark(String bookmarkId) async {
    try {
      await _syncService?.deleteBookmark(bookmarkId);
      notifyListeners();
    } catch (e) {
      debugPrint('Error deleting bookmark: $e');
    }
  }

  List<Bookmark> getBookmarksForBook(String bookId) {
    return bookmarks.where((b) => b.bookId == bookId).toList();
  }

  List<Bookmark> getBookmarksByTag(String tag) {
    return bookmarks.where((b) => b.tags.contains(tag)).toList();
  }

  List<String> get allTags {
    final tags = <String>{};
    for (final bookmark in bookmarks) {
      tags.addAll(bookmark.tags);
    }
    return tags.toList();
  }
}

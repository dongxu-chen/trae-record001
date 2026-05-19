import 'package:flutter/foundation.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../models/book.dart';
import '../services/firebase_service.dart';
import '../services/sync_service.dart';

class BookProvider extends ChangeNotifier {
  final FirebaseService _firebaseService = FirebaseService();
  SyncService? _syncService;
  User? _user;
  bool _isLoading = false;

  List<Book> get books => _syncService?.getLocalBooks() ?? [];
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

  Future<void> loadBooks() async {
    if (_user == null) return;

    _isLoading = true;
    notifyListeners();

    try {
      if (_syncService != null && _syncService!.isSyncing) {
        await _syncService!.sync();
      }
    } catch (e) {
      debugPrint('Error loading books: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<Book?> addBook(Book book) async {
    try {
      await _syncService?.createBook(book);
      notifyListeners();
      return book;
    } catch (e) {
      debugPrint('Error adding book: $e');
      return null;
    }
  }

  Future<void> updateBook(Book book) async {
    try {
      await _syncService?.updateBook(book);
      notifyListeners();
    } catch (e) {
      debugPrint('Error updating book: $e');
    }
  }

  Future<void> deleteBook(String bookId) async {
    try {
      await _syncService?.deleteBook(bookId);
      notifyListeners();
    } catch (e) {
      debugPrint('Error deleting book: $e');
    }
  }

  Book? getBookById(String bookId) {
    try {
      return books.firstWhere((b) => b.id == bookId);
    } catch (e) {
      return null;
    }
  }
}

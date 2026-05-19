import 'package:flutter/foundation.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../models/note.dart';
import '../services/firebase_service.dart';
import '../services/sync_service.dart';

class NoteProvider extends ChangeNotifier {
  final FirebaseService _firebaseService = FirebaseService();
  SyncService? _syncService;
  User? _user;
  bool _isLoading = false;

  List<Note> get notes => _syncService?.getLocalNotes() ?? [];
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

  List<Note> getNotesForBook(String bookId) {
    return notes.where((n) => n.bookId == bookId).toList();
  }

  Future<void> loadNotesForBook(String bookId) async {
    if (_user == null) return;
    notifyListeners();
  }

  Future<Note?> addNote(Note note) async {
    try {
      await _syncService?.createNote(note);
      notifyListeners();
      return note;
    } catch (e) {
      debugPrint('Error adding note: $e');
      return null;
    }
  }

  Future<void> updateNote(Note note) async {
    try {
      await _syncService?.updateNote(note);
      notifyListeners();
    } catch (e) {
      debugPrint('Error updating note: $e');
    }
  }

  Future<void> deleteNote(String noteId) async {
    try {
      await _syncService?.deleteNote(noteId);
      notifyListeners();
    } catch (e) {
      debugPrint('Error deleting note: $e');
    }
  }
}

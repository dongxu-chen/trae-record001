import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_storage/firebase_storage.dart';
import 'package:uuid/uuid.dart';
import '../models/book.dart';
import '../models/note.dart';
import '../models/reading_progress.dart';
import '../models/bookmark.dart';

class FirebaseService {
  final FirebaseAuth _auth = FirebaseAuth.instance;
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;
  final FirebaseStorage _storage = FirebaseStorage.instance;
  final Uuid _uuid = const Uuid();

  User? get currentUser => _auth.currentUser;
  bool get isAuthenticated => _auth.currentUser != null;

  Future<UserCredential?> signInWithEmail(String email, String password) async {
    try {
      return await _auth.signInWithEmailAndPassword(
        email: email,
        password: password,
      );
    } catch (e) {
      rethrow;
    }
  }

  Future<UserCredential?> signUpWithEmail(String email, String password) async {
    try {
      return await _auth.createUserWithEmailAndPassword(
        email: email,
        password: password,
      );
    } catch (e) {
      rethrow;
    }
  }

  Future<void> signOut() async {
    await _auth.signOut();
  }

  Stream<User?> authStateChanges() {
    return _auth.authStateChanges();
  }

  Future<List<Book>> getUserBooks(String userId) async {
    final snapshot = await _firestore
        .collection('books')
        .where('userId', isEqualTo: userId)
        .orderBy('updatedAt', descending: true)
        .get();

    return snapshot.docs.map((doc) => Book.fromMap(doc.data())).toList();
  }

  Stream<List<Book>> getUserBooksStream(String userId) {
    return _firestore
        .collection('books')
        .where('userId', isEqualTo: userId)
        .orderBy('updatedAt', descending: true)
        .snapshots()
        .map((snapshot) =>
            snapshot.docs.map((doc) => Book.fromMap(doc.data())).toList());
  }

  Future<Book> addBook(Book book) async {
    final bookId = _uuid.v4();
    final newBook = book.copyWith(id: bookId);
    await _firestore.collection('books').doc(bookId).set(newBook.toMap());
    return newBook;
  }

  Future<void> updateBook(Book book) async {
    await _firestore.collection('books').doc(book.id).update(book.toMap());
  }

  Future<void> deleteBook(String bookId) async {
    await _firestore.collection('books').doc(bookId).delete();
  }

  Future<List<Note>> getBookNotes(String bookId, String userId) async {
    final snapshot = await _firestore
        .collection('notes')
        .where('bookId', isEqualTo: bookId)
        .where('userId', isEqualTo: userId)
        .orderBy('createdAt', descending: true)
        .get();

    return snapshot.docs.map((doc) => Note.fromMap(doc.data())).toList();
  }

  Stream<List<Note>> getBookNotesStream(String bookId, String userId) {
    return _firestore
        .collection('notes')
        .where('bookId', isEqualTo: bookId)
        .where('userId', isEqualTo: userId)
        .orderBy('createdAt', descending: true)
        .snapshots()
        .map((snapshot) =>
            snapshot.docs.map((doc) => Note.fromMap(doc.data())).toList());
  }

  Future<Note> addNote(Note note) async {
    final noteId = _uuid.v4();
    final newNote = note.copyWith(id: noteId);
    await _firestore.collection('notes').doc(noteId).set(newNote.toMap());
    return newNote;
  }

  Future<void> updateNote(Note note) async {
    await _firestore.collection('notes').doc(note.id).update(note.toMap());
  }

  Future<void> deleteNote(String noteId) async {
    await _firestore.collection('notes').doc(noteId).delete();
  }

  Future<ReadingProgress?> getReadingProgress(
      String bookId, String userId) async {
    final snapshot = await _firestore
        .collection('readingProgress')
        .where('bookId', isEqualTo: bookId)
        .where('userId', isEqualTo: userId)
        .limit(1)
        .get();

    if (snapshot.docs.isNotEmpty) {
      return ReadingProgress.fromMap(snapshot.docs.first.data());
    }
    return null;
  }

  Stream<ReadingProgress?> getReadingProgressStream(
      String bookId, String userId) {
    return _firestore
        .collection('readingProgress')
        .where('bookId', isEqualTo: bookId)
        .where('userId', isEqualTo: userId)
        .limit(1)
        .snapshots()
        .map((snapshot) => snapshot.docs.isNotEmpty
            ? ReadingProgress.fromMap(snapshot.docs.first.data())
            : null);
  }

  Future<ReadingProgress> updateReadingProgress(
      ReadingProgress progress) async {
    final progressId = progress.id.isEmpty ? _uuid.v4() : progress.id;
    final newProgress = progress.copyWith(id: progressId);
    await _firestore
        .collection('readingProgress')
        .doc(progressId)
        .set(newProgress.toMap());
    return newProgress;
  }

  Future<List<Bookmark>> getUserBookmarks(String userId) async {
    final snapshot = await _firestore
        .collection('bookmarks')
        .where('userId', isEqualTo: userId)
        .orderBy('createdAt', descending: true)
        .get();

    return snapshot.docs.map((doc) => Bookmark.fromMap(doc.data())).toList();
  }

  Stream<List<Bookmark>> getUserBookmarksStream(String userId) {
    return _firestore
        .collection('bookmarks')
        .where('userId', isEqualTo: userId)
        .orderBy('createdAt', descending: true)
        .snapshots()
        .map((snapshot) =>
            snapshot.docs.map((doc) => Bookmark.fromMap(doc.data())).toList());
  }

  Future<Bookmark> addBookmark(Bookmark bookmark) async {
    final bookmarkId = _uuid.v4();
    final newBookmark = bookmark.copyWith(id: bookmarkId);
    await _firestore
        .collection('bookmarks')
        .doc(bookmarkId)
        .set(newBookmark.toMap());
    return newBookmark;
  }

  Future<void> updateBookmark(Bookmark bookmark) async {
    await _firestore
        .collection('bookmarks')
        .doc(bookmark.id)
        .update(bookmark.toMap());
  }

  Future<void> deleteBookmark(String bookmarkId) async {
    await _firestore.collection('bookmarks').doc(bookmarkId).delete();
  }
}

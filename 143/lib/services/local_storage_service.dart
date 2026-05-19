import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/book.dart';
import '../models/note.dart';
import '../models/reading_progress.dart';
import '../models/bookmark.dart';
import '../models/reading_stats.dart';
import '../utils/delta_format.dart';

class LocalStorageService {
  static const String _keyBooks = 'local_books';
  static const String _keyNotes = 'local_notes';
  static const String _keyProgress = 'local_progress';
  static const String _keyBookmarks = 'local_bookmarks';
  static const String _keySyncState = 'sync_state';
  static const String _keyNoteDeltas = 'local_note_deltas';
  static const String _keyReadingSessions = 'reading_sessions';
  static const String _keyBookmarkSummaries = 'bookmark_summaries';

  SharedPreferences? _prefs;

  Future<void> init() async {
    _prefs ??= await SharedPreferences.getInstance();
  }

  Future<void> _ensureInitialized() async {
    if (_prefs == null) {
      await init();
    }
  }

  Future<void> saveBooks(List<Book> books) async {
    await _ensureInitialized();
    final data = books.map((b) => b.toMap()).toList();
    await _prefs!.setString(_keyBooks, json.encode(data));
  }

  Future<List<Book>> getBooks() async {
    await _ensureInitialized();
    final data = _prefs!.getString(_keyBooks);
    if (data == null) return [];
    final list = json.decode(data) as List;
    return list.map((item) => Book.fromMap(item as Map<String, dynamic>)).toList();
  }

  Future<void> saveNotes(List<Note> notes) async {
    await _ensureInitialized();
    final data = notes.map((n) => n.toMap()).toList();
    await _prefs!.setString(_keyNotes, json.encode(data));
  }

  Future<List<Note>> getNotes() async {
    await _ensureInitialized();
    final data = _prefs!.getString(_keyNotes);
    if (data == null) return [];
    final list = json.decode(data) as List;
    return list.map((item) => Note.fromMap(item as Map<String, dynamic>)).toList();
  }

  Future<void> saveNoteDeltas(Map<String, List<NoteDelta>> deltas) async {
    await _ensureInitialized();
    final data = deltas.map((key, value) => MapEntry(
      key,
      value.map((d) => d.toMap()).toList(),
    ));
    await _prefs!.setString(_keyNoteDeltas, json.encode(data));
  }

  Future<Map<String, List<NoteDelta>>> getNoteDeltas() async {
    await _ensureInitialized();
    final data = _prefs!.getString(_keyNoteDeltas);
    if (data == null) return {};
    final map = json.decode(data) as Map<String, dynamic>;
    return map.map((key, value) => MapEntry(
      key,
      (value as List).map((item) => NoteDelta.fromMap(item as Map<String, dynamic>)).toList(),
    ));
  }

  Future<void> saveReadingProgress(List<ReadingProgress> progress) async {
    await _ensureInitialized();
    final data = progress.map((p) => p.toMap()).toList();
    await _prefs!.setString(_keyProgress, json.encode(data));
  }

  Future<List<ReadingProgress>> getReadingProgress() async {
    await _ensureInitialized();
    final data = _prefs!.getString(_keyProgress);
    if (data == null) return [];
    final list = json.decode(data) as List;
    return list.map((item) => ReadingProgress.fromMap(item as Map<String, dynamic>)).toList();
  }

  Future<void> saveBookmarks(List<Bookmark> bookmarks) async {
    await _ensureInitialized();
    final data = bookmarks.map((b) => b.toMap()).toList();
    await _prefs!.setString(_keyBookmarks, json.encode(data));
  }

  Future<List<Bookmark>> getBookmarks() async {
    await _ensureInitialized();
    final data = _prefs!.getString(_keyBookmarks);
    if (data == null) return [];
    final list = json.decode(data) as List;
    return list.map((item) => Bookmark.fromMap(item as Map<String, dynamic>)).toList();
  }

  Future<SyncState> getSyncState() async {
    await _ensureInitialized();
    final data = _prefs!.getString(_keySyncState);
    if (data == null) return SyncState.initial();
    return SyncState.fromMap(json.decode(data) as Map<String, dynamic>);
  }

  Future<void> saveSyncState(SyncState state) async {
    await _ensureInitialized();
    await _prefs!.setString(_keySyncState, json.encode(state.toMap()));
  }

  Future<void> clearAll() async {
    await _ensureInitialized();
    await _prefs!.clear();
  }

  Future<void> saveReadingSessions(List<ReadingSession> sessions) async {
    await _ensureInitialized();
    final data = sessions.map((s) => s.toMap()).toList();
    await _prefs!.setString(_keyReadingSessions, json.encode(data));
  }

  Future<List<ReadingSession>> getReadingSessions() async {
    await _ensureInitialized();
    final data = _prefs!.getString(_keyReadingSessions);
    if (data == null) return [];
    final list = json.decode(data) as List;
    return list.map((item) => ReadingSession.fromMap(item as Map<String, dynamic>)).toList();
  }

  Future<void> saveBookmarkSummary(BookmarkSummary summary) async {
    await _ensureInitialized();
    final summaries = await getBookmarkSummaries();
    summaries.removeWhere((s) => s.bookmarkId == summary.bookmarkId);
    summaries.add(summary);
    final data = summaries.map((s) => s.toMap()).toList();
    await _prefs!.setString(_keyBookmarkSummaries, json.encode(data));
  }

  Future<List<BookmarkSummary>> getBookmarkSummaries() async {
    await _ensureInitialized();
    final data = _prefs!.getString(_keyBookmarkSummaries);
    if (data == null) return [];
    final list = json.decode(data) as List;
    return list.map((item) => BookmarkSummary.fromMap(item as Map<String, dynamic>)).toList();
  }

  Future<void> clearUserData() async {
    await _ensureInitialized();
    await _prefs!.remove(_keyBooks);
    await _prefs!.remove(_keyNotes);
    await _prefs!.remove(_keyProgress);
    await _prefs!.remove(_keyBookmarks);
    await _prefs!.remove(_keySyncState);
    await _prefs!.remove(_keyNoteDeltas);
    await _prefs!.remove(_keyReadingSessions);
    await _prefs!.remove(_keyBookmarkSummaries);
  }
}

class SyncState {
  final DateTime lastSyncTime;
  final Map<String, int> entityVersions;
  final bool isOfflineMode;
  final List<String> pendingOperations;

  SyncState({
    required this.lastSyncTime,
    required this.entityVersions,
    required this.isOfflineMode,
    required this.pendingOperations,
  });

  factory SyncState.initial() {
    return SyncState(
      lastSyncTime: DateTime.fromMillisecondsSinceEpoch(0),
      entityVersions: {},
      isOfflineMode: false,
      pendingOperations: [],
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'lastSyncTime': lastSyncTime.toIso8601String(),
      'entityVersions': entityVersions,
      'isOfflineMode': isOfflineMode,
      'pendingOperations': pendingOperations,
    };
  }

  factory SyncState.fromMap(Map<String, dynamic> map) {
    return SyncState(
      lastSyncTime: DateTime.parse(map['lastSyncTime'] as String),
      entityVersions: Map<String, int>.from(map['entityVersions'] as Map),
      isOfflineMode: map['isOfflineMode'] as bool? ?? false,
      pendingOperations: List<String>.from(map['pendingOperations'] as List),
    );
  }

  SyncState copyWith({
    DateTime? lastSyncTime,
    Map<String, int>? entityVersions,
    bool? isOfflineMode,
    List<String>? pendingOperations,
  }) {
    return SyncState(
      lastSyncTime: lastSyncTime ?? this.lastSyncTime,
      entityVersions: entityVersions ?? this.entityVersions,
      isOfflineMode: isOfflineMode ?? this.isOfflineMode,
      pendingOperations: pendingOperations ?? this.pendingOperations,
    );
  }
}

class LocalDataManager {
  final LocalStorageService _storage = LocalStorageService();
  final Map<String, dynamic> _liveCache = {};

  Future<void> init() async {
    await _storage.init();
    await _loadToCache();
  }

  Future<void> _loadToCache() async {
    _liveCache['books'] = await _storage.getBooks();
    _liveCache['notes'] = await _storage.getNotes();
    _liveCache['progress'] = await _storage.getReadingProgress();
    _liveCache['bookmarks'] = await _storage.getBookmarks();
    _liveCache['noteDeltas'] = await _storage.getNoteDeltas();
    _liveCache['readingSessions'] = await _storage.getReadingSessions();
    _liveCache['bookmarkSummaries'] = await _storage.getBookmarkSummaries();
  }

  List<Book> get books => List<Book>.from(_liveCache['books'] as List? ?? []);
  
  List<Note> get notes => List<Note>.from(_liveCache['notes'] as List? ?? []);
  
  List<ReadingProgress> get progress => List<ReadingProgress>.from(_liveCache['progress'] as List? ?? []);
  
  List<Bookmark> get bookmarks => List<Bookmark>.from(_liveCache['bookmarks'] as List? ?? []);
  
  List<ReadingSession> get readingSessions => List<ReadingSession>.from(_liveCache['readingSessions'] as List? ?? []);
  
  List<BookmarkSummary> get bookmarkSummaries => List<BookmarkSummary>.from(_liveCache['bookmarkSummaries'] as List? ?? []);

  Future<void> updateBook(Book book) async {
    final books = this.books;
    final index = books.indexWhere((b) => b.id == book.id);
    if (index >= 0) {
      books[index] = book;
    } else {
      books.add(book);
    }
    _liveCache['books'] = books;
    await _storage.saveBooks(books);
  }

  Future<void> deleteBook(String bookId) async {
    final books = this.books.where((b) => b.id != bookId).toList();
    _liveCache['books'] = books;
    await _storage.saveBooks(books);
  }

  Future<void> updateNote(Note note) async {
    final notes = this.notes;
    final index = notes.indexWhere((n) => n.id == note.id);
    if (index >= 0) {
      notes[index] = note;
    } else {
      notes.add(note);
    }
    _liveCache['notes'] = notes;
    await _storage.saveNotes(notes);
  }

  Future<void> deleteNote(String noteId) async {
    final notes = this.notes.where((n) => n.id != noteId).toList();
    _liveCache['notes'] = notes;
    await _storage.saveNotes(notes);
  }

  Future<void> updateProgress(ReadingProgress progress) async {
    final allProgress = this.progress;
    final index = allProgress.indexWhere((p) => p.bookId == progress.bookId);
    if (index >= 0) {
      allProgress[index] = progress;
    } else {
      allProgress.add(progress);
    }
    _liveCache['progress'] = allProgress;
    await _storage.saveReadingProgress(allProgress);
  }

  Future<void> updateBookmark(Bookmark bookmark) async {
    final bookmarks = this.bookmarks;
    final index = bookmarks.indexWhere((b) => b.id == bookmark.id);
    if (index >= 0) {
      bookmarks[index] = bookmark;
    } else {
      bookmarks.add(bookmark);
    }
    _liveCache['bookmarks'] = bookmarks;
    await _storage.saveBookmarks(bookmarks);
  }

  Future<void> deleteBookmark(String bookmarkId) async {
    final bookmarks = this.bookmarks.where((b) => b.id != bookmarkId).toList();
    _liveCache['bookmarks'] = bookmarks;
    await _storage.saveBookmarks(bookmarks);
  }

  ReadingProgress? getProgressForBook(String bookId) {
    try {
      return progress.firstWhere((p) => p.bookId == bookId);
    } catch (e) {
      return null;
    }
  }

  List<Note> getNotesForBook(String bookId) {
    return notes.where((n) => n.bookId == bookId).toList();
  }

  List<Bookmark> getBookmarksForBook(String bookId) {
    return bookmarks.where((b) => b.bookId == bookId).toList();
  }

  Future<SyncState> getSyncState() => _storage.getSyncState();
  
  Future<void> saveSyncState(SyncState state) => _storage.saveSyncState(state);

  Future<void> addReadingSession(ReadingSession session) async {
    final sessions = readingSessions;
    sessions.add(session);
    _liveCache['readingSessions'] = sessions;
    await _storage.saveReadingSessions(sessions);
  }

  Future<void> updateReadingSession(ReadingSession session) async {
    final sessions = readingSessions;
    final index = sessions.indexWhere((s) => s.id == session.id);
    if (index >= 0) {
      sessions[index] = session;
      _liveCache['readingSessions'] = sessions;
      await _storage.saveReadingSessions(sessions);
    }
  }

  List<ReadingSession> getSessionsForBook(String bookId) {
    return readingSessions.where((s) => s.bookId == bookId).toList();
  }

  Future<void> clearCache() async {
    _liveCache.clear();
    await _storage.clearUserData();
  }
}

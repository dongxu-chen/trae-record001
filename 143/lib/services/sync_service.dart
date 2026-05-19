import 'dart:convert';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../models/book.dart';
import '../models/note.dart';
import '../models/reading_progress.dart';
import '../models/bookmark.dart';
import 'local_storage_service.dart';

enum SyncOperationType {
  create,
  update,
  delete,
}

enum ConflictResolutionStrategy {
  lastWriteWins,
  merge,
  serverWins,
  clientWins,
}

class SyncOperation {
  final String id;
  final String entityType;
  final String entityId;
  final SyncOperationType type;
  final Map<String, dynamic> data;
  final DateTime timestamp;
  final String deviceId;
  final int vectorClock;

  SyncOperation({
    required this.id,
    required this.entityType,
    required this.entityId,
    required this.type,
    required this.data,
    required this.timestamp,
    required this.deviceId,
    required this.vectorClock,
  });

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'entityType': entityType,
      'entityId': entityId,
      'type': type.index,
      'data': data,
      'timestamp': timestamp.toIso8601String(),
      'deviceId': deviceId,
      'vectorClock': vectorClock,
    };
  }

  factory SyncOperation.fromMap(Map<String, dynamic> map) {
    return SyncOperation(
      id: map['id'] as String,
      entityType: map['entityType'] as String,
      entityId: map['entityId'] as String,
      type: SyncOperationType.values[map['type'] as int],
      data: Map<String, dynamic>.from(map['data'] as Map),
      timestamp: DateTime.parse(map['timestamp'] as String),
      deviceId: map['deviceId'] as String,
      vectorClock: map['vectorClock'] as int,
    );
  }

  String toJson() => json.encode(toMap());

  factory SyncOperation.fromJson(String source) =>
      SyncOperation.fromMap(json.decode(source) as Map<String, dynamic>);
}

class LWWRegister<T> {
  final T value;
  final DateTime timestamp;
  final String replicaId;

  LWWRegister({
    required this.value,
    required this.timestamp,
    required this.replicaId,
  });

  LWWRegister<T> merge(LWWRegister<T> other) {
    if (other.timestamp.isAfter(timestamp)) {
      return other;
    } else if (other.timestamp.isAtSameMomentAs(timestamp)) {
      return replicaId.compareTo(other.replicaId) < 0 ? this : other;
    }
    return this;
  }

  Map<String, dynamic> toMap() {
    return {
      'value': value,
      'timestamp': timestamp.toIso8601String(),
      'replicaId': replicaId,
    };
  }
}

class VectorClock {
  final Map<String, int> _clocks = {};

  int get(String replicaId) => _clocks[replicaId] ?? 0;

  void increment(String replicaId) {
    _clocks[replicaId] = get(replicaId) + 1;
  }

  void merge(VectorClock other) {
    other._clocks.forEach((key, value) {
      _clocks[key] = max(get(key), value);
    });
  }

  bool happensBefore(VectorClock other) {
    bool hasSmaller = false;
    for (final key in {..._clocks.keys, ...other._clocks.keys}) {
      final a = get(key);
      final b = other.get(key);
      if (a > b) return false;
      if (a < b) hasSmaller = true;
    }
    return hasSmaller;
  }

  bool isConcurrent(VectorClock other) {
    return !happensBefore(other) && !other.happensBefore(this);
  }

  Map<String, dynamic> toMap() => Map<String, int>.from(_clocks);

  factory VectorClock.fromMap(Map<String, dynamic> map) {
    final vc = VectorClock();
    map.forEach((key, value) {
      vc._clocks[key] = value as int;
    });
    return vc;
  }
}

int max(int a, int b) => a > b ? a : b;

class SyncService {
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;
  final LocalDataManager _localManager = LocalDataManager();
  final ConflictResolutionStrategy _defaultStrategy =
      ConflictResolutionStrategy.lastWriteWins;
  final String _deviceId;
  final VectorClock _vectorClock = VectorClock();
  bool _isSyncing = false;

  SyncService(this._deviceId);

  Future<void> init() async {
    await _localManager.init();
  }

  bool get isSyncing => _isSyncing;

  Future<void> queueOperation(SyncOperation operation) async {
    final syncState = await _localManager.getSyncState();
    final pending = List<String>.from(syncState.pendingOperations);
    pending.add(operation.toJson());
    await _localManager.saveSyncState(
      syncState.copyWith(pendingOperations: pending),
    );
  }

  Future<List<SyncOperation>> getPendingOperations() async {
    final syncState = await _localManager.getSyncState();
    return syncState.pendingOperations
        .map((json) => SyncOperation.fromJson(json))
        .toList();
  }

  Future<void> clearPendingOperations(List<String> operationIds) async {
    final syncState = await _localManager.getSyncState();
    final pending = syncState.pendingOperations.where((json) {
      final op = SyncOperation.fromJson(json);
      return !operationIds.contains(op.id);
    }).toList();
    await _localManager.saveSyncState(
      syncState.copyWith(pendingOperations: pending),
    );
  }

  Future<void> sync({
    ConflictResolutionStrategy? strategy,
    void Function(double progress)? onProgress,
  }) async {
    if (_isSyncing) return;
    _isSyncing = true;

    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user == null) throw Exception('Not authenticated');

      strategy ??= _defaultStrategy;

      final pendingOps = await getPendingOperations();
      final totalOps = pendingOps.length;
      var completedOps = 0;

      for (final op in pendingOps) {
        await _syncOperation(op, user.uid, strategy);
        completedOps++;
        onProgress?.call(completedOps / totalOps);
      }

      await _pullFromServer(user.uid);

      await _localManager.saveSyncState(
        (await _localManager.getSyncState()).copyWith(
          lastSyncTime: DateTime.now(),
        ),
      );

      await clearPendingOperations(pendingOps.map((o) => o.id).toList());
    } finally {
      _isSyncing = false;
    }
  }

  Future<void> _syncOperation(
    SyncOperation operation,
    String userId,
    ConflictResolutionStrategy strategy,
  ) async {
    final collection = _getCollectionForType(operation.entityType);
    final docRef = _firestore.collection(collection).doc(operation.entityId);

    try {
      await _firestore.runTransaction((transaction) async {
        final doc = await transaction.get(docRef);
        final serverData = doc.data();

        if (serverData == null || strategy == ConflictResolutionStrategy.clientWins) {
          if (operation.type == SyncOperationType.delete) {
            transaction.delete(docRef);
          } else {
            transaction.set(docRef, {
              ...operation.data,
              'userId': userId,
              'lastModified': operation.timestamp.toIso8601String(),
              'lastModifiedBy': _deviceId,
              'vectorClock': _vectorClock.toMap(),
            });
          }
        } else if (strategy == ConflictResolutionStrategy.lastWriteWins) {
          final serverTimestamp = DateTime.parse(
            serverData['lastModified'] as String? ??
                DateTime.fromMillisecondsSinceEpoch(0).toIso8601String(),
          );

          if (operation.timestamp.isAfter(serverTimestamp)) {
            if (operation.type == SyncOperationType.delete) {
              transaction.delete(docRef);
            } else {
              transaction.set(docRef, {
                ...operation.data,
                'userId': userId,
                'lastModified': operation.timestamp.toIso8601String(),
                'lastModifiedBy': _deviceId,
                'vectorClock': _vectorClock.toMap(),
              }, SetOptions(merge: true));
            }
          }
        } else if (strategy == ConflictResolutionStrategy.merge) {
          await _mergeOperation(transaction, docRef, operation, serverData, userId);
        }
      });
    } catch (e) {
      rethrow;
    }
  }

  Future<void> _mergeOperation(
    Transaction transaction,
    DocumentReference docRef,
    SyncOperation operation,
    Map<String, dynamic> serverData,
    String userId,
  ) async {
    final serverVc = VectorClock.fromMap(
      Map<String, dynamic>.from(serverData['vectorClock'] as Map? ?? {}),
    );

    if (_vectorClock.happensBefore(serverVc)) {
      return;
    } else if (_vectorClock.isConcurrent(serverVc)) {
      final mergedData = await _resolveConcurrentEdit(operation.data, serverData);
      transaction.set(docRef, {
        ...mergedData,
        'userId': userId,
        'lastModified': DateTime.now().toIso8601String(),
        'lastModifiedBy': _deviceId,
        'vectorClock': _vectorClock.toMap(),
      }, SetOptions(merge: true));
    } else {
      transaction.set(docRef, {
        ...operation.data,
        'userId': userId,
        'lastModified': operation.timestamp.toIso8601String(),
        'lastModifiedBy': _deviceId,
        'vectorClock': _vectorClock.toMap(),
      }, SetOptions(merge: true));
    }
  }

  Future<Map<String, dynamic>> _resolveConcurrentEdit(
    Map<String, dynamic> clientData,
    Map<String, dynamic> serverData,
  ) async {
    final merged = Map<String, dynamic>.from(serverData);
    
    clientData.forEach((key, value) {
      if (!merged.containsKey(key)) {
        merged[key] = value;
      } else if (key == 'content' || key == 'excerpt') {
        merged[key] = _mergeText(
          merged[key] as String? ?? '',
          value as String? ?? '',
        );
      }
    });

    return merged;
  }

  String _mergeText(String a, String b) {
    final setA = a.split('\n').toSet();
    final setB = b.split('\n').toSet();
    final merged = <String>{}..addAll(setA)..addAll(setB);
    return merged.join('\n');
  }

  Future<void> _pullFromServer(String userId) async {
    final lastSync = (await _localManager.getSyncState()).lastSyncTime;
    const collections = ['books', 'notes', 'readingProgress', 'bookmarks'];

    for (final collection in collections) {
      final snapshot = await _firestore
          .collection(collection)
          .where('userId', isEqualTo: userId)
          .where('lastModified', isGreaterThan: lastSync.toIso8601String())
          .get();

      for (final doc in snapshot.docs) {
        await _applyServerChange(collection, doc.data());
      }
    }
  }

  Future<void> _applyServerChange(
    String collection,
    Map<String, dynamic> data,
  ) async {
    switch (collection) {
      case 'books':
        await _localManager.updateBook(Book.fromMap(data));
        break;
      case 'notes':
        await _localManager.updateNote(Note.fromMap(data));
        break;
      case 'readingProgress':
        await _localManager.updateProgress(ReadingProgress.fromMap(data));
        break;
      case 'bookmarks':
        await _localManager.updateBookmark(Bookmark.fromMap(data));
        break;
    }
  }

  String _getCollectionForType(String entityType) {
    switch (entityType) {
      case 'book':
        return 'books';
      case 'note':
        return 'notes';
      case 'progress':
        return 'readingProgress';
      case 'bookmark':
        return 'bookmarks';
      default:
        throw ArgumentError('Unknown entity type: $entityType');
    }
  }

  Future<void> createBook(Book book) async {
    _vectorClock.increment(_deviceId);
    final operation = SyncOperation(
      id: 'op_${DateTime.now().millisecondsSinceEpoch}',
      entityType: 'book',
      entityId: book.id,
      type: SyncOperationType.create,
      data: book.toMap(),
      timestamp: DateTime.now(),
      deviceId: _deviceId,
      vectorClock: _vectorClock.get(_deviceId),
    );
    await _localManager.updateBook(book);
    await queueOperation(operation);
  }

  Future<void> updateBook(Book book) async {
    _vectorClock.increment(_deviceId);
    final operation = SyncOperation(
      id: 'op_${DateTime.now().millisecondsSinceEpoch}',
      entityType: 'book',
      entityId: book.id,
      type: SyncOperationType.update,
      data: book.toMap(),
      timestamp: DateTime.now(),
      deviceId: _deviceId,
      vectorClock: _vectorClock.get(_deviceId),
    );
    await _localManager.updateBook(book);
    await queueOperation(operation);
  }

  Future<void> deleteBook(String bookId) async {
    _vectorClock.increment(_deviceId);
    final operation = SyncOperation(
      id: 'op_${DateTime.now().millisecondsSinceEpoch}',
      entityType: 'book',
      entityId: bookId,
      type: SyncOperationType.delete,
      data: {'id': bookId},
      timestamp: DateTime.now(),
      deviceId: _deviceId,
      vectorClock: _vectorClock.get(_deviceId),
    );
    await _localManager.deleteBook(bookId);
    await queueOperation(operation);
  }

  Future<void> createNote(Note note) async {
    _vectorClock.increment(_deviceId);
    final operation = SyncOperation(
      id: 'op_${DateTime.now().millisecondsSinceEpoch}',
      entityType: 'note',
      entityId: note.id,
      type: SyncOperationType.create,
      data: note.toMap(),
      timestamp: DateTime.now(),
      deviceId: _deviceId,
      vectorClock: _vectorClock.get(_deviceId),
    );
    await _localManager.updateNote(note);
    await queueOperation(operation);
  }

  Future<void> updateNote(Note note) async {
    _vectorClock.increment(_deviceId);
    final operation = SyncOperation(
      id: 'op_${DateTime.now().millisecondsSinceEpoch}',
      entityType: 'note',
      entityId: note.id,
      type: SyncOperationType.update,
      data: note.toMap(),
      timestamp: DateTime.now(),
      deviceId: _deviceId,
      vectorClock: _vectorClock.get(_deviceId),
    );
    await _localManager.updateNote(note);
    await queueOperation(operation);
  }

  Future<void> deleteNote(String noteId) async {
    _vectorClock.increment(_deviceId);
    final operation = SyncOperation(
      id: 'op_${DateTime.now().millisecondsSinceEpoch}',
      entityType: 'note',
      entityId: noteId,
      type: SyncOperationType.delete,
      data: {'id': noteId},
      timestamp: DateTime.now(),
      deviceId: _deviceId,
      vectorClock: _vectorClock.get(_deviceId),
    );
    await _localManager.deleteNote(noteId);
    await queueOperation(operation);
  }

  Future<void> updateProgress(ReadingProgress progress) async {
    _vectorClock.increment(_deviceId);
    final operation = SyncOperation(
      id: 'op_${DateTime.now().millisecondsSinceEpoch}',
      entityType: 'progress',
      entityId: progress.id,
      type: SyncOperationType.update,
      data: progress.toMap(),
      timestamp: DateTime.now(),
      deviceId: _deviceId,
      vectorClock: _vectorClock.get(_deviceId),
    );
    await _localManager.updateProgress(progress);
    await queueOperation(operation);
  }

  Future<void> createBookmark(Bookmark bookmark) async {
    _vectorClock.increment(_deviceId);
    final operation = SyncOperation(
      id: 'op_${DateTime.now().millisecondsSinceEpoch}',
      entityType: 'bookmark',
      entityId: bookmark.id,
      type: SyncOperationType.create,
      data: bookmark.toMap(),
      timestamp: DateTime.now(),
      deviceId: _deviceId,
      vectorClock: _vectorClock.get(_deviceId),
    );
    await _localManager.updateBookmark(bookmark);
    await queueOperation(operation);
  }

  Future<void> updateBookmark(Bookmark bookmark) async {
    _vectorClock.increment(_deviceId);
    final operation = SyncOperation(
      id: 'op_${DateTime.now().millisecondsSinceEpoch}',
      entityType: 'bookmark',
      entityId: bookmark.id,
      type: SyncOperationType.update,
      data: bookmark.toMap(),
      timestamp: DateTime.now(),
      deviceId: _deviceId,
      vectorClock: _vectorClock.get(_deviceId),
    );
    await _localManager.updateBookmark(bookmark);
    await queueOperation(operation);
  }

  Future<void> deleteBookmark(String bookmarkId) async {
    _vectorClock.increment(_deviceId);
    final operation = SyncOperation(
      id: 'op_${DateTime.now().millisecondsSinceEpoch}',
      entityType: 'bookmark',
      entityId: bookmarkId,
      type: SyncOperationType.delete,
      data: {'id': bookmarkId},
      timestamp: DateTime.now(),
      deviceId: _deviceId,
      vectorClock: _vectorClock.get(_deviceId),
    );
    await _localManager.deleteBookmark(bookmarkId);
    await queueOperation(operation);
  }

  Future<void> forceFullSync() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) throw Exception('Not authenticated');

    await _localManager.clearCache();
    await _pullFromServer(user.uid);
  }

  List<Book> getLocalBooks() => _localManager.books;
  List<Note> getLocalNotes() => _localManager.notes;
  List<ReadingProgress> getLocalProgress() => _localManager.progress;
  List<Bookmark> getLocalBookmarks() => _localManager.bookmarks;
}

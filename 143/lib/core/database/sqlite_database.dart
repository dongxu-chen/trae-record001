import 'dart:async';
import 'dart:convert';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import '../encryption/crypto_service.dart';
import '../architecture.dart';

class SQLiteDatabase {
  static Database? _database;
  final CryptoService _crypto = CryptoService();
  final String deviceId;
  Uint8List? _encryptionKey;

  SQLiteDatabase(this.deviceId);

  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDatabase();
    return _database!;
  }

  void setEncryptionKey(Uint8List key) {
    _encryptionKey = key;
  }

  Future<Database> _initDatabase() async {
    final path = join(await getDatabasesPath(), 'app_data_$deviceId.db');
    return openDatabase(
      path,
      version: 1,
      onCreate: _onCreate,
      onConfigure: _onConfigure,
    );
  }

  Future<void> _onConfigure(Database db) async {
    await db.execute('PRAGMA foreign_keys = ON');
    await db.execute('PRAGMA journal_mode = WAL');
    await db.execute('PRAGMA synchronous = NORMAL');
  }

  Future<void> _onCreate(Database db, int version) async {
    await db.execute('''
      CREATE TABLE documents (
        id TEXT PRIMARY KEY,
        collection_id TEXT NOT NULL,
        encrypted_data TEXT NOT NULL,
        version INTEGER NOT NULL DEFAULT 1,
        vector_clock TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        deleted INTEGER NOT NULL DEFAULT 0,
        synced INTEGER NOT NULL DEFAULT 0
      )
    ''');

    await db.execute('''
      CREATE TABLE operation_logs (
        id TEXT PRIMARY KEY,
        collection_id TEXT NOT NULL,
        document_id TEXT NOT NULL,
        operation TEXT NOT NULL,
        encrypted_data TEXT NOT NULL,
        version INTEGER NOT NULL,
        vector_clock TEXT NOT NULL,
        device_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        signature TEXT NOT NULL,
        nonce TEXT NOT NULL,
        synced INTEGER NOT NULL DEFAULT 0
      )
    ''');

    await db.execute('''
      CREATE TABLE sync_state (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
      )
    ''');

    await db.execute('CREATE INDEX idx_collection ON documents(collection_id)');
    await db.execute('CREATE INDEX idx_synced ON documents(synced)');
    await db.execute('CREATE INDEX idx_unsynced_ops ON operation_logs(synced)');
  }

  Future<void> insertDocument(String collectionId, String documentId, Map<String, dynamic> data) async {
    final db = await database;
    final vectorClock = VectorClock()..increment(deviceId);
    final now = DateTime.now().toIso8601String();

    final encryptedData = _encryptData(data);

    await db.insert(
      'documents',
      {
        'id': documentId,
        'collection_id': collectionId,
        'encrypted_data': json.encode(encryptedData.toJson()),
        'version': 1,
        'vector_clock': vectorClock.encode(),
        'created_at': now,
        'updated_at': now,
        'deleted': 0,
        'synced': 0,
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );

    await _appendOperationLog(
      collectionId,
      documentId,
      SyncOperation.create,
      data,
      1,
      vectorClock,
    );
  }

  Future<void> updateDocument(String collectionId, String documentId, Map<String, dynamic> data) async {
    final db = await database;

    final currentDoc = await getDocument(collectionId, documentId);
    final currentVersion = currentDoc?['version'] as int? ?? 0;
    final currentVectorClock = currentDoc != null
        ? VectorClock.decode(currentDoc['vector_clock'] as String)
        : VectorClock();

    currentVectorClock.increment(deviceId);
    final newVersion = currentVersion + 1;
    final now = DateTime.now().toIso8601String();

    final encryptedData = _encryptData(data);

    await db.update(
      'documents',
      {
        'encrypted_data': json.encode(encryptedData.toJson()),
        'version': newVersion,
        'vector_clock': currentVectorClock.encode(),
        'updated_at': now,
        'synced': 0,
      },
      where: 'id = ? AND collection_id = ?',
      whereArgs: [documentId, collectionId],
    );

    await _appendOperationLog(
      collectionId,
      documentId,
      SyncOperation.update,
      data,
      newVersion,
      currentVectorClock,
    );
  }

  Future<void> deleteDocument(String collectionId, String documentId) async {
    final db = await database;

    final currentDoc = await getDocument(collectionId, documentId);
    final currentVersion = currentDoc?['version'] as int? ?? 0;
    final currentVectorClock = currentDoc != null
        ? VectorClock.decode(currentDoc['vector_clock'] as String)
        : VectorClock();

    currentVectorClock.increment(deviceId);
    final newVersion = currentVersion + 1;
    final now = DateTime.now().toIso8601String();

    await db.update(
      'documents',
      {
        'deleted': 1,
        'version': newVersion,
        'vector_clock': currentVectorClock.encode(),
        'updated_at': now,
        'synced': 0,
      },
      where: 'id = ? AND collection_id = ?',
      whereArgs: [documentId, collectionId],
    );

    await _appendOperationLog(
      collectionId,
      documentId,
      SyncOperation.delete,
      {},
      newVersion,
      currentVectorClock,
    );
  }

  Future<Map<String, dynamic>?> getDocument(String collectionId, String documentId) async {
    final db = await database;
    final results = await db.query(
      'documents',
      where: 'id = ? AND collection_id = ? AND deleted = 0',
      whereArgs: [documentId, collectionId],
      limit: 1,
    );

    if (results.isEmpty) return null;

    final row = results.first;
    final encryptedData = EncryptedData.fromJson(
      json.decode(row['encrypted_data'] as String) as Map<String, dynamic>,
    );

    return {
      'id': row['id'],
      'collection_id': row['collection_id'],
      'data': _decryptData(encryptedData),
      'version': row['version'],
      'vector_clock': row['vector_clock'],
      'created_at': row['created_at'],
      'updated_at': row['updated_at'],
    };
  }

  Future<List<Map<String, dynamic>>> getCollection(String collectionId) async {
    final db = await database;
    final results = await db.query(
      'documents',
      where: 'collection_id = ? AND deleted = 0',
      whereArgs: [collectionId],
    );

    return Future.wait(results.map((row) async {
      final encryptedData = EncryptedData.fromJson(
        json.decode(row['encrypted_data'] as String) as Map<String, dynamic>,
      );
      return {
        'id': row['id'],
        'data': _decryptData(encryptedData),
        'version': row['version'],
        'vector_clock': row['vector_clock'],
        'created_at': row['created_at'],
        'updated_at': row['updated_at'],
      };
    }));
  }

  Future<List<SyncMessage>> getUnsyncedOperations() async {
    final db = await database;
    final results = await db.query(
      'operation_logs',
      where: 'synced = 0',
      orderBy: 'timestamp ASC',
    );

    return results.map((row) => SyncMessage(
      id: row['id'] as String,
      collectionId: row['collection_id'] as String,
      documentId: row['document_id'] as String,
      operation: SyncOperation.values.firstWhere((e) => e.name == row['operation']),
      encryptedData: json.decode(row['encrypted_data'] as String) as Map<String, dynamic>,
      version: row['version'] as int,
      vectorClock: row['vector_clock'] as String,
      deviceId: row['device_id'] as String,
      timestamp: DateTime.parse(row['timestamp'] as String),
      signature: row['signature'] as String,
      nonce: row['nonce'] as String,
    )).toList();
  }

  Future<void> markOperationSynced(String operationId) async {
    final db = await database;
    await db.update(
      'operation_logs',
      {'synced': 1},
      where: 'id = ?',
      whereArgs: [operationId],
    );
  }

  Future<void> markDocumentSynced(String collectionId, String documentId) async {
    final db = await database;
    await db.update(
      'documents',
      {'synced': 1},
      where: 'id = ? AND collection_id = ?',
      whereArgs: [documentId, collectionId],
    );
  }

  Future<void> applyRemoteOperation(SyncMessage message) async {
    final db = await database;

    final currentDoc = await getDocument(message.collectionId, message.documentId);
    final currentVectorClock = currentDoc != null
        ? VectorClock.decode(currentDoc['vector_clock'] as String)
        : VectorClock();

    final remoteVectorClock = VectorClock.decode(message.vectorClock);

    if (remoteVectorClock.happensBefore(currentVectorClock)) {
      return;
    }

    if (message.operation == SyncOperation.delete) {
      await deleteDocument(message.collectionId, message.documentId);
    } else {
      final encryptedData = EncryptedData.fromJson(message.encryptedData);
      final data = _decryptData(encryptedData);

      if (currentDoc == null) {
        await db.insert(
          'documents',
          {
            'id': message.documentId,
            'collection_id': message.collectionId,
            'encrypted_data': json.encode(message.encryptedData),
            'version': message.version,
            'vector_clock': message.vectorClock,
            'created_at': message.timestamp.toIso8601String(),
            'updated_at': message.timestamp.toIso8601String(),
            'deleted': 0,
            'synced': 1,
          },
          conflictAlgorithm: ConflictAlgorithm.replace,
        );
      } else {
        final mergedClock = currentVectorClock.merge(remoteVectorClock);
        await db.update(
          'documents',
          {
            'encrypted_data': json.encode(message.encryptedData),
            'version': message.version,
            'vector_clock': mergedClock.encode(),
            'updated_at': message.timestamp.toIso8601String(),
            'synced': 1,
          },
          where: 'id = ? AND collection_id = ?',
          whereArgs: [message.documentId, message.collectionId],
        );
      }
    }
  }

  Future<void> _appendOperationLog(
    String collectionId,
    String documentId,
    SyncOperation operation,
    Map<String, dynamic> data,
    int version,
    VectorClock vectorClock,
  ) async {
    final db = await database;
    final nonce = _crypto.generateNonceString();
    final timestamp = DateTime.now();

    final encryptedData = _encryptData(data);
    final signatureData = '$collectionId$documentId${operation.name}$version$nonce';
    final signature = _crypto.generateHMAC(signatureData, _encryptionKey!);

    await db.insert(
      'operation_logs',
      {
        'id': '${timestamp.millisecondsSinceEpoch}_${deviceId}_$nonce',
        'collection_id': collectionId,
        'document_id': documentId,
        'operation': operation.name,
        'encrypted_data': json.encode(encryptedData.toJson()),
        'version': version,
        'vector_clock': vectorClock.encode(),
        'device_id': deviceId,
        'timestamp': timestamp.toIso8601String(),
        'signature': signature,
        'nonce': nonce,
        'synced': 0,
      },
    );
  }

  EncryptedData _encryptData(Map<String, dynamic> data) {
    if (_encryptionKey == null) {
      throw StateError('Encryption key not set');
    }
    return _crypto.encrypt(data, _encryptionKey!);
  }

  Map<String, dynamic> _decryptData(EncryptedData encrypted) {
    if (_encryptionKey == null) {
      throw StateError('Encryption key not set');
    }
    return _crypto.decrypt(encrypted, _encryptionKey!);
  }

  Future<void> saveSyncState(String key, String value) async {
    final db = await database;
    await db.insert(
      'sync_state',
      {'key': key, 'value': value},
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<String?> getSyncState(String key) async {
    final db = await database;
    final results = await db.query(
      'sync_state',
      where: 'key = ?',
      whereArgs: [key],
      limit: 1,
    );
    return results.isNotEmpty ? results.first['value'] as String : null;
  }

  Future<void> close() async {
    await _database?.close();
    _database = null;
  }
}

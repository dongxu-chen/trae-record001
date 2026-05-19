import 'dart:convert';
import 'dart:typed_data';
import 'package:appwrite/appwrite.dart';
import 'package:appwrite/models.dart' as models;
import '../encryption/crypto_service.dart';
import '../database/sqlite_database.dart';
import '../architecture.dart';

class AppwriteSyncClient {
  final Client _client;
  final Databases _databases;
  final Storage _storage;
  final String _databaseId;
  final String _deviceId;
  final Uint8List _encryptionKey;
  final CryptoService _crypto = CryptoService();
  final SQLiteDatabase _localDb;
  final Map<String, Set<String>> _syncedDocuments = {};
  bool _isSyncing = false;

  AppwriteSyncClient({
    required String endpoint,
    required String projectId,
    required String databaseId,
    required String deviceId,
    required Uint8List encryptionKey,
    required SQLiteDatabase localDb,
  }) : _client = Client(endPoint: endpoint, project: projectId),
       _databaseId = databaseId,
       _deviceId = deviceId,
       _encryptionKey = encryptionKey,
       _localDb = localDb,
       _databases = Databases(Client(endPoint: endpoint, project: projectId)),
       _storage = Storage(Client(endPoint: endpoint, project: projectId)) {
    _setSession();
  }

  void _setSession() {
    _client.setSelfSigned();
  }

  Future<models.User?> getCurrentUser() async {
    try {
      final account = Account(_client);
      return await account.get();
    } catch (e) {
      return null;
    }
  }

  Future<models.User?> login(String email, String password) async {
    try {
      final account = Account(_client);
      final session = await account.createEmailPasswordSession(
        email: email,
        password: password,
      );
      return await account.get();
    } catch (e) {
      rethrow;
    }
  }

  Future<void> logout() async {
    try {
      final account = Account(_client);
      await account.deleteSession(sessionId: 'current');
    } catch (e) {
      print('Logout error: $e');
    }
  }

  Future<models.User?> register(String email, String password, String name) async {
    try {
      final account = Account(_client);
      await account.create(
        userId: ID.unique(),
        email: email,
        password: password,
        name: name,
      );
      return await login(email, password);
    } catch (e) {
      rethrow;
    }
  }

  Future<List<String>> getCollections() async {
    try {
      final collections = await _databases.listCollections(databaseId: _databaseId);
      return collections.collections.map((c) => c.$id).toList();
    } catch (e) {
      print('Error getting collections: $e');
      return [];
    }
  }

  Future<models.DocumentList> listDocuments(String collectionId, {
    List<String>? queries,
  }) async {
    return _databases.listDocuments(
      databaseId: _databaseId,
      collectionId: collectionId,
      queries: queries,
    );
  }

  Future<void> uploadEncryptedDocument(String collectionId, Map<String, dynamic> data) async {
    final encrypted = _crypto.encrypt(data, _encryptionKey);
    final documentData = {
      'encrypted_data': base64.encode(Uint8List.fromList(utf8.encode(json.encode(encrypted.toJson())))),
      'device_id': _deviceId,
      'vector_clock': VectorClock().encode(),
      'version': 1,
      'updated_at': DateTime.now().toIso8601String(),
    };

    await _databases.createDocument(
      databaseId: _databaseId,
      collectionId: collectionId,
      documentId: ID.unique(),
      data: documentData,
    );
  }

  Future<Map<String, dynamic>?> downloadDecryptedDocument(String collectionId, String documentId) async {
    try {
      final doc = await _databases.getDocument(
        databaseId: _databaseId,
        collectionId: collectionId,
        documentId: documentId,
      );

      final encryptedBase64 = doc.data['encrypted_data'] as String;
      final encryptedJson = utf8.decode(base64.decode(encryptedBase64));
      final encryptedData = EncryptedData.fromJson(json.decode(encryptedJson) as Map<String, dynamic>);

      return _crypto.decrypt(encryptedData, _encryptionKey);
    } catch (e) {
      print('Error downloading document: $e');
      return null;
    }
  }

  Future<void> syncLocalToRemote() async {
    if (_isSyncing) return;
    _isSyncing = true;

    try {
      final unsyncedOps = await _localDb.getUnsyncedOperations();

      for (final op in unsyncedOps) {
        try {
          await _uploadOperation(op);
          await _localDb.markOperationSynced(op.id);
          _syncedDocuments.putIfAbsent(op.collectionId, () => {}).add(op.documentId);
        } catch (e) {
          print('Error syncing document ${op.documentId}: $e');
        }
      }
    } finally {
      _isSyncing = false;
    }
  }

  Future<void> _uploadOperation(SyncMessage operation) async {
    final encryptedBase64 = base64.encode(
      Uint8List.fromList(utf8.encode(json.encode(operation.encryptedData))),
    );

    final documentData = {
      'encrypted_data': encryptedBase64,
      'device_id': _deviceId,
      'vector_clock': operation.vectorClock,
      'version': operation.version,
      'updated_at': operation.timestamp.toIso8601String(),
    };

    if (operation.operation == SyncOperation.delete) {
      try {
        await _databases.deleteDocument(
          databaseId: _databaseId,
          collectionId: operation.collectionId,
          documentId: operation.documentId,
        );
      } catch (e) {
        print('Document may not exist, skipping delete: $e');
      }
    } else {
      try {
        await _databases.getDocument(
          databaseId: _databaseId,
          collectionId: operation.collectionId,
          documentId: operation.documentId,
        );

        await _databases.updateDocument(
          databaseId: _databaseId,
          collectionId: operation.collectionId,
          documentId: operation.documentId,
          data: documentData,
        );
      } catch (e) {
        await _databases.createDocument(
          databaseId: _databaseId,
          collectionId: operation.collectionId,
          documentId: operation.documentId,
          data: documentData,
        );
      }
    }
  }

  Future<void> syncRemoteToLocal() async {
    if (_isSyncing) return;
    _isSyncing = true;

    try {
      final collections = await getCollections();

      for (final collectionId in collections) {
        final lastSync = await _localDb.getSyncState('last_sync_$collectionId');
        final queries = lastSync != null
            ? [Query.greaterThan('updated_at', lastSync)]
            : null;

        final docs = await listDocuments(collectionId, queries: queries);

        for (final doc in docs.documents) {
          await _downloadAndDecryptDocument(collectionId, doc.$id, doc.data);
        }

        await _localDb.saveSyncState(
          'last_sync_$collectionId',
          DateTime.now().toIso8601String(),
        );
      }
    } catch (e) {
      print('Error syncing remote to local: $e');
    } finally {
      _isSyncing = false;
    }
  }

  Future<void> _downloadAndDecryptDocument(String collectionId, String documentId, Map<String, dynamic> remoteData) async {
    try {
      final encryptedBase64 = remoteData['encrypted_data'] as String;
      final encryptedJson = utf8.decode(base64.decode(encryptedBase64));
      final encryptedMap = json.decode(encryptedJson) as Map<String, dynamic>;
      final encryptedData = EncryptedData.fromJson(encryptedMap);
      final decryptedData = _crypto.decrypt(encryptedData, _encryptionKey);

      final remoteVectorClock = remoteData['vector_clock'] as String;
      final remoteVersion = remoteData['version'] as int;
      final remoteTimestamp = remoteData['updated_at'] as String;

      final localDoc = await _localDb.getDocument(collectionId, documentId);

      if (localDoc != null) {
        final localClock = VectorClock.decode(localDoc['vector_clock'] as String);
        final remoteClock = VectorClock.decode(remoteVectorClock);

        if (remoteClock.happensBefore(localClock)) {
          return;
        }

        if (localClock.isConcurrent(remoteClock)) {
          final mergedClock = localClock.merge(remoteClock);
          mergedClock.increment(_deviceId);

          await _localDb.updateDocument(collectionId, documentId, decryptedData);
        } else {
          await _localDb.updateDocument(collectionId, documentId, decryptedData);
        }
      } else {
        await _localDb.insertDocument(collectionId, documentId, decryptedData);
      }

      await _localDb.markDocumentSynced(collectionId, documentId);
    } catch (e) {
      print('Error processing document $documentId: $e');
    }
  }

  Future<void> fullSync() async {
    await syncRemoteToLocal();
    await syncLocalToRemote();
  }

  Future<String> uploadFile(String bucketId, Uint8List fileData, String fileName) async {
    final encryptedFile = _crypto.encrypt({'file': base64.encode(fileData)}, _encryptionKey);
    final encryptedBytes = utf8.encode(json.encode(encryptedFile.toJson()));

    final file = await _storage.createFile(
      bucketId: bucketId,
      fileId: ID.unique(),
      file: InputFile.fromBytes(
        bytes: Uint8List.fromList(encryptedBytes),
        filename: '$fileName.enc',
      ),
    );

    return file.$id;
  }

  Future<Uint8List?> downloadFile(String bucketId, String fileId) async {
    try {
      final file = await _storage.getFileDownload(
        bucketId: bucketId,
        fileId: fileId,
      );

      final encryptedJson = utf8.decode(file);
      final encryptedData = EncryptedData.fromJson(json.decode(encryptedJson) as Map<String, dynamic>);
      final decrypted = _crypto.decrypt(encryptedData, _encryptionKey);

      return base64.decode(decrypted['file'] as String);
    } catch (e) {
      print('Error downloading file: $e');
      return null;
    }
  }

  Client get rawClient => _client;
  Databases get databases => _databases;
  Storage get storage => _storage;
}

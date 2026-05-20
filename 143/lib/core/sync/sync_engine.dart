import 'dart:async';
import '../architecture.dart';
import '../database/sqlite_database.dart';
import 'mqtt_sync_client.dart';
import '../encryption/crypto_service.dart';

class SyncEngine {
  final SQLiteDatabase _db;
  final MQTTSyncClient _mqtt;
  final String _deviceId;
  final CryptoService _crypto = CryptoService();
  final ConflictStrategy _conflictStrategy;
  final _statusController = StreamController<SyncStatus>.broadcast();
  final _syncProgressController = StreamController<double>.broadcast();
  StreamSubscription<SyncMessage>? _messageSubscription;
  StreamSubscription<SyncStatus>? _connectionSubscription;
  bool _isSyncing = false;
  DateTime? _lastSyncTime;

  Stream<SyncStatus> get statusStream => _statusController.stream;
  Stream<double> get progressStream => _syncProgressController.stream;
  DateTime? get lastSyncTime => _lastSyncTime;
  bool get isSyncing => _isSyncing;
  bool get isConnected => _mqtt.isConnected;

  SyncEngine({
    required SQLiteDatabase db,
    required MQTTSyncClient mqtt,
    required String deviceId,
    ConflictStrategy conflictStrategy = ConflictStrategy.lastWriteWins,
  }) : _db = db, _mqtt = mqtt, _deviceId = deviceId, _conflictStrategy = conflictStrategy;

  Future<void> initialize() async {
    _connectionSubscription = _mqtt.connectionStream.listen(_handleConnectionChange);
    _messageSubscription = _mqtt.messageStream.listen(_handleIncomingMessage);
    await _connect();
  }

  Future<void> _connect() async {
    try {
      _statusController.add(SyncStatus.connecting);
      await _mqtt.connect();
    } catch (e) {
      _statusController.add(SyncStatus.offline);
      rethrow;
    }
  }

  void _handleConnectionChange(SyncStatus status) {
    _statusController.add(status);

    if (status == SyncStatus.online) {
      syncPendingOperations();
    }
  }

  void _handleIncomingMessage(SyncMessage message) {
    if (message.deviceId == _deviceId) return;

    _applyRemoteOperation(message);
  }

  Future<void> syncPendingOperations() async {
    if (_isSyncing || !_mqtt.isConnected) return;

    try {
      _isSyncing = true;
      _statusController.add(SyncStatus.syncing);

      final pendingOps = await _db.getUnsyncedOperations();

      if (pendingOps.isEmpty) {
        _isSyncing = false;
        _statusController.add(SyncStatus.online);
        return;
      }

      await _mqtt.publishBatch(
        pendingOps,
        onProgress: (current, total) {
          _syncProgressController.add(current / total);
        },
      );

      for (final op in pendingOps) {
        await _db.markOperationSynced(op.id);
      }

      _lastSyncTime = DateTime.now();
    } catch (e) {
      print('Sync error: $e');
    } finally {
      _isSyncing = false;
      _statusController.add(SyncStatus.online);
    }
  }

  Future<void> _applyRemoteOperation(SyncMessage message) async {
    final currentDoc = await _db.getDocument(message.collectionId, message.documentId);

    if (currentDoc != null) {
      final currentClock = VectorClock.decode(currentDoc['vector_clock'] as String);
      final remoteClock = VectorClock.decode(message.vectorClock);

      if (remoteClock.happensBefore(currentClock)) {
        return;
      }

      if (currentClock.isConcurrent(remoteClock)) {
        final resolved = await _resolveConflict(currentDoc, message);
        if (resolved != null) {
          await _db.applyRemoteOperation(resolved);
        }
        return;
      }
    }

    await _db.applyRemoteOperation(message);
  }

  Future<SyncMessage?> _resolveConflict(Map<String, dynamic> local, SyncMessage remote) async {
    switch (_conflictStrategy) {
      case ConflictStrategy.lastWriteWins:
        return remote;

      case ConflictStrategy.clientWins:
        return null;

      case ConflictStrategy.merge:
        return await _mergeDocuments(local, remote);

      case ConflictStrategy.manual:
        return null;

      default:
        return remote;
    }
  }

  Future<SyncMessage> _mergeDocuments(Map<String, dynamic> local, SyncMessage remote) async {
    final localData = Map<String, dynamic>.from(local['data'] as Map);
    final localEncrypted = EncryptedData.fromJson(Map<String, dynamic>.from(local['encrypted_data'] as Map));
    final remoteEncrypted = EncryptedData.fromJson(remote.encryptedData);

    final key = (await _crypto.deriveKey('temp', 'salt', iterations: 1));
    final remoteData = _crypto.decrypt(remoteEncrypted, key);

    final mergedData = <String, dynamic>{...localData, ...remoteData};

    final localClock = VectorClock.decode(local['vector_clock'] as String);
    final remoteClock = VectorClock.decode(remote.vectorClock);
    final mergedClock = localClock.merge(remoteClock);
    mergedClock.increment(_deviceId);

    final mergedEncrypted = _crypto.encrypt(mergedData, key);

    return SyncMessage(
      id: remote.id,
      collectionId: remote.collectionId,
      documentId: remote.documentId,
      operation: SyncOperation.merge,
      encryptedData: mergedEncrypted.toJson(),
      version: (local['version'] as int) + 1,
      vectorClock: mergedClock.encode(),
      deviceId: _deviceId,
      timestamp: DateTime.now(),
      signature: _generateSignature(remote.collectionId, remote.documentId, SyncOperation.merge, (local['version'] as int) + 1, mergedClock.encode()),
      nonce: _crypto.generateNonceString(),
    );
  }

  String _generateSignature(String collectionId, String documentId, SyncOperation operation, int version, String nonce) {
    final signatureData = '$collectionId$documentId${operation.name}$version$nonce';
    final key = _crypto.deriveKey('signature', 'salt', iterations: 1);
    return _crypto.generateHMAC(signatureData, key);
  }

  Future<void> createDocument(String collectionId, String documentId, Map<String, dynamic> data) async {
    await _db.insertDocument(collectionId, documentId, data);
    unawaited(syncPendingOperations());
  }

  Future<void> updateDocument(String collectionId, String documentId, Map<String, dynamic> data) async {
    await _db.updateDocument(collectionId, documentId, data);
    unawaited(syncPendingOperations());
  }

  Future<void> deleteDocument(String collectionId, String documentId) async {
    await _db.deleteDocument(collectionId, documentId);
    unawaited(syncPendingOperations());
  }

  Future<Map<String, dynamic>?> getDocument(String collectionId, String documentId) async {
    return _db.getDocument(collectionId, documentId);
  }

  Future<List<Map<String, dynamic>>> getCollection(String collectionId) async {
    return _db.getCollection(collectionId);
  }

  Future<void> requestFullSync(String collectionId) async {
    if (!_mqtt.isConnected) return;
    await _mqtt.requestCheckpoint(collectionId);
  }

  Future<void> forceSync() async {
    if (_isSyncing || !_mqtt.isConnected) return;
    await syncPendingOperations();
  }

  Future<void> dispose() async {
    await _connectionSubscription?.cancel();
    await _messageSubscription?.cancel();
    _mqtt.disconnect();
    await _statusController.close();
    await _syncProgressController.close();
  }
}

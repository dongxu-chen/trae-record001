library architecture;

export 'encryption/crypto_service.dart';
export 'database/sqlite_database.dart';
export 'sync/mqtt_sync_client.dart';
export 'sync/sync_engine.dart';
export 'appwrite/appwrite_client.dart';

enum SyncStatus {
  offline,
  connecting,
  online,
  syncing,
  error,
}

enum ConflictStrategy {
  lastWriteWins,
  firstWriteWins,
  merge,
  manual,
  clientWins,
}

enum QoSLevel {
  atMostOnce(0),
  atLeastOnce(1),
  exactlyOnce(2);

  final int value;
  const QoSLevel(this.value);
}

class SyncMessage {
  final String id;
  final String collectionId;
  final String documentId;
  final SyncOperation operation;
  final Map<String, dynamic> encryptedData;
  final int version;
  final String vectorClock;
  final String deviceId;
  final DateTime timestamp;
  final String signature;
  final String nonce;

  SyncMessage({
    required this.id,
    required this.collectionId,
    required this.documentId,
    required this.operation,
    required this.encryptedData,
    required this.version,
    required this.vectorClock,
    required this.deviceId,
    required this.timestamp,
    required this.signature,
    required this.nonce,
  });

  Map<String, dynamic> toJson() => {
    'id': id,
    'collectionId': collectionId,
    'documentId': documentId,
    'operation': operation.name,
    'encryptedData': encryptedData,
    'version': version,
    'vectorClock': vectorClock,
    'deviceId': deviceId,
    'timestamp': timestamp.toIso8601String(),
    'signature': signature,
    'nonce': nonce,
  };

  factory SyncMessage.fromJson(Map<String, dynamic> json) => SyncMessage(
    id: json['id'] as String,
    collectionId: json['collectionId'] as String,
    documentId: json['documentId'] as String,
    operation: SyncOperation.values.firstWhere((e) => e.name == json['operation']),
    encryptedData: Map<String, dynamic>.from(json['encryptedData'] as Map),
    version: json['version'] as int,
    vectorClock: json['vectorClock'] as String,
    deviceId: json['deviceId'] as String,
    timestamp: DateTime.parse(json['timestamp'] as String),
    signature: json['signature'] as String,
    nonce: json['nonce'] as String,
  );
}

enum SyncOperation {
  create,
  update,
  delete,
  merge,
  checkpoint,
}

class VectorClock {
  final Map<String, int> _clocks;

  VectorClock([Map<String, int>? clocks]) : _clocks = Map.from(clocks ?? {});

  int operator [](String deviceId) => _clocks[deviceId] ?? 0;

  void operator []=(String deviceId, int value) {
    _clocks[deviceId] = value;
  }

  void increment(String deviceId) {
    _clocks[deviceId] = (this[deviceId]) + 1;
  }

  bool happensBefore(VectorClock other) {
    bool atLeastOneLess = false;
    for (final key in {..._clocks.keys, ...other._clocks.keys}) {
      if (this[key] > other[key]) return false;
      if (this[key] < other[key]) atLeastOneLess = true;
    }
    return atLeastOneLess;
  }

  bool isConcurrent(VectorClock other) {
    return !happensBefore(other) && !other.happensBefore(this);
  }

  VectorClock merge(VectorClock other) {
    final merged = VectorClock();
    for (final key in {..._clocks.keys, ...other._clocks.keys}) {
      merged[key] = this[key] > other[key] ? this[key] : other[key];
    }
    return merged;
  }

  Map<String, dynamic> toJson() => Map.from(_clocks);

  factory VectorClock.fromJson(Map<String, dynamic> json) =>
    VectorClock(Map<String, int>.from(json.map((k, v) => MapEntry(k.toString(), v as int))));

  String encode() => toJson().toString();

  factory VectorClock.decode(String encoded) {
    final cleaned = encoded.replaceAll(RegExp(r'[\{\}\s]'), '');
    final entries = cleaned.split(',').where((e) => e.contains(':'));
    final map = <String, int>{};
    for (final entry in entries) {
      final parts = entry.split(':');
      if (parts.length == 2) {
        map[parts[0].trim()] = int.tryParse(parts[1].trim()) ?? 0;
      }
    }
    return VectorClock(map);
  }
}

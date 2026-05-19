import 'dart:async';
import 'dart:convert';
import 'package:mqtt_client/mqtt_client.dart';
import 'package:mqtt_client/mqtt_server_client.dart';
import '../architecture.dart';
import '../encryption/crypto_service.dart';

class MQTTSyncClient {
  final String broker;
  final int port;
  final String clientId;
  final String userId;
  final Uint8List encryptionKey;
  MqttServerClient? _client;
  final CryptoService _crypto = CryptoService();
  final _messageController = StreamController<SyncMessage>.broadcast();
  final _connectionController = StreamController<SyncStatus>.broadcast();
  final _syncProgressController = StreamController<double>.broadcast();
  final Map<String, List<String>> _nonceCache = {};
  final int _maxNonceCache = 1000;
  final Set<String> _processedMessages = {};
  final Duration _messageTimeout = const Duration(seconds: 5);

  Stream<SyncMessage> get messageStream => _messageController.stream;
  Stream<SyncStatus> get connectionStream => _connectionController.stream;
  Stream<double> get syncProgressStream => _syncProgressController.stream;
  bool get isConnected => _client?.connectionStatus?.state == MqttConnectionState.connected;

  MQTTSyncClient({
    required this.broker,
    required this.port,
    required this.clientId,
    required this.userId,
    required this.encryptionKey,
  });

  Future<void> connect() async {
    _client = MqttServerClient.withPort(broker, clientId, port);
    _client!.keepAlivePeriod = 30;
    _client!.onDisconnected = _onDisconnected;
    _client!.onConnected = _onConnected;
    _client!.onSubscribed = _onSubscribed;

    final connMess = MqttConnectMessage()
        .withClientIdentifier(clientId)
        .startClean()
        .withWillQos(MqttQos.atLeastOnce)
        .withWillTopic('users/$userId/offline')
        .withWillMessage(json.encode({'clientId': clientId, 'timestamp': DateTime.now().toIso8601String()}));

    _client!.connectionMessage = connMess;

    try {
      _connectionController.add(SyncStatus.connecting);
      await _client!.connect();
    } catch (e) {
      _connectionController.add(SyncStatus.error);
      rethrow;
    }
  }

  void _onConnected() {
    _connectionController.add(SyncStatus.online);
    _subscribeToSyncTopics();
  }

  void _onDisconnected() {
    _connectionController.add(SyncStatus.offline);
  }

  void _onSubscribed(String topic) {
    print('Subscribed to topic: $topic');
  }

  void _subscribeToSyncTopics() {
    final topics = [
      'users/$userId/sync/#',
      'users/$userId/broadcast/#',
    ];

    for (final topic in topics) {
      _client!.subscribe(topic, MqttQos.exactlyOnce);
    }

    _client!.updates!.listen(_handleMessage);
  }

  void _handleMessage(List<MqttReceivedMessage<MqttMessage>> messages) {
    for (final message in messages) {
      final payload = message.payload as MqttPublishMessage;
      final messageStr = MqttUtilities.bytesToStringAsString(payload.payload.message);

      try {
        final data = json.decode(messageStr) as Map<String, dynamic>;
        final syncMessage = SyncMessage.fromJson(data);

        if (_verifyMessage(syncMessage)) {
          if (!_processedMessages.contains(syncMessage.id)) {
            _processedMessages.add(syncMessage.id);
            if (_processedMessages.length > 10000) {
              _processedMessages.clear();
            }
            _messageController.add(syncMessage);
          }
        }
      } catch (e) {
        print('Error parsing sync message: $e');
      }
    }
  }

  bool _verifyMessage(SyncMessage message) {
    final signatureData = '${message.collectionId}${message.documentId}${message.operation.name}${message.version}${message.nonce}';
    final isValid = _crypto.verifyHMAC(signatureData, message.signature, encryptionKey);

    if (!isValid) return false;

    final messageAge = DateTime.now().difference(message.timestamp);
    if (messageAge > const Duration(minutes: 5)) {
      return false;
    }

    final deviceNonces = _nonceCache.putIfAbsent(message.deviceId, () => []);
    if (deviceNonces.contains(message.nonce)) {
      return false;
    }

    deviceNonces.add(message.nonce);
    if (deviceNonces.length > _maxNonceCache) {
      deviceNonces.removeAt(0);
    }

    return true;
  }

  Future<void> publishMessage(SyncMessage message) async {
    if (!isConnected) {
      throw StateError('Not connected to MQTT broker');
    }

    final topic = 'users/$userId/sync/${message.collectionId}';
    final payload = json.encode(message.toJson());

    final builder = MqttClientPayloadBuilder();
    builder.addString(payload);

    _client!.publishMessage(
      topic,
      MqttQos.exactlyOnce,
      builder.payload!,
      retain: false,
    );
  }

  Future<void> publishBatch(List<SyncMessage> messages, {
    void Function(int current, int total)? onProgress,
  }) async {
    for (var i = 0; i < messages.length; i++) {
      await publishMessage(messages[i]);
      onProgress?.call(i + 1, messages.length);
      _syncProgressController.add((i + 1) / messages.length);
      await Future.delayed(const Duration(milliseconds: 10));
    }
  }

  Future<void> requestCheckpoint(String collectionId) async {
    if (!isConnected) return;

    final topic = 'users/$userId/broadcast/checkpoint';
    final payload = json.encode({
      'collectionId': collectionId,
      'requestedBy': clientId,
      'timestamp': DateTime.now().toIso8601String(),
    });

    final builder = MqttClientPayloadBuilder();
    builder.addString(payload);

    _client!.publishMessage(
      topic,
      MqttQos.atLeastOnce,
      builder.payload!,
    );
  }

  Future<void> sendCheckpointResponse(String collectionId, int latestVersion) async {
    if (!isConnected) return;

    final topic = 'users/$userId/sync/checkpoint_response';
    final payload = json.encode({
      'collectionId': collectionId,
      'latestVersion': latestVersion,
      'responder': clientId,
      'timestamp': DateTime.now().toIso8601String(),
    });

    final builder = MqttClientPayloadBuilder();
    builder.addString(payload);

    _client!.publishMessage(
      topic,
      MqttQos.atLeastOnce,
      builder.payload!,
    );
  }

  Future<void> syncCollection(String collectionId, List<SyncMessage> messages) async {
    final progressTopic = 'users/$userId/sync/progress';
    final total = messages.length;

    for (var i = 0; i < messages.length; i++) {
      await publishMessage(messages[i]);
      final progress = (i + 1) / total;

      final progressPayload = json.encode({
        'collectionId': collectionId,
        'progress': progress,
        'completed': i + 1,
        'total': total,
      });

      final builder = MqttClientPayloadBuilder();
      builder.addString(progressPayload);
      _client!.publishMessage(
        progressTopic,
        MqttQos.atMostOnce,
        builder.payload!,
      );

      _syncProgressController.add(progress);
    }
  }

  void unsubscribe(String topic) {
    _client?.unsubscribe(topic);
  }

  void disconnect() {
    _client?.disconnect();
    _messageController.close();
    _connectionController.close();
    _syncProgressController.close();
  }
}

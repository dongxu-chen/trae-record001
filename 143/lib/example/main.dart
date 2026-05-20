import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:uuid/uuid.dart';
import '../core/architecture.dart';
import '../core/database/sqlite_database.dart';
import '../core/encryption/crypto_service.dart';
import '../core/sync/mqtt_sync_client.dart';
import '../core/sync/sync_engine.dart';
import '../core/appwrite/appwrite_client.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Appwrite MQTT Sync Demo',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
      ),
      home: const HomeScreen(),
    );
  }
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late SQLiteDatabase _db;
  late SyncEngine _syncEngine;
  late AppwriteSyncClient _appwriteClient;
  final _crypto = CryptoService();
  final _deviceId = const Uuid().v4().substring(0, 8);
  late Uint8List _encryptionKey;

  bool _isInitialized = false;
  bool _isConnected = false;
  double _syncProgress = 0.0;
  SyncStatus _status = SyncStatus.offline;
  List<Map<String, dynamic>> _notes = [];
  final _textController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _initialize();
  }

  Future<void> _initialize() async {
    _encryptionKey = _crypto.deriveKey('user_password', 'salt_value');

    _db = SQLiteDatabase(_deviceId);
    _db.setEncryptionKey(_encryptionKey);

    final mqtt = MQTTSyncClient(
      broker: 'broker.hivemq.com',
      port: 1883,
      clientId: 'device_$_deviceId',
      userId: 'demo_user',
      encryptionKey: _encryptionKey,
    );

    _syncEngine = SyncEngine(
      db: _db,
      mqtt: mqtt,
      deviceId: _deviceId,
    );

    _appwriteClient = AppwriteSyncClient(
      endpoint: 'https://cloud.appwrite.io/v1',
      projectId: 'YOUR_PROJECT_ID',
      databaseId: 'YOUR_DATABASE_ID',
      deviceId: _deviceId,
      encryptionKey: _encryptionKey,
      localDb: _db,
    );

    _syncEngine.statusStream.listen((status) {
      if (mounted) {
        setState(() {
          _status = status;
          _isConnected = status == SyncStatus.online || status == SyncStatus.syncing;
        });
      }
    });

    _syncEngine.progressStream.listen((progress) {
      if (mounted) {
        setState(() => _syncProgress = progress);
      }
    });

    await _syncEngine.initialize();
    await _loadNotes();

    if (mounted) {
      setState(() => _isInitialized = true);
    }
  }

  Future<void> _loadNotes() async {
    final notes = await _db.getCollection('notes');
    if (mounted) {
      setState(() => _notes = notes);
    }
  }

  Future<void> _addNote() async {
    if (_textController.text.trim().isEmpty) return;

    final noteId = const Uuid().v4();
    await _syncEngine.createDocument('notes', noteId, {
      'title': _textController.text,
      'content': 'Note created on device: $_deviceId',
      'createdAt': DateTime.now().toIso8601String(),
    });

    _textController.clear();
    await _loadNotes();
  }

  Future<void> _deleteNote(String id) async {
    await _syncEngine.deleteDocument('notes', id);
    await _loadNotes();
  }

  Future<void> _syncWithAppwrite() async {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Starting Appwrite sync...')),
    );

    await _appwriteClient.fullSync();

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Appwrite sync completed!')),
      );
    }
    await _loadNotes();
  }

  Color _getStatusColor(SyncStatus status) {
    switch (status) {
      case SyncStatus.offline:
        return Colors.grey;
      case SyncStatus.connecting:
        return Colors.orange;
      case SyncStatus.online:
        return Colors.green;
      case SyncStatus.syncing:
        return Colors.blue;
      case SyncStatus.error:
        return Colors.red;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Offline-First Sync Demo'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => _syncEngine.forceSync(),
          ),
          IconButton(
            icon: const Icon(Icons.cloud_sync),
            onPressed: _syncWithAppwrite,
          ),
        ],
        bottom: _isConnected
            ? PreferredSize(
                preferredSize: const Size.fromHeight(6),
                child: LinearProgressIndicator(value: _syncProgress),
              )
            : null,
      ),
      body: _isInitialized
          ? Column(
              children: [
                Container(
                  padding: const EdgeInsets.all(16),
                  color: _getStatusColor(_status).withOpacity(0.1),
                  child: Row(
                    children: [
                      Icon(Icons.cloud, color: _getStatusColor(_status)),
                      const SizedBox(width: 12),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'MQTT: ${_status.name}',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              color: _getStatusColor(_status),
                            ),
                          ),
                          Text(
                            'Device ID: $_deviceId',
                            style: TextStyle(
                              fontSize: 12,
                              color: Colors.grey.shade600,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _textController,
                          decoration: const InputDecoration(
                            labelText: 'Add a note...',
                            border: OutlineInputBorder(),
                          ),
                          onSubmitted: (_) => _addNote(),
                        ),
                      ),
                      const SizedBox(width: 12),
                      ElevatedButton(
                        onPressed: _addNote,
                        child: const Text('Add'),
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: _notes.isEmpty
                      ? const Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(Icons.note, size: 64, color: Colors.grey),
                              SizedBox(height: 16),
                              Text('No notes yet. Add your first note!'),
                            ],
                          ),
                        )
                      : ListView.builder(
                          itemCount: _notes.length,
                          padding: const EdgeInsets.symmetric(horizontal: 16),
                          itemBuilder: (context, index) {
                            final note = _notes[index];
                            final data = note['data'] as Map<String, dynamic>;
                            return Card(
                              child: ListTile(
                                title: Text(data['title'] as String),
                                subtitle: Text(data['content'] as String),
                                trailing: IconButton(
                                  icon: const Icon(Icons.delete, color: Colors.red),
                                  onPressed: () => _deleteNote(note['id'] as String),
                                ),
                              ),
                            );
                          },
                        ),
                ),
              ],
            )
          : const Center(child: CircularProgressIndicator()),
    );
  }

  @override
  void dispose() {
    _textController.dispose();
    _syncEngine.dispose();
    super.dispose();
  }
}

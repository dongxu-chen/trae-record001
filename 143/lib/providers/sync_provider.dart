import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import '../services/sync_service.dart';

class SyncProvider extends ChangeNotifier {
  final SyncService _syncService;
  final Connectivity _connectivity = Connectivity();
  StreamSubscription<List<ConnectivityResult>>? _connectivitySubscription;
  Timer? _autoSyncTimer;
  bool _isOnline = true;
  double _syncProgress = 0.0;

  SyncProvider(this._syncService) {
    _initConnectivityListener();
    _startAutoSync();
  }

  SyncService get syncService => _syncService;
  bool get isSyncing => _syncService.isSyncing;
  bool get isOnline => _isOnline;
  double get syncProgress => _syncProgress;

  Future<void> _initConnectivityListener() async {
    final results = await _connectivity.checkConnectivity();
    _isOnline = !results.contains(ConnectivityResult.none);
    notifyListeners();

    _connectivitySubscription = _connectivity.onConnectivityChanged.listen((results) {
      final wasOffline = !_isOnline;
      _isOnline = !results.contains(ConnectivityResult.none);
      notifyListeners();

      if (wasOffline && _isOnline) {
        sync();
      }
    });
  }

  void _startAutoSync() {
    _autoSyncTimer = Timer.periodic(
      const Duration(minutes: 5),
      (_) {
        if (_isOnline && !_syncService.isSyncing) {
          sync();
        }
      },
    );
  }

  Future<void> sync() async {
    if (!_isOnline || _syncService.isSyncing) return;

    try {
      await _syncService.sync(
        onProgress: (progress) {
          _syncProgress = progress;
          notifyListeners();
        },
      );
    } catch (e) {
      debugPrint('Sync error: $e');
    } finally {
      _syncProgress = 0.0;
      notifyListeners();
    }
  }

  Future<void> forceFullSync() async {
    if (!_isOnline) return;

    try {
      await _syncService.forceFullSync();
      notifyListeners();
    } catch (e) {
      debugPrint('Full sync error: $e');
    }
  }

  Future<int> getPendingOperationsCount() async {
    final ops = await _syncService.getPendingOperations();
    return ops.length;
  }

  @override
  void dispose() {
    _connectivitySubscription?.cancel();
    _autoSyncTimer?.cancel();
    super.dispose();
  }
}

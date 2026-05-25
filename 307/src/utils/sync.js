import { cryptoService } from './crypto.js';
import { dbService } from './database.js';

const SYNC_STORAGE_KEY = 'password_manager_sync';

export class SyncService {
  constructor() {
    this.syncKey = null;
    this.syncStatus = 'idle';
    this.lastSyncTime = null;
    this.autoSyncEnabled = false;
    this.autoSyncInterval = null;
  }

  async init() {
    this.syncStatus = 'idle';
    this.lastSyncTime = null;
    
    const savedKey = await this.getStoredSyncKey();
    if (savedKey) {
      this.syncKey = savedKey;
    }

    const settings = await this.getSyncSettings();
    if (settings.autoSync) {
      this.enableAutoSync(settings.syncInterval || 5 * 60 * 1000);
    }
  }

  async generateSyncKey() {
    const key = await cryptoService.generateSyncKey();
    this.syncKey = key;
    await this.storeSyncKey(key);
    return key;
  }

  async importSyncKey(syncKeyBase64) {
    try {
      const key = await cryptoService.importSyncKey(syncKeyBase64);
      this.syncKey = syncKeyBase64;
      await this.storeSyncKey(syncKeyBase64);
      return true;
    } catch (error) {
      throw new Error('无效的同步密钥');
    }
  }

  async storeSyncKey(key) {
    const encryptedKey = await cryptoService.encrypt({ syncKey: key });
    await dbService.setSetting('syncKey', encryptedKey);
  }

  async getStoredSyncKey() {
    try {
      const encrypted = await dbService.getSetting('syncKey');
      if (!encrypted) return null;
      
      const decrypted = await cryptoService.decrypt(encrypted);
      return decrypted.syncKey;
    } catch {
      return null;
    }
  }

  async clearSyncKey() {
    this.syncKey = null;
    await dbService.deleteSetting('syncKey');
  }

  async getSyncSettings() {
    const settings = await dbService.getSetting('syncSettings');
    return settings || {
      autoSync: false,
      syncInterval: 5 * 60 * 1000,
      syncOnStart: false,
      syncOnChange: true
    };
  }

  async updateSyncSettings(newSettings) {
    const currentSettings = await this.getSyncSettings();
    const merged = { ...currentSettings, ...newSettings };
    await dbService.setSetting('syncSettings', merged);

    if (merged.autoSync && !this.autoSyncEnabled) {
      this.enableAutoSync(merged.syncInterval);
    } else if (!merged.autoSync && this.autoSyncEnabled) {
      this.disableAutoSync();
    }

    return merged;
  }

  enableAutoSync(interval = 5 * 60 * 1000) {
    this.disableAutoSync();
    this.autoSyncEnabled = true;
    this.autoSyncInterval = setInterval(() => {
      this.sync();
    }, interval);
  }

  disableAutoSync() {
    if (this.autoSyncInterval) {
      clearInterval(this.autoSyncInterval);
      this.autoSyncInterval = null;
    }
    this.autoSyncEnabled = false;
  }

  async sync() {
    if (!this.syncKey) {
      throw new Error('请先设置同步密钥');
    }

    if (!cryptoService.isInitialized()) {
      throw new Error('请先解锁密码管理器');
    }

    this.syncStatus = 'syncing';
    this.notifyListeners();

    try {
      const localData = await dbService.getAllDataForSync();
      const syncKeyObj = await cryptoService.importSyncKey(this.syncKey);
      const encryptedLocal = await cryptoService.encryptForSync(localData, syncKeyObj);

      const remoteData = await this.getRemoteData();
      
      let mergedData;
      if (remoteData) {
        const decryptedRemote = await cryptoService.decryptFromSync(remoteData, syncKeyObj);
        mergedData = this.mergeData(localData, decryptedRemote);
      } else {
        mergedData = localData;
      }

      const encryptedMerged = await cryptoService.encryptForSync(mergedData, syncKeyObj);
      await this.putRemoteData(encryptedMerged);

      await dbService.restoreFromSync(mergedData);

      this.lastSyncTime = Date.now();
      this.syncStatus = 'synced';
      
      await dbService.saveSyncData({
        id: 'lastSync',
        timestamp: this.lastSyncTime,
        status: 'success'
      });

    } catch (error) {
      this.syncStatus = 'error';
      await dbService.saveSyncData({
        id: 'lastSync',
        timestamp: Date.now(),
        status: 'error',
        error: error.message
      });
      throw error;
    } finally {
      this.notifyListeners();
    }
  }

  mergeData(localData, remoteData) {
    if (localData.timestamp > remoteData.timestamp) {
      return localData;
    }

    const mergedPasswords = new Map();

    localData.passwords.forEach(pwd => {
      mergedPasswords.set(pwd.id, pwd);
    });

    remoteData.passwords.forEach(pwd => {
      const existing = mergedPasswords.get(pwd.id);
      if (!existing || pwd.updatedAt > existing.updatedAt) {
        mergedPasswords.set(pwd.id, pwd);
      }
    });

    const mergedSettings = new Map();
    
    localData.settings.forEach(setting => {
      mergedSettings.set(setting.key, setting);
    });

    remoteData.settings.forEach(setting => {
      mergedSettings.set(setting.key, setting);
    });

    return {
      version: Math.max(localData.version, remoteData.version),
      timestamp: Math.max(localData.timestamp, remoteData.timestamp),
      passwords: Array.from(mergedPasswords.values()),
      settings: Array.from(mergedSettings.values())
    };
  }

  async getRemoteData() {
    try {
      const data = localStorage.getItem(SYNC_STORAGE_KEY);
      return data ? JSON.parse(data) : null;
    } catch (error) {
      console.warn('获取远程同步数据失败，使用本地存储:', error);
      const data = localStorage.getItem(SYNC_STORAGE_KEY);
      return data ? JSON.parse(data) : null;
    }
  }

  async putRemoteData(data) {
    try {
      localStorage.setItem(SYNC_STORAGE_KEY, JSON.stringify(data));
    } catch (error) {
      console.warn('推送同步数据失败，使用本地存储:', error);
      localStorage.setItem(SYNC_STORAGE_KEY, JSON.stringify(data));
    }
  }

  async getSyncStatus() {
    return {
      status: this.syncStatus,
      lastSyncTime: this.lastSyncTime,
      autoSyncEnabled: this.autoSyncEnabled,
      hasSyncKey: this.syncKey !== null
    };
  }

  async triggerSync() {
    return this.sync();
  }

  async exportSyncKey() {
    if (!this.syncKey) {
      throw new Error('没有同步密钥可导出');
    }
    return this.syncKey;
  }

  async resetSync() {
    this.disableAutoSync();
    await this.clearSyncKey();
    await dbService.clearSyncData();
    this.syncStatus = 'idle';
    this.lastSyncTime = null;
    this.notifyListeners();
  }

  notifyListeners() {
    this.syncListeners?.forEach(listener => listener(this.getSyncStatus()));
  }

  addSyncListener(listener) {
    if (!this.syncListeners) {
      this.syncListeners = [];
    }
    this.syncListeners.push(listener);
    return () => {
      this.syncListeners = this.syncListeners.filter(l => l !== listener);
    };
  }
}

export const syncService = new SyncService();

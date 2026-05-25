import { cryptoService } from './crypto.js';
import { PasswordGenerator } from './passwordGenerator.js';

const DB_NAME = 'SecurePasswordManager';
const DB_VERSION = 1;

const STORE_PASSWORDS = 'passwords';
const STORE_SETTINGS = 'settings';
const STORE_SHARED = 'shared';
const STORE_SYNC = 'sync';

export class DatabaseService {
  constructor() {
    this.db = null;
    this.listeners = [];
  }

  async init() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        this.db = request.result;
        resolve(this);
      };

      request.onupgradeneeded = (event) => {
        const db = event.target.result;

        if (!db.objectStoreNames.contains(STORE_PASSWORDS)) {
          const passwordStore = db.createObjectStore(STORE_PASSWORDS, {
            keyPath: 'id',
            autoIncrement: true
          });
          passwordStore.createIndex('title', 'title');
          passwordStore.createIndex('username', 'username');
          passwordStore.createIndex('url', 'url');
          passwordStore.createIndex('createdAt', 'createdAt');
          passwordStore.createIndex('updatedAt', 'updatedAt');
          passwordStore.createIndex('category', 'category');
        }

        if (!db.objectStoreNames.contains(STORE_SETTINGS)) {
          db.createObjectStore(STORE_SETTINGS, { keyPath: 'key' });
        }

        if (!db.objectStoreNames.contains(STORE_SHARED)) {
          const sharedStore = db.createObjectStore(STORE_SHARED, {
            keyPath: 'id',
            autoIncrement: true
          });
          sharedStore.createIndex('passwordId', 'passwordId');
          sharedStore.createIndex('sharedWith', 'sharedWith');
          sharedStore.createIndex('expiresAt', 'expiresAt');
        }

        if (!db.objectStoreNames.contains(STORE_SYNC)) {
          const syncStore = db.createObjectStore(STORE_SYNC, { keyPath: 'id' });
          syncStore.createIndex('timestamp', 'timestamp');
        }
      };
    });
  }

  isInitialized() {
    return this.db !== null;
  }

  async close() {
    if (this.db) {
      this.db.close();
      this.db = null;
    }
  }

  async deleteDatabase() {
    this.close();
    return new Promise((resolve, reject) => {
      const request = indexedDB.deleteDatabase(DB_NAME);
      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve();
    });
  }

  notifyListeners() {
    this.listeners.forEach(listener => listener());
  }

  addListener(listener) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  async addPassword(passwordData) {
    if (!cryptoService.isInitialized()) {
      throw new Error('请先输入主密码解锁');
    }

    const now = Date.now();
    const strength = PasswordGenerator.checkStrength(passwordData.password);
    const dataToEncrypt = {
      password: passwordData.password,
      notes: passwordData.notes || ''
    };

    const encryptedData = await cryptoService.encrypt(dataToEncrypt);

    const password = {
      title: passwordData.title,
      username: passwordData.username,
      url: passwordData.url,
      category: passwordData.category || 'general',
      encryptedData: encryptedData,
      strength: strength.strength,
      strengthScore: strength.score,
      entropy: strength.entropy,
      createdAt: now,
      updatedAt: now,
      lastUsed: null,
      favorite: passwordData.favorite || false,
      tags: passwordData.tags || []
    };

    return this._executeTransaction(STORE_PASSWORDS, 'readwrite', (store) => {
      return new Promise((resolve, reject) => {
        const request = store.add(password);
        request.onsuccess = () => {
          this.notifyListeners();
          resolve(request.result);
        };
        request.onerror = () => reject(request.error);
      });
    });
  }

  async updatePassword(id, passwordData) {
    if (!cryptoService.isInitialized()) {
      throw new Error('请先输入主密码解锁');
    }

    const existing = await this.getPassword(id);
    if (!existing) {
      throw new Error('密码记录不存在');
    }

    const now = Date.now();
    const updates = { ...existing, ...passwordData, updatedAt: now };

    if (passwordData.password) {
      const strength = PasswordGenerator.checkStrength(passwordData.password);
      updates.strength = strength.strength;
      updates.strengthScore = strength.score;
      updates.entropy = strength.entropy;

      const dataToEncrypt = {
        password: passwordData.password,
        notes: passwordData.notes || existing.notes || ''
      };
      updates.encryptedData = await cryptoService.encrypt(dataToEncrypt);
    } else if (passwordData.notes !== undefined) {
      const decrypted = await cryptoService.decrypt(existing.encryptedData);
      const dataToEncrypt = {
        password: decrypted.password,
        notes: passwordData.notes
      };
      updates.encryptedData = await cryptoService.encrypt(dataToEncrypt);
    }

    delete updates.id;

    return this._executeTransaction(STORE_PASSWORDS, 'readwrite', (store) => {
      return new Promise((resolve, reject) => {
        const request = store.put({ ...updates, id: Number(id) });
        request.onsuccess = () => {
          this.notifyListeners();
          resolve(request.result);
        };
        request.onerror = () => reject(request.error);
      });
    });
  }

  async deletePassword(id) {
    return this._executeTransaction(STORE_PASSWORDS, 'readwrite', (store) => {
      return new Promise((resolve, reject) => {
        const request = store.delete(Number(id));
        request.onsuccess = () => {
          this.notifyListeners();
          resolve();
        };
        request.onerror = () => reject(request.error);
      });
    });
  }

  async getPassword(id) {
    return this._executeTransaction(STORE_PASSWORDS, 'readonly', (store) => {
      return new Promise((resolve, reject) => {
        const request = store.get(Number(id));
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
      });
    });
  }

  async getDecryptedPassword(id) {
    if (!cryptoService.isInitialized()) {
      throw new Error('请先输入主密码解锁');
    }

    const password = await this.getPassword(id);
    if (!password) return null;

    const decrypted = await cryptoService.decrypt(password.encryptedData);
    return {
      ...password,
      password: decrypted.password,
      notes: decrypted.notes
    };
  }

  async getAllPasswords(includeDecrypted = false) {
    const passwords = await this._executeTransaction(STORE_PASSWORDS, 'readonly', (store) => {
      return new Promise((resolve, reject) => {
        const request = store.getAll();
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
      });
    });

    if (includeDecrypted && cryptoService.isInitialized()) {
      return Promise.all(
        passwords.map(async (p) => {
          try {
            const decrypted = await cryptoService.decrypt(p.encryptedData);
            return { ...p, ...decrypted };
          } catch {
            return p;
          }
        })
      );
    }

    return passwords;
  }

  async searchPasswords(query) {
    if (!query) return this.getAllPasswords();
    
    const passwords = await this.getAllPasswords();
    const lowerQuery = query.toLowerCase();
    
    return passwords.filter(p => 
      p.title.toLowerCase().includes(lowerQuery) ||
      p.username.toLowerCase().includes(lowerQuery) ||
      p.url.toLowerCase().includes(lowerQuery) ||
      (p.tags && p.tags.some(t => t.toLowerCase().includes(lowerQuery)))
    );
  }

  async getPasswordsByUrl(url) {
    const passwords = await this.getAllPasswords();
    return passwords.filter(p => {
      if (!p.url) return false;
      try {
        const passwordHost = new URL(p.url).hostname;
        const targetHost = new URL(url).hostname;
        return passwordHost === targetHost || 
               targetHost.endsWith('.' + passwordHost) ||
               passwordHost.endsWith('.' + targetHost);
      } catch {
        return p.url.includes(url) || url.includes(p.url);
      }
    });
  }

  async markAsUsed(id) {
    const password = await this.getPassword(id);
    if (!password) return;

    return this._executeTransaction(STORE_PASSWORDS, 'readwrite', (store) => {
      return new Promise((resolve, reject) => {
        const request = store.put({ ...password, lastUsed: Date.now(), id: Number(id) });
        request.onsuccess = () => {
          this.notifyListeners();
          resolve();
        };
        request.onerror = () => reject(request.error);
      });
    });
  }

  async toggleFavorite(id) {
    const password = await this.getPassword(id);
    if (!password) return;

    return this._executeTransaction(STORE_PASSWORDS, 'readwrite', (store) => {
      return new Promise((resolve, reject) => {
        const request = store.put({ ...password, favorite: !password.favorite, id: Number(id) });
        request.onsuccess = () => {
          this.notifyListeners();
          resolve();
        };
        request.onerror = () => reject(request.error);
      });
    });
  }

  async getSetting(key) {
    return this._executeTransaction(STORE_SETTINGS, 'readonly', (store) => {
      return new Promise((resolve, reject) => {
        const request = store.get(key);
        request.onsuccess = () => resolve(request.result ? request.result.value : null);
        request.onerror = () => reject(request.error);
      });
    });
  }

  async setSetting(key, value) {
    return this._executeTransaction(STORE_SETTINGS, 'readwrite', (store) => {
      return new Promise((resolve, reject) => {
        const request = store.put({ key, value });
        request.onsuccess = () => {
          this.notifyListeners();
          resolve();
        };
        request.onerror = () => reject(request.error);
      });
    });
  }

  async deleteSetting(key) {
    return this._executeTransaction(STORE_SETTINGS, 'readwrite', (store) => {
      return new Promise((resolve, reject) => {
        const request = store.delete(key);
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
      });
    });
  }

  async getStats() {
    const passwords = await this.getAllPasswords(true);
    
    const categories = {};
    let weakCount = 0;
    let duplicatePasswords = [];
    const passwordMap = new Map();

    passwords.forEach(p => {
      categories[p.category] = (categories[p.category] || 0) + 1;
      
      if (p.strength === 'weak') {
        weakCount++;
      }

      if (p.password) {
        if (passwordMap.has(p.password)) {
          passwordMap.get(p.password).push(p);
        } else {
          passwordMap.set(p.password, [p]);
        }
      }
    });

    passwordMap.forEach((entries, password) => {
      if (entries.length > 1) {
        duplicatePasswords.push({
          password,
          count: entries.length,
          entries
        });
      }
    });

    return {
      total: passwords.length,
      categories,
      weakCount,
      duplicateCount: duplicatePasswords.length,
      duplicatePasswords,
      lastUpdated: Math.max(...passwords.map(p => p.updatedAt), 0)
    };
  }

  async exportData() {
    if (!cryptoService.isInitialized()) {
      throw new Error('请先输入主密码解锁');
    }

    const passwords = await this.getAllPasswords(true);
    const settings = await this._executeTransaction(STORE_SETTINGS, 'readonly', (store) => {
      return new Promise((resolve, reject) => {
        const request = store.getAll();
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
      });
    });

    return {
      version: DB_VERSION,
      exportedAt: Date.now(),
      passwords,
      settings
    };
  }

  async importData(data) {
    if (!cryptoService.isInitialized()) {
      throw new Error('请先输入主密码解锁');
    }

    if (!data.passwords || !Array.isArray(data.passwords)) {
      throw new Error('无效的导入数据格式');
    }

    for (const pwd of data.passwords) {
      if (pwd.password) {
        await this.addPassword({
          title: pwd.title || 'Imported',
          username: pwd.username || '',
          url: pwd.url || '',
          password: pwd.password,
          notes: pwd.notes || '',
          category: pwd.category || 'general',
          tags: pwd.tags || []
        });
      }
    }

    if (data.settings && Array.isArray(data.settings)) {
      for (const setting of data.settings) {
        await this.setSetting(setting.key, setting.value);
      }
    }

    return data.passwords.length;
  }

  async addSharedPassword(shareData) {
    return this._executeTransaction(STORE_SHARED, 'readwrite', (store) => {
      return new Promise((resolve, reject) => {
        const request = store.add({
          ...shareData,
          createdAt: Date.now()
        });
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
      });
    });
  }

  async getSharedPasswords() {
    return this._executeTransaction(STORE_SHARED, 'readonly', (store) => {
      return new Promise((resolve, reject) => {
        const request = store.getAll();
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
      });
    });
  }

  async deleteSharedPassword(id) {
    return this._executeTransaction(STORE_SHARED, 'readwrite', (store) => {
      return new Promise((resolve, reject) => {
        const request = store.delete(Number(id));
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
      });
    });
  }

  async saveSyncData(syncData) {
    return this._executeTransaction(STORE_SYNC, 'readwrite', (store) => {
      return new Promise((resolve, reject) => {
        const request = store.put({
          ...syncData,
          timestamp: Date.now()
        });
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
      });
    });
  }

  async getSyncData() {
    return this._executeTransaction(STORE_SYNC, 'readonly', (store) => {
      return new Promise((resolve, reject) => {
        const request = store.getAll();
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
      });
    });
  }

  async clearSyncData() {
    return this._executeTransaction(STORE_SYNC, 'readwrite', (store) => {
      return new Promise((resolve, reject) => {
        const request = store.clear();
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
      });
    });
  }

  async getAllDataForSync() {
    if (!cryptoService.isInitialized()) {
      throw new Error('请先输入主密码解锁');
    }

    const passwords = await this.getAllPasswords();
    const settings = await this._executeTransaction(STORE_SETTINGS, 'readonly', (store) => {
      return new Promise((resolve, reject) => {
        const request = store.getAll();
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
      });
    });

    return {
      version: DB_VERSION,
      timestamp: Date.now(),
      passwords,
      settings
    };
  }

  async restoreFromSync(data) {
    if (!data || !data.passwords) {
      throw new Error('无效的同步数据');
    }

    await this._executeTransaction(STORE_PASSWORDS, 'readwrite', (store) => {
      return new Promise((resolve, reject) => {
        const clearRequest = store.clear();
        clearRequest.onsuccess = () => {
          let count = 0;
          data.passwords.forEach(pwd => {
            const addRequest = store.put(pwd);
            addRequest.onsuccess = () => {
              count++;
              if (count === data.passwords.length) {
                resolve();
              }
            };
            addRequest.onerror = () => reject(addRequest.error);
          });
          if (data.passwords.length === 0) resolve();
        };
        clearRequest.onerror = () => reject(clearRequest.error);
      });
    });

    if (data.settings) {
      await this._executeTransaction(STORE_SETTINGS, 'readwrite', (store) => {
        return new Promise((resolve, reject) => {
          const clearRequest = store.clear();
          clearRequest.onsuccess = () => {
            let count = 0;
            data.settings.forEach(setting => {
              const addRequest = store.put(setting);
              addRequest.onsuccess = () => {
                count++;
                if (count === data.settings.length) {
                  resolve();
                }
              };
              addRequest.onerror = () => reject(addRequest.error);
            });
            if (data.settings.length === 0) resolve();
          };
          clearRequest.onerror = () => reject(clearRequest.error);
        });
      });
    }

    this.notifyListeners();
    return data.passwords.length;
  }

  _executeTransaction(storeName, mode, callback) {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('数据库未初始化'));
        return;
      }

      const transaction = this.db.transaction(storeName, mode);
      const store = transaction.objectStore(storeName);

      transaction.onerror = () => reject(transaction.error);
      transaction.onabort = () => reject(transaction.error);

      callback(store).then(resolve).catch(reject);
    });
  }
}

export const dbService = new DatabaseService();

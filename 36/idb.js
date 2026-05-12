const DB_NAME = 'OfflineDiaryDB';
const DB_VERSION = 3;

const objectStores = {
  diaries: {
    name: 'diaries',
    keyPath: 'id',
    indexes: [
      { name: 'userId', keyPath: 'userId', unique: false },
      { name: 'createdAt', keyPath: 'createdAt', unique: false },
      { name: 'updatedAt', keyPath: 'updatedAt', unique: false },
      { name: 'encrypted', keyPath: 'encrypted', unique: false }
    ]
  },
  users: {
    name: 'users',
    keyPath: 'email',
    indexes: []
  },
  syncQueue: {
    name: 'syncQueue',
    keyPath: 'id',
    indexes: [
      { name: 'type', keyPath: 'type', unique: false },
      { name: 'createdAt', keyPath: 'createdAt', unique: false },
      { name: 'chunkId', keyPath: 'chunkId', unique: false }
    ]
  },
  encryptionKeys: {
    name: 'encryptionKeys',
    keyPath: 'userId',
    indexes: [
      { name: 'createdAt', keyPath: 'createdAt', unique: false }
    ]
  },
  settings: {
    name: 'settings',
    keyPath: 'key',
    indexes: []
  },
  backupMetadata: {
    name: 'backupMetadata',
    keyPath: 'id',
    indexes: [
      { name: 'userId', keyPath: 'userId', unique: false },
      { name: 'createdAt', keyPath: 'createdAt', unique: false }
    ]
  }
};

let dbInstance = null;
let dbOpenPromise = null;
const operationQueue = [];
let isProcessingQueue = false;

function openDB() {
  if (dbInstance) {
    return Promise.resolve(dbInstance);
  }
  
  if (dbOpenPromise) {
    return dbOpenPromise;
  }

  dbOpenPromise = new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => {
      dbOpenPromise = null;
      reject(request.error);
    };
    
    request.onsuccess = () => {
      dbInstance = request.result;
      
      dbInstance.onerror = (event) => {
        console.error('[IDB] 数据库错误:', event.target.error);
      };
      
      dbInstance.onversionchange = (event) => {
        console.log('[IDB] 数据库版本变更，关闭连接');
        if (dbInstance) {
          dbInstance.close();
          dbInstance = null;
          dbOpenPromise = null;
        }
      };
      
      processQueue();
      resolve(dbInstance);
    };

    request.onblocked = () => {
      console.warn('[IDB] 数据库打开被阻塞，其他标签页可能需要关闭');
    };

    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      const transaction = event.target.transaction;
      const oldVersion = event.oldVersion || 0;

      Object.values(objectStores).forEach(storeConfig => {
        if (!db.objectStoreNames.contains(storeConfig.name)) {
          const store = db.createObjectStore(storeConfig.name, {
            keyPath: storeConfig.keyPath,
            autoIncrement: storeConfig.keyPath === 'id' && 
                           storeConfig.name !== 'settings' &&
                           storeConfig.name !== 'encryptionKeys'
          });

          storeConfig.indexes.forEach(index => {
            if (!store.indexNames.contains(index.name)) {
              store.createIndex(index.name, index.keyPath, {
                unique: index.unique
              });
            }
          });
        } else {
          const store = transaction.objectStore(storeConfig.name);
          storeConfig.indexes.forEach(index => {
            if (!store.indexNames.contains(index.name)) {
              store.createIndex(index.name, index.keyPath, {
                unique: index.unique
              });
            }
          });
        }
      });
    };
  });

  return dbOpenPromise;
}

function closeDB() {
  if (dbInstance) {
    dbInstance.close();
    dbInstance = null;
    dbOpenPromise = null;
  }
}

function enqueueOperation(operation) {
  return new Promise((resolve, reject) => {
    operationQueue.push({ operation, resolve, reject });
    processQueue();
  });
}

async function processQueue() {
  if (isProcessingQueue || operationQueue.length === 0) {
    return;
  }
  
  isProcessingQueue = true;
  
  while (operationQueue.length > 0) {
    const { operation, resolve, reject } = operationQueue.shift();
    
    try {
      const result = await operation();
      resolve(result);
    } catch (error) {
      reject(error);
    }
  }
  
  isProcessingQueue = false;
}

function executeTransaction(storeName, mode, callback) {
  return enqueueOperation(async () => {
    const db = await openDB();
    
    return new Promise((resolve, reject) => {
      let transaction;
      try {
        transaction = db.transaction(storeName, mode);
      } catch (error) {
        reject(error);
        return;
      }
      
      const store = transaction.objectStore(storeName);
      let request;
      
      try {
        request = callback(store);
      } catch (error) {
        transaction.abort();
        reject(error);
        return;
      }
      
      transaction.oncomplete = () => {
        if (request instanceof IDBRequest) {
          if (request.readyState === 'done') {
            if (request.error) {
              reject(request.error);
            } else {
              resolve(request.result);
            }
          } else {
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
          }
        } else {
          resolve(request);
        }
      };
      
      transaction.onerror = () => {
        const error = transaction.error || request?.error;
        reject(error);
      };
      
      transaction.onabort = () => {
        reject(transaction.error || new Error('Transaction aborted'));
      };
    });
  });
}

function executeMultiStoreTransaction(storeNames, mode, callback) {
  return enqueueOperation(async () => {
    const db = await openDB();
    
    return new Promise((resolve, reject) => {
      let transaction;
      try {
        transaction = db.transaction(storeNames, mode);
      } catch (error) {
        reject(error);
        return;
      }
      
      const stores = {};
      storeNames.forEach(name => {
        stores[name] = transaction.objectStore(name);
      });
      
      let result;
      try {
        result = callback(stores);
      } catch (error) {
        transaction.abort();
        reject(error);
        return;
      }
      
      transaction.oncomplete = () => {
        if (result instanceof IDBRequest) {
          if (result.readyState === 'done') {
            if (result.error) {
              reject(result.error);
            } else {
              resolve(result.result);
            }
          } else {
            result.onsuccess = () => resolve(result.result);
            result.onerror = () => reject(result.error);
          }
        } else {
          resolve(result);
        }
      };
      
      transaction.onerror = () => {
        reject(transaction.error);
      };
      
      transaction.onabort = () => {
        reject(transaction.error || new Error('Transaction aborted'));
      };
    });
  });
}

const DiaryStore = {
  async getAll(userId) {
    const diaries = await executeTransaction('diaries', 'readonly', (store) => {
      const index = store.index('userId');
      const request = index.getAll(userId);
      
      request.onsuccess = function() {
        const sorted = this.result.sort((a, b) => 
          new Date(b.updatedAt) - new Date(a.updatedAt)
        );
        request.result = sorted;
      };
      
      return request;
    });

    const encryptionKey = await EncryptionKeyStore.getForUser(userId);
    if (encryptionKey) {
      try {
        const key = await CryptoManager.importKey(encryptionKey.key);
        const decryptedDiaries = [];
        for (const diary of diaries) {
          if (diary.encrypted) {
            try {
              const decrypted = await CryptoManager.decryptDiary(diary, key);
              decryptedDiaries.push(decrypted);
            } catch (error) {
              console.warn('[IDB] 日记解密失败，保留加密版本:', diary.id);
              decryptedDiaries.push(diary);
            }
          } else {
            decryptedDiaries.push(diary);
          }
        }
        return decryptedDiaries;
      } catch (error) {
        console.error('[IDB] 批量解密失败:', error);
        return diaries;
      }
    }

    return diaries;
  },

  async getById(id) {
    const diary = await executeTransaction('diaries', 'readonly', (store) => {
      return store.get(id);
    });

    if (!diary) return null;

    if (diary.encrypted && diary.userId) {
      const encryptionKey = await EncryptionKeyStore.getForUser(diary.userId);
      if (encryptionKey) {
        try {
          const key = await CryptoManager.importKey(encryptionKey.key);
          return await CryptoManager.decryptDiary(diary, key);
        } catch (error) {
          console.warn('[IDB] 日记解密失败:', error);
        }
      }
    }

    return diary;
  },

  async save(diary, userId) {
    const now = new Date().toISOString();
    const actualUserId = userId || diary.userId;
    
    let diaryToSave = {
      ...diary,
      updatedAt: now,
      synced: false
    };

    if (!diaryToSave.createdAt) {
      diaryToSave.createdAt = now;
    }

    if (!diaryToSave.id) {
      diaryToSave.id = `diary_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    if (actualUserId) {
      diaryToSave.userId = actualUserId;
      
      const settings = await SettingsStore.get('encryptionEnabled');
      const encryptionEnabled = settings?.value !== false;
      
      if (encryptionEnabled) {
        const encryptionKey = await EncryptionKeyStore.getOrCreateForUser(actualUserId);
        if (encryptionKey) {
          try {
            const key = await CryptoManager.importKey(encryptionKey.key);
            diaryToSave = await CryptoManager.encryptDiary(diaryToSave, key);
          } catch (error) {
            console.error('[IDB] 日记加密失败:', error);
          }
        }
      }
    }

    const isNew = !diary.id;
    const action = isNew ? 'create' : 'update';

    const diarySize = JSON.stringify(diaryToSave).length;
    const MAX_CHUNK_SIZE = 500 * 1024;

    if (diarySize > MAX_CHUNK_SIZE) {
      return await this.saveWithChunks(diaryToSave, action, now);
    }

    return executeMultiStoreTransaction(['diaries', 'syncQueue'], 'readwrite', (stores) => {
      const diaryStore = stores.diaries;
      const syncStore = stores.syncQueue;
      
      diaryStore.put(diaryToSave);
      
      const syncItem = {
        id: `sync_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        type: 'diary',
        action,
        data: diaryToSave,
        createdAt: now,
        attempts: 0
      };
      
      syncStore.add(syncItem);
      
      return diaryToSave;
    });
  },

  async saveWithChunks(diary, action, now) {
    const diaryData = JSON.stringify(diary);
    const MAX_CHUNK_SIZE = 500 * 1024;
    const chunks = [];
    
    for (let i = 0; i < diaryData.length; i += MAX_CHUNK_SIZE) {
      chunks.push(diaryData.slice(i, i + MAX_CHUNK_SIZE));
    }

    const chunkId = `chunk_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    return executeMultiStoreTransaction(['diaries', 'syncQueue'], 'readwrite', (stores) => {
      const diaryStore = stores.diaries;
      const syncStore = stores.syncQueue;
      
      const diaryMeta = {
        ...diary,
        content: '',
        chunked: true,
        chunkId,
        chunkCount: chunks.length
      };
      
      diaryStore.put(diaryMeta);
      
      chunks.forEach((chunk, index) => {
        const syncItem = {
          id: `sync_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          type: 'diary-chunk',
          action,
          chunkId,
          chunkIndex: index,
          chunkCount: chunks.length,
          data: chunk,
          diaryId: diary.id,
          createdAt: now,
          attempts: 0
        };
        syncStore.add(syncItem);
      });
      
      return diaryMeta;
    });
  },

  async bulkSave(diaries, userId) {
    if (!diaries || diaries.length === 0) {
      return [];
    }

    const now = new Date().toISOString();
    let encryptionKey = null;
    let key = null;

    if (userId) {
      const settings = await SettingsStore.get('encryptionEnabled');
      const encryptionEnabled = settings?.value !== false;
      
      if (encryptionEnabled) {
        encryptionKey = await EncryptionKeyStore.getOrCreateForUser(userId);
        if (encryptionKey) {
          key = await CryptoManager.importKey(encryptionKey.key);
        }
      }
    }

    const diariesToSave = await Promise.all(
      diaries.map(async (diary) => {
        let savedDiary = {
          ...diary,
          updatedAt: now,
          synced: diary.synced !== undefined ? diary.synced : false,
          createdAt: diary.createdAt || now,
          id: diary.id || `diary_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
        };

        if (userId) {
          savedDiary.userId = userId;
        }

        if (key && savedDiary.title && !savedDiary.encrypted) {
          try {
            savedDiary = await CryptoManager.encryptDiary(savedDiary, key);
          } catch (error) {
            console.warn('[IDB] 批量加密失败:', error);
          }
        }

        return savedDiary;
      })
    );

    return executeTransaction('diaries', 'readwrite', (store) => {
      return new Promise((resolve, reject) => {
        const results = [];
        let pending = diariesToSave.length;
        
        if (pending === 0) {
          resolve([]);
          return;
        }
        
        diariesToSave.forEach((diary, index) => {
          const request = store.put(diary);
          
          request.onsuccess = () => {
            results[index] = diary;
            pending--;
            if (pending === 0) {
              resolve(results);
            }
          };
          
          request.onerror = () => {
            reject(request.error);
          };
        });
      });
    });
  },

  async delete(id) {
    const diary = await this.getById(id);
    if (!diary) return;

    return executeMultiStoreTransaction(['diaries', 'syncQueue'], 'readwrite', (stores) => {
      const diaryStore = stores.diaries;
      const syncStore = stores.syncQueue;
      
      diaryStore.delete(id);
      
      const syncItem = {
        id: `sync_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        type: 'diary',
        action: 'delete',
        data: { id, userId: diary.userId },
        createdAt: new Date().toISOString(),
        attempts: 0
      };
      
      syncStore.add(syncItem);
      
      return true;
    });
  },

  async markSynced(id) {
    return executeTransaction('diaries', 'readwrite', (store) => {
      const getRequest = store.get(id);
      
      getRequest.onsuccess = function() {
        const diary = this.result;
        if (diary) {
          diary.synced = true;
          store.put(diary);
        }
      };
      
      return getRequest;
    });
  },

  async search(userId, query) {
    const allDiaries = await this.getAll(userId);
    const lowerQuery = query.toLowerCase();
    
    return allDiaries.filter(diary => {
      const title = (diary.title || '').toLowerCase();
      const content = (diary.content || '').toLowerCase();
      return title.includes(lowerQuery) || content.includes(lowerQuery);
    });
  },

  async getAllByStatus(userId, synced) {
    const allDiaries = await this.getAll(userId);
    return allDiaries.filter(d => d.synced === synced);
  },

  async exportAll(userId) {
    const diaries = await this.getAll(userId);
    return {
      version: 1,
      exportedAt: new Date().toISOString(),
      userId,
      diaries
    };
  },

  async importAll(data, userId) {
    if (!data.diaries || !Array.isArray(data.diaries)) {
      throw new Error('无效的备份数据格式');
    }

    return this.bulkSave(data.diaries, userId);
  }
};

const EncryptionKeyStore = {
  async getForUser(userId) {
    return executeTransaction('encryptionKeys', 'readonly', (store) => {
      return store.get(userId);
    });
  },

  async getOrCreateForUser(userId) {
    let keyRecord = await this.getForUser(userId);
    
    if (!keyRecord) {
      const key = await CryptoManager.generateKey();
      const exportedKey = await CryptoManager.exportKey(key);
      
      keyRecord = {
        userId,
        key: exportedKey,
        createdAt: new Date().toISOString(),
        algorithm: 'AES-GCM-256'
      };
      
      await this.save(keyRecord);
    }
    
    return keyRecord;
  },

  async save(keyRecord) {
    return executeTransaction('encryptionKeys', 'readwrite', (store) => {
      return store.put(keyRecord);
    });
  },

  async delete(userId) {
    return executeTransaction('encryptionKeys', 'readwrite', (store) => {
      return store.delete(userId);
    });
  },

  async rotateKey(userId) {
    const oldKeyRecord = await this.getForUser(userId);
    if (!oldKeyRecord) {
      return this.getOrCreateForUser(userId);
    }

    const newKey = await CryptoManager.generateKey();
    const newExportedKey = await CryptoManager.exportKey(newKey);
    const oldKey = await CryptoManager.importKey(oldKeyRecord.key);

    const diaries = await DiaryStore.getAll(userId);
    
    for (const diary of diaries) {
      if (diary.encrypted) {
        try {
          const decrypted = await CryptoManager.decryptDiary(diary, oldKey);
          const reencrypted = await CryptoManager.encryptDiary(decrypted, newKey);
          reencrypted.synced = false;
          await executeTransaction('diaries', 'readwrite', (store) => {
            store.put(reencrypted);
          });
        } catch (error) {
          console.error('[IDB] 密钥轮换失败，日记:', diary.id, error);
        }
      }
    }

    const newKeyRecord = {
      userId,
      key: newExportedKey,
      createdAt: new Date().toISOString(),
      algorithm: 'AES-GCM-256',
      previousKeys: oldKeyRecord.previousKeys 
        ? [...oldKeyRecord.previousKeys, oldKeyRecord]
        : [oldKeyRecord]
    };

    await this.save(newKeyRecord);
    return newKeyRecord;
  },

  async exportKeyForBackup(userId, password) {
    const keyRecord = await this.getForUser(userId);
    if (!keyRecord) {
      throw new Error('没有找到加密密钥');
    }

    const { key: derivedKey, salt } = await CryptoManager.deriveKeyFromPassword(password);
    const encryptedKey = await CryptoManager.encrypt(
      { key: keyRecord.key },
      derivedKey
    );

    return {
      encryptedKey,
      salt,
      algorithm: keyRecord.algorithm,
      createdAt: keyRecord.createdAt
    };
  },

  async importKeyFromBackup(encryptedData, password, userId) {
    const { key: derivedKey } = await CryptoManager.deriveKeyFromPassword(
      password,
      encryptedData.salt
    );

    const decrypted = await CryptoManager.decrypt(
      encryptedData.encryptedKey,
      derivedKey
    );

    const keyRecord = {
      userId,
      key: decrypted.key,
      createdAt: encryptedData.createdAt || new Date().toISOString(),
      algorithm: encryptedData.algorithm || 'AES-GCM-256',
      imported: true
    };

    await this.save(keyRecord);
    return keyRecord;
  }
};

const SettingsStore = {
  async get(key) {
    return executeTransaction('settings', 'readonly', (store) => {
      return store.get(key);
    });
  },

  async set(key, value) {
    return executeTransaction('settings', 'readwrite', (store) => {
      return store.put({
        key,
        value,
        updatedAt: new Date().toISOString()
      });
    });
  },

  async getAll() {
    return executeTransaction('settings', 'readonly', (store) => {
      const request = store.getAll();
      return request;
    });
  },

  async delete(key) {
    return executeTransaction('settings', 'readwrite', (store) => {
      return store.delete(key);
    });
  },

  async getBackupSettings(userId) {
    const settings = await this.getAll();
    const result = {};
    settings.forEach(s => {
      if (s.key.startsWith('backup.')) {
        result[s.key.replace('backup.', '')] = s.value;
      }
    });
    return result;
  },

  async setBackupSettings(userId, settings) {
    for (const [key, value] of Object.entries(settings)) {
      await this.set(`backup.${key}`, value);
    }
  }
};

const UserStore = {
  async save(user) {
    return executeTransaction('users', 'readwrite', (store) => {
      return store.put(user);
    });
  },

  async get(email) {
    return executeTransaction('users', 'readonly', (store) => {
      return store.get(email);
    });
  },

  async delete(email) {
    return executeTransaction('users', 'readwrite', (store) => {
      return store.delete(email);
    });
  },

  async bulkSave(users) {
    if (!users || users.length === 0) {
      return [];
    }

    return executeTransaction('users', 'readwrite', (store) => {
      return new Promise((resolve, reject) => {
        const results = [];
        let pending = users.length;
        
        users.forEach((user, index) => {
          const request = store.put(user);
          
          request.onsuccess = () => {
            results[index] = user;
            pending--;
            if (pending === 0) {
              resolve(results);
            }
          };
          
          request.onerror = () => {
            reject(request.error);
          };
        });
      });
    });
  }
};

const SyncQueue = {
  async add(item) {
    return executeTransaction('syncQueue', 'readwrite', (store) => {
      const itemToSave = {
        ...item,
        id: `sync_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        createdAt: item.createdAt || new Date().toISOString(),
        attempts: item.attempts || 0
      };
      
      return store.add(itemToSave);
    });
  },

  async getAll() {
    return executeTransaction('syncQueue', 'readonly', (store) => {
      const index = store.index('createdAt');
      return index.getAll();
    });
  },

  async getByType(type) {
    return executeTransaction('syncQueue', 'readonly', (store) => {
      const index = store.index('type');
      return index.getAll(type);
    });
  },

  async getByChunkId(chunkId) {
    return executeTransaction('syncQueue', 'readonly', (store) => {
      const index = store.index('chunkId');
      return index.getAll(chunkId);
    });
  },

  async remove(id) {
    return executeTransaction('syncQueue', 'readwrite', (store) => {
      return store.delete(id);
    });
  },

  async bulkRemove(ids) {
    if (!ids || ids.length === 0) {
      return;
    }

    return executeTransaction('syncQueue', 'readwrite', (store) => {
      return new Promise((resolve, reject) => {
        let pending = ids.length;
        
        ids.forEach(id => {
          const request = store.delete(id);
          
          request.onsuccess = () => {
            pending--;
            if (pending === 0) {
              resolve();
            }
          };
          
          request.onerror = () => {
            reject(request.error);
          };
        });
      });
    });
  },

  async updateAttempts(id) {
    return executeTransaction('syncQueue', 'readwrite', (store) => {
      const getRequest = store.get(id);
      
      getRequest.onsuccess = function() {
        const item = this.result;
        if (item) {
          item.attempts = (item.attempts || 0) + 1;
          store.put(item);
        }
      };
      
      return getRequest;
    });
  },

  async clear() {
    return executeTransaction('syncQueue', 'readwrite', (store) => {
      return store.clear();
    });
  },

  async getCount() {
    return executeTransaction('syncQueue', 'readonly', (store) => {
      return store.count();
    });
  },

  async getPendingChunks(chunkId) {
    const items = await this.getByChunkId(chunkId);
    return items.sort((a, b) => a.chunkIndex - b.chunkIndex);
  }
};

const BackupMetadataStore = {
  async save(metadata) {
    return executeTransaction('backupMetadata', 'readwrite', (store) => {
      const record = {
        ...metadata,
        id: metadata.id || `backup_${Date.now()}`,
        createdAt: metadata.createdAt || new Date().toISOString()
      };
      return store.put(record);
    });
  },

  async get(id) {
    return executeTransaction('backupMetadata', 'readonly', (store) => {
      return store.get(id);
    });
  },

  async getAll(userId) {
    return executeTransaction('backupMetadata', 'readonly', (store) => {
      const index = store.index('userId');
      const request = index.getAll(userId);
      
      request.onsuccess = function() {
        const sorted = this.result.sort((a, b) => 
          new Date(b.createdAt) - new Date(a.createdAt)
        );
        request.result = sorted;
      };
      
      return request;
    });
  },

  async delete(id) {
    return executeTransaction('backupMetadata', 'readwrite', (store) => {
      return store.delete(id);
    });
  },

  async getLatest(userId) {
    const all = await this.getAll(userId);
    return all[0] || null;
  }
};

window.IDB = {
  DiaryStore,
  UserStore,
  SyncQueue,
  EncryptionKeyStore,
  SettingsStore,
  BackupMetadataStore,
  openDB,
  closeDB,
  executeTransaction,
  executeMultiStoreTransaction
};

const SyncManager = {
  API_BASE: 'http://localhost:3000/api',
  isOnline: true,
  syncing: false,
  maxAttempts: 5,
  MAX_CHUNK_SIZE: 500 * 1024,
  concurrentChunks: 2,

  init() {
    this.isOnline = navigator.onLine;
    
    window.addEventListener('online', () => this.handleOnline());
    window.addEventListener('offline', () => this.handleOffline());
    
    navigator.serviceWorker?.addEventListener('message', (event) => {
      if (event.data.type === 'TRIGGER_SYNC') {
        this.startSync();
      }
    });

    if (this.isOnline) {
      setTimeout(() => this.startSync(), 1000);
    }
  },

  handleOnline() {
    console.log('[Sync] 网络已连接');
    this.isOnline = true;
    this.updateStatusUI(true);
    this.startSync();
  },

  handleOffline() {
    console.log('[Sync] 网络已断开');
    this.isOnline = false;
    this.updateStatusUI(false);
  },

  updateStatusUI(isOnline) {
    const statusEl = document.getElementById('sync-status');
    if (statusEl) {
      statusEl.textContent = isOnline ? '在线' : '离线';
      statusEl.className = `sync-status ${isOnline ? 'online' : 'offline'}`;
    }
  },

  async registerSync() {
    if ('serviceWorker' in navigator && 'SyncManager' in window) {
      try {
        const registration = await navigator.serviceWorker.ready;
        await registration.sync.register('sync-diaries');
        console.log('[Sync] 已注册后台同步');
      } catch (error) {
        console.error('[Sync] 后台同步注册失败:', error);
      }
    }
  },

  async startSync() {
    if (this.syncing || !this.isOnline) {
      return;
    }

    this.syncing = true;
    console.log('[Sync] 开始同步...');
    this.updateProgress('正在同步...');

    try {
      const queue = await IDB.SyncQueue.getAll();
      
      if (queue.length === 0) {
        console.log('[Sync] 没有待同步的项目');
        await this.syncFromServer();
        this.syncing = false;
        this.updateProgress('');
        return;
      }

      const regularItems = queue.filter(item => item.type !== 'diary-chunk');
      const chunkItems = queue.filter(item => item.type === 'diary-chunk');

      for (const item of regularItems) {
        if (item.attempts >= this.maxAttempts) {
          console.log('[Sync] 项目已超过最大尝试次数:', item.id);
          await IDB.SyncQueue.remove(item.id);
          continue;
        }

        const success = await this.syncItem(item);
        
        if (success) {
          await IDB.SyncQueue.remove(item.id);
          console.log('[Sync] 同步成功:', item.id);
        } else {
          await IDB.SyncQueue.updateAttempts(item.id);
          console.log('[Sync] 同步失败，已记录重试:', item.id);
        }
      }

      if (chunkItems.length > 0) {
        await this.syncChunks(chunkItems);
      }

      await this.syncFromServer();

    } catch (error) {
      console.error('[Sync] 同步过程出错:', error);
    } finally {
      this.syncing = false;
      this.updateProgress('');
      if (typeof window.refreshDiaryList === 'function') {
        window.refreshDiaryList();
      }
    }
  },

  updateProgress(message) {
    if (typeof window.updateSyncProgress === 'function') {
      window.updateSyncProgress(message);
    }
  },

  async syncChunks(chunkItems) {
    console.log('[Sync] 处理分块上传，共', chunkItems.length, '个块');

    const chunkGroups = {};
    chunkItems.forEach(chunk => {
      if (!chunkGroups[chunk.chunkId]) {
        chunkGroups[chunk.chunkId] = [];
      }
      chunkGroups[chunk.chunkId].push(chunk);
    });

    for (const [chunkId, chunks] of Object.entries(chunkGroups)) {
      chunks.sort((a, b) => a.chunkIndex - b.chunkIndex);
      
      const success = await this.uploadChunksSequentially(chunks, chunkId);
      
      if (success) {
        const idsToRemove = chunks.map(c => c.id);
        await IDB.SyncQueue.bulkRemove(idsToRemove);
        console.log('[Sync] 分块上传完成:', chunkId);
      }
    }
  },

  async uploadChunksSequentially(chunks, chunkId) {
    const user = await this.getCurrentUser();
    if (!user?.token) {
      console.log('[Sync] 未登录，跳过分块同步');
      return false;
    }

    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${user.token}`
    };

    const totalChunks = chunks[0].chunkCount;

    for (let i = 0; i < chunks.length; i++) {
      const chunk = chunks[i];
      this.updateProgress(`上传分块 ${chunk.chunkIndex + 1}/${totalChunks}...`);

      try {
        const response = await fetch(`${this.API_BASE}/diaries/chunk`, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            chunkId,
            chunkIndex: chunk.chunkIndex,
            chunkCount: chunk.chunkCount,
            diaryId: chunk.diaryId,
            data: chunk.data,
            action: chunk.action
          })
        });

        if (!response.ok) {
          await IDB.SyncQueue.updateAttempts(chunk.id);
          console.error('[Sync] 分块上传失败:', chunk.chunkIndex);
          return false;
        }

      } catch (error) {
        console.error('[Sync] 分块上传错误:', error);
        await IDB.SyncQueue.updateAttempts(chunk.id);
        return false;
      }
    }

    this.updateProgress('完成分块上传...');
    return true;
  },

  async uploadChunksInParallel(chunks, chunkId) {
    const user = await this.getCurrentUser();
    if (!user?.token) {
      console.log('[Sync] 未登录，跳过分块同步');
      return false;
    }

    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${user.token}`
    };

    const results = [];
    
    for (let i = 0; i < chunks.length; i += this.concurrentChunks) {
      const batch = chunks.slice(i, i + this.concurrentChunks);
      this.updateProgress(`上传分块 ${i + 1}-${Math.min(i + this.concurrentChunks, chunks.length)}/${chunks.length}...`);

      const batchPromises = batch.map(async (chunk) => {
        try {
          const response = await fetch(`${this.API_BASE}/diaries/chunk`, {
            method: 'POST',
            headers,
            body: JSON.stringify({
              chunkId,
              chunkIndex: chunk.chunkIndex,
              chunkCount: chunk.chunkCount,
              diaryId: chunk.diaryId,
              data: chunk.data,
              action: chunk.action
            })
          });

          return {
            success: response.ok,
            chunkId: chunk.id
          };
        } catch (error) {
          return {
            success: false,
            chunkId: chunk.id
          };
        }
      });

      const batchResults = await Promise.all(batchPromises);
      results.push(...batchResults);
    }

    const successfulIds = results.filter(r => r.success).map(r => r.chunkId);
    await IDB.SyncQueue.bulkRemove(successfulIds);

    const failedIds = results.filter(r => !r.success).map(r => r.chunkId);
    for (const id of failedIds) {
      await IDB.SyncQueue.updateAttempts(id);
    }

    return results.every(r => r.success);
  },

  async syncItem(item) {
    try {
      const user = await this.getCurrentUser();
      if (!user?.token) {
        console.log('[Sync] 未登录，跳过同步');
        return false;
      }

      const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${user.token}`
      };

      if (item.type === 'diary') {
        return await this.syncDiaryItem(item, headers);
      }

      return false;
    } catch (error) {
      console.error('[Sync] 同步项目失败:', error);
      return false;
    }
  },

  async syncDiaryItem(item, headers) {
    const { action, data } = item;

    try {
      let response;

      switch (action) {
        case 'create':
        case 'update':
          response = await fetch(`${this.API_BASE}/diaries`, {
            method: 'POST',
            headers,
            body: JSON.stringify(data)
          });
          break;

        case 'delete':
          response = await fetch(`${this.API_BASE}/diaries/${data.id}`, {
            method: 'DELETE',
            headers
          });
          break;

        default:
          return false;
      }

      if (response.ok) {
        if (action !== 'delete' && data.id) {
          await IDB.DiaryStore.markSynced(data.id);
        }
        return true;
      }

      return false;
    } catch (error) {
      console.error('[Sync] 日记同步失败:', error);
      return false;
    }
  },

  async syncFromServer() {
    try {
      const user = await this.getCurrentUser();
      if (!user?.token) return;

      const response = await fetch(`${this.API_BASE}/diaries`, {
        headers: {
          'Authorization': `Bearer ${user.token}`
        }
      });

      if (!response.ok) return;

      const serverDiaries = await response.json();
      const localDiaries = await IDB.DiaryStore.getAll(user.id);
      
      const localIds = new Set(localDiaries.map(d => d.id));

      for (const serverDiary of serverDiaries) {
        const localDiary = localDiaries.find(d => d.id === serverDiary.id);
        
        if (!localDiary || new Date(serverDiary.updatedAt) > new Date(localDiary.updatedAt)) {
          serverDiary.synced = true;
          serverDiary.userId = user.id;
          await IDB.DiaryStore.save(serverDiary, user.id);
        }
      }

      console.log('[Sync] 从服务器同步完成');
    } catch (error) {
      console.error('[Sync] 从服务器同步失败:', error);
    }
  },

  async getCurrentUser() {
    try {
      const userStr = localStorage.getItem('currentUser');
      if (userStr) {
        return JSON.parse(userStr);
      }
    } catch (error) {
      console.error('[Sync] 获取用户信息失败:', error);
    }
    return null;
  },

  async queueForSync(type, action, data) {
    await IDB.SyncQueue.add({
      type,
      action,
      data,
      createdAt: new Date().toISOString()
    });

    if (this.isOnline) {
      this.startSync();
    } else {
      this.registerSync();
    }
  },

  async getSyncStatus() {
    const count = await IDB.SyncQueue.getCount();
    return {
      online: this.isOnline,
      syncing: this.syncing,
      pendingCount: count
    };
  },

  async forceSync() {
    if (!this.isOnline) {
      throw new Error('当前处于离线状态');
    }
    return this.startSync();
  }
};

window.SyncManager = SyncManager;

document.addEventListener('DOMContentLoaded', () => {
  SyncManager.init();
});

const GoogleDriveBackup = {
  CLIENT_ID: '',
  API_KEY: '',
  SCOPES: 'https://www.googleapis.com/auth/drive.file',
  DISCOVERY_DOCS: ['https://www.googleapis.com/discovery/v1/apis/drive/v3/rest'],
  
  isAuthenticated: false,
  tokenClient: null,
  gapiInited: false,
  gisInited: false,
  initialized: false,

  async init(clientId, apiKey) {
    if (this.initialized) return true;

    this.CLIENT_ID = clientId || this.CLIENT_ID;
    this.API_KEY = apiKey || this.API_KEY;

    if (!this.CLIENT_ID || !this.API_KEY) {
      console.warn('[Backup] 未配置 Google API 凭证，使用本地备份模式');
      this.initialized = true;
      return false;
    }

    try {
      await this.loadGoogleAPIs();
      this.initialized = true;
      return true;
    } catch (error) {
      console.error('[Backup] Google API 加载失败:', error);
      this.initialized = true;
      return false;
    }
  },

  loadGoogleAPIs() {
    return new Promise((resolve, reject) => {
      if (typeof gapi !== 'undefined' && typeof google !== 'undefined') {
        resolve();
        return;
      }

      const gapiScript = document.createElement('script');
      gapiScript.src = 'https://apis.google.com/js/api.js';
      gapiScript.async = true;
      gapiScript.defer = true;
      gapiScript.onload = () => {
        gapi.load('client:auth2', async () => {
          await gapi.client.init({
            apiKey: this.API_KEY,
            discoveryDocs: this.DISCOVERY_DOCS,
          });
          this.gapiInited = true;
        });
      };
      gapiScript.onerror = () => reject(new Error('Google API 加载失败'));
      document.head.appendChild(gapiScript);

      const gisScript = document.createElement('script');
      gisScript.src = 'https://accounts.google.com/gsi/client';
      gisScript.async = true;
      gisScript.defer = true;
      gisScript.onload = () => {
        this.tokenClient = google.accounts.oauth2.initTokenClient({
          client_id: this.CLIENT_ID,
          scope: this.SCOPES,
          callback: (response) => {
            if (response.error !== undefined) {
              throw (response);
            }
            this.isAuthenticated = true;
          },
        });
        this.gisInited = true;
      };
      gisScript.onerror = () => reject(new Error('Google Identity Services 加载失败'));
      document.head.appendChild(gisScript);

      const checkInterval = setInterval(() => {
        if (this.gapiInited && this.gisInited) {
          clearInterval(checkInterval);
          resolve();
        }
      }, 100);

      setTimeout(() => {
        clearInterval(checkInterval);
        reject(new Error('Google API 加载超时'));
      }, 10000);
    });
  },

  async authenticate() {
    if (this.isAuthenticated) return true;
    if (!this.tokenClient) return false;

    return new Promise((resolve, reject) => {
      this.tokenClient.requestAccessToken({
        prompt: 'consent',
        callback: (response) => {
          if (response.error) {
            reject(new Error(response.error));
          } else {
            this.isAuthenticated = true;
            resolve(true);
          }
        }
      });
    });
  },

  async createBackup(userId, options = {}) {
    const { includeEncrypted = false, progressCallback = null } = options;

    if (progressCallback) progressCallback('正在收集数据...');

    const exportData = await IDB.DiaryStore.exportAll(userId);
    const keyRecord = await IDB.EncryptionKeyStore.getForUser(userId);
    
    const backupData = {
      version: 1,
      created: new Date().toISOString(),
      userId,
      data: exportData,
      hasEncryptionKey: !!keyRecord
    };

    if (keyRecord && options.encryptionPassword) {
      const encryptedKey = await IDB.EncryptionKeyStore.exportKeyForBackup(
        userId,
        options.encryptionPassword
      );
      backupData.encryptedKey = encryptedKey;
    }

    const backupJson = JSON.stringify(backupData);
    const backupBlob = new Blob([backupJson], { type: 'application/json' });

    const metadata = {
      id: `backup_${Date.now()}`,
      userId,
      createdAt: backupData.created,
      size: backupBlob.size,
      diaryCount: exportData.diaries.length,
      hasEncryption: !!keyRecord
    };

    await IDB.BackupMetadataStore.save(metadata);

    if (progressCallback) progressCallback('正在保存到本地...');

    const localFile = new File([backupBlob], `diary-backup-${new Date().toISOString().slice(0, 10)}.json`, {
      type: 'application/json'
    });

    if (progressCallback) progressCallback('正在上传到云端...');

    if (this.isAuthenticated && this.gapiInited) {
      try {
        const fileId = await this.uploadToDrive(backupBlob, metadata);
        metadata.driveFileId = fileId;
        await IDB.BackupMetadataStore.save(metadata);
        if (progressCallback) progressCallback('备份完成！');
      } catch (error) {
        console.warn('[Backup] 云端上传失败，仅保存到本地:', error);
        if (progressCallback) progressCallback('已保存到本地（云端上传失败）');
      }
    } else {
      if (progressCallback) progressCallback('已保存到本地（请下载文件）');
    }

    return {
      metadata,
      file: localFile,
      backupData
    };
  },

  async uploadToDrive(blob, metadata) {
    const fileMetadata = {
      name: `OfflineDiary-Backup-${metadata.createdAt.slice(0, 10)}.json`,
      mimeType: 'application/json',
      parents: ['appDataFolder']
    };

    const form = new FormData();
    form.append('metadata', new Blob([JSON.stringify(fileMetadata)], { type: 'application/json' }));
    form.append('file', blob);

    const response = await gapi.client.drive.files.create({
      resource: fileMetadata,
      media: {
        mimeType: 'application/json',
        body: blob
      },
      fields: 'id'
    });

    return response.result.id;
  },

  async listBackups(userId) {
    const localBackups = await IDB.BackupMetadataStore.getAll(userId);
    
    let driveBackups = [];
    if (this.isAuthenticated && this.gapiInited) {
      try {
        driveBackups = await this.listDriveBackups();
      } catch (error) {
        console.warn('[Backup] 获取云端备份失败:', error);
      }
    }

    return {
      local: localBackups,
      drive: driveBackups
    };
  },

  async listDriveBackups() {
    const response = await gapi.client.drive.files.list({
      spaces: 'appDataFolder',
      fields: 'files(id, name, createdTime, size)',
      orderBy: 'createdTime desc'
    });

    return response.result.files.map(file => ({
      id: file.id,
      name: file.name,
      createdAt: file.createdTime,
      size: parseInt(file.size || '0'),
      source: 'drive'
    }));
  },

  async restoreBackup(backupId, options = {}) {
    const { progressCallback = null, encryptionPassword = null } = options;

    if (progressCallback) progressCallback('正在读取备份数据...');

    let backupData;
    let metadata;

    metadata = await IDB.BackupMetadataStore.get(backupId);

    if (metadata) {
      if (metadata.driveFileId && this.isAuthenticated) {
        try {
          backupData = await this.downloadFromDrive(metadata.driveFileId);
        } catch (error) {
          console.warn('[Backup] 从云端下载失败:', error);
        }
      }
    }

    if (!backupData && backupId.startsWith('drive_')) {
      const driveId = backupId.replace('drive_', '');
      backupData = await this.downloadFromDrive(driveId);
    }

    if (!backupData) {
      throw new Error('无法找到备份数据');
    }

    if (progressCallback) progressCallback('正在恢复数据...');

    if (backupData.encryptedKey && encryptionPassword) {
      try {
        await IDB.EncryptionKeyStore.importKeyFromBackup(
          backupData.encryptedKey,
          encryptionPassword,
          backupData.userId
        );
        if (progressCallback) progressCallback('加密密钥已恢复');
      } catch (error) {
        console.warn('[Backup] 密钥恢复失败，可能是密码错误:', error);
      }
    }

    await IDB.DiaryStore.importAll(backupData.data, backupData.userId);

    if (progressCallback) progressCallback('恢复完成！');

    return {
      success: true,
      diaryCount: backupData.data.diaries.length,
      backupDate: backupData.created
    };
  },

  async downloadFromDrive(fileId) {
    const response = await gapi.client.drive.files.get({
      fileId,
      alt: 'media'
    });

    const text = typeof response.body === 'string' 
      ? response.body 
      : JSON.stringify(response.result);
    
    return JSON.parse(text);
  },

  async downloadBackupFile(backupId) {
    const metadata = await IDB.BackupMetadataStore.get(backupId);
    if (!metadata) {
      throw new Error('备份不存在');
    }

    const exportData = await IDB.DiaryStore.exportAll(metadata.userId);
    const backupData = {
      version: 1,
      created: metadata.createdAt,
      userId: metadata.userId,
      data: exportData,
      hasEncryptionKey: metadata.hasEncryption
    };

    const keyRecord = await IDB.EncryptionKeyStore.getForUser(metadata.userId);
    if (keyRecord) {
      backupData.keyInfo = {
        algorithm: keyRecord.algorithm,
        createdAt: keyRecord.createdAt
      };
    }

    const blob = new Blob([JSON.stringify(backupData, null, 2)], {
      type: 'application/json'
    });

    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `diary-backup-${metadata.createdAt.slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },

  async importFromFile(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      
      reader.onload = async (e) => {
        try {
          const backupData = JSON.parse(e.target.result);
          
          if (!backupData.version || !backupData.data || !backupData.data.diaries) {
            throw new Error('无效的备份文件格式');
          }

          resolve(backupData);
        } catch (error) {
          reject(error);
        }
      };

      reader.onerror = () => reject(new Error('文件读取失败'));
      reader.readAsText(file);
    });
  },

  async deleteBackup(backupId) {
    await IDB.BackupMetadataStore.delete(backupId);
    
    if (backupId.startsWith('drive_') && this.isAuthenticated) {
      const driveId = backupId.replace('drive_', '');
      try {
        await gapi.client.drive.files.delete({ fileId: driveId });
      } catch (error) {
        console.warn('[Backup] 删除云端备份失败:', error);
      }
    }
  },

  async signOut() {
    if (gapi.auth2) {
      const auth2 = gapi.auth2.getAuthInstance();
      if (auth2) {
        auth2.signOut();
      }
    }
    this.isAuthenticated = false;
  }
};

window.GoogleDriveBackup = GoogleDriveBackup;

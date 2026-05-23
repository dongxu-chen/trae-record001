const EventEmitter = require('events');
const path = require('path');
const chokidar = require('chokidar');
const FileUtils = require('./FileUtils');
const SyncState = require('./SyncState');

const SYNC_INTERVAL = 30000;
const CONCURRENT_TRANSFERS = 3;
const CHUNK_SIZE = 1024 * 1024;
const MINIMUM_CHUNK_SIZE = 512 * 1024;

class SyncEngine extends EventEmitter {
  constructor(cloudAPI) {
    super();
    this.cloudAPI = cloudAPI;
    this.syncState = new SyncState();
    this.watcher = null;
    this.isRunning = false;
    this.isPaused = false;
    this.syncInterval = null;
    this.syncFolder = null;
    this.transferQueue = [];
    this.activeTransfers = 0;
  }

  async setSyncFolder(folderPath) {
    this.syncFolder = folderPath;
    this.syncState.setSyncFolder(folderPath);
  }

  async start() {
    if (this.isRunning) return;
    
    this.isRunning = true;
    this.isPaused = false;
    
    this.startFileWatcher();
    this.startSyncInterval();
    
    await this.performFullSync();
    
    this.emit('sync-status', { status: 'running' });
  }

  async stop() {
    this.isRunning = false;
    this.isPaused = false;
    
    this.stopFileWatcher();
    this.stopSyncInterval();
    
    this.emit('sync-status', { status: 'stopped' });
  }

  pause() {
    this.isPaused = true;
    this.emit('sync-status', { status: 'paused' });
  }

  resume() {
    this.isPaused = false;
    this.emit('sync-status', { status: 'running' });
  }

  getStatus() {
    return {
      isRunning: this.isRunning,
      isPaused: this.isPaused,
      syncFolder: this.syncFolder,
      lastSyncTime: this.syncState.getLastSyncTime(),
      queueLength: this.transferQueue.length,
      activeTransfers: this.activeTransfers
    };
  }

  getHistory() {
    return this.syncState.getHistory();
  }

  getHistoryWithFilters(options) {
    return this.syncState.getHistoryWithFilters(options);
  }

  getHistoryStats(days) {
    return this.syncState.getHistoryStats(days);
  }

  getSelectedFolders() {
    return this.syncState.getSelectedFolders();
  }

  setSelectedFolders(folders) {
    this.syncState.setSelectedFolders(folders);
  }

  isPathIncluded(relativePath) {
    return this.syncState.isFolderSelected(relativePath);
  }

  async scanFolders() {
    if (!this.syncFolder) return [];
    
    const results = [];
    const items = await FileUtils.walkDirectory(this.syncFolder);
    
    const folderSet = new Set();
    for (const item of items) {
      const dirPath = path.dirname(item.path);
      if (dirPath && dirPath !== '.') {
        const parts = dirPath.split('/');
        let current = '';
        for (const part of parts) {
          current = current ? current + '/' + part : part;
          folderSet.add(current);
        }
      }
    }
    
    const sortedFolders = Array.from(folderSet).sort();
    return sortedFolders.map(folder => ({
      path: folder,
      selected: this.syncState.isFolderSelected(folder)
    }));
  }

  startFileWatcher() {
    if (this.watcher) return;
    
    this.watcher = chokidar.watch(this.syncFolder, {
      ignoreInitial: true,
      persistent: true,
      ignorePermissionErrors: true,
      interval: 1000,
      binaryInterval: 3000
    });

    this.watcher.on('add', (filePath) => this.handleFileChange(filePath, 'add'));
    this.watcher.on('change', (filePath) => this.handleFileChange(filePath, 'change'));
    this.watcher.on('unlink', (filePath) => this.handleFileChange(filePath, 'delete'));
    this.watcher.on('addDir', (filePath) => this.handleFileChange(filePath, 'addDir'));
    this.watcher.on('unlinkDir', (filePath) => this.handleFileChange(filePath, 'deleteDir'));
  }

  stopFileWatcher() {
    if (this.watcher) {
      this.watcher.close();
      this.watcher = null;
    }
  }

  startSyncInterval() {
    this.syncInterval = setInterval(() => {
      if (this.isRunning && !this.isPaused) {
        this.performFullSync().catch(err => {
          this.emit('error', err.message);
        });
      }
    }, SYNC_INTERVAL);
  }

  stopSyncInterval() {
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
      this.syncInterval = null;
    }
  }

  async handleFileChange(filePath, eventType) {
    if (!this.isRunning || this.isPaused) return;
    
    const relativePath = path.relative(this.syncFolder, filePath).replace(/\\/g, '/');
    
    if (!this.isPathIncluded(relativePath)) {
      return;
    }
    
    this.emit('sync-status', { status: 'syncing', file: relativePath, action: eventType });
    
    try {
      if (eventType === 'add' || eventType === 'change') {
        await this.uploadFileWithResume(relativePath);
      } else if (eventType === 'delete') {
        await this.cloudAPI.deleteFile(relativePath);
        this.syncState.removeFileState(relativePath);
        this.addHistory(relativePath, 'delete', 'local');
      } else if (eventType === 'addDir') {
        await this.cloudAPI.createFolder(relativePath);
      } else if (eventType === 'deleteDir') {
        await this.cloudAPI.deleteFolder(relativePath);
      }
    } catch (error) {
      this.emit('error', `Failed to handle ${eventType} for ${relativePath}: ${error.message}`);
    }
  }

  async performFullSync() {
    if (!this.isRunning || this.isPaused) return;
    
    this.emit('sync-status', { status: 'scanning' });
    
    try {
      const [localFiles, cloudFiles] = await Promise.all([
        this.getLocalFiles(),
        this.getCloudFiles()
      ]);
      
      const filteredLocalFiles = localFiles.filter(f => this.isPathIncluded(f.path));
      const filteredCloudFiles = cloudFiles.filter(f => this.isPathIncluded(f.path));
      
      const cloudFileMap = new Map(filteredCloudFiles.map(f => [f.path, f]));
      const localFileMap = new Map(filteredLocalFiles.map(f => [f.path, f]));
      
      const conflicts = [];
      const toUpload = [];
      const toDownload = [];
      const toDeleteLocal = [];
      const toDeleteCloud = [];
      
      for (const localFile of filteredLocalFiles) {
        const cloudFile = cloudFileMap.get(localFile.path);
        const savedState = this.syncState.getFileState(localFile.path);
        
        if (!cloudFile) {
          toUpload.push(localFile);
        } else {
          const conflict = await this.detectConflict(localFile, cloudFile, savedState);
          if (conflict) {
            conflicts.push(conflict);
          } else if (this.isLocalNewer(localFile, cloudFile, savedState)) {
            toUpload.push(localFile);
          } else if (this.isCloudNewer(localFile, cloudFile, savedState)) {
            toDownload.push(cloudFile);
          }
        }
      }
      
      for (const cloudFile of filteredCloudFiles) {
        if (!localFileMap.has(cloudFile.path)) {
          const savedState = this.syncState.getFileState(cloudFile.path);
          if (savedState && savedState.deletedLocally) {
            toDeleteCloud.push(cloudFile);
          } else {
            toDownload.push(cloudFile);
          }
        }
      }
      
      for (const conflict of conflicts) {
        const savedConflict = this.syncState.addConflict(conflict);
        this.emit('conflict-detected', savedConflict);
      }
      
      await this.processSyncQueue(toUpload, toDownload);
      
      this.syncState.setLastSyncTime(Date.now());
      
      this.emit('sync-complete', {
        uploaded: toUpload.length,
        downloaded: toDownload.length,
        conflicts: conflicts.length,
        timestamp: Date.now()
      });
      
    } catch (error) {
      this.emit('error', `Full sync failed: ${error.message}`);
    }
  }

  async getLocalFiles() {
    return await FileUtils.walkDirectory(this.syncFolder);
  }

  async getCloudFiles() {
    try {
      const response = await this.cloudAPI.getFileList();
      return response.files || [];
    } catch (error) {
      this.emit('error', `Failed to get cloud files: ${error.message}`);
      return [];
    }
  }

  async detectConflict(localFile, cloudFile, savedState) {
    const localModified = localFile.mtime;
    const cloudModified = cloudFile.mtime || 0;
    
    const localChanged = !savedState || 
                         localModified > (savedState.localMtime || 0) || 
                         localFile.size !== (savedState.size || 0);
    const cloudChanged = !savedState ||
                         cloudModified > (savedState.cloudMtime || 0) ||
                         cloudFile.size !== (savedState.size || 0);
    
    if (localChanged && cloudChanged) {
      if (localFile.size === cloudFile.size) {
        const localChecksum = await FileUtils.calculateSHA256(localFile.fullPath);
        const cloudChecksum = cloudFile.sha256 || cloudFile.checksum || '';
        
        if (localChecksum === cloudChecksum) {
          return null;
        }
      }
      
      const localChecksum = await FileUtils.calculateSHA256(localFile.fullPath);
      const cloudChecksum = cloudFile.sha256 || cloudFile.checksum || '';
      
      return {
        filePath: localFile.path,
        localFullPath: localFile.fullPath,
        localMtime: localModified,
        cloudMtime: cloudModified,
        localSize: localFile.size,
        cloudSize: cloudFile.size,
        localChecksum,
        cloudChecksum,
        type: 'both-modified'
      };
    }
    
    return null;
  }

  isLocalNewer(localFile, cloudFile, savedState) {
    if (!savedState) {
      return localFile.mtime > (cloudFile.mtime || 0);
    }
    return localFile.mtime > savedState.localMtime;
  }

  isCloudNewer(localFile, cloudFile, savedState) {
    if (!savedState) {
      return (cloudFile.mtime || 0) > localFile.mtime;
    }
    return (cloudFile.mtime || 0) > savedState.cloudMtime;
  }

  async processSyncQueue(toUpload, toDownload) {
    this.transferQueue = [
      ...toUpload.map(f => ({ type: 'upload', file: f })),
      ...toDownload.map(f => ({ type: 'download', file: f }))
    ];
    
    await this.processTransferQueue();
  }

  async processTransferQueue() {
    while (this.transferQueue.length > 0 && this.activeTransfers < CONCURRENT_TRANSFERS) {
      const item = this.transferQueue.shift();
      if (item) {
        this.activeTransfers++;
        this.processTransfer(item).finally(() => {
          this.activeTransfers--;
          this.processTransferQueue();
        });
      }
    }
  }

  async processTransfer(item) {
    if (!this.isRunning || this.isPaused) return;
    
    try {
      if (item.type === 'upload') {
        await this.uploadFileWithResume(item.file.path);
      } else if (item.type === 'download') {
        await this.downloadFileWithResume(item.file.path);
      }
    } catch (error) {
      this.emit('error', `${item.type} failed for ${item.file.path}: ${error.message}`);
    }
  }

  async uploadFileWithResume(relativePath) {
    const localPath = path.join(this.syncFolder, relativePath);
    const fileSize = await FileUtils.getFileSize(localPath);
    
    const chunkMap = this.syncState.getChunkMap(relativePath);
    const totalChunks = Math.ceil(fileSize / CHUNK_SIZE);
    
    let uploadedBytes = this.calculateUploadedBytes(chunkMap, totalChunks, fileSize);
    
    if (uploadedBytes > 0 && uploadedBytes < fileSize) {
      try {
        const serverStatus = await this.cloudAPI.getUploadStatus(relativePath);
        if (serverStatus.chunkMap) {
          for (let i = 0; i < totalChunks; i++) {
            if (serverStatus.chunkMap[i]) {
              chunkMap[i] = true;
            }
          }
          uploadedBytes = this.calculateUploadedBytes(chunkMap, totalChunks, fileSize);
        }
      } catch (error) {
        // 服务器状态查询失败，使用本地记录
      }
    }
    
    this.emit('sync-progress', {
      filePath: relativePath,
      action: 'upload',
      progress: (uploadedBytes / fileSize) * 100,
      uploaded: uploadedBytes,
      total: fileSize,
      chunks: totalChunks,
      uploadedChunks: Object.keys(chunkMap).filter(k => chunkMap[k]).length
    });
    
    for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
      if (!this.isRunning || this.isPaused) {
        this.syncState.setChunkMap(relativePath, chunkMap);
        return;
      }
      
      if (chunkMap[chunkIndex]) {
        continue;
      }
      
      const startByte = chunkIndex * CHUNK_SIZE;
      const endByte = Math.min(startByte + CHUNK_SIZE, fileSize);
      
      try {
        await this.cloudAPI.uploadChunk(localPath, relativePath, {
          chunkIndex,
          startByte,
          endByte,
          totalChunks,
          fileSize,
          onProgress: (progress) => {
            const currentUploaded = startByte + (endByte - startByte) * (progress.chunkProgress / 100);
            this.emit('sync-progress', {
              filePath: relativePath,
              action: 'upload',
              progress: (currentUploaded / fileSize) * 100,
              uploaded: currentUploaded,
              total: fileSize,
              chunks: totalChunks,
              uploadedChunks: Object.keys(chunkMap).filter(k => chunkMap[k]).length,
              currentChunk: chunkIndex + 1
            });
          }
        });
        
        chunkMap[chunkIndex] = true;
        this.syncState.setChunkMap(relativePath, chunkMap);
        
      } catch (error) {
        this.syncState.setChunkMap(relativePath, chunkMap);
        throw error;
      }
    }
    
    const checksum = await FileUtils.calculateSHA256(localPath);
    const stats = await FileUtils.getFileInfo(localPath, this.syncFolder);
    
    try {
      await this.cloudAPI.completeUpload(relativePath, {
        fileSize,
        sha256: checksum,
        totalChunks
      });
    } catch (error) {
      // 完成上传请求可能失败，但文件已传输完毕
      console.warn('Complete upload warning:', error.message);
    }
    
    this.syncState.setFileState(relativePath, {
      path: relativePath,
      size: stats.size,
      localMtime: stats.mtime,
      cloudMtime: Date.now(),
      sha256: checksum
    });
    
    this.syncState.clearChunkMap(relativePath);
    this.syncState.clearUploadProgress(relativePath);
    this.addHistory(relativePath, 'upload', 'local');
  }

  calculateUploadedBytes(chunkMap, totalChunks, fileSize) {
    let uploaded = 0;
    for (let i = 0; i < totalChunks; i++) {
      if (chunkMap[i]) {
        const startByte = i * CHUNK_SIZE;
        const endByte = Math.min(startByte + CHUNK_SIZE, fileSize);
        uploaded += (endByte - startByte);
      }
    }
    return uploaded;
  }

  async downloadFileWithResume(relativePath) {
    const localPath = path.join(this.syncFolder, relativePath);
    await FileUtils.ensureFileDirectory(localPath);
    
    try {
      const metadata = await this.cloudAPI.getFileMetadata(relativePath);
      const fileSize = metadata.size || 0;
      const totalChunks = Math.ceil(fileSize / CHUNK_SIZE);
      
      const chunkMap = this.syncState.getChunkMap(relativePath, 'download');
      let downloadedBytes = this.calculateUploadedBytes(chunkMap, totalChunks, fileSize);
      
      if (await FileUtils.fileExists(localPath)) {
        const existingSize = await FileUtils.getFileSize(localPath);
        if (existingSize !== fileSize) {
          await FileUtils.deleteFile(localPath);
          for (let i = 0; i < totalChunks; i++) {
            delete chunkMap[i];
          }
          downloadedBytes = 0;
        }
      }
      
      this.emit('sync-progress', {
        filePath: relativePath,
        action: 'download',
        progress: (downloadedBytes / fileSize) * 100,
        downloaded: downloadedBytes,
        total: fileSize,
        chunks: totalChunks,
        downloadedChunks: Object.keys(chunkMap).filter(k => chunkMap[k]).length
      });
      
      const fs = require('fs');
      let fileHandle = null;
      
      try {
        fileHandle = await fs.promises.open(localPath, 'r+');
      } catch {
        fileHandle = await fs.promises.open(localPath, 'w');
      }
      
      for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
        if (!this.isRunning || this.isPaused) {
          await fileHandle.close();
          this.syncState.setChunkMap(relativePath, chunkMap, 'download');
          return;
        }
        
        if (chunkMap[chunkIndex]) {
          continue;
        }
        
        const startByte = chunkIndex * CHUNK_SIZE;
        const endByte = Math.min(startByte + CHUNK_SIZE, fileSize) - 1;
        
        try {
          const chunkData = await this.cloudAPI.downloadChunk(relativePath, {
            startByte,
            endByte,
            chunkIndex,
            totalChunks
          });
          
          await fileHandle.write(chunkData, 0, chunkData.length, startByte);
          
          chunkMap[chunkIndex] = true;
          this.syncState.setChunkMap(relativePath, chunkMap, 'download');
          
          const currentDownloaded = (chunkIndex + 1) * CHUNK_SIZE;
          this.emit('sync-progress', {
            filePath: relativePath,
            action: 'download',
            progress: Math.min(100, (currentDownloaded / fileSize) * 100),
            downloaded: Math.min(currentDownloaded, fileSize),
            total: fileSize,
            chunks: totalChunks,
            downloadedChunks: Object.keys(chunkMap).filter(k => chunkMap[k]).length,
            currentChunk: chunkIndex + 1
          });
          
        } catch (error) {
          await fileHandle.close();
          this.syncState.setChunkMap(relativePath, chunkMap, 'download');
          throw error;
        }
      }
      
      await fileHandle.close();
      
      const checksum = await FileUtils.calculateSHA256(localPath);
      const stats = await FileUtils.getFileInfo(localPath, this.syncFolder);
      
      this.syncState.setFileState(relativePath, {
        path: relativePath,
        size: stats.size,
        localMtime: stats.mtime,
        cloudMtime: metadata.mtime || Date.now(),
        sha256: checksum
      });
      
      this.syncState.clearChunkMap(relativePath, 'download');
      this.addHistory(relativePath, 'download', 'cloud');
      
    } catch (error) {
      throw error;
    }
  }

  async resolveConflict(conflictId, resolution) {
    const conflict = this.syncState.resolveConflict(conflictId, resolution);
    
    if (!conflict) {
      throw new Error('Conflict not found');
    }
    
    switch (resolution) {
      case 'keep-local':
        await this.uploadFileWithResume(conflict.filePath);
        break;
      case 'keep-cloud':
        await this.downloadFileWithResume(conflict.filePath);
        break;
      case 'keep-both':
        await this.keepBoth(conflict);
        break;
      default:
        throw new Error('Invalid resolution type');
    }
    
    this.syncState.removeConflict(conflictId);
  }

  async keepBoth(conflict) {
    const localPath = path.join(this.syncFolder, conflict.filePath);
    const ext = path.extname(conflict.filePath);
    const baseName = path.basename(conflict.filePath, ext);
    const dirName = path.dirname(conflict.filePath);
    
    const newLocalPath = path.join(
      this.syncFolder,
      dirName,
      `${baseName}_local${ext}`
    );
    
    const fs = require('fs').promises;
    await fs.copyFile(localPath, newLocalPath);
    
    await this.uploadFileWithResume(conflict.filePath);
    
    const newRelativePath = path.relative(this.syncFolder, newLocalPath).replace(/\\/g, '/');
    await this.uploadFileWithResume(newRelativePath);
  }

  addHistory(filePath, action, source) {
    this.syncState.addHistoryEntry({
      filePath,
      action,
      source
    });
  }
}

module.exports = SyncEngine;

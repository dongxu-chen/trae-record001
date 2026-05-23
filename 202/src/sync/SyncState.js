const fs = require('fs');
const path = require('path');
const os = require('os');

class SyncState {
  constructor() {
    this.stateFilePath = this.getStateFilePath();
    this.state = {
      syncFolder: null,
      files: {},
      conflicts: [],
      history: [],
      lastSyncTime: null,
      uploadsInProgress: {},
      chunkMaps: {
        upload: {},
        download: {}
      },
      selectedFolders: {},
      settings: {
        runInBackground: true,
        showNotifications: true,
        historyDays: 30
      }
    };
    this.load();
  }

  getStateFilePath() {
    const appDir = path.join(os.homedir(), '.filesync-client');
    if (!fs.existsSync(appDir)) {
      fs.mkdirSync(appDir, { recursive: true });
    }
    return path.join(appDir, 'sync-state.json');
  }

  load() {
    try {
      if (fs.existsSync(this.stateFilePath)) {
        const data = fs.readFileSync(this.stateFilePath, 'utf8');
        const loadedState = JSON.parse(data);
        this.state = { ...this.state, ...loadedState };
      }
    } catch (error) {
      console.error('Failed to load sync state:', error);
    }
  }

  save() {
    try {
      const data = JSON.stringify(this.state, null, 2);
      fs.writeFileSync(this.stateFilePath, data, 'utf8');
    } catch (error) {
      console.error('Failed to save sync state:', error);
    }
  }

  getSyncFolder() {
    return this.state.syncFolder;
  }

  setSyncFolder(folderPath) {
    this.state.syncFolder = folderPath;
    this.save();
  }

  getFileState(filePath) {
    return this.state.files[filePath] || null;
  }

  setFileState(filePath, fileState) {
    this.state.files[filePath] = {
      ...fileState,
      lastSynced: Date.now()
    };
    this.save();
  }

  removeFileState(filePath) {
    delete this.state.files[filePath];
    this.save();
  }

  getAllFileStates() {
    return { ...this.state.files };
  }

  getConflicts() {
    return [...this.state.conflicts];
  }

  addConflict(conflict) {
    const conflictId = this.generateConflictId();
    const newConflict = {
      id: conflictId,
      ...conflict,
      timestamp: Date.now(),
      resolved: false
    };
    this.state.conflicts.push(newConflict);
    this.save();
    return newConflict;
  }

  resolveConflict(conflictId, resolution) {
    const conflict = this.state.conflicts.find(c => c.id === conflictId);
    if (conflict) {
      conflict.resolved = true;
      conflict.resolution = resolution;
      conflict.resolvedAt = Date.now();
      this.save();
    }
    return conflict;
  }

  removeConflict(conflictId) {
    this.state.conflicts = this.state.conflicts.filter(c => c.id !== conflictId);
    this.save();
  }

  getUnresolvedConflicts() {
    return this.state.conflicts.filter(c => !c.resolved);
  }

  getHistory(limit = 100) {
    return this.state.history.slice(-limit).reverse();
  }

  addHistoryEntry(entry) {
    this.state.history.push({
      ...entry,
      timestamp: Date.now()
    });
    if (this.state.history.length > 1000) {
      this.state.history = this.state.history.slice(-500);
    }
    this.save();
  }

  getLastSyncTime() {
    return this.state.lastSyncTime;
  }

  setLastSyncTime(time) {
    this.state.lastSyncTime = time;
    this.save();
  }

  getUploadProgress(filePath) {
    return this.state.uploadsInProgress[filePath] || null;
  }

  setUploadProgress(filePath, progress) {
    if (progress) {
      this.state.uploadsInProgress[filePath] = progress;
    } else {
      delete this.state.uploadsInProgress[filePath];
    }
    this.save();
  }

  clearUploadProgress(filePath) {
    delete this.state.uploadsInProgress[filePath];
    this.save();
  }

  getAllUploadsInProgress() {
    return { ...this.state.uploadsInProgress };
  }

  getChunkMap(filePath, type = 'upload') {
    const key = type === 'download' ? 'download' : 'upload';
    return { ...(this.state.chunkMaps[key][filePath] || {}) };
  }

  setChunkMap(filePath, chunkMap, type = 'upload') {
    const key = type === 'download' ? 'download' : 'upload';
    this.state.chunkMaps[key][filePath] = { ...chunkMap };
    this.save();
  }

  clearChunkMap(filePath, type = 'upload') {
    const key = type === 'download' ? 'download' : 'upload';
    delete this.state.chunkMaps[key][filePath];
    this.save();
  }

  clearAllChunkMaps() {
    this.state.chunkMaps = {
      upload: {},
      download: {}
    };
    this.save();
  }

  generateConflictId() {
    return 'conflict_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }

  getSelectedFolders() {
    return { ...this.state.selectedFolders };
  }

  setSelectedFolders(folders) {
    this.state.selectedFolders = { ...folders };
    this.save();
  }

  isFolderSelected(folderPath) {
    if (Object.keys(this.state.selectedFolders).length === 0) {
      return true;
    }
    
    const normalized = folderPath.replace(/\\/g, '/');
    for (const [selectedPath, isSelected] of Object.entries(this.state.selectedFolders)) {
      if (!isSelected) continue;
      if (normalized === selectedPath || normalized.startsWith(selectedPath + '/')) {
        return true;
      }
    }
    return false;
  }

  getSettings() {
    return { ...this.state.settings };
  }

  updateSettings(settings) {
    this.state.settings = { ...this.state.settings, ...settings };
    this.save();
  }

  getHistoryWithFilters(options = {}) {
    const { 
      days = 30, 
      search = '', 
      actionType = 'all',
      startDate = null,
      endDate = null
    } = options;
    
    let history = [...this.state.history];
    
    const cutoffTime = startDate ? new Date(startDate).getTime() : Date.now() - (days * 24 * 60 * 60 * 1000);
    history = history.filter(h => h.timestamp >= cutoffTime);
    
    if (endDate) {
      const endTime = new Date(endDate).getTime();
      history = history.filter(h => h.timestamp <= endTime);
    }
    
    if (search && search.trim()) {
      const searchLower = search.toLowerCase();
      history = history.filter(h => 
        h.filePath.toLowerCase().includes(searchLower)
      );
    }
    
    if (actionType && actionType !== 'all') {
      history = history.filter(h => h.action === actionType);
    }
    
    return history.reverse();
  }

  getHistoryStats(days = 30) {
    const history = this.getHistoryWithFilters({ days });
    
    return {
      total: history.length,
      uploads: history.filter(h => h.action === 'upload').length,
      downloads: history.filter(h => h.action === 'download').length,
      deletes: history.filter(h => h.action === 'delete').length,
      byDate: this.groupHistoryByDate(history)
    };
  }

  groupHistoryByDate(history) {
    const groups = {};
    for (const item of history) {
      const date = new Date(item.timestamp).toLocaleDateString('zh-CN');
      if (!groups[date]) {
        groups[date] = { uploads: 0, downloads: 0, deletes: 0, total: 0 };
      }
      groups[date].total++;
      if (item.action === 'upload') groups[date].uploads++;
      else if (item.action === 'download') groups[date].downloads++;
      else if (item.action === 'delete') groups[date].deletes++;
    }
    return groups;
  }

  clearHistory() {
    this.state.history = [];
    this.save();
  }

  clear() {
    this.state = {
      syncFolder: null,
      files: {},
      conflicts: [],
      history: [],
      lastSyncTime: null,
      uploadsInProgress: {},
      chunkMaps: {
        upload: {},
        download: {}
      },
      selectedFolders: {},
      settings: {
        runInBackground: true,
        showNotifications: true,
        historyDays: 30
      }
    };
    this.save();
  }
}

module.exports = SyncState;

const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const SyncEngine = require('./sync/SyncEngine');
const CloudAPI = require('./api/CloudAPI');
const TrayManager = require('./tray/TrayManager');

let mainWindow;
let syncEngine;
let cloudAPI;
let trayManager;
let conflictWindows = new Map();

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1000,
    height: 750,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      enableRemoteModule: true
    },
    icon: path.join(__dirname, '../assets/icon.png')
  });

  mainWindow.loadFile(path.join(__dirname, 'renderer/index.html'));

  if (process.argv.includes('--dev')) {
    mainWindow.webContents.openDevTools();
  }

  mainWindow.on('close', (event) => {
    const settings = syncEngine ? syncEngine.syncState.getSettings() : { runInBackground: true };
    if (settings.runInBackground && !app.isQuitting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  cloudAPI = new CloudAPI();
  syncEngine = new SyncEngine(cloudAPI);
  
  setupIPCHandlers();
  createWindow();
  
  setTimeout(() => {
    trayManager = new TrayManager(mainWindow, syncEngine);
  }, 100);

  syncEngine.on('sync-status', (status) => {
    if (mainWindow) {
      mainWindow.webContents.send('sync-status', status);
    }
    if (trayManager) {
      trayManager.updateStatus(status.status || status, {
        file: status.file,
        progress: 0
      });
    }
  });

  syncEngine.on('sync-progress', (progress) => {
    if (mainWindow) {
      mainWindow.webContents.send('sync-progress', progress);
    }
    if (trayManager) {
      trayManager.updateStatus('syncing', {
        file: progress.filePath,
        progress: progress.progress || 0
      });
    }
  });

  syncEngine.on('conflict-detected', (conflict) => {
    if (mainWindow) {
      mainWindow.webContents.send('conflict-detected', conflict);
    }
    
    if (trayManager) {
      trayManager.showNotification('文件冲突', `检测到冲突: ${conflict.filePath}`);
    }
    
    if (!conflictWindows.has(conflict.id)) {
      createConflictDialog(conflict);
    }
  });

  syncEngine.on('sync-complete', (stats) => {
    if (mainWindow) {
      mainWindow.webContents.send('sync-complete', stats);
    }
    if (trayManager) {
      trayManager.updateStatus('running');
      if (stats.uploaded > 0 || stats.downloaded > 0) {
        trayManager.showNotification('同步完成', `上传 ${stats.uploaded} 个, 下载 ${stats.downloaded} 个`);
      }
    }
  });

  syncEngine.on('error', (error) => {
    if (mainWindow) {
      mainWindow.webContents.send('sync-error', error);
    }
    if (trayManager) {
      trayManager.updateStatus('error');
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

function createConflictDialog(conflict) {
  const conflictWindow = new BrowserWindow({
    width: 850,
    height: 680,
    minWidth: 700,
    minHeight: 550,
    parent: mainWindow,
    modal: true,
    resizable: true,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      enableRemoteModule: true
    },
    icon: path.join(__dirname, '../assets/icon.png')
  });

  conflictWindow.setMenu(null);
  
  conflictWindow.loadFile(path.join(__dirname, 'renderer/conflict-dialog.html'));
  
  conflictWindow.webContents.on('did-finish-load', () => {
    conflictWindow.webContents.send('set-conflict-data', conflict);
  });
  
  conflictWindows.set(conflict.id, conflictWindow);
  
  conflictWindow.on('closed', () => {
    conflictWindows.delete(conflict.id);
  });

  ipcMain.once('conflict-resolved', (event, data) => {
    if (mainWindow) {
      mainWindow.webContents.send('conflict-resolved', data);
    }
  });
}

function setupIPCHandlers() {
  ipcMain.handle('select-folder', async () => {
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ['openDirectory']
    });
    if (!result.canceled && result.filePaths.length > 0) {
      return result.filePaths[0];
    }
    return null;
  });

  ipcMain.handle('start-sync', async (event, folderPath) => {
    try {
      await syncEngine.setSyncFolder(folderPath);
      await syncEngine.start();
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });

  ipcMain.handle('stop-sync', async () => {
    try {
      await syncEngine.stop();
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });

  ipcMain.handle('pause-sync', async () => {
    try {
      syncEngine.pause();
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });

  ipcMain.handle('resume-sync', async () => {
    try {
      syncEngine.resume();
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });

  ipcMain.handle('get-sync-status', () => {
    return syncEngine.getStatus();
  });

  ipcMain.handle('resolve-conflict', async (event, conflictId, resolution) => {
    try {
      await syncEngine.resolveConflict(conflictId, resolution);
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });

  ipcMain.handle('open-folder', async (event, folderPath) => {
    shell.openPath(folderPath);
  });

  ipcMain.handle('get-sync-history', () => {
    return syncEngine.getHistory();
  });

  ipcMain.handle('configure-api', async (event, config) => {
    try {
      cloudAPI.configure(config);
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });

  ipcMain.handle('test-connection', async () => {
    try {
      const result = await cloudAPI.testConnection();
      return { success: true, result };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });

  ipcMain.on('open-conflict-dialog', (event, conflict) => {
    if (!conflictWindows.has(conflict.id)) {
      createConflictDialog(conflict);
    } else {
      const win = conflictWindows.get(conflict.id);
      if (win) {
        win.focus();
      }
    }
  });

  ipcMain.handle('scan-folders', async () => {
    try {
      const folders = await syncEngine.scanFolders();
      return { success: true, folders };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });

  ipcMain.handle('get-selected-folders', () => {
    return syncEngine.getSelectedFolders();
  });

  ipcMain.handle('set-selected-folders', async (event, folders) => {
    try {
      syncEngine.setSelectedFolders(folders);
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });

  ipcMain.handle('get-history-with-filters', async (event, options) => {
    return syncEngine.getHistoryWithFilters(options);
  });

  ipcMain.handle('get-history-stats', async (event, days) => {
    return syncEngine.getHistoryStats(days);
  });

  ipcMain.handle('get-settings', () => {
    return syncEngine.syncState.getSettings();
  });

  ipcMain.handle('update-settings', async (event, settings) => {
    try {
      syncEngine.syncState.updateSettings(settings);
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });

  ipcMain.handle('quit-app', () => {
    app.isQuitting = true;
    app.quit();
  });

  ipcMain.handle('hide-window', () => {
    if (mainWindow) {
      mainWindow.hide();
    }
  });

  ipcMain.handle('show-window', () => {
    if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

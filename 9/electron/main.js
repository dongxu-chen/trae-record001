const { app, BrowserWindow, ipcMain, Tray, Menu, nativeImage, shell } = require('electron');
const path = require('path');
const Storage = require('./storage.js');
const GistSync = require('./sync.js');

let storage;
let gistSync;
let tray;
let settings = { encryptionEnabled: true, githubToken: null, gistId: null };

const isDev = !app.isPackaged;

function getTrayIconPath() {
  const platforms = {
    win32: 'tray.ico',
    darwin: 'tray.png',
    linux: 'tray.png'
  };
  const iconName = platforms[process.platform] || 'tray.png';
  return path.join(__dirname, 'icons', iconName);
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  if (isDev) {
    win.loadURL('http://localhost:5173');
    win.webContents.openDevTools();
  } else {
    win.loadFile(path.join(__dirname, '..', 'dist', 'index.html'));
  }

  win.on('close', (e) => {
    if (!app.isQuiting) {
      e.preventDefault();
      win.hide();
    }
  });

  return win;
}

function createTray() {
  let icon;
  try {
    const iconPath = getTrayIconPath();
    icon = nativeImage.createFromPath(iconPath);
    if (icon.isEmpty()) {
      icon = nativeImage.createEmpty();
    }
  } catch {
    icon = nativeImage.createEmpty();
  }

  if (icon.isEmpty()) {
    icon = nativeImage.createFromDataURL(
      'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAAdgAAAHYBTnsmCAAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAADdSURBVDiNY2AABhQwMjCg4GRgYGD8x+e2v4GBgUjD08ePH/337t0/4GBgSDBd/PGiRYs/4+PjHzNmzIj//////gAqQbGRmZv7s2bP/8ePH/5+fH119fX38g3wWlCIGBgYGBgYEBgUlQaGBgYGBgUHDw88cff/zevXu/MTEx/7u7u388PDy+srKy/gYGBgUJBQYGCAwUJAwPBUyfHjx49////H3r16v2SkpL/8vLy/qqqqj8zMzP+U2AIGBgYGBgYoCgYFBIYGBgUKBw0NDQ8PDw8fDw8PHw8PDx8PDw8Hw8RCoYGBgYkAwPBUyPn369PnExMT/8PDw/1JSUv5OTk5/rq6uv4WFhf/+/Pn/6enp/0dHR38lJSW/kZGR/xEREX9/f3//iYmJ/9nZ2f90dHR/v7+//7+/v/+iIiI/6ioqP+3t7f/dnZ2/yUlJf9wcHD/8ePH/729vf/FxcX/9vLy/7y8vL+/v7///f39/4GBgYH+/v7///n5+f8QEX8CAAC2X+L9k184XQAAAABJRU5ErkJggg=='
    );
  }

  tray = new Tray(icon);

  updateTrayMenu();

  tray.on('click', () => {
    const windows = BrowserWindow.getAllWindows();
    if (windows.length === 0) {
      createWindow();
    } else {
      const win = windows[0];
      if (win.isVisible()) {
        win.hide();
      } else {
        win.show();
        win.focus();
      }
    }
  });
}

function updateTrayMenu() {
  if (!tray) return;

  const contextMenu = Menu.buildFromTemplate([
    {
      label: '显示窗口',
      click: () => {
        const windows = BrowserWindow.getAllWindows();
        if (windows.length === 0) {
          createWindow();
        } else {
          const win = windows[0];
          win.show();
          win.focus();
        }
      }
    },
    { type: 'separator' },
    {
      label: '立即同步',
      enabled: !!settings.githubToken,
      click: async () => {
        try {
          await handleSyncUpload();
        } catch (error) {
          console.error('Sync failed:', error);
        }
      }
    },
    {
      label: '从 Gist 导入',
      enabled: !!settings.githubToken && !!settings.gistId,
      click: async () => {
        try {
          await handleSyncDownload();
        } catch (error) {
          console.error('Import failed:', error);
        }
      }
    },
    { type: 'separator' },
    {
      label: settings.encryptionEnabled ? '禁用加密' : '启用加密',
      type: 'checkbox',
      checked: settings.encryptionEnabled,
      click: async (menuItem) => {
        settings.encryptionEnabled = menuItem.checked;
        storage.setEncryptionEnabled(menuItem.checked);
        await storage.saveSettings(settings);
      }
    },
    { type: 'separator' },
    {
      label: '打开 Gist 设置',
      click: () => {
        const windows = BrowserWindow.getAllWindows();
        if (windows.length === 0) {
          createWindow();
        } else {
          const win = windows[0];
          win.show();
          win.focus();
          win.webContents.send('settings:open-gist');
        }
      }
    },
    {
      label: '打开 GitHub Gist',
      enabled: !!settings.gistId,
      click: () => {
        if (settings.gistId) {
          shell.openExternal(`https://gist.github.com/${settings.gistId}`);
        }
      }
    },
    { type: 'separator' },
    {
      label: '退出',
      click: () => {
        app.isQuiting = true;
        app.quit();
      }
    }
  ]);

  tray.setToolTip('代码片段管理器');
  tray.setContextMenu(contextMenu);
}

function broadcastToOtherWindows(exceptWebContentsId, channel, ...args) {
  BrowserWindow.getAllWindows().forEach(win => {
    const contents = win.webContents;
    if (contents.id !== exceptWebContentsId && !contents.isDestroyed()) {
      contents.send(channel, ...args);
    }
  });
}

function broadcastToAllWindows(channel, ...args) {
  BrowserWindow.getAllWindows().forEach(win => {
    const contents = win.webContents;
    if (!contents.isDestroyed()) {
      contents.send(channel, ...args);
    }
  });
}

async function handleSyncUpload() {
  if (!settings.githubToken) {
    throw new Error('GitHub token not configured');
  }

  gistSync.setToken(settings.githubToken);
  const snippets = await storage.load();
  const result = await gistSync.uploadSnippets(snippets, settings.gistId);

  if (!settings.gistId && result.id) {
    settings.gistId = result.id;
    await storage.saveSettings(settings);
    updateTrayMenu();
  }

  broadcastToAllWindows('sync:status', { success: true, message: '同步成功', timestamp: Date.now() });
  return result;
}

async function handleSyncDownload() {
  if (!settings.githubToken) {
    throw new Error('GitHub token not configured');
  }
  if (!settings.gistId) {
    throw new Error('Gist ID not configured');
  }

  gistSync.setToken(settings.githubToken);
  const result = await gistSync.downloadSnippets(settings.gistId);

  await storage.saveNow(result.snippets);

  broadcastToAllWindows('snippets:changed', result.snippets);
  broadcastToAllWindows('sync:status', { success: true, message: '导入成功', timestamp: Date.now() });

  return result;
}

app.whenReady().then(async () => {
  storage = new Storage();
  settings = await storage.loadSettings();
  storage.setEncryptionEnabled(settings.encryptionEnabled);
  gistSync = new GistSync(settings.githubToken);

  createWindow();
  createTray();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

ipcMain.handle('snippets:get', async () => {
  return await storage.load();
});

ipcMain.handle('snippets:save', async (event, snippets) => {
  const success = await storage.save(snippets);
  if (success) {
    broadcastToOtherWindows(event.sender.id, 'snippets:changed', snippets);
  }
  return success;
});

ipcMain.handle('settings:get', async () => {
  return await storage.loadSettings();
});

ipcMain.handle('settings:save', async (event, newSettings) => {
  settings = { ...settings, ...newSettings };
  const success = await storage.saveSettings(settings);
  
  if (newSettings.encryptionEnabled !== undefined) {
    storage.setEncryptionEnabled(newSettings.encryptionEnabled);
  }
  if (newSettings.githubToken !== undefined) {
    gistSync.setToken(newSettings.githubToken);
  }
  
  updateTrayMenu();
  return success;
});

ipcMain.handle('sync:upload', async () => {
  try {
    const result = await handleSyncUpload();
    return { success: true, gistId: result.id };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

ipcMain.handle('sync:download', async () => {
  try {
    const result = await handleSyncDownload();
    return { success: true, snippets: result.snippets };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

const { Tray, Menu, app } = require('electron');
const path = require('path');

class TrayManager {
  constructor(mainWindow, syncEngine) {
    this.mainWindow = mainWindow;
    this.syncEngine = syncEngine;
    this.tray = null;
    this.currentStatus = 'stopped';
    this.currentProgress = 0;
    this.currentFile = '';
    
    this.init();
  }

  init() {
    const iconPath = this.getIconPath();
    
    try {
      this.tray = new Tray(iconPath);
      this.tray.setToolTip('FileSync Client');
      
      this.updateContextMenu();
      this.setupEventListeners();
    } catch (error) {
      console.error('Failed to create tray:', error);
    }
  }

  getIconPath() {
    const iconsDir = path.join(__dirname, '../../assets');
    
    if (process.platform === 'win32') {
      return path.join(iconsDir, 'icon.ico');
    } else if (process.platform === 'darwin') {
      return path.join(iconsDir, 'iconTemplate.png');
    } else {
      return path.join(iconsDir, 'icon.png');
    }
  }

  setupEventListeners() {
    this.tray.on('click', () => {
      if (this.mainWindow) {
        if (this.mainWindow.isVisible()) {
          this.mainWindow.hide();
        } else {
          this.mainWindow.show();
          this.mainWindow.focus();
        }
      }
    });

    this.tray.on('double-click', () => {
      if (this.mainWindow) {
        this.mainWindow.show();
        this.mainWindow.focus();
      }
    });
  }

  updateStatus(status, data = {}) {
    this.currentStatus = status;
    this.currentProgress = data.progress || 0;
    this.currentFile = data.file || '';
    
    this.updateToolTip();
    this.updateContextMenu();
  }

  updateToolTip() {
    let tooltip = 'FileSync Client\n';
    
    switch (this.currentStatus) {
      case 'running':
        tooltip += '状态: 运行中 ✓';
        break;
      case 'paused':
        tooltip += '状态: 已暂停 ⏸';
        break;
      case 'syncing':
      case 'scanning':
        tooltip += `状态: ${this.currentStatus === 'scanning' ? '扫描中' : '同步中'}\n`;
        tooltip += `进度: ${this.currentProgress.toFixed(1)}%`;
        if (this.currentFile) {
          tooltip += `\n文件: ${this.currentFile}`;
        }
        break;
      case 'error':
        tooltip += '状态: 错误 ⚠';
        break;
      default:
        tooltip += '状态: 未运行';
    }
    
    this.tray.setToolTip(tooltip.substring(0, 120));
  }

  updateContextMenu() {
    const statusItems = this.getStatusMenuItems();
    const actionItems = this.getActionMenuItems();
    const windowItems = this.getWindowMenuItems();
    
    const template = [
      ...statusItems,
      { type: 'separator' },
      ...actionItems,
      { type: 'separator' },
      ...windowItems,
      { type: 'separator' },
      {
        label: '退出',
        click: () => {
          app.quit();
        }
      }
    ];
    
    const menu = Menu.buildFromTemplate(template);
    this.tray.setContextMenu(menu);
  }

  getStatusMenuItems() {
    const items = [];
    let statusText = '未运行';
    let statusIcon = '⚪';
    
    switch (this.currentStatus) {
      case 'running':
        statusText = '运行中';
        statusIcon = '🟢';
        break;
      case 'paused':
        statusText = '已暂停';
        statusIcon = '🟡';
        break;
      case 'syncing':
      case 'scanning':
        statusText = this.currentStatus === 'scanning' ? '扫描中...' : '同步中...';
        statusIcon = '🔵';
        break;
      case 'error':
        statusText = '错误';
        statusIcon = '🔴';
        break;
    }
    
    items.push({
      label: `${statusIcon} ${statusText}`,
      enabled: false
    });
    
    if (this.currentStatus === 'syncing' && this.currentFile) {
      items.push({
        label: `  ${this.currentProgress.toFixed(1)}% - ${this.currentFile}`,
        enabled: false
      });
    }
    
    return items;
  }

  getActionMenuItems() {
    const items = [];
    const isRunning = this.currentStatus === 'running' || 
                      this.currentStatus === 'syncing' || 
                      this.currentStatus === 'scanning';
    const isPaused = this.currentStatus === 'paused';
    
    if (isRunning) {
      items.push({
        label: '⏸ 暂停同步',
        click: () => {
          if (this.syncEngine) {
            this.syncEngine.pause();
          }
        }
      });
    } else if (isPaused) {
      items.push({
        label: '▶ 继续同步',
        click: () => {
          if (this.syncEngine) {
            this.syncEngine.resume();
          }
        }
      });
    }
    
    if (isRunning || isPaused) {
      items.push({
        label: '⏹ 停止同步',
        click: () => {
          if (this.syncEngine) {
            this.syncEngine.stop();
          }
        }
      });
      
      items.push({
        label: '🔄 立即同步',
        click: () => {
          if (this.syncEngine && this.syncEngine.isRunning) {
            this.syncEngine.performFullSync();
          }
        }
      });
    }
    
    return items;
  }

  getWindowMenuItems() {
    const items = [];
    
    if (this.mainWindow) {
      items.push({
        label: this.mainWindow.isVisible() ? '隐藏窗口' : '显示窗口',
        click: () => {
          if (this.mainWindow.isVisible()) {
            this.mainWindow.hide();
          } else {
            this.mainWindow.show();
            this.mainWindow.focus();
          }
        }
      });
    }
    
    return items;
  }

  showNotification(title, message) {
    if (this.tray && this.tray.displayBalloon) {
      this.tray.displayBalloon({
        title,
        content: message,
        icon: this.getIconPath()
      });
    }
  }

  destroy() {
    if (this.tray) {
      this.tray.destroy();
      this.tray = null;
    }
  }
}

module.exports = TrayManager;

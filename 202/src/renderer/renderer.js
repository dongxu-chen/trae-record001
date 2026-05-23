const { ipcRenderer } = require('electron');

let currentFolder = null;
let activeConflicts = [];
let activityItems = new Map();
let currentView = 'dashboard';
let folderList = [];
let historySearchTimeout = null;

const elements = {
  pageTitle: document.getElementById('pageTitle'),
  statusDot: document.getElementById('statusDot'),
  statusText: document.getElementById('statusText'),
  hideWindowBtn: document.getElementById('hideWindowBtn'),
  folderPath: document.getElementById('folderPath'),
  apiUrl: document.getElementById('apiUrl'),
  apiKey: document.getElementById('apiKey'),
  selectFolderBtn: document.getElementById('selectFolderBtn'),
  testConnBtn: document.getElementById('testConnBtn'),
  startSyncBtn: document.getElementById('startSyncBtn'),
  setupCard: document.getElementById('setupCard'),
  syncDashboard: document.getElementById('syncDashboard'),
  folderDisplay: document.getElementById('folderDisplay'),
  openFolderBtn: document.getElementById('openFolderBtn'),
  lastSyncTime: document.getElementById('lastSyncTime'),
  pauseSyncBtn: document.getElementById('pauseSyncBtn'),
  syncNowBtn: document.getElementById('syncNowBtn'),
  stopSyncBtn: document.getElementById('stopSyncBtn'),
  progressSection: document.getElementById('progressSection'),
  progressTitle: document.getElementById('progressTitle'),
  progressPercent: document.getElementById('progressPercent'),
  progressFill: document.getElementById('progressFill'),
  progressDetail: document.getElementById('progressDetail'),
  activityEmpty: document.getElementById('activityEmpty'),
  activityList: document.getElementById('activityList'),
  uploadCount: document.getElementById('uploadCount'),
  downloadCount: document.getElementById('downloadCount'),
  deleteCount: document.getElementById('deleteCount'),
  folderCount: document.getElementById('folderCount'),
  historySearch: document.getElementById('historySearch'),
  historyTypeFilter: document.getElementById('historyTypeFilter'),
  historyDaysFilter: document.getElementById('historyDaysFilter'),
  historyTotal: document.getElementById('historyTotal'),
  historyUploads: document.getElementById('historyUploads'),
  historyDownloads: document.getElementById('historyDownloads'),
  historyDeletes: document.getElementById('historyDeletes'),
  historyEmpty: document.getElementById('historyEmpty'),
  historyList: document.getElementById('historyList'),
  folderTree: document.getElementById('folderTree'),
  refreshFoldersBtn: document.getElementById('refreshFoldersBtn'),
  selectAllFoldersBtn: document.getElementById('selectAllFoldersBtn'),
  deselectAllFoldersBtn: document.getElementById('deselectAllFoldersBtn'),
  saveFoldersBtn: document.getElementById('saveFoldersBtn'),
  bgRunSetting: document.getElementById('bgRunSetting'),
  notifySetting: document.getElementById('notifySetting'),
  historyDaysSetting: document.getElementById('historyDaysSetting'),
  saveSettingsBtn: document.getElementById('saveSettingsBtn'),
  quitAppBtn: document.getElementById('quitAppBtn'),
  notification: document.getElementById('notification'),
  notificationIcon: document.getElementById('notificationIcon'),
  notificationMessage: document.getElementById('notificationMessage')
};

function init() {
  bindEvents();
  setupIPCListeners();
  loadSettings();
}

function bindEvents() {
  document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
      switchView(btn.dataset.view);
    });
  });

  elements.selectFolderBtn.addEventListener('click', async () => {
    const folderPath = await ipcRenderer.invoke('select-folder');
    if (folderPath) {
      currentFolder = folderPath;
      elements.folderPath.value = folderPath;
      validateForm();
    }
  });

  elements.testConnBtn.addEventListener('click', async () => {
    const apiUrl = elements.apiUrl.value.trim();
    const apiKey = elements.apiKey.value.trim();
    
    if (!apiUrl) {
      showNotification('请输入API地址', 'error');
      return;
    }

    elements.testConnBtn.disabled = true;
    elements.testConnBtn.textContent = '测试中...';

    try {
      await ipcRenderer.invoke('configure-api', { baseURL: apiUrl, apiKey });
      const result = await ipcRenderer.invoke('test-connection');
      
      if (result.success) {
        showNotification('连接成功！', 'success');
      } else {
        showNotification(`连接失败: ${result.error}`, 'error');
      }
    } catch (error) {
      showNotification(`连接失败: ${error.message}`, 'error');
    } finally {
      elements.testConnBtn.disabled = false;
      elements.testConnBtn.textContent = '测试连接';
    }
  });

  elements.startSyncBtn.addEventListener('click', async () => {
    const apiUrl = elements.apiUrl.value.trim();
    const apiKey = elements.apiKey.value.trim();

    try {
      await ipcRenderer.invoke('configure-api', { baseURL: apiUrl, apiKey });
      const result = await ipcRenderer.invoke('start-sync', currentFolder);
      
      if (result.success) {
        showSyncUI();
        showNotification('同步已启动', 'success');
        loadFolderList();
        loadHistory();
      } else {
        showNotification(`启动失败: ${result.error}`, 'error');
      }
    } catch (error) {
      showNotification(`启动失败: ${error.message}`, 'error');
    }
  });

  elements.pauseSyncBtn.addEventListener('click', async () => {
    const status = await ipcRenderer.invoke('get-sync-status');
    if (status.isPaused) {
      await ipcRenderer.invoke('resume-sync');
      elements.pauseSyncBtn.innerHTML = getPauseIcon() + '暂停';
    } else {
      await ipcRenderer.invoke('pause-sync');
      elements.pauseSyncBtn.innerHTML = getResumeIcon() + '继续';
    }
  });

  elements.syncNowBtn.addEventListener('click', async () => {
    showNotification('正在执行同步...', 'info');
  });

  elements.stopSyncBtn.addEventListener('click', async () => {
    await ipcRenderer.invoke('stop-sync');
    showSetupUI();
    showNotification('同步已停止', 'warning');
  });

  elements.openFolderBtn.addEventListener('click', async () => {
    if (currentFolder) {
      await ipcRenderer.invoke('open-folder', currentFolder);
    }
  });

  elements.hideWindowBtn.addEventListener('click', async () => {
    await ipcRenderer.invoke('hide-window');
  });

  elements.historySearch.addEventListener('input', () => {
    clearTimeout(historySearchTimeout);
    historySearchTimeout = setTimeout(() => {
      loadHistory();
    }, 300);
  });

  elements.historyTypeFilter.addEventListener('change', loadHistory);
  elements.historyDaysFilter.addEventListener('change', loadHistory);

  elements.refreshFoldersBtn.addEventListener('click', loadFolderList);
  elements.selectAllFoldersBtn.addEventListener('click', () => selectAllFolders(true));
  elements.deselectAllFoldersBtn.addEventListener('click', () => selectAllFolders(false));
  elements.saveFoldersBtn.addEventListener('click', saveFolderSelection);

  elements.saveSettingsBtn.addEventListener('click', saveSettings);
  elements.quitAppBtn.addEventListener('click', async () => {
    await ipcRenderer.invoke('quit-app');
  });

  elements.apiUrl.addEventListener('input', validateForm);
  elements.apiKey.addEventListener('input', validateForm);
}

function setupIPCListeners() {
  ipcRenderer.on('sync-status', (event, status) => {
    updateStatusIndicator(status.status || status);
    
    if (status.file && status.action) {
      addActivityItem(status.file, status.action);
    }
  });

  ipcRenderer.on('sync-progress', (event, progress) => {
    showProgress(progress);
    updateActivityProgress(progress.filePath, progress.progress);
  });

  ipcRenderer.on('conflict-detected', (event, conflict) => {
    showNotification(`检测到文件冲突: ${conflict.filePath}`, 'warning');
    addConflict(conflict);
  });

  ipcRenderer.on('sync-complete', async (event, stats) => {
    hideProgress();
    updateLastSyncTime();
    loadHistory();
    updateStats(stats);
    
    if (stats.uploaded > 0 || stats.downloaded > 0) {
      showNotification(`同步完成: 上传 ${stats.uploaded} 个, 下载 ${stats.downloaded} 个`, 'success');
    }
  });

  ipcRenderer.on('sync-error', (event, error) => {
    showNotification(error, 'error');
  });

  ipcRenderer.on('conflict-resolved', (event, data) => {
    activeConflicts = activeConflicts.filter(c => c.id !== data.conflictId);
    
    if (data.resolution === 'cancel') {
      showNotification('冲突已暂存', 'warning');
    } else {
      loadHistory();
    }
  });
}

function validateForm() {
  const hasFolder = currentFolder && currentFolder.length > 0;
  const hasApiUrl = elements.apiUrl.value.trim().length > 0;
  elements.startSyncBtn.disabled = !(hasFolder && hasApiUrl);
}

function switchView(viewId) {
  currentView = viewId;
  
  document.querySelectorAll('.nav-item').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.view === viewId);
  });
  
  document.querySelectorAll('.view-section').forEach(section => {
    section.classList.toggle('active', section.id === `${viewId}View`);
  });
  
  const titles = {
    dashboard: '概览',
    folders: '文件夹',
    history: '历史记录',
    settings: '设置'
  };
  elements.pageTitle.textContent = titles[viewId] || '概览';
  
  if (viewId === 'history') {
    loadHistory();
  } else if (viewId === 'folders') {
    loadFolderList();
  }
}

function showSyncUI() {
  elements.setupCard.style.display = 'none';
  elements.syncDashboard.style.display = 'flex';
  elements.folderDisplay.textContent = currentFolder;
  updateStatusIndicator('running');
}

function showSetupUI() {
  elements.setupCard.style.display = 'block';
  elements.syncDashboard.style.display = 'none';
  updateStatusIndicator('stopped');
}

function updateStatusIndicator(status) {
  elements.statusDot.className = 'status-dot';
  
  switch (status) {
    case 'running':
      elements.statusDot.classList.add('running');
      elements.statusText.textContent = '运行中';
      break;
    case 'paused':
      elements.statusDot.classList.add('paused');
      elements.statusText.textContent = '已暂停';
      break;
    case 'syncing':
    case 'scanning':
      elements.statusDot.classList.add('syncing');
      elements.statusText.textContent = status === 'scanning' ? '扫描中' : '同步中';
      break;
    case 'error':
      elements.statusDot.classList.add('error');
      elements.statusText.textContent = '错误';
      break;
    default:
      elements.statusText.textContent = '未运行';
  }
}

function showProgress(progress) {
  elements.progressSection.style.display = 'block';
  elements.progressTitle.textContent = progress.action === 'upload' ? 
    `正在上传: ${progress.filePath}` : `正在下载: ${progress.filePath}`;
  elements.progressPercent.textContent = `${progress.progress.toFixed(1)}%`;
  elements.progressFill.style.width = `${progress.progress}%`;
  
  const transferred = progress.action === 'upload' ? progress.uploaded : progress.downloaded;
  elements.progressDetail.textContent = `${formatSize(transferred)} / ${formatSize(progress.total)}`;
}

function hideProgress() {
  setTimeout(() => {
    elements.progressSection.style.display = 'none';
  }, 1000);
}

function addActivityItem(filePath, action) {
  if (activityItems.has(filePath)) {
    activityItems.delete(filePath);
  }

  const item = {
    id: Date.now(),
    filePath,
    action,
    progress: 0,
    timestamp: Date.now()
  };
  activityItems.set(filePath, item);
  renderActivityList();
}

function updateActivityProgress(filePath, progress) {
  if (activityItems.has(filePath)) {
    const item = activityItems.get(filePath);
    item.progress = progress;
    renderActivityList();
  }
}

function renderActivityList() {
  const items = Array.from(activityItems.values()).slice(0, 10);
  
  if (items.length === 0) {
    elements.activityEmpty.style.display = 'flex';
    elements.activityList.innerHTML = '';
    return;
  }

  elements.activityEmpty.style.display = 'none';
  elements.activityList.innerHTML = items.map(item => `
    <div class="activity-item">
      <div class="activity-icon ${item.action}">
        ${getActionIcon(item.action)}
      </div>
      <div class="activity-content">
        <div class="activity-file">${item.filePath}</div>
        <div class="activity-meta">
          ${getActionText(item.action)} • ${formatTime(item.timestamp)}
          ${item.progress > 0 && item.progress < 100 ? ` • ${item.progress.toFixed(0)}%` : ''}
        </div>
      </div>
    </div>
  `).join('');
}

function addConflict(conflict) {
  activeConflicts.unshift(conflict);
}

async function loadFolderList() {
  try {
    const result = await ipcRenderer.invoke('scan-folders');
    
    if (!result.success || result.folders.length === 0) {
      elements.folderTree.innerHTML = `
        <div class="empty-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
          </svg>
          <p>请先启动同步</p>
        </div>
      `;
      return;
    }
    
    folderList = result.folders;
    renderFolderTree();
  } catch (error) {
    console.error('Failed to load folders:', error);
  }
}

function renderFolderTree() {
  const tree = buildFolderTree(folderList);
  
  elements.folderTree.innerHTML = renderFolderNode(tree, 0);
}

function buildFolderTree(folders) {
  const root = { children: {}, name: '', fullPath: '', selected: true };
  
  for (const folder of folders) {
    const parts = folder.path.split('/');
    let current = root;
    
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      if (!current.children[part]) {
        const fullPath = parts.slice(0, i + 1).join('/');
        current.children[part] = {
          children: {},
          name: part,
          fullPath,
          selected: folder.selected
        };
      }
      current = current.children[part];
    }
  }
  
  return root;
}

function renderFolderNode(node, level) {
  let html = '';
  
  const childKeys = Object.keys(node.children).sort();
  for (const key of childKeys) {
    const child = node.children[key];
    const hasChildren = Object.keys(child.children).length > 0;
    
    html += `
      <div class="folder-item" style="padding-left: ${16 + level * 20}px">
        <input type="checkbox" 
               data-path="${child.fullPath}" 
               ${child.selected ? 'checked' : ''}
               onchange="onFolderToggle('${child.fullPath}', this.checked)">
        <svg class="folder-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
        </svg>
        <span class="folder-name">${child.name}</span>
      </div>
    `;
    
    if (hasChildren) {
      html += renderFolderNode(child, level + 1);
    }
  }
  
  return html;
}

function onFolderToggle(path, checked) {
  const folder = folderList.find(f => f.path === path);
  if (folder) {
    folder.selected = checked;
  }
  
  const checkboxes = document.querySelectorAll('.folder-item input[type="checkbox"]');
  checkboxes.forEach(cb => {
    if (cb.dataset.path.startsWith(path + '/')) {
      cb.checked = checked;
      const f = folderList.find(f => f.path === cb.dataset.path);
      if (f) f.selected = checked;
    }
  });
}

function selectAllFolders(selected) {
  folderList.forEach(f => f.selected = selected);
  renderFolderTree();
}

async function saveFolderSelection() {
  const selectedFolders = {};
  folderList.forEach(f => {
    selectedFolders[f.path] = f.selected;
  });
  
  try {
    await ipcRenderer.invoke('set-selected-folders', selectedFolders);
    showNotification('文件夹选择已保存', 'success');
  } catch (error) {
    showNotification('保存失败: ' + error.message, 'error');
  }
}

async function loadHistory() {
  const options = {
    days: parseInt(elements.historyDaysFilter.value),
    search: elements.historySearch.value.trim(),
    actionType: elements.historyTypeFilter.value
  };
  
  try {
    const [history, stats] = await Promise.all([
      ipcRenderer.invoke('get-history-with-filters', options),
      ipcRenderer.invoke('get-history-stats', options.days)
    ]);
    
    updateHistoryStats(stats);
    renderHistoryList(history);
  } catch (error) {
    console.error('Failed to load history:', error);
  }
}

function updateHistoryStats(stats) {
  elements.historyTotal.textContent = stats.total;
  elements.historyUploads.textContent = stats.uploads;
  elements.historyDownloads.textContent = stats.downloads;
  elements.historyDeletes.textContent = stats.deletes;
}

function renderHistoryList(history) {
  if (history.length === 0) {
    elements.historyEmpty.style.display = 'flex';
    elements.historyList.innerHTML = '';
    return;
  }

  elements.historyEmpty.style.display = 'none';
  elements.historyList.innerHTML = history.map(item => `
    <div class="history-item">
      <div class="history-icon ${item.action}">
        ${getHistoryIcon(item.action)}
      </div>
      <div class="history-content">
        <div class="history-file">${item.filePath}</div>
        <div class="history-time">${getActionText(item.action)} • ${formatTime(item.timestamp)}</div>
      </div>
    </div>
  `).join('');
}

function updateStats(stats) {
  if (stats.uploaded !== undefined) {
    elements.uploadCount.textContent = parseInt(elements.uploadCount.textContent) + stats.uploaded;
  }
  if (stats.downloaded !== undefined) {
    elements.downloadCount.textContent = parseInt(elements.downloadCount.textContent) + stats.downloaded;
  }
}

function updateLastSyncTime() {
  elements.lastSyncTime.textContent = formatTime(Date.now());
}

async function loadSettings() {
  try {
    const settings = await ipcRenderer.invoke('get-settings');
    elements.bgRunSetting.checked = settings.runInBackground;
    elements.notifySetting.checked = settings.showNotifications;
    elements.historyDaysSetting.value = settings.historyDays;
  } catch (error) {
    console.error('Failed to load settings:', error);
  }
}

async function saveSettings() {
  const settings = {
    runInBackground: elements.bgRunSetting.checked,
    showNotifications: elements.notifySetting.checked,
    historyDays: parseInt(elements.historyDaysSetting.value)
  };
  
  try {
    await ipcRenderer.invoke('update-settings', settings);
    showNotification('设置已保存', 'success');
  } catch (error) {
    showNotification('保存失败: ' + error.message, 'error');
  }
}

function showNotification(message, type = 'info') {
  elements.notificationMessage.textContent = message;
  elements.notificationIcon.className = 'notification-icon ' + type;
  elements.notificationIcon.innerHTML = getNotificationIcon(type);
  
  elements.notification.classList.add('show');
  
  setTimeout(() => {
    elements.notification.classList.remove('show');
  }, 3000);
}

function getActionIcon(action) {
  switch (action) {
    case 'add':
    case 'upload':
      return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>';
    case 'download':
      return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>';
    case 'delete':
      return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>';
    case 'change':
      return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>';
    default:
      return '';
  }
}

function getHistoryIcon(action) {
  switch (action) {
    case 'upload': return '↑';
    case 'download': return '↓';
    case 'delete': return '×';
    default: return '•';
  }
}

function getActionText(action) {
  switch (action) {
    case 'add': return '添加';
    case 'upload': return '上传';
    case 'download': return '下载';
    case 'delete': return '删除';
    case 'change': return '修改';
    default: return action;
  }
}

function getNotificationIcon(type) {
  switch (type) {
    case 'success':
      return '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>';
    case 'error':
      return '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>';
    case 'warning':
      return '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>';
    default:
      return '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>';
  }
}

function getPauseIcon() {
  return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg>';
}

function getResumeIcon() {
  return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>';
}

function formatSize(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatTime(timestamp) {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now - date;
  
  if (diff < 60000) {
    return '刚刚';
  } else if (diff < 3600000) {
    return Math.floor(diff / 60000) + '分钟前';
  } else if (diff < 86400000) {
    return Math.floor(diff / 3600000) + '小时前';
  } else {
    return date.toLocaleDateString('zh-CN') + ' ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  }
}

window.onFolderToggle = onFolderToggle;
window.resolveConflict = async (conflictId, resolution) => {
  try {
    await ipcRenderer.invoke('resolve-conflict', conflictId, resolution);
    activeConflicts = activeConflicts.filter(c => c.id !== conflictId);
    showNotification('冲突已解决', 'success');
  } catch (error) {
    showNotification(`解决冲突失败: ${error.message}`, 'error');
  }
};

window.openConflictDetail = (conflictId) => {
  const conflict = activeConflicts.find(c => c.id === conflictId);
  if (conflict) {
    ipcRenderer.send('open-conflict-dialog', conflict);
  }
};

init();

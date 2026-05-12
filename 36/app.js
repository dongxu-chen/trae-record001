const DiaryApp = {
  API_BASE: 'http://localhost:3000/api',
  currentUser: null,
  currentDiary: null,
  originalViewportHeight: 0,
  keyboardOpen: false,
  autoSaveTimer: null,
  pendingPasswordAction: null,

  async init() {
    this.originalViewportHeight = window.innerHeight;
    await this.registerServiceWorker();
    this.setupEventListeners();
    this.setupMobileKeyboardHandler();
    this.setupSWUpdateListener();
    this.checkAuth();
    this.setupEditor();
    window.updateSyncProgress = (msg) => this.updateSyncProgress(msg);
  },

  async registerServiceWorker() {
    if ('serviceWorker' in navigator) {
      try {
        const registration = await navigator.serviceWorker.register('./sw.js');
        console.log('[App] Service Worker 注册成功:', registration.scope);
        
        if (registration.waiting) {
          this.showUpdateNotification(registration.waiting);
        }
        
        registration.addEventListener('updatefound', () => {
          console.log('[App] 发现新版本，正在下载...');
          const newWorker = registration.installing;
          
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              console.log('[App] 新版本已安装');
              this.showUpdateNotification(newWorker);
            }
          });
        });
      } catch (error) {
        console.error('[App] Service Worker 注册失败:', error);
      }
    }
  },

  setupSWUpdateListener() {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.addEventListener('message', (event) => {
        const { data } = event;
        
        if (data.type === 'SW_UPDATED') {
          console.log('[App] Service Worker 已更新:', data.version);
        }
        
        if (data.type === 'CONTENT_UPDATED') {
          console.log('[App] 内容已更新:', data.url);
        }
      });
      
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        console.log('[App] Service Worker 控制器已变更');
      });
    }
  },

  showUpdateNotification(worker) {
    if (confirm('发现新版本！是否立即刷新？')) {
      worker.postMessage({ type: 'SKIP_WAITING' });
      window.location.reload();
    }
  },

  setupMobileKeyboardHandler() {
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    
    if (!isMobile && !('visualViewport' in window)) {
      return;
    }
    
    if ('visualViewport' in window) {
      window.visualViewport.addEventListener('resize', () => {
        this.handleViewportResize();
      });
      
      window.visualViewport.addEventListener('scroll', () => {
        this.handleViewportScroll();
      });
    }
    
    window.addEventListener('resize', () => {
      this.handleWindowResize();
    });
    
    const editor = document.getElementById('editor');
    if (editor) {
      editor.addEventListener('focus', () => {
        setTimeout(() => this.scrollEditorIntoView(), 300);
      });
      
      editor.addEventListener('touchend', () => {
        setTimeout(() => this.scrollEditorIntoView(), 300);
      });
    }
    
    const titleInput = document.getElementById('diary-title');
    if (titleInput) {
      titleInput.addEventListener('focus', () => {
        setTimeout(() => this.scrollEditorIntoView(), 300);
      });
    }
  },

  handleViewportResize() {
    const viewport = window.visualViewport;
    if (!viewport) return;
    
    const heightDiff = this.originalViewportHeight - viewport.height;
    const keyboardThreshold = 100;
    
    this.keyboardOpen = heightDiff > keyboardThreshold;
    
    if (this.keyboardOpen) {
      document.body.classList.add('keyboard-open');
      this.adjustEditorForKeyboard(viewport.height);
    } else {
      document.body.classList.remove('keyboard-open');
      this.restoreEditorLayout();
    }
  },

  handleViewportScroll() {
    if (!this.keyboardOpen) return;
    
    const editorSection = document.querySelector('.editor-section');
    if (editorSection) {
      const toolbar = document.querySelector('.toolbar');
      if (toolbar) {
        const rect = toolbar.getBoundingClientRect();
        const viewport = window.visualViewport;
        
        if (rect.top < viewport.offsetTop) {
          toolbar.style.position = 'fixed';
          toolbar.style.top = viewport.offsetTop + 'px';
          toolbar.style.left = rect.left + 'px';
          toolbar.style.width = rect.width + 'px';
          toolbar.style.zIndex = '1000';
        } else {
          toolbar.style.position = '';
          toolbar.style.top = '';
          toolbar.style.left = '';
          toolbar.style.width = '';
          toolbar.style.zIndex = '';
        }
      }
    }
  },

  handleWindowResize() {
    const newHeight = window.innerHeight;
    const heightDiff = this.originalViewportHeight - newHeight;
    const keyboardThreshold = 150;
    
    this.keyboardOpen = heightDiff > keyboardThreshold;
    
    if (this.keyboardOpen) {
      document.body.classList.add('keyboard-open');
      this.adjustEditorForKeyboard(newHeight);
    } else {
      document.body.classList.remove('keyboard-open');
      this.restoreEditorLayout();
    }
  },

  adjustEditorForKeyboard(availableHeight) {
    const editorContainer = document.querySelector('.editor-container');
    const headerHeight = document.querySelector('.app-header')?.offsetHeight || 73;
    const reservedSpace = headerHeight + 20;
    
    if (editorContainer) {
      const maxHeight = availableHeight - reservedSpace;
      editorContainer.style.maxHeight = maxHeight + 'px';
      editorContainer.style.height = 'auto';
      editorContainer.style.minHeight = '200px';
    }
    
    const editorContent = document.querySelector('.editor-content');
    if (editorContent) {
      editorContent.style.maxHeight = (availableHeight - 300) + 'px';
      editorContent.style.minHeight = '100px';
    }
    
    setTimeout(() => this.scrollEditorIntoView(), 100);
  },

  restoreEditorLayout() {
    const editorContainer = document.querySelector('.editor-container');
    if (editorContainer) {
      editorContainer.style.maxHeight = '';
      editorContainer.style.height = '';
      editorContainer.style.minHeight = '';
    }
    
    const editorContent = document.querySelector('.editor-content');
    if (editorContent) {
      editorContent.style.maxHeight = '';
      editorContent.style.minHeight = '';
    }
    
    const toolbar = document.querySelector('.toolbar');
    if (toolbar) {
      toolbar.style.position = '';
      toolbar.style.top = '';
      toolbar.style.left = '';
      toolbar.style.width = '';
      toolbar.style.zIndex = '';
    }
  },

  scrollEditorIntoView() {
    const editor = document.getElementById('editor');
    if (!editor) return;
    
    const selection = window.getSelection();
    if (selection.rangeCount > 0) {
      const range = selection.getRangeAt(0);
      const rect = range.getBoundingClientRect();
      
      if (rect.bottom > (window.visualViewport?.height || window.innerHeight) - 50) {
        editor.scrollTop += rect.bottom - (window.visualViewport?.height || window.innerHeight) + 50;
      }
    }
    
    const editorRect = editor.getBoundingClientRect();
    const viewportHeight = window.visualViewport?.height || window.innerHeight;
    
    if (editorRect.bottom > viewportHeight - 20) {
      const scrollAmount = editorRect.bottom - viewportHeight + 20;
      window.scrollBy(0, scrollAmount);
    }
  },

  setupEventListeners() {
    document.querySelectorAll('.auth-tab').forEach(tab => {
      tab.addEventListener('click', () => this.switchAuthTab(tab));
    });

    document.getElementById('login-form').addEventListener('submit', (e) => {
      e.preventDefault();
      this.handleLogin();
    });

    document.getElementById('register-form').addEventListener('submit', (e) => {
      e.preventDefault();
      this.handleRegister();
    });

    document.getElementById('logout-btn').addEventListener('click', () => {
      this.handleLogout();
    });

    document.getElementById('new-diary-btn').addEventListener('click', () => {
      this.createNewDiary();
    });

    document.getElementById('save-btn').addEventListener('click', () => {
      this.saveDiary();
    });

    document.getElementById('delete-btn').addEventListener('click', () => {
      this.deleteDiary();
    });

    document.getElementById('search-input').addEventListener('input', (e) => {
      this.searchDiaries(e.target.value);
    });

    document.getElementById('editor').addEventListener('input', () => {
      this.updateWordCount();
      this.updateSaveStatus('unsaved');
      this.scheduleAutoSave();
    });

    document.getElementById('diary-title').addEventListener('input', () => {
      this.updateSaveStatus('unsaved');
      this.scheduleAutoSave();
    });

    document.querySelectorAll('.toolbar-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const command = btn.dataset.command;
        this.executeCommand(command);
        this.updateToolbarState();
      });
    });

    document.getElementById('font-size').addEventListener('change', (e) => {
      this.executeCommand('fontSize', e.target.value);
    });

    document.getElementById('text-color').addEventListener('input', (e) => {
      this.executeCommand('foreColor', e.target.value);
    });

    document.getElementById('bg-color').addEventListener('input', (e) => {
      this.executeCommand('hiliteColor', e.target.value);
    });

    document.addEventListener('selectionchange', () => {
      this.updateToolbarState();
    });

    this.setupModalListeners();
    this.setupSettingsListeners();
    this.setupBackupListeners();
  },

  setupModalListeners() {
    document.getElementById('settings-btn')?.addEventListener('click', () => {
      this.openSettingsModal();
    });

    document.getElementById('backup-btn')?.addEventListener('click', () => {
      this.openBackupModal();
    });

    document.getElementById('close-settings')?.addEventListener('click', () => {
      this.closeModal('settings-modal');
    });

    document.getElementById('close-backup')?.addEventListener('click', () => {
      this.closeModal('backup-modal');
    });

    document.getElementById('close-password-modal')?.addEventListener('click', () => {
      this.closeModal('password-modal');
      this.pendingPasswordAction = null;
    });

    document.getElementById('cancel-password-btn')?.addEventListener('click', () => {
      this.closeModal('password-modal');
      this.pendingPasswordAction = null;
    });

    document.getElementById('confirm-password-btn')?.addEventListener('click', () => {
      this.handlePasswordConfirm();
    });

    document.querySelectorAll('.modal-overlay').forEach(overlay => {
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
          overlay.style.display = 'none';
        }
      });
    });
  },

  setupSettingsListeners() {
    document.getElementById('save-settings-btn')?.addEventListener('click', () => {
      this.saveSettings();
    });

    document.getElementById('rotate-key-btn')?.addEventListener('click', () => {
      this.rotateEncryptionKey();
    });

    document.getElementById('export-key-btn')?.addEventListener('click', () => {
      this.exportEncryptionKey();
    });

    document.getElementById('import-key-btn')?.addEventListener('click', () => {
      document.getElementById('key-file-input').click();
    });

    document.getElementById('key-file-input')?.addEventListener('change', (e) => {
      if (e.target.files.length > 0) {
        this.importEncryptionKey(e.target.files[0]);
      }
    });
  },

  setupBackupListeners() {
    document.getElementById('create-backup-btn')?.addEventListener('click', () => {
      this.createBackup();
    });

    document.getElementById('import-backup-btn')?.addEventListener('click', () => {
      document.getElementById('backup-file-input').click();
    });

    document.getElementById('backup-file-input')?.addEventListener('change', (e) => {
      if (e.target.files.length > 0) {
        this.importBackup(e.target.files[0]);
      }
    });
  },

  async openSettingsModal() {
    const modal = document.getElementById('settings-modal');
    if (!modal) return;

    const encryptionEnabled = await SettingsManager.get('encryptionEnabled', true);
    const theme = await SettingsManager.get('theme', 'light');
    const fontSize = await SettingsManager.get('fontSize', 'medium');
    const autoSave = await SettingsManager.get('autoSave', true);
    const autoSaveInterval = await SettingsManager.get('autoSaveInterval', 30);
    const autoBackup = await SettingsManager.get('autoBackup', false);
    const backupInterval = await SettingsManager.get('autoBackupInterval', 24);

    document.getElementById('setting-encryption').checked = encryptionEnabled;
    document.getElementById('setting-theme').value = theme;
    document.getElementById('setting-fontsize').value = fontSize;
    document.getElementById('setting-autosave').checked = autoSave;
    document.getElementById('setting-autosave-interval').value = autoSaveInterval;
    document.getElementById('setting-autobackup').checked = autoBackup;
    document.getElementById('setting-backup-interval').value = backupInterval;

    modal.style.display = 'flex';
  },

  async openBackupModal() {
    const modal = document.getElementById('backup-modal');
    if (!modal) return;

    await this.loadBackupHistory();
    modal.style.display = 'flex';
  },

  closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.style.display = 'none';
    }
  },

  async loadBackupHistory() {
    const listEl = document.getElementById('backup-list');
    if (!listEl || !this.currentUser) return;

    const backups = await IDB.BackupMetadataStore.getAll(this.currentUser.id);

    if (backups.length === 0) {
      listEl.innerHTML = `
        <div class="empty-state">
          <p>暂无备份记录</p>
        </div>
      `;
      return;
    }

    listEl.innerHTML = backups.map(backup => `
      <div class="backup-item">
        <div class="backup-item-info">
          <div class="backup-item-title">备份 - ${new Date(backup.createdAt).toLocaleString('zh-CN')}</div>
          <div class="backup-item-meta">
            ${backup.diaryCount || 0} 篇日记 · ${this.formatSize(backup.size || 0)}
          </div>
        </div>
        <div class="backup-item-actions">
          <button class="btn btn-secondary" onclick="DiaryApp.restoreBackup('${backup.id}')">恢复</button>
          <button class="btn btn-secondary" onclick="DiaryApp.downloadBackup('${backup.id}')">下载</button>
        </div>
      </div>
    `).join('');
  },

  formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  },

  async saveSettings() {
    try {
      await SettingsManager.set('encryptionEnabled', document.getElementById('setting-encryption').checked);
      await SettingsManager.set('theme', document.getElementById('setting-theme').value);
      await SettingsManager.set('fontSize', document.getElementById('setting-fontsize').value);
      await SettingsManager.set('autoSave', document.getElementById('setting-autosave').checked);
      await SettingsManager.set('autoSaveInterval', parseInt(document.getElementById('setting-autosave-interval').value) || 30);
      await SettingsManager.set('autoBackup', document.getElementById('setting-autobackup').checked);
      await SettingsManager.set('autoBackupInterval', parseInt(document.getElementById('setting-backup-interval').value) || 24);

      this.showToast('设置已保存', 'success');
      this.closeModal('settings-modal');
      this.updateEncryptionStatus();
    } catch (error) {
      console.error('[App] 保存设置失败:', error);
      this.showToast('保存设置失败', 'error');
    }
  },

  async rotateEncryptionKey() {
    if (!this.currentUser) return;
    
    if (!confirm('警告：轮换密钥将重新加密所有日记。请确保已导出当前密钥作为备份。是否继续？')) {
      return;
    }

    try {
      await SettingsManager.rotateEncryptionKey(this.currentUser.id, true);
      this.showToast('密钥轮换成功', 'success');
    } catch (error) {
      console.error('[App] 密钥轮换失败:', error);
      this.showToast('密钥轮换失败: ' + error.message, 'error');
    }
  },

  async exportEncryptionKey() {
    if (!this.currentUser) return;

    this.pendingPasswordAction = 'export-key';
    this.showPasswordModal('设置保护密码', true);
  },

  async importEncryptionKey(file) {
    if (!this.currentUser) return;

    this.pendingPasswordAction = 'import-key';
    this.pendingFile = file;
    this.showPasswordModal('输入密钥保护密码', false);
  },

  async handlePasswordConfirm() {
    const password = document.getElementById('password-input').value;
    const confirmPassword = document.getElementById('confirm-password-input').value;

    if (!password || password.length < 6) {
      this.showToast('密码至少6位', 'error');
      return;
    }

    if (this.pendingPasswordAction === 'export-key' && password !== confirmPassword) {
      this.showToast('两次密码不一致', 'error');
      return;
    }

    this.closeModal('password-modal');

    try {
      switch (this.pendingPasswordAction) {
        case 'export-key':
          await SettingsManager.exportEncryptionKey(this.currentUser.id, password);
          this.showToast('密钥已导出', 'success');
          break;

        case 'import-key':
          await SettingsManager.importEncryptionKey(this.pendingFile, password, this.currentUser.id);
          this.showToast('密钥已导入', 'success');
          break;

        case 'create-backup':
          await this.doCreateBackup(password);
          break;

        case 'restore-backup':
          await this.doRestoreBackup(this.pendingBackupData, password);
          break;
      }
    } catch (error) {
      console.error('[App] 密码操作失败:', error);
      this.showToast('操作失败: ' + error.message, 'error');
    } finally {
      this.pendingPasswordAction = null;
      this.pendingFile = null;
      this.pendingBackupData = null;
    }
  },

  showPasswordModal(title, needConfirm = false) {
    document.getElementById('password-modal-title').textContent = title;
    document.getElementById('password-input').value = '';
    document.getElementById('confirm-password-input').value = '';
    document.getElementById('confirm-password-group').style.display = needConfirm ? 'block' : 'none';
    document.getElementById('password-modal').style.display = 'flex';
    document.getElementById('password-input').focus();
  },

  async createBackup() {
    if (!this.currentUser) return;

    const encryptionEnabled = await SettingsManager.get('encryptionEnabled', true);
    if (encryptionEnabled) {
      this.pendingPasswordAction = 'create-backup';
      this.showPasswordModal('设置备份密码（用于加密密钥）', true);
    } else {
      await this.doCreateBackup(null);
    }
  },

  async doCreateBackup(password) {
    try {
      this.showBackupProgress(true, '正在创建备份...');

      const result = await GoogleDriveBackup.createBackup(this.currentUser.id, {
        encryptionPassword: password,
        progressCallback: (msg) => this.showBackupProgress(true, msg)
      });

      await SettingsManager.recordBackup();
      await this.loadBackupHistory();

      this.showBackupProgress(false);
      this.showToast('备份成功！共 ' + result.backupData.data.diaries.length + ' 篇日记', 'success');
    } catch (error) {
      console.error('[App] 备份失败:', error);
      this.showBackupProgress(false);
      this.showToast('备份失败: ' + error.message, 'error');
    }
  },

  async importBackup(file) {
    try {
      const backupData = await GoogleDriveBackup.importFromFile(file);
      
      if (backupData.encryptedKey) {
        this.pendingPasswordAction = 'restore-backup';
        this.pendingBackupData = backupData;
        this.showPasswordModal('输入备份密码', false);
      } else {
        await this.doRestoreBackup(backupData, null);
      }
    } catch (error) {
      console.error('[App] 导入备份失败:', error);
      this.showToast('导入失败: ' + error.message, 'error');
    }
  },

  async doRestoreBackup(backupData, password) {
    try {
      this.showBackupProgress(true, '正在恢复数据...');

      const result = await GoogleDriveBackup.restoreBackup(backupData.data?.userId || this.currentUser?.id, {
        progressCallback: (msg) => this.showBackupProgress(true, msg),
        encryptionPassword: password
      });

      this.showBackupProgress(false);
      this.showToast('恢复成功！共 ' + result.diaryCount + ' 篇日记', 'success');
      
      await this.loadDiaries();
      await this.loadBackupHistory();
    } catch (error) {
      console.error('[App] 恢复失败:', error);
      this.showBackupProgress(false);
      this.showToast('恢复失败: ' + error.message, 'error');
    }
  },

  async restoreBackup(backupId) {
    if (!confirm('恢复备份将覆盖当前数据。是否继续？')) {
      return;
    }

    try {
      this.showBackupProgress(true, '正在恢复备份...');

      const result = await GoogleDriveBackup.restoreBackup(backupId, {
        progressCallback: (msg) => this.showBackupProgress(true, msg)
      });

      this.showBackupProgress(false);
      this.showToast('恢复成功！共 ' + result.diaryCount + ' 篇日记', 'success');
      
      await this.loadDiaries();
    } catch (error) {
      console.error('[App] 恢复失败:', error);
      this.showBackupProgress(false);
      this.showToast('恢复失败: ' + error.message, 'error');
    }
  },

  async downloadBackup(backupId) {
    try {
      await GoogleDriveBackup.downloadBackupFile(backupId);
      this.showToast('备份文件已下载', 'success');
    } catch (error) {
      console.error('[App] 下载失败:', error);
      this.showToast('下载失败: ' + error.message, 'error');
    }
  },

  showBackupProgress(show, text = '') {
    const progressEl = document.getElementById('backup-progress');
    if (progressEl) {
      progressEl.style.display = show ? 'block' : 'none';
    }
    const textEl = document.getElementById('backup-progress-text');
    if (textEl && text) {
      textEl.textContent = text;
    }
  },

  scheduleAutoSave() {
    if (this.autoSaveTimer) {
      clearTimeout(this.autoSaveTimer);
    }

    const autoSave = SettingsManager.userSettings.autoSave !== false;
    if (!autoSave) return;

    const interval = (SettingsManager.userSettings.autoSaveInterval || 30) * 1000;
    
    this.autoSaveTimer = setTimeout(() => {
      this.saveDiary(true);
    }, interval);
  },

  showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    container.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('toast-show');
    }, 10);

    setTimeout(() => {
      toast.classList.remove('toast-show');
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  },

  updateSyncProgress(message) {
    if (message) {
      document.getElementById('sync-status').textContent = message;
    }
  },

  updateEncryptionStatus() {
    const statusEl = document.getElementById('encryption-status');
    if (!statusEl || !this.currentUser) return;

    const encryptionEnabled = SettingsManager.userSettings.encryptionEnabled !== false;
    statusEl.textContent = encryptionEnabled ? '🔒' : '';
    statusEl.title = encryptionEnabled ? '日记已加密' : '未加密';
  },

  switchAuthTab(tab) {
    document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.auth-form').forEach(f => f.classList.remove('active'));
    
    tab.classList.add('active');
    const tabName = tab.dataset.tab;
    document.getElementById(`${tabName}-form`).classList.add('active');
    this.hideAuthMessage();
  },

  showAuthMessage(message, isError = false) {
    const msgEl = document.getElementById('auth-message');
    msgEl.textContent = message;
    msgEl.className = `auth-message show ${isError ? 'error' : 'success'}`;
  },

  hideAuthMessage() {
    const msgEl = document.getElementById('auth-message');
    msgEl.classList.remove('show');
  },

  async checkAuth() {
    const userStr = localStorage.getItem('currentUser');
    if (userStr) {
      try {
        this.currentUser = JSON.parse(userStr);
        await SettingsManager.init(this.currentUser.id);
        this.showMainApp();
        await this.loadDiaries();
        this.updateEncryptionStatus();
      } catch (error) {
        this.showAuthUI();
      }
    } else {
      this.showAuthUI();
    }
  },

  showAuthUI() {
    document.getElementById('auth-container').style.display = 'flex';
    document.getElementById('main-container').style.display = 'none';
    document.getElementById('logout-btn').style.display = 'none';
    document.getElementById('settings-btn').style.display = 'none';
    document.getElementById('backup-btn').style.display = 'none';
    document.getElementById('user-info').textContent = '';
  },

  showMainApp() {
    document.getElementById('auth-container').style.display = 'none';
    document.getElementById('main-container').style.display = 'flex';
    document.getElementById('logout-btn').style.display = 'inline-block';
    document.getElementById('settings-btn').style.display = 'inline-block';
    document.getElementById('backup-btn').style.display = 'inline-block';
    document.getElementById('user-info').textContent = this.currentUser?.name || '';
  },

  async handleLogin() {
    const email = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;

    if (!email || !password) {
      this.showAuthMessage('请填写邮箱和密码', true);
      return;
    }

    try {
      const response = await fetch(`${this.API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      if (response.ok) {
        const data = await response.json();
        this.currentUser = data.user;
        localStorage.setItem('currentUser', JSON.stringify(data.user));
        await IDB.UserStore.save(data.user);
        await SettingsManager.init(this.currentUser.id);
        
        this.showAuthMessage('登录成功！');
        setTimeout(() => {
          this.showMainApp();
          this.loadDiaries();
          this.updateEncryptionStatus();
        }, 500);
      } else {
        const cachedUser = await IDB.UserStore.get(email);
        if (cachedUser && cachedUser.password === password) {
          this.currentUser = cachedUser;
          localStorage.setItem('currentUser', JSON.stringify(cachedUser));
          await SettingsManager.init(this.currentUser.id);
          this.showAuthMessage('离线登录成功！');
          setTimeout(() => {
            this.showMainApp();
            this.loadDiaries();
            this.updateEncryptionStatus();
          }, 500);
        } else {
          const error = await response.json().catch(() => ({ message: '登录失败' }));
          this.showAuthMessage(error.message || '登录失败', true);
        }
      }
    } catch (error) {
      const cachedUser = await IDB.UserStore.get(email);
      if (cachedUser && cachedUser.password === password) {
        this.currentUser = cachedUser;
        localStorage.setItem('currentUser', JSON.stringify(cachedUser));
        await SettingsManager.init(this.currentUser.id);
        this.showAuthMessage('离线登录成功！');
        setTimeout(() => {
          this.showMainApp();
          this.loadDiaries();
          this.updateEncryptionStatus();
        }, 500);
      } else {
        this.showAuthMessage('网络错误，请检查连接', true);
      }
    }
  },

  async handleRegister() {
    const name = document.getElementById('register-name').value.trim();
    const email = document.getElementById('register-email').value.trim();
    const password = document.getElementById('register-password').value;

    if (!name || !email || !password) {
      this.showAuthMessage('请填写完整信息', true);
      return;
    }

    if (password.length < 6) {
      this.showAuthMessage('密码至少6位', true);
      return;
    }

    try {
      const response = await fetch(`${this.API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, password })
      });

      if (response.ok) {
        const data = await response.json();
        this.currentUser = data.user;
        localStorage.setItem('currentUser', JSON.stringify(data.user));
        await IDB.UserStore.save(data.user);
        await SettingsManager.init(this.currentUser.id);
        
        this.showAuthMessage('注册成功！');
        setTimeout(() => {
          this.showMainApp();
          this.loadDiaries();
          this.updateEncryptionStatus();
        }, 500);
      } else {
        const error = await response.json().catch(() => ({ message: '注册失败' }));
        this.showAuthMessage(error.message || '注册失败', true);
      }
    } catch (error) {
      this.showAuthMessage('网络错误，请稍后重试', true);
    }
  },

  handleLogout() {
    if (this.autoSaveTimer) {
      clearTimeout(this.autoSaveTimer);
    }
    this.currentUser = null;
    localStorage.removeItem('currentUser');
    this.currentDiary = null;
    this.clearEditor();
    this.showAuthUI();
  },

  setupEditor() {
    const editor = document.getElementById('editor');
    editor.setAttribute('data-placeholder', '开始写作...');
  },

  executeCommand(command, value = null) {
    document.execCommand(command, false, value);
    document.getElementById('editor').focus();
  },

  updateToolbarState() {
    const commands = ['bold', 'italic', 'underline', 'strikeThrough'];
    commands.forEach(cmd => {
      const btn = document.querySelector(`[data-command="${cmd}"]`);
      if (btn) {
        if (document.queryCommandState(cmd)) {
          btn.classList.add('active');
        } else {
          btn.classList.remove('active');
        }
      }
    });
  },

  updateWordCount() {
    const editor = document.getElementById('editor');
    const text = editor.innerText.trim();
    const count = text.length;
    document.getElementById('word-count').textContent = `字数: ${count}`;
  },

  updateSaveStatus(status) {
    const statusEl = document.getElementById('save-status');
    switch (status) {
      case 'saving':
        statusEl.textContent = '保存中...';
        break;
      case 'saved':
        statusEl.textContent = '已保存';
        break;
      case 'unsaved':
        statusEl.textContent = '未保存';
        break;
      case 'syncing':
        statusEl.textContent = '同步中...';
        break;
      default:
        statusEl.textContent = '';
    }
  },

  createNewDiary() {
    this.currentDiary = null;
    this.clearEditor();
    document.getElementById('delete-btn').style.display = 'none';
    document.getElementById('diary-date').textContent = 
      new Date().toLocaleDateString('zh-CN', { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric',
        weekday: 'long'
      });
    document.getElementById('diary-title').focus();
  },

  clearEditor() {
    document.getElementById('diary-title').value = '';
    document.getElementById('editor').innerHTML = '';
    this.updateWordCount();
    this.updateSaveStatus('');
  },

  async loadDiaries() {
    if (!this.currentUser) return;

    try {
      const diaries = await IDB.DiaryStore.getAll(this.currentUser.id);
      this.renderDiaryList(diaries);
      window.refreshDiaryList = () => this.loadDiaries();
    } catch (error) {
      console.error('[App] 加载日记失败:', error);
    }
  },

  renderDiaryList(diaries) {
    const listEl = document.getElementById('diary-list');

    if (diaries.length === 0) {
      listEl.innerHTML = `
        <div class="empty-state">
          <p>还没有日记</p>
          <p class="empty-hint">点击上方按钮开始写作</p>
        </div>
      `;
      return;
    }

    listEl.innerHTML = diaries.map(diary => `
      <div class="diary-item ${diary.synced ? 'synced' : 'pending'}" 
           data-id="${diary.id}">
        <div class="diary-item-title">${diary.title || '无标题'}</div>
        <div class="diary-item-preview">${this.stripHtml(diary.content || '')}</div>
        <div class="diary-item-date">${this.formatDate(diary.updatedAt)}
          ${diary.encrypted ? '<span class="diary-encrypted" title="已加密">🔒</span>' : ''}
        </div>
      </div>
    `).join('');

    listEl.querySelectorAll('.diary-item').forEach(item => {
      item.addEventListener('click', () => {
        const diaryId = item.dataset.id;
        this.openDiary(diaryId);
      });
    });
  },

  stripHtml(html) {
    const tmp = document.createElement('div');
    tmp.innerHTML = html;
    return tmp.textContent || tmp.innerText || '';
  },

  formatDate(dateStr) {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now - date;
    const oneDay = 24 * 60 * 60 * 1000;

    if (diff < oneDay && date.getDate() === now.getDate()) {
      return `今天 ${date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`;
    } else if (diff < 2 * oneDay) {
      return '昨天';
    } else {
      return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
    }
  },

  async openDiary(diaryId) {
    try {
      const diary = await IDB.DiaryStore.getById(diaryId);
      if (diary) {
        this.currentDiary = diary;
        document.getElementById('diary-title').value = diary.title || '';
        document.getElementById('editor').innerHTML = diary.content || '';
        document.getElementById('diary-date').textContent = 
          new Date(diary.createdAt).toLocaleDateString('zh-CN', { 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric',
            weekday: 'long'
          });
        document.getElementById('delete-btn').style.display = 'inline-block';
        this.updateWordCount();
        this.updateSaveStatus(diary.synced ? 'saved' : 'unsaved');

        document.querySelectorAll('.diary-item').forEach(item => {
          item.classList.remove('active');
          if (item.dataset.id === diaryId) {
            item.classList.add('active');
          }
        });
      }
    } catch (error) {
      console.error('[App] 打开日记失败:', error);
    }
  },

  async saveDiary(isAutoSave = false) {
    if (!this.currentUser) return;

    const title = document.getElementById('diary-title').value.trim();
    const content = document.getElementById('editor').innerHTML;

    if (!title && !content.trim()) {
      if (!isAutoSave) {
        this.showToast('请输入日记内容', 'error');
      }
      return;
    }

    this.updateSaveStatus('saving');

    try {
      const diary = {
        ...(this.currentDiary || {}),
        title: title || '无标题',
        content,
        userId: this.currentUser.id
      };

      const savedDiary = await IDB.DiaryStore.save(diary, this.currentUser.id);
      this.currentDiary = savedDiary;

      this.updateSaveStatus('saved');
      document.getElementById('delete-btn').style.display = 'inline-block';
      
      await this.loadDiaries();

      if (SyncManager.isOnline) {
        this.updateSaveStatus('syncing');
        setTimeout(() => SyncManager.startSync(), 500);
      }
    } catch (error) {
      console.error('[App] 保存日记失败:', error);
      this.updateSaveStatus('unsaved');
      if (!isAutoSave) {
        this.showToast('保存失败: ' + error.message, 'error');
      }
    }
  },

  async deleteDiary() {
    if (!this.currentDiary) return;

    if (!confirm('确定要删除这篇日记吗？')) {
      return;
    }

    try {
      await IDB.DiaryStore.delete(this.currentDiary.id);
      this.currentDiary = null;
      this.clearEditor();
      document.getElementById('delete-btn').style.display = 'none';
      await this.loadDiaries();
      
      if (SyncManager.isOnline) {
        SyncManager.startSync();
      }
      
      this.showToast('日记已删除', 'success');
    } catch (error) {
      console.error('[App] 删除日记失败:', error);
      this.showToast('删除失败: ' + error.message, 'error');
    }
  },

  async searchDiaries(query) {
    if (!this.currentUser) return;

    try {
      if (!query.trim()) {
        await this.loadDiaries();
        return;
      }

      const diaries = await IDB.DiaryStore.search(this.currentUser.id, query);
      this.renderDiaryList(diaries);
    } catch (error) {
      console.error('[App] 搜索失败:', error);
    }
  }
};

window.DiaryApp = DiaryApp;

document.addEventListener('DOMContentLoaded', () => {
  DiaryApp.init();
});

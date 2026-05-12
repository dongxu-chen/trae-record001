const SettingsManager = {
  defaultSettings: {
    encryptionEnabled: true,
    autoBackup: false,
    autoBackupInterval: 24,
    backupToDrive: false,
    lastBackupTime: null,
    theme: 'light',
    fontSize: 'medium',
    autoSave: true,
    autoSaveInterval: 30
  },

  userSettings: {},

  async init(userId) {
    if (!userId) return;
    
    await this.loadSettings(userId);
    
    if (!Object.keys(this.userSettings).length) {
      this.userSettings = { ...this.defaultSettings };
      await this.saveAllSettings(userId);
    }
  },

  async loadSettings(userId) {
    try {
      const allSettings = await IDB.SettingsStore.getAll();
      this.userSettings = {};
      
      allSettings.forEach(item => {
        if (item.key) {
          this.userSettings[item.key] = item.value;
        }
      });

      return this.userSettings;
    } catch (error) {
      console.error('[Settings] 加载设置失败:', error);
      return this.defaultSettings;
    }
  },

  async get(key, defaultValue = undefined) {
    if (this.userSettings[key] !== undefined) {
      return this.userSettings[key];
    }
    return defaultValue !== undefined ? defaultValue : this.defaultSettings[key];
  },

  async set(key, value) {
    this.userSettings[key] = value;
    await IDB.SettingsStore.set(key, value);
    
    this.applySetting(key, value);
    
    return value;
  },

  async getAll() {
    return { ...this.defaultSettings, ...this.userSettings };
  },

  async saveAllSettings(userId) {
    for (const [key, value] of Object.entries(this.userSettings)) {
      await IDB.SettingsStore.set(key, value);
    }
  },

  applySetting(key, value) {
    switch (key) {
      case 'theme':
        this.applyTheme(value);
        break;
      case 'fontSize':
        this.applyFontSize(value);
        break;
      case 'encryptionEnabled':
        console.log('[Settings] 加密设置已变更:', value);
        break;
    }
  },

  applyTheme(theme) {
    document.body.classList.remove('theme-light', 'theme-dark');
    document.body.classList.add(`theme-${theme}`);
    
    if (theme === 'dark') {
      document.documentElement.style.setProperty('--bg', '#1e293b');
      document.documentElement.style.setProperty('--surface', '#334155');
      document.documentElement.style.setProperty('--text', '#f8fafc');
      document.documentElement.style.setProperty('--border', '#475569');
    } else {
      document.documentElement.style.setProperty('--bg', '#f8fafc');
      document.documentElement.style.setProperty('--surface', '#ffffff');
      document.documentElement.style.setProperty('--text', '#1e293b');
      document.documentElement.style.setProperty('--border', '#e2e8f0');
    }
  },

  applyFontSize(size) {
    const sizes = {
      small: '14px',
      medium: '16px',
      large: '18px'
    };
    
    const editor = document.getElementById('editor');
    if (editor) {
      editor.style.fontSize = sizes[size] || sizes.medium;
    }
  },

  async toggleEncryption(enabled, userId) {
    if (enabled) {
      await IDB.EncryptionKeyStore.getOrCreateForUser(userId);
    }
    
    await this.set('encryptionEnabled', enabled);
    return enabled;
  },

  async rotateEncryptionKey(userId, confirm = false) {
    if (!confirm) {
      throw new Error('请确认要轮换密钥');
    }

    const newKey = await IDB.EncryptionKeyStore.rotateKey(userId);
    return newKey;
  },

  async exportEncryptionKey(userId, password) {
    if (!password || password.length < 6) {
      throw new Error('请设置至少6位的保护密码');
    }

    const encryptedKey = await IDB.EncryptionKeyStore.exportKeyForBackup(userId, password);
    
    const exportData = {
      version: 1,
      type: 'encryption-key',
      createdAt: new Date().toISOString(),
      userId,
      encryptedKey
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json'
    });

    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `encryption-key-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    return true;
  },

  async importEncryptionKey(file, password, userId) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      
      reader.onload = async (e) => {
        try {
          const importData = JSON.parse(e.target.result);
          
          if (importData.type !== 'encryption-key') {
            throw new Error('无效的密钥文件格式');
          }

          await IDB.EncryptionKeyStore.importKeyFromBackup(
            importData.encryptedKey,
            password,
            userId
          );

          resolve(true);
        } catch (error) {
          reject(error);
        }
      };

      reader.onerror = () => reject(new Error('文件读取失败'));
      reader.readAsText(file);
    });
  },

  async getBackupSchedule() {
    return {
      enabled: await this.get('autoBackup', false),
      interval: await this.get('autoBackupInterval', 24),
      lastBackup: await this.get('lastBackupTime', null),
      backupToDrive: await this.get('backupToDrive', false)
    };
  },

  async shouldAutoBackup() {
    const schedule = await this.getBackupSchedule();
    if (!schedule.enabled) return false;
    if (!schedule.lastBackup) return true;

    const now = Date.now();
    const last = new Date(schedule.lastBackup).getTime();
    const interval = schedule.interval * 60 * 60 * 1000;

    return (now - last) > interval;
  },

  async recordBackup() {
    await this.set('lastBackupTime', new Date().toISOString());
  },

  async resetAll() {
    this.userSettings = { ...this.defaultSettings };
    const allSettings = await IDB.SettingsStore.getAll();
    
    for (const setting of allSettings) {
      await IDB.SettingsStore.delete(setting.key);
    }
    
    for (const [key, value] of Object.entries(this.defaultSettings)) {
      await IDB.SettingsStore.set(key, value);
      this.applySetting(key, value);
    }

    return this.userSettings;
  }
};

window.SettingsManager = SettingsManager;

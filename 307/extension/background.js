const crypto = require('../src/utils/crypto.js');

class ExtensionBackground {
  constructor() {
    this.isUnlocked = false;
    this.masterKeyHash = null;
    this.setupMessageListeners();
    this.setupCommandListeners();
  }

  setupMessageListeners() {
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      this.handleMessage(request, sender).then(sendResponse).catch(error => {
        sendResponse({ success: false, error: error.message });
      });
      return true;
    });
  }

  setupCommandListeners() {
    chrome.commands.onCommand.addListener(async (command) => {
      if (command === 'generate-password') {
        const password = this.generatePassword();
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        chrome.tabs.sendMessage(tab.id, {
          type: 'INSERT_PASSWORD',
          password: password
        });
      } else if (command === 'autofill') {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        this.triggerAutoFill(tab.id, tab.url);
      }
    });
  }

  async handleMessage(request, sender) {
    switch (request.type) {
      case 'UNLOCK':
        return this.handleUnlock(request.masterPassword);
      case 'LOCK':
        return this.handleLock();
      case 'CHECK_UNLOCKED':
        return { success: true, unlocked: this.isUnlocked };
      case 'GET_PASSWORDS_FOR_URL':
        return this.handleGetPasswordsForUrl(request.url);
      case 'GET_ALL_PASSWORDS':
        return this.handleGetAllPasswords();
      case 'ADD_PASSWORD':
        return this.handleAddPassword(request.password);
      case 'UPDATE_PASSWORD':
        return this.handleUpdatePassword(request.id, request.password);
      case 'DELETE_PASSWORD':
        return this.handleDeletePassword(request.id);
      case 'GENERATE_PASSWORD':
        return { success: true, password: this.generatePassword(request.options) };
      case 'CHECK_STRENGTH':
        return this.handleCheckStrength(request.password);
      case 'AUTO_FILL':
        return this.triggerAutoFill(sender.tab.id, request.url);
      case 'COPY_TO_CLIPBOARD':
        return this.handleCopyToClipboard(request.text);
      case 'DECRYPT_PASSWORD':
        return this.handleDecryptPassword(request.id);
      default:
        return { success: false, error: 'Unknown command' };
    }
  }

  generatePassword(options = {}) {
    const {
      length = 16,
      includeUppercase = true,
      includeLowercase = true,
      includeNumbers = true,
      includeSymbols = true
    } = options;

    let charset = '';
    if (includeLowercase) charset += 'abcdefghijklmnopqrstuvwxyz';
    if (includeUppercase) charset += 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
    if (includeNumbers) charset += '0123456789';
    if (includeSymbols) charset += '!@#$%^&*()_+-=[]{}|;:,.<>?';

    const array = new Uint32Array(length);
    crypto.getRandomValues(array);

    let password = '';
    for (let i = 0; i < length; i++) {
      password += charset[array[i] % charset.length];
    }

    return password;
  }

  handleCheckStrength(password) {
    let score = 0;
    const feedback = [];

    if (password.length >= 8) score++;
    if (password.length >= 12) score++;
    if (password.length >= 16) score++;
    if (/[a-z]/.test(password)) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^a-zA-Z0-9]/.test(password)) score++;

    let strength;
    if (score <= 2) strength = 'weak';
    else if (score <= 4) strength = 'fair';
    else if (score <= 5) strength = 'good';
    else strength = 'strong';

    return { success: true, strength, score };
  }

  async triggerAutoFill(tabId, url) {
    if (!this.isUnlocked) {
      chrome.tabs.sendMessage(tabId, {
        type: 'AUTO_FILL_ERROR',
        error: '请先解锁密码管理器'
      });
      return { success: false, error: 'Locked' };
    }

    try {
      const passwords = await this.getPasswordsForUrl(url);
      chrome.tabs.sendMessage(tabId, {
        type: 'AUTO_FILL_DATA',
        passwords: passwords
      });
      return { success: true, count: passwords.length };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async handleUnlock(masterPassword) {
    try {
      const storedSalt = await this.getFromStorage('salt');
      const storedHash = await this.getFromStorage('masterPasswordHash');

      if (!storedSalt || !storedHash) {
        return { success: false, error: '未找到账户，请先创建账户' };
      }

      const hash = await this.hashPassword(masterPassword);
      if (hash !== storedHash) {
        return { success: false, error: '主密码错误' };
      }

      await crypto.cryptoService.init(masterPassword, storedSalt);
      this.isUnlocked = true;
      this.masterKeyHash = hash;

      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  handleLock() {
    crypto.cryptoService.clearKeys();
    this.isUnlocked = false;
    this.masterKeyHash = null;
    return { success: true };
  }

  async handleGetPasswordsForUrl(url) {
    if (!this.isUnlocked) {
      return { success: false, error: '请先解锁密码管理器' };
    }

    try {
      const passwords = await this.getPasswordsForUrl(url);
      return { success: true, passwords };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async handleGetAllPasswords() {
    if (!this.isUnlocked) {
      return { success: false, error: '请先解锁密码管理器' };
    }

    try {
      const passwords = await this.getAllPasswords();
      return { success: true, passwords };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async handleAddPassword(passwordData) {
    if (!this.isUnlocked) {
      return { success: false, error: '请先解锁密码管理器' };
    }

    try {
      const id = await this.addPassword(passwordData);
      return { success: true, id };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async handleUpdatePassword(id, passwordData) {
    if (!this.isUnlocked) {
      return { success: false, error: '请先解锁密码管理器' };
    }

    try {
      await this.updatePassword(id, passwordData);
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async handleDeletePassword(id) {
    if (!this.isUnlocked) {
      return { success: false, error: '请先解锁密码管理器' };
    }

    try {
      await this.deletePassword(id);
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async handleDecryptPassword(id) {
    if (!this.isUnlocked) {
      return { success: false, error: '请先解锁密码管理器' };
    }

    try {
      const password = await this.getDecryptedPassword(id);
      return { success: true, password };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async handleCopyToClipboard(text) {
    try {
      await chrome.clipboard.set({ text });
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async getPasswordsForUrl(url) {
    const allPasswords = await this.getAllPasswords();
    return allPasswords.filter(p => {
      if (!p.url) return false;
      try {
        const passwordHost = new URL(p.url).hostname;
        const targetHost = new URL(url).hostname;
        return passwordHost === targetHost || 
               targetHost.endsWith('.' + passwordHost) ||
               passwordHost.endsWith('.' + targetHost);
      } catch {
        return p.url.includes(url) || url.includes(p.url);
      }
    });
  }

  async getAllPasswords() {
    const data = await this.getFromStorage('passwords');
    return data ? JSON.parse(data) : [];
  }

  async addPassword(passwordData) {
    const passwords = await this.getAllPasswords();
    const id = Date.now();
    passwords.push({ id, ...passwordData });
    await this.saveToStorage('passwords', JSON.stringify(passwords));
    return id;
  }

  async updatePassword(id, passwordData) {
    const passwords = await this.getAllPasswords();
    const index = passwords.findIndex(p => p.id === id);
    if (index === -1) throw new Error('密码不存在');
    passwords[index] = { ...passwords[index], ...passwordData, updatedAt: Date.now() };
    await this.saveToStorage('passwords', JSON.stringify(passwords));
  }

  async deletePassword(id) {
    const passwords = await this.getAllPasswords();
    const filtered = passwords.filter(p => p.id !== id);
    await this.saveToStorage('passwords', JSON.stringify(filtered));
  }

  async getDecryptedPassword(id) {
    const passwords = await this.getAllPasswords();
    const password = passwords.find(p => p.id === id);
    if (!password) throw new Error('密码不存在');

    if (password.encryptedData) {
      const decrypted = await crypto.cryptoService.decrypt(password.encryptedData);
      return { ...password, password: decrypted.password, notes: decrypted.notes };
    }

    return password;
  }

  async hashPassword(password) {
    const buffer = new TextEncoder().encode(password);
    const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  }

  getFromStorage(key) {
    return new Promise((resolve) => {
      chrome.storage.local.get(key, (result) => {
        resolve(result[key]);
      });
    });
  }

  saveToStorage(key, value) {
    return new Promise((resolve) => {
      chrome.storage.local.set({ [key]: value }, resolve);
    });
  }
}

new ExtensionBackground();

class PopupApp {
  constructor() {
    this.isUnlocked = false;
    this.passwords = [];
    this.currentTab = 'passwords';
    this.init();
  }

  init() {
    this.bindEvents();
    this.checkUnlockStatus();
  }

  bindEvents() {
    document.getElementById('unlockBtn').addEventListener('click', () => this.unlock());
    document.getElementById('masterPassword').addEventListener('keypress', (e) => {
      if (e.key === 'Enter') this.unlock();
    });
    document.getElementById('lockBtn').addEventListener('click', () => this.lock());
    
    document.querySelectorAll('.tab').forEach(tab => {
      tab.addEventListener('click', () => this.switchTab(tab.dataset.tab));
    });

    document.getElementById('searchInput').addEventListener('input', () => this.renderPasswords());
    document.getElementById('generateBtn').addEventListener('click', () => this.generatePassword());
    document.getElementById('copyGeneratedBtn').addEventListener('click', () => this.copyGenerated());
    document.getElementById('insertGeneratedBtn').addEventListener('click', () => this.insertGenerated());
    
    document.getElementById('passwordLength').addEventListener('input', () => {
      if (document.getElementById('passwordText').textContent !== '点击生成按钮') {
        this.generatePassword();
      }
    });
    
    ['includeUppercase', 'includeLowercase', 'includeNumbers', 'includeSymbols'].forEach(id => {
      document.getElementById(id).addEventListener('change', () => {
        if (document.getElementById('passwordText').textContent !== '点击生成按钮') {
          this.generatePassword();
        }
      });
    });
  }

  async checkUnlockStatus() {
    try {
      const response = await chrome.runtime.sendMessage({ type: 'CHECK_UNLOCKED' });
      if (response.success && response.unlocked) {
        this.isUnlocked = true;
        this.showApp();
        this.loadPasswords();
      } else {
        this.showUnlock();
      }
    } catch (error) {
      this.showUnlock();
    }
  }

  async unlock() {
    const password = document.getElementById('masterPassword').value;
    if (!password) {
      this.showError('请输入主密码');
      return;
    }

    try {
      const response = await chrome.runtime.sendMessage({
        type: 'UNLOCK',
        masterPassword: password
      });

      if (response.success) {
        this.isUnlocked = true;
        this.showApp();
        this.loadPasswords();
      } else {
        this.showError(response.error || '解锁失败');
      }
    } catch (error) {
      this.showError('解锁失败: ' + error.message);
    }
  }

  async lock() {
    try {
      await chrome.runtime.sendMessage({ type: 'LOCK' });
      this.isUnlocked = false;
      document.getElementById('masterPassword').value = '';
      this.showUnlock();
    } catch (error) {
      console.error('锁定失败:', error);
    }
  }

  showUnlock() {
    document.getElementById('unlockForm').classList.remove('hidden');
    document.getElementById('appContent').classList.add('hidden');
    document.getElementById('lockBtn').classList.add('hidden');
  }

  showApp() {
    document.getElementById('unlockForm').classList.add('hidden');
    document.getElementById('appContent').classList.remove('hidden');
    document.getElementById('lockBtn').classList.remove('hidden');
  }

  showError(message) {
    const errorDiv = document.getElementById('unlockError');
    errorDiv.innerHTML = `<div class="alert alert-error">${message}</div>`;
    setTimeout(() => errorDiv.innerHTML = '', 3000);
  }

  switchTab(tab) {
    this.currentTab = tab;
    
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelector(`[data-tab="${tab}"]`).classList.add('active');

    document.getElementById('passwordsTab').classList.toggle('hidden', tab !== 'passwords');
    document.getElementById('generatorTab').classList.toggle('hidden', tab !== 'generator');
  }

  async loadPasswords() {
    try {
      const response = await chrome.runtime.sendMessage({ type: 'GET_ALL_PASSWORDS' });
      if (response.success) {
        this.passwords = response.passwords;
        this.renderPasswords();
      }
    } catch (error) {
      console.error('加载密码失败:', error);
    }
  }

  renderPasswords() {
    const list = document.getElementById('passwordList');
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();

    const filtered = this.passwords.filter(p => 
      p.title.toLowerCase().includes(searchTerm) ||
      p.username.toLowerCase().includes(searchTerm)
    );

    if (filtered.length === 0) {
      list.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">🔒</div>
          <div>${searchTerm ? '未找到匹配的密码' : '暂无密码记录'}</div>
        </div>
      `;
      return;
    }

    list.innerHTML = filtered.map(pwd => `
      <div class="password-item" data-id="${pwd.id}">
        <div class="password-title">${this.escapeHtml(pwd.title)}</div>
        <div class="password-username">${this.escapeHtml(pwd.username)}</div>
        <div class="password-actions">
          <button class="action-btn" data-action="copy" data-id="${pwd.id}">复制密码</button>
          <button class="action-btn" data-action="fill" data-id="${pwd.id}">自动填充</button>
        </div>
      </div>
    `).join('');

    list.querySelectorAll('.action-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const action = btn.dataset.action;
        const id = parseInt(btn.dataset.id);
        if (action === 'copy') this.copyPassword(id);
        if (action === 'fill') this.fillPassword(id);
      });
    });
  }

  async copyPassword(id) {
    try {
      const response = await chrome.runtime.sendMessage({
        type: 'DECRYPT_PASSWORD',
        id: id
      });

      if (response.success) {
        await navigator.clipboard.writeText(response.password.password);
        this.showNotification('密码已复制到剪贴板', 'success');
      }
    } catch (error) {
      this.showNotification('复制失败: ' + error.message, 'error');
    }
  }

  async fillPassword(id) {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      chrome.tabs.sendMessage(tab.id, {
        type: 'TRIGGER_FILL',
        passwordId: id
      });
      window.close();
    } catch (error) {
      this.showNotification('填充失败: ' + error.message, 'error');
    }
  }

  async generatePassword() {
    const options = {
      length: parseInt(document.getElementById('passwordLength').value),
      includeUppercase: document.getElementById('includeUppercase').checked,
      includeLowercase: document.getElementById('includeLowercase').checked,
      includeNumbers: document.getElementById('includeNumbers').checked,
      includeSymbols: document.getElementById('includeSymbols').checked
    };

    try {
      const response = await chrome.runtime.sendMessage({
        type: 'GENERATE_PASSWORD',
        options: options
      });

      if (response.success) {
        document.getElementById('passwordText').textContent = response.password;
        this.updateStrength(response.password);
      }
    } catch (error) {
      this.showNotification('生成失败: ' + error.message, 'error');
    }
  }

  updateStrength(password) {
    const response = this.checkStrength(password);
    const fill = document.getElementById('strengthFill');
    
    const widths = { weak: '25%', fair: '50%', good: '75%', strong: '100%' };
    const colors = { weak: '#ef4444', fair: '#f59e0b', good: '#3b82f6', strong: '#22c55e' };
    
    fill.style.width = widths[response.strength] || '0%';
    fill.style.background = colors[response.strength] || '#6b7280';
  }

  checkStrength(password) {
    let score = 0;
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

    return { strength, score };
  }

  async copyGenerated() {
    const password = document.getElementById('passwordText').textContent;
    if (password === '点击生成按钮') {
      this.showNotification('请先生成密码', 'error');
      return;
    }

    try {
      await navigator.clipboard.writeText(password);
      this.showNotification('密码已复制到剪贴板', 'success');
    } catch (error) {
      this.showNotification('复制失败: ' + error.message, 'error');
    }
  }

  async insertGenerated() {
    const password = document.getElementById('passwordText').textContent;
    if (password === '点击生成按钮') {
      this.showNotification('请先生成密码', 'error');
      return;
    }

    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      chrome.tabs.sendMessage(tab.id, {
        type: 'INSERT_PASSWORD',
        password: password
      });
      window.close();
    } catch (error) {
      this.showNotification('插入失败: ' + error.message, 'error');
    }
  }

  showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type}`;
    notification.textContent = message;
    notification.style.position = 'fixed';
    notification.style.bottom = '16px';
    notification.style.left = '16px';
    notification.style.right = '16px';
    notification.style.zIndex = '1000';
    document.body.appendChild(notification);

    setTimeout(() => notification.remove(), 3000);
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  new PopupApp();
});

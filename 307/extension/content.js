class AutoFillService {
  constructor() {
    this.passwords = [];
    this.currentUrl = window.location.href;
    this.processedFrames = new WeakSet();
    this.setupMessageListener();
    this.observeFormChanges();
    this.injectFillButton();
    this.scanAllFrames();
    this.setupIframeObserver();
  }

  setupMessageListener() {
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      switch (request.type) {
        case 'AUTO_FILL_DATA':
          this.handleAutoFillData(request.passwords);
          sendResponse({ success: true });
          break;
        case 'AUTO_FILL_ERROR':
          this.showNotification(request.error, 'error');
          sendResponse({ success: true });
          break;
        case 'INSERT_PASSWORD':
          this.insertPassword(request.password);
          sendResponse({ success: true });
          break;
        case 'FILL_ALL_FORMS':
          this.fillAllFormsRecursively();
          sendResponse({ success: true });
          break;
        default:
          break;
      }
      return true;
    });
  }

  observeFormChanges() {
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === 'childList') {
          this.checkForLoginForms(document);
          mutation.addedNodes.forEach(node => {
            if (node.tagName === 'IFRAME') {
              this.handleIframeLoad(node);
            }
          });
        }
      });
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });

    this.checkForLoginForms(document);
  }

  setupIframeObserver() {
    const iframes = document.querySelectorAll('iframe');
    iframes.forEach(iframe => this.handleIframeLoad(iframe));

    const iframeObserver = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === 'childList') {
          mutation.addedNodes.forEach(node => {
            if (node.tagName === 'IFRAME') {
              this.handleIframeLoad(node);
            }
          });
        }
      });
    });

    iframeObserver.observe(document.documentElement, {
      childList: true,
      subtree: true
    });
  }

  handleIframeLoad(iframe) {
    if (this.processedFrames.has(iframe)) return;
    
    try {
      const tryAccess = () => {
        try {
          if (iframe.contentDocument && iframe.contentDocument.body) {
            this.processedFrames.add(iframe);
            this.checkForLoginForms(iframe.contentDocument);
            this.setupNestedIframeObserver(iframe.contentDocument);
          }
        } catch (e) {
          if (e.name !== 'SecurityError') {
            console.warn('无法访问iframe:', e.message);
          }
        }
      };

      if (iframe.contentDocument && iframe.contentDocument.readyState === 'complete') {
        tryAccess();
      } else {
        iframe.addEventListener('load', tryAccess, { once: true });
      }
    } catch (e) {
      console.warn('处理iframe失败:', e.message);
    }
  }

  setupNestedIframeObserver(doc) {
    try {
      const iframes = doc.querySelectorAll('iframe');
      iframes.forEach(iframe => this.handleIframeLoad(iframe));

      const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
          if (mutation.type === 'childList') {
            mutation.addedNodes.forEach(node => {
              if (node.tagName === 'IFRAME') {
                this.handleIframeLoad(node);
              }
            });
          }
        });
      });

      observer.observe(doc.documentElement, {
        childList: true,
        subtree: true
      });
    } catch (e) {
      console.warn('设置嵌套iframe观察者失败:', e.message);
    }
  }

  scanAllFrames() {
    this.processDocumentRecursively(document);
  }

  processDocumentRecursively(doc, depth = 0) {
    if (depth > 10) return;

    try {
      this.checkForLoginForms(doc);

      const iframes = doc.querySelectorAll('iframe');
      iframes.forEach(iframe => {
        try {
          if (iframe.contentDocument) {
            this.processedFrames.add(iframe);
            this.processDocumentRecursively(iframe.contentDocument, depth + 1);
          }
        } catch (e) {
          if (e.name !== 'SecurityError') {
            console.warn('无法处理嵌套iframe:', e.message);
          }
        }
      });
    } catch (e) {
      console.warn('递归处理文档失败:', e.message);
    }
  }

  checkForLoginForms(doc) {
    try {
      const forms = doc.querySelectorAll('form');
      forms.forEach((form) => {
        if (this.isLoginForm(form) && !form.hasAttribute('data-pm-processed')) {
          form.setAttribute('data-pm-processed', 'true');
          this.enhanceForm(form);
        }
      });

      this.checkForNonFormPasswordInputs(doc);
    } catch (e) {
      console.warn('检查登录表单失败:', e.message);
    }
  }

  checkForNonFormPasswordInputs(doc) {
    try {
      const passwordInputs = doc.querySelectorAll('input[type="password"]:not(form input)');
      passwordInputs.forEach(input => {
        if (!input.hasAttribute('data-pm-processed')) {
          input.setAttribute('data-pm-processed', 'true');
          const usernameInput = this.findAdjacentUsernameInput(input);
          this.addFillIcon(input, null, usernameInput, input);
        }
      });
    } catch (e) {
      console.warn('检查非表单密码输入失败:', e.message);
    }
  }

  isLoginForm(form) {
    const hasPassword = form.querySelector('input[type="password"]');
    const hasEmail = form.querySelector('input[type="email"], input[name*="email"], input[name*="user"]');
    return hasPassword && (hasEmail || form.querySelectorAll('input[type="text"]').length > 0);
  }

  enhanceForm(form) {
    const passwordInput = form.querySelector('input[type="password"]');
    if (!passwordInput) return;

    const usernameInput = this.findUsernameInput(form, passwordInput);
    
    this.addFillIcon(passwordInput, form, usernameInput, passwordInput);
    
    if (usernameInput) {
      this.addFillIcon(usernameInput, form, usernameInput, passwordInput);
    }

    passwordInput.addEventListener('focus', () => {
      this.requestAutoFill();
    });

    const submitButton = form.querySelector('button[type="submit"], input[type="submit"]');
    if (submitButton) {
      submitButton.addEventListener('click', (e) => {
        this.handleFormSubmit(form, usernameInput, passwordInput);
      }, true);
    }
  }

  findUsernameInput(form, passwordInput) {
    const emailInput = form.querySelector('input[type="email"]');
    if (emailInput) return emailInput;

    const textInputs = Array.from(form.querySelectorAll('input[type="text"], input:not([type])'));
    for (const input of textInputs) {
      const name = input.name.toLowerCase();
      const id = input.id.toLowerCase();
      if (name.includes('user') || name.includes('email') || name.includes('login') ||
          id.includes('user') || id.includes('email') || id.includes('login')) {
        return input;
      }
    }

    const allInputs = Array.from(form.querySelectorAll('input'));
    const passwordIndex = allInputs.indexOf(passwordInput);
    if (passwordIndex > 0) {
      return allInputs[passwordIndex - 1];
    }

    return null;
  }

  findAdjacentUsernameInput(passwordInput) {
    const parent = passwordInput.parentElement;
    if (!parent) return null;

    const allInputs = Array.from(parent.querySelectorAll('input'));
    const passwordIndex = allInputs.indexOf(passwordInput);
    
    for (let i = passwordIndex - 1; i >= 0; i--) {
      const input = allInputs[i];
      if (input.type === 'email' || input.type === 'text' || !input.type) {
        return input;
      }
    }

    return null;
  }

  addFillIcon(input, form, usernameInput, passwordInput) {
    try {
      const wrapper = document.createElement('div');
      wrapper.style.position = 'relative';
      wrapper.style.display = 'inline-block';
      wrapper.style.width = '100%';

      input.parentNode.insertBefore(wrapper, input);
      wrapper.appendChild(input);

      const icon = document.createElement('div');
      icon.innerHTML = '🔐';
      icon.style.cssText = `
        position: absolute;
        right: 10px;
        top: 50%;
        transform: translateY(-50%);
        cursor: pointer;
        font-size: 18px;
        z-index: 1000;
        user-select: none;
      `;
      icon.title = '从密码管理器填充';

      icon.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.showPasswordPicker(form, usernameInput, passwordInput, icon);
      });

      wrapper.appendChild(icon);
    } catch (e) {
      console.warn('添加填充图标失败:', e.message);
    }
  }

  injectFillButton() {
    const style = document.createElement('style');
    style.textContent = `
      .pm-picker {
        position: absolute;
        background: #1e293b;
        border: 1px solid #475569;
        border-radius: 8px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        z-index: 10000;
        min-width: 280px;
        max-height: 300px;
        overflow-y: auto;
        color: #f1f5f9;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      }
      .pm-picker-header {
        padding: 12px 16px;
        font-weight: 600;
        font-size: 14px;
        border-bottom: 1px solid #475569;
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      .pm-picker-item {
        padding: 12px 16px;
        cursor: pointer;
        border-bottom: 1px solid #334155;
        transition: background-color 0.2s;
      }
      .pm-picker-item:hover {
        background: #334155;
      }
      .pm-picker-item-title {
        font-weight: 500;
        font-size: 14px;
        margin-bottom: 4px;
      }
      .pm-picker-item-username {
        font-size: 12px;
        color: #94a3b8;
      }
      .pm-picker-empty {
        padding: 20px;
        text-align: center;
        color: #94a3b8;
        font-size: 13px;
      }
      .pm-notification {
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 8px;
        z-index: 10001;
        font-size: 14px;
        animation: pmSlideIn 0.3s ease;
      }
      .pm-notification.success {
        background: rgba(34, 197, 94, 0.9);
        color: white;
      }
      .pm-notification.error {
        background: rgba(239, 68, 68, 0.9);
        color: white;
      }
      @keyframes pmSlideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
      }
      .pm-context-menu {
        position: fixed;
        background: #1e293b;
        border: 1px solid #475569;
        border-radius: 8px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        z-index: 10002;
        min-width: 200px;
        color: #f1f5f9;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      }
      .pm-context-menu-item {
        padding: 10px 16px;
        cursor: pointer;
        font-size: 13px;
        transition: background-color 0.2s;
      }
      .pm-context-menu-item:hover {
        background: #334155;
      }
      .pm-context-menu-divider {
        height: 1px;
        background: #475569;
        margin: 4px 0;
      }
    `;
    document.head.appendChild(style);
  }

  async showPasswordPicker(form, usernameInput, passwordInput, icon) {
    await this.requestAutoFill();

    const existingPicker = document.querySelector('.pm-picker');
    if (existingPicker) {
      existingPicker.remove();
    }

    if (this.passwords.length === 0) {
      this.showNotification('未找到匹配的密码记录', 'error');
      return;
    }

    const picker = document.createElement('div');
    picker.className = 'pm-picker';

    const header = document.createElement('div');
    header.className = 'pm-picker-header';
    header.innerHTML = `
      <span>选择要填充的账户</span>
      <span style="cursor:pointer;color:#94a3b8;" onclick="this.closest('.pm-picker').remove()">✕</span>
    `;
    picker.appendChild(header);

    this.passwords.forEach(pwd => {
      const item = document.createElement('div');
      item.className = 'pm-picker-item';
      item.innerHTML = `
        <div class="pm-picker-item-title">${this.escapeHtml(pwd.title)}</div>
        <div class="pm-picker-item-username">${this.escapeHtml(pwd.username)}</div>
      `;
      item.addEventListener('click', () => {
        this.fillCredentials(form, usernameInput, passwordInput, pwd);
        picker.remove();
      });
      picker.appendChild(item);
    });

    const fillAllItem = document.createElement('div');
    fillAllItem.className = 'pm-picker-item';
    fillAllItem.innerHTML = `
      <div class="pm-picker-item-title" style="color: #3b82f6;">🔄 填充所有表单</div>
      <div class="pm-picker-item-username">递归填充所有检测到的表单</div>
    `;
    fillAllItem.addEventListener('click', () => {
      this.fillAllFormsRecursively();
      picker.remove();
    });
    picker.appendChild(fillAllItem);

    const rect = icon.getBoundingClientRect();
    picker.style.top = `${rect.bottom + window.scrollY + 5}px`;
    picker.style.left = `${rect.left + window.scrollX}px`;

    document.body.appendChild(picker);

    setTimeout(() => {
      document.addEventListener('click', function closePicker(e) {
        if (!picker.contains(e.target)) {
          picker.remove();
          document.removeEventListener('click', closePicker);
        }
      });
    }, 0);
  }

  async fillCredentials(form, usernameInput, passwordInput, pwd) {
    try {
      const response = await chrome.runtime.sendMessage({
        type: 'DECRYPT_PASSWORD',
        id: pwd.id
      });

      if (response.success) {
        const password = response.password.password;

        if (usernameInput) {
          this.fillInput(usernameInput, pwd.username);
        }

        if (passwordInput) {
          this.fillInput(passwordInput, password);
        }

        this.showNotification(`已填充 ${pwd.title} 的账户信息`, 'success');
      } else {
        this.showNotification(response.error, 'error');
      }
    } catch (error) {
      this.showNotification('填充失败: ' + error.message, 'error');
    }
  }

  fillInput(input, value) {
    input.focus();
    input.value = value;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
    input.dispatchEvent(new Event('blur', { bubbles: true }));
    
    try {
      input.dispatchEvent(new Event('react-change', { bubbles: true }));
      input.dispatchEvent(new Event('blur', { bubbles: true }));
    } catch (e) {}
  }

  async fillAllFormsRecursively() {
    await this.requestAutoFill();
    
    if (this.passwords.length === 0) {
      this.showNotification('未找到密码记录', 'error');
      return;
    }

    if (this.passwords.length === 1) {
      const pwd = this.passwords[0];
      const response = await chrome.runtime.sendMessage({
        type: 'DECRYPT_PASSWORD',
        id: pwd.id
      });

      if (response.success) {
        const password = response.password.password;
        this.fillAllDocumentsRecursively(document, pwd.username, password, 0);
        this.showNotification(`已填充 ${pwd.title} 到所有检测到的表单`, 'success');
      }
    } else {
      this.showNotification(`找到 ${this.passwords.length} 个账户，请在具体表单中选择`, 'success');
    }
  }

  fillAllDocumentsRecursively(doc, username, password, depth) {
    if (depth > 10) return;

    try {
      const forms = doc.querySelectorAll('form');
      forms.forEach(form => {
        const passwordInput = form.querySelector('input[type="password"]');
        if (passwordInput) {
          const usernameInput = this.findUsernameInput(form, passwordInput);
          if (usernameInput) {
            this.fillInput(usernameInput, username);
          }
          this.fillInput(passwordInput, password);
        }
      });

      const standalonePasswordInputs = doc.querySelectorAll('input[type="password"]:not(form input)');
      standalonePasswordInputs.forEach(input => {
        this.fillInput(input, password);
        const usernameInput = this.findAdjacentUsernameInput(input);
        if (usernameInput) {
          this.fillInput(usernameInput, username);
        }
      });

      const iframes = doc.querySelectorAll('iframe');
      iframes.forEach(iframe => {
        try {
          if (iframe.contentDocument) {
            this.fillAllDocumentsRecursively(iframe.contentDocument, username, password, depth + 1);
          }
        } catch (e) {
          if (e.name !== 'SecurityError') {
            console.warn('无法填充嵌套iframe:', e.message);
          }
        }
      });
    } catch (e) {
      console.warn('递归填充文档失败:', e.message);
    }
  }

  async requestAutoFill() {
    try {
      const response = await chrome.runtime.sendMessage({
        type: 'GET_PASSWORDS_FOR_URL',
        url: this.currentUrl
      });

      if (response.success) {
        this.passwords = response.passwords;
      }
    } catch (error) {
      console.error('获取密码失败:', error);
    }
  }

  handleAutoFillData(passwords) {
    this.passwords = passwords;

    if (passwords.length === 0) {
      this.showNotification('未找到匹配的密码记录', 'error');
      return;
    }

    if (passwords.length === 1) {
      const form = this.findActiveForm();
      if (form) {
        const passwordInput = form.querySelector('input[type="password"]');
        const usernameInput = this.findUsernameInput(form, passwordInput);
        this.fillCredentials(form, usernameInput, passwordInput, passwords[0]);
      } else {
        this.showNotification('找到1个匹配的账户，点击🔐图标填充', 'success');
      }
    } else {
      this.showNotification(`找到 ${passwords.length} 个匹配的账户，请选择`, 'success');
    }
  }

  findActiveForm() {
    const activeElement = document.activeElement;
    if (activeElement && activeElement.closest) {
      const form = activeElement.closest('form');
      if (form && form.querySelector('input[type="password"]')) {
        return form;
      }
    }

    const forms = document.querySelectorAll('form');
    for (const form of forms) {
      if (form.querySelector('input[type="password"]')) {
        return form;
      }
    }

    return null;
  }

  insertPassword(password) {
    const activeElement = document.activeElement;
    if (activeElement && (activeElement.tagName === 'INPUT' || activeElement.tagName === 'TEXTAREA')) {
      this.fillInput(activeElement, password);
      this.showNotification('密码已插入', 'success');
    } else {
      navigator.clipboard.writeText(password).then(() => {
        this.showNotification('密码已复制到剪贴板', 'success');
      });
    }
  }

  handleFormSubmit(form, usernameInput, passwordInput) {
    if (!usernameInput || !passwordInput) return;
    
    chrome.runtime.sendMessage({
      type: 'SAVE_CREDENTIALS_PROMPT',
      url: window.location.href,
      username: usernameInput.value,
      password: passwordInput.value
    });
  }

  showNotification(message, type = 'success') {
    const existing = document.querySelector('.pm-notification');
    if (existing) existing.remove();

    const notification = document.createElement('div');
    notification.className = `pm-notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
      notification.style.animation = 'pmSlideIn 0.3s ease reverse';
      setTimeout(() => notification.remove(), 300);
    }, 3000);
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

if (window.top === window.self) {
  new AutoFillService();
}

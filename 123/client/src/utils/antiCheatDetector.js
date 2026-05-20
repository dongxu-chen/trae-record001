class AntiCheatDetector {
  constructor(onAlert) {
    this.onAlert = onAlert;
    this.isMonitoring = false;
    this.lastVisibilityState = 'visible';
    this.lastFullscreenState = false;
    this.alertCooldown = {};
    this.cooldownPeriod = 3000;
    this.isFullscreenMode = false;
    this.fullscreenCheckInterval = null;
    this.focusCheckInterval = null;
  }

  startMonitoring() {
    if (this.isMonitoring) return;
    this.isMonitoring = true;

    this.setupVisibilityDetection();
    this.setupFullscreenDetection();
    this.setupVirtualMachineDetection();
    this.setupWindowBlurDetection();
    this.setupTabDetection();
    this.setupFocusMonitoring();
    this.setupKeyboardRestrictions();
    this.setupDevToolsDetection();
    
    this.checkInitialState();
  }

  stopMonitoring() {
    this.isMonitoring = false;
    this.stopFullscreenEnforcement();
    this.cleanup();
  }

  shouldAlert(type) {
    const now = Date.now();
    const lastAlert = this.alertCooldown[type] || 0;
    if (now - lastAlert >= this.cooldownPeriod) {
      this.alertCooldown[type] = now;
      return true;
    }
    return false;
  }

  setupVisibilityDetection() {
    this.visibilityHandler = () => {
      if (!this.isMonitoring) return;
      
      const currentState = document.visibilityState;
      
      if (currentState === 'hidden' && this.lastVisibilityState === 'visible') {
        if (this.shouldAlert('tab-switch')) {
          this.onAlert({
            type: 'tab-switch',
            severity: 'danger',
            message: '检测到页面切换（最小化或切换标签页）',
            timestamp: new Date().toISOString(),
            details: {
              visibilityState: currentState,
              previousState: this.lastVisibilityState
            }
          });
        }
      }
      
      this.lastVisibilityState = currentState;
    };

    document.addEventListener('visibilitychange', this.visibilityHandler);
  }

  setupFullscreenDetection() {
    this.fullscreenHandler = () => {
      if (!this.isMonitoring) return;
      
      const isFullscreen = document.fullscreenElement !== null ||
                          document.webkitFullscreenElement !== null ||
                          document.mozFullScreenElement !== null ||
                          document.msFullscreenElement !== null;

      if (isFullscreen !== this.lastFullscreenState && !isFullscreen && this.isFullscreenMode) {
        if (this.shouldAlert('fullscreen-exit')) {
          this.onAlert({
            type: 'fullscreen-exit',
            severity: 'danger',
            message: '检测到退出全屏模式，正在尝试恢复...',
            timestamp: new Date().toISOString(),
            details: {
              isFullscreen,
              previousState: this.lastFullscreenState
            }
          });
          
          this.forceFullscreen();
        }
      }
      
      this.lastFullscreenState = isFullscreen;
    };

    document.addEventListener('fullscreenchange', this.fullscreenHandler);
    document.addEventListener('webkitfullscreenchange', this.fullscreenHandler);
    document.addEventListener('mozfullscreenchange', this.fullscreenHandler);
    document.addEventListener('MSFullscreenChange', this.fullscreenHandler);
  }

  enterFullscreenMode() {
    this.isFullscreenMode = true;
    this.forceFullscreen();
    this.startFullscreenEnforcement();
  }

  exitFullscreenMode() {
    this.isFullscreenMode = false;
    this.stopFullscreenEnforcement();
    this.exitFullscreen();
  }

  forceFullscreen() {
    try {
      const element = document.documentElement;
      if (element.requestFullscreen) {
        element.requestFullscreen();
      } else if (element.webkitRequestFullscreen) {
        element.webkitRequestFullscreen();
      } else if (element.mozRequestFullScreen) {
        element.mozRequestFullScreen();
      } else if (element.msRequestFullscreen) {
        element.msRequestFullscreen();
      }
    } catch (error) {
      console.warn('进入全屏失败:', error);
    }
  }

  exitFullscreen() {
    try {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      } else if (document.webkitExitFullscreen) {
        document.webkitExitFullscreen();
      } else if (document.mozCancelFullScreen) {
        document.mozCancelFullScreen();
      } else if (document.msExitFullscreen) {
        document.msExitFullscreen();
      }
    } catch (error) {
      console.warn('退出全屏失败:', error);
    }
  }

  startFullscreenEnforcement() {
    this.fullscreenCheckInterval = setInterval(() => {
      if (this.isMonitoring && this.isFullscreenMode) {
        const isFullscreen = document.fullscreenElement !== null ||
                            document.webkitFullscreenElement !== null ||
                            document.mozFullScreenElement !== null ||
                            document.msFullscreenElement !== null;
        
        if (!isFullscreen) {
          this.forceFullscreen();
        }
      }
    }, 1000);
  }

  stopFullscreenEnforcement() {
    if (this.fullscreenCheckInterval) {
      clearInterval(this.fullscreenCheckInterval);
      this.fullscreenCheckInterval = null;
    }
  }

  setupFocusMonitoring() {
    this.focusCheckInterval = setInterval(() => {
      if (!this.isMonitoring) return;
      
      if (!document.hasFocus()) {
        if (this.shouldAlert('window-lost-focus')) {
          this.onAlert({
            type: 'window-lost-focus',
            severity: 'warning',
            message: '检测到考试窗口失去焦点',
            timestamp: new Date().toISOString(),
            details: {}
          });
        }
      }
    }, 2000);
  }

  setupWindowBlurDetection() {
    this.blurHandler = () => {
      if (!this.isMonitoring) return;
      
      if (this.shouldAlert('window-blur')) {
        setTimeout(() => {
          if (!document.hasFocus()) {
            this.onAlert({
              type: 'window-blur',
              severity: 'warning',
              message: '检测到窗口失去焦点',
              timestamp: new Date().toISOString(),
              details: {
                hasFocus: document.hasFocus()
              }
            });
          }
        }, 500);
      }
    };

    window.addEventListener('blur', this.blurHandler);
  }

  setupTabDetection() {
    this.beforeUnloadHandler = (e) => {
      if (!this.isMonitoring) return;
      
      this.onAlert({
        type: 'page-leave',
        severity: 'critical',
        message: '考生尝试关闭或刷新页面',
        timestamp: new Date().toISOString(),
        details: {}
      });
      
      e.preventDefault();
      e.returnValue = '确定要离开考试页面吗？考试记录将被提交。';
      return e.returnValue;
    };

    window.addEventListener('beforeunload', this.beforeUnloadHandler);
  }

  setupKeyboardRestrictions() {
    this.keyDownHandler = (e) => {
      if (!this.isMonitoring) return;

      const restrictedKeys = {
        'F1': 'F1帮助',
        'F3': 'F3搜索',
        'F5': 'F5刷新',
        'F11': 'F11全屏切换',
        'F12': 'F12开发者工具'
      };

      if (restrictedKeys[e.key]) {
        e.preventDefault();
        if (this.shouldAlert(`key-${e.key}`)) {
          this.onAlert({
            type: 'restricted-key',
            severity: 'warning',
            message: `检测到使用受限按键: ${restrictedKeys[e.key]}`,
            timestamp: new Date().toISOString(),
            details: { key: e.key }
          });
        }
        return;
      }

      if (e.ctrlKey || e.metaKey) {
        const restrictedCombos = {
          'r': 'Ctrl+R刷新',
          'R': 'Ctrl+R刷新',
          't': 'Ctrl+T新建标签',
          'T': 'Ctrl+T新建标签',
          'n': 'Ctrl+N新建窗口',
          'N': 'Ctrl+N新建窗口',
          'w': 'Ctrl+W关闭标签',
          'W': 'Ctrl+W关闭标签',
          'Tab': 'Ctrl+Tab切换标签',
          'j': 'Ctrl+J下载历史',
          'J': 'Ctrl+J下载历史',
          'p': 'Ctrl+P打印',
          'P': 'Ctrl+P打印',
          's': 'Ctrl+S保存',
          'S': 'Ctrl+S保存'
        };

        if (restrictedCombos[e.key]) {
          e.preventDefault();
          e.stopPropagation();
          if (this.shouldAlert(`combo-${e.key}`)) {
            this.onAlert({
              type: 'restricted-combination',
              severity: 'warning',
              message: `检测到使用受限按键组合: ${restrictedCombos[e.key]}`,
              timestamp: new Date().toISOString(),
              details: { key: e.key, ctrlKey: e.ctrlKey, metaKey: e.metaKey }
            });
          }
          return;
        }
      }

      if (e.altKey) {
        if (e.key === 'Tab' || e.key === 'Escape') {
          e.preventDefault();
          if (this.shouldAlert('alt-tab')) {
            this.onAlert({
              type: 'alt-tab',
              severity: 'warning',
              message: '检测到使用Alt+Tab或Alt+Esc切换窗口',
              timestamp: new Date().toISOString(),
              details: { key: e.key }
            });
          }
        }
      }
    };

    document.addEventListener('keydown', this.keyDownHandler, true);
  }

  setupDevToolsDetection() {
    this.devToolsDetector = setInterval(() => {
      if (!this.isMonitoring) return;

      const threshold = 160;
      const widthThreshold = window.outerWidth - window.innerWidth > threshold;
      const heightThreshold = window.outerHeight - window.innerHeight > threshold;

      if (widthThreshold || heightThreshold) {
        if (this.shouldAlert('devtools')) {
          this.onAlert({
            type: 'devtools-detected',
            severity: 'danger',
            message: '检测到开发者工具可能已打开',
            timestamp: new Date().toISOString(),
            details: { widthThreshold, heightThreshold }
          });
        }
      }
    }, 1000);
  }

  detectVMFeatures() {
    const indicators = [];
    
    if (navigator.userAgent.includes('VirtualBox') ||
        navigator.userAgent.includes('VMware') ||
        navigator.userAgent.includes('QEMU') ||
        navigator.userAgent.includes('VirtualPC') ||
        navigator.userAgent.includes('Xen') ||
        navigator.userAgent.includes('Hyper-V')) {
      indicators.push('VM userAgent detected');
    }

    if (navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 2) {
      indicators.push('Low CPU core count (possible VM)');
    }

    try {
      const canvas = document.createElement('canvas');
      const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
      if (gl) {
        const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
        if (debugInfo) {
          const renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
          if (renderer.includes('VirtualBox') ||
              renderer.includes('VMware') ||
              renderer.includes('llvmpipe') ||
              renderer.includes('SVGA3D')) {
            indicators.push(`VM GPU detected: ${renderer}`);
          }
        }
      }
    } catch (e) {}

    if (window.screen.width <= 1024 && window.screen.height <= 768) {
      indicators.push('Low resolution screen (possible VM)');
    }

    return indicators;
  }

  setupVirtualMachineDetection() {
    setTimeout(() => {
      const vmIndicators = this.detectVMFeatures();
      
      if (vmIndicators.length >= 2) {
        if (this.shouldAlert('vm-detected')) {
          this.onAlert({
            type: 'vm-detected',
            severity: 'critical',
            message: '检测到可能在虚拟机环境中运行',
            timestamp: new Date().toISOString(),
            details: {
              indicators: vmIndicators
            }
          });
        }
      }
    }, 5000);
  }

  checkInitialState() {
    this.lastVisibilityState = document.visibilityState;
    this.lastFullscreenState = document.fullscreenElement !== null;

    if (document.visibilityState === 'hidden') {
      this.onAlert({
        type: 'initial-hidden',
        severity: 'warning',
        message: '考试开始时页面处于隐藏状态',
        timestamp: new Date().toISOString(),
        details: {}
      });
    }
  }

  cleanup() {
    if (this.visibilityHandler) {
      document.removeEventListener('visibilitychange', this.visibilityHandler);
    }
    if (this.fullscreenHandler) {
      document.removeEventListener('fullscreenchange', this.fullscreenHandler);
      document.removeEventListener('webkitfullscreenchange', this.fullscreenHandler);
      document.removeEventListener('mozfullscreenchange', this.fullscreenHandler);
      document.removeEventListener('MSFullscreenChange', this.fullscreenHandler);
    }
    if (this.blurHandler) {
      window.removeEventListener('blur', this.blurHandler);
    }
    if (this.beforeUnloadHandler) {
      window.removeEventListener('beforeunload', this.beforeUnloadHandler);
    }
    if (this.keyDownHandler) {
      document.removeEventListener('keydown', this.keyDownHandler, true);
    }
    if (this.focusCheckInterval) {
      clearInterval(this.focusCheckInterval);
      this.focusCheckInterval = null;
    }
    if (this.devToolsDetector) {
      clearInterval(this.devToolsDetector);
      this.devToolsDetector = null;
    }
    this.stopFullscreenEnforcement();
  }
}

export default AntiCheatDetector;

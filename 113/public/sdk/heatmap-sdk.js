(function(global) {
  'use strict';

  class HeatmapSDK {
    constructor(config = {}) {
      this.trackUrl = config.trackUrl || '/api/heatmap/track';
      this.sessionId = this.generateSessionId();
      this.fingerprint = null;
      this.clicks = [];
      this.pageInfo = this.getPageInfo();
      this.maxBatchSize = config.maxBatchSize || 50;
      this.flushInterval = config.flushInterval || 5000;
      
      this.init();
    }

    generateSessionId() {
      return 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    async generateFingerprint() {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      
      canvas.width = 200;
      canvas.height = 50;
      
      ctx.textBaseline = 'top';
      ctx.font = '14px Arial';
      ctx.fillStyle = '#f60';
      ctx.fillRect(125, 1, 62, 20);
      ctx.fillStyle = '#069';
      ctx.fillText('Hello, world!', 2, 15);
      ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
      ctx.fillText('Hello, world!', 4, 17);
      
      const canvasData = canvas.toDataURL();
      
      const components = {
        userAgent: navigator.userAgent,
        language: navigator.language,
        colorDepth: screen.colorDepth,
        screenResolution: `${screen.width}x${screen.height}`,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        platform: navigator.platform,
        plugins: Array.from(navigator.plugins || []).map(p => p.name).join(','),
        canvasHash: this.hashString(canvasData),
        webglVendor: this.getWebglInfo(),
        touchSupport: 'ontouchstart' in window,
        cookiesEnabled: navigator.cookieEnabled,
        doNotTrack: navigator.doNotTrack
      };

      const fingerprintStr = JSON.stringify(components);
      this.fingerprint = this.hashString(fingerprintStr);
      
      return this.fingerprint;
    }

    getWebglInfo() {
      try {
        const canvas = document.createElement('canvas');
        const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
        if (gl) {
          const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
          if (debugInfo) {
            return gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) + '|' + 
                   gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
          }
        }
      } catch (e) {}
      return 'unknown';
    }

    hashString(str) {
      let hash = 0;
      for (let i = 0; i < str.length; i++) {
        const char = str.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash;
      }
      return Math.abs(hash).toString(36);
    }

    getPageInfo() {
      return {
        url: window.location.href,
        path: window.location.pathname,
        title: document.title,
        referrer: document.referrer,
        viewportWidth: window.innerWidth,
        viewportHeight: window.innerHeight,
        scrollWidth: document.documentElement.scrollWidth,
        scrollHeight: document.documentElement.scrollHeight
      };
    }

    trackClick(event) {
      const clickData = {
        x: event.clientX,
        y: event.clientY,
        scrollX: window.scrollX,
        scrollY: window.scrollY,
        absoluteX: event.clientX + window.scrollX,
        absoluteY: event.clientY + window.scrollY,
        target: event.target.tagName,
        id: event.target.id,
        className: event.target.className,
        timestamp: Date.now(),
        sessionId: this.sessionId,
        fingerprint: this.fingerprint
      };

      this.clicks.push(clickData);

      if (this.clicks.length >= this.maxBatchSize) {
        this.flush();
      }
    }

    async flush() {
      if (this.clicks.length === 0) return;

      const data = {
        fingerprint: this.fingerprint,
        sessionId: this.sessionId,
        pageInfo: this.pageInfo,
        clicks: [...this.clicks],
        timestamp: Date.now()
      };

      try {
        await fetch(this.trackUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(data)
        });
        this.clicks = [];
      } catch (error) {
        console.error('Heatmap track failed:', error);
      }
    }

    async init() {
      await this.generateFingerprint();
      
      document.addEventListener('click', (e) => this.trackClick(e));
      
      setInterval(() => this.flush(), this.flushInterval);
      
      window.addEventListener('beforeunload', () => this.flush());
      
      console.log(`Heatmap SDK initialized. Fingerprint: ${this.fingerprint}`);
    }

    getFingerprint() {
      return this.fingerprint;
    }

    getSessionId() {
      return this.sessionId;
    }
  }

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = HeatmapSDK;
  } else {
    global.HeatmapSDK = HeatmapSDK;
    
    if (!global.heatmapInstance) {
      global.heatmapInstance = new HeatmapSDK();
    }
  }

})(typeof window !== 'undefined' ? window : this);
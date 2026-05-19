export class BrowserCompatibility {
  constructor() {
    this.detections = {};
    this.init();
  }

  init() {
    this.detectAll();
  }

  detectAll() {
    this.detections = {
      webCodecs: this.detectWebCodecs(),
      avif: this.detectAVIF(),
      webp: this.detectWebP(),
      webWorkers: this.detectWebWorkers(),
      offscreenCanvas: this.detectOffscreenCanvas(),
      hardwareConcurrency: navigator.hardwareConcurrency || 2,
      browser: this.detectBrowser(),
      isMobile: this.isMobile(),
      webGL: this.detectWebGL()
    };
    
    return this.detections;
  }

  detectWebCodecs() {
    const hasImageDecoder = typeof ImageDecoder !== 'undefined';
    const hasImageEncoder = typeof ImageEncoder !== 'undefined';
    const hasVideoDecoder = typeof VideoDecoder !== 'undefined';
    
    return {
      supported: hasImageDecoder,
      imageDecoder: hasImageDecoder,
      imageEncoder: hasImageEncoder,
      videoDecoder: hasVideoDecoder
    };
  }

  async detectAVIF() {
    return new Promise(resolve => {
      const canvas = document.createElement('canvas');
      canvas.width = 1;
      canvas.height = 1;
      
      const ctx = canvas.getContext('2d');
      const imageData = ctx.createImageData(1, 1);
      imageData.data[0] = 0;
      imageData.data[1] = 0;
      imageData.data[2] = 0;
      imageData.data[3] = 255;
      ctx.putImageData(imageData, 0, 0);
      
      try {
        canvas.toBlob(async (blob) => {
          if (blob && typeof ImageDecoder !== 'undefined') {
            try {
              const avifData = this.getTestAVIFData();
              if (avifData) {
                const decoder = new ImageDecoder({
                  data: avifData,
                  type: 'image/avif'
                });
                await decoder.completed;
                resolve(true);
              } else {
                resolve(this.detectAVIFViaImage());
              }
            } catch (e) {
              resolve(false);
            }
          } else {
            resolve(this.detectAVIFViaImage());
          }
        }, 'image/avif');
      } catch (e) {
        resolve(this.detectAVIFViaImage());
      }
    });
  }

  detectAVIFViaImage() {
    return new Promise(resolve => {
      const img = new Image();
      img.onload = () => resolve(true);
      img.onerror = () => resolve(false);
      img.src = 'data:image/avif;base64,AAAAIGZ0eXBhdmlmAAAAAGF2aWZtaXNwMmF2aWNpc28ybWlhZgAAADxpc29tAAAAGG1pZmFAAAEAAAAkAAAACgAAACAAAAA';
    });
  }

  detectWebP() {
    return new Promise(resolve => {
      const img = new Image();
      img.onload = () => resolve(true);
      img.onerror = () => resolve(false);
      img.src = 'data:image/webp;base64,UklGRjoAAABXRUJQVlA4IC4AAACyAgCdASoCAAIALmk0mk0iIiIiIgBoSygABc6WWgAA/veff/0PP8bA//LwYAAA';
    });
  }

  detectWebWorkers() {
    try {
      return typeof Worker !== 'undefined';
    } catch (e) {
      return false;
    }
  }

  detectOffscreenCanvas() {
    try {
      return typeof OffscreenCanvas !== 'undefined';
    } catch (e) {
      return false;
    }
  }

  detectWebGL() {
    try {
      const canvas = document.createElement('canvas');
      const webgl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
      const webgl2 = canvas.getContext('webgl2');
      
      return {
        webgl: !!webgl,
        webgl2: !!webgl2
      };
    } catch (e) {
      return { webgl: false, webgl2: false };
    }
  }

  detectBrowser() {
    const ua = navigator.userAgent;
    
    if (ua.match(/chrome|chromium|crios/i)) {
      return { name: 'Chrome', version: this.extractVersion(ua, /Chrome\/(\d+)/) };
    }
    if (ua.match(/firefox|fxios/i)) {
      return { name: 'Firefox', version: this.extractVersion(ua, /Firefox\/(\d+)/) };
    }
    if (ua.match(/safari/i)) {
      return { name: 'Safari', version: this.extractVersion(ua, /Version\/(\d+)/) };
    }
    if (ua.match(/opr\//i)) {
      return { name: 'Opera', version: this.extractVersion(ua, /OPR\/(\d+)/) };
    }
    if (ua.match(/edg/i)) {
      return { name: 'Edge', version: this.extractVersion(ua, /Edg\/(\d+)/) };
    }
    
    return { name: 'Unknown', version: 0 };
  }

  extractVersion(ua, regex) {
    const match = ua.match(regex);
    return match ? parseInt(match[1], 10) : 0;
  }

  isMobile() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
  }

  getOptimalDecodeConfig() {
    const { webCodecs, webWorkers, hardwareConcurrency, browser, isMobile } = this.detections;
    
    let maxWorkers = 2;
    let maxConcurrent = 4;
    
    if (isMobile) {
      maxWorkers = Math.min(2, hardwareConcurrency);
      maxConcurrent = maxWorkers * 2;
    } else {
      maxWorkers = Math.min(4, hardwareConcurrency);
      maxConcurrent = maxWorkers * 2;
    }
    
    if (browser.name === 'Safari' && browser.version < 16.4) {
      maxWorkers = Math.min(2, maxWorkers);
    }
    
    return {
      useWebCodecs: webCodecs.supported && webWorkers,
      maxWorkers,
      maxConcurrent,
      preferredFormat: this.getPreferredFormat()
    };
  }

  getPreferredFormat() {
    const { avif, webp } = this.detections;
    
    if (avif) return 'avif';
    if (webp) return 'webp';
    return 'jpeg';
  }

  getSupportSummary() {
    const { webCodecs, avif, webp, webWorkers, offscreenCanvas, browser, isMobile, webGL } = this.detections;
    
    return {
      title: '浏览器兼容性检测',
      features: [
        {
          name: 'WebCodecs (硬件图像解码)',
          supported: webCodecs.supported,
          required: true,
          impact: '不支持时降级使用传统Image解码，性能下降约30%'
        },
        {
          name: 'Web Workers (多线程)',
          supported: webWorkers,
          required: true,
          impact: '不支持时在主线程解码，可能阻塞UI'
        },
        {
          name: 'OffscreenCanvas (后台渲染)',
          supported: offscreenCanvas,
          required: false,
          impact: '提升解码后处理性能'
        },
        {
          name: 'AVIF 图像格式',
          supported: avif,
          required: false,
          impact: '支持时可获得更高压缩比，体积减小约50%'
        },
        {
          name: 'WebP 图像格式',
          supported: webp,
          required: false,
          impact: '比JPEG体积小约25-35%'
        },
        {
          name: 'WebGL 2.0',
          supported: webGL.webgl2,
          required: false,
          impact: '更好的渲染性能和质量'
        }
      ],
      browser: `${browser.name} ${browser.version}`,
      isMobile,
      recommendation: this.getRecommendation()
    };
  }

  getRecommendation() {
    const { webCodecs, avif, browser, isMobile } = this.detections;
    const recommendations = [];
    
    if (!webCodecs.supported) {
      recommendations.push({
        level: 'warning',
        text: '建议升级到 Chrome 94+, Firefox 105+, Safari 16.4+ 以启用硬件图像解码'
      });
    }
    
    if (!avif && webCodecs.supported) {
      recommendations.push({
        level: 'info',
        text: '浏览器不支持AVIF格式，将使用WebP或JPEG'
      });
    }
    
    if (isMobile) {
      recommendations.push({
        level: 'info',
        text: '移动设备检测到，已自动降低并发数以保证流畅度'
      });
    }
    
    if (browser.name === 'Safari') {
      recommendations.push({
        level: 'info',
        text: 'Safari浏览器注意：确保关闭"跨站点跟踪预防"以优化图片缓存'
      });
    }
    
    if (recommendations.length === 0) {
      recommendations.push({
        level: 'success',
        text: '浏览器完美支持所有优化功能！'
      });
    }
    
    return recommendations;
  }

  getTestAVIFData() {
    try {
      const base64 = 'AAAAIGZ0eXBhdmlmAAAAAGF2aWZtaXNwMmF2aWNpc28ybWlhZgAAADxpc29tAAAAGG1pZmFAAAEAAAAkAAAACgAAACAAAAA';
      const binaryString = atob(base64);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      return bytes.buffer;
    } catch (e) {
      return null;
    }
  }
}

export const browserCompatibility = new BrowserCompatibility();
export default BrowserCompatibility;

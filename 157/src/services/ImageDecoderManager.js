import * as PIXI from 'pixi.js';

class ImageDecoderManager {
  constructor(options = {}) {
    this.maxWorkers = options.maxWorkers || Math.min(4, navigator.hardwareConcurrency || 2);
    this.workers = [];
    this.pendingRequests = new Map();
    this.requestQueue = [];
    this.activeRequests = new Set();
    this.maxConcurrent = options.maxConcurrent || this.maxWorkers * 2;
    this.requestId = 0;
    this.isReady = false;
    this.supportsWebCodecs = false;
    this.supportsAVIF = false;
    this.fallbackMode = false;
    this.stats = {
      totalDecoded: 0,
      webCodecsDecoded: 0,
      fallbackDecoded: 0,
      totalTime: 0,
      hardwareAccelerated: 0
    };
    
    this.init();
  }

  async init() {
    try {
      this.supportsWebCodecs = typeof ImageDecoder !== 'undefined';
      
      if (this.supportsWebCodecs) {
        await this.initWorkers();
      }
      
      if (!this.supportsWebCodecs || this.workers.length === 0) {
        console.warn('WebCodecs not supported, using Image fallback');
        this.fallbackMode = true;
      }
      
      this.isReady = true;
      console.log(`ImageDecoderManager ready: workers=${this.workers.length}, webcodecs=${this.supportsWebCodecs}, avif=${this.supportsAVIF}`);
    } catch (e) {
      console.error('Failed to init ImageDecoderManager:', e);
      this.fallbackMode = true;
      this.isReady = true;
    }
  }

  async initWorkers() {
    const initPromises = [];
    
    for (let i = 0; i < this.maxWorkers; i++) {
      initPromises.push(this.createWorker());
    }
    
    await Promise.allSettled(initPromises);
    
    if (this.workers.length > 0) {
      const firstWorker = this.workers[0];
      this.supportsWebCodecs = firstWorker.supported;
      this.supportsAVIF = firstWorker.features?.avif || false;
    }
  }

  createWorker() {
    return new Promise((resolve, reject) => {
      try {
        const worker = new Worker(
          new URL('../workers/imageDecoder.worker.js', import.meta.url),
          { type: 'module' }
        );
        
        const workerInfo = {
          worker,
          busy: false,
          supported: false,
          features: {}
        };
        
        worker.onmessage = (e) => {
          if (e.data.type === 'ready') {
            workerInfo.supported = e.data.supported;
            workerInfo.features = e.data.features || {};
            this.workers.push(workerInfo);
            resolve(workerInfo);
          }
        };
        
        worker.onerror = (err) => {
          console.error('Worker error:', err);
          reject(err);
        };
        
      } catch (e) {
        console.error('Failed to create worker:', e);
        reject(e);
      }
    });
  }

  async decode(url, options = {}) {
    if (!this.isReady) {
      await this.waitForReady();
    }
    
    const id = ++this.requestId;
    const startTime = performance.now();
    
    try {
      let result;
      
      if (!this.fallbackMode && this.workers.length > 0) {
        result = await this.decodeWithWorker(id, url, options);
        this.stats.webCodecsDecoded++;
        if (result.hardwareAccelerated) {
          this.stats.hardwareAccelerated++;
        }
      } else {
        result = await this.decodeWithFallback(url, options);
        this.stats.fallbackDecoded++;
      }
      
      this.stats.totalDecoded++;
      this.stats.totalTime += performance.now() - startTime;
      
      return result;
    } catch (error) {
      console.warn(`Decode failed, trying fallback: ${error.message}`);
      const result = await this.decodeWithFallback(url, options);
      this.stats.fallbackDecoded++;
      this.stats.totalDecoded++;
      this.stats.totalTime += performance.now() - startTime;
      return result;
    }
  }

  async decodeWithWorker(id, url, options) {
    return new Promise((resolve, reject) => {
      const request = {
        id,
        url,
        options,
        resolve,
        reject,
        createdAt: Date.now()
      };
      
      this.pendingRequests.set(id, request);
      this.requestQueue.push(id);
      
      this.processQueue();
    });
  }

  processQueue() {
    while (this.requestQueue.length > 0 && this.activeRequests.size < this.maxConcurrent) {
      const id = this.requestQueue.shift();
      const request = this.pendingRequests.get(id);
      
      if (!request) continue;
      
      const worker = this.getAvailableWorker();
      if (!worker) {
        this.requestQueue.unshift(id);
        break;
      }
      
      this.activeRequests.add(id);
      worker.busy = true;
      
      worker.worker.postMessage({
        type: 'decode',
        id: request.id,
        url: request.url,
        type: request.options.type,
        options: request.options
      });
      
      const handleMessage = (e) => {
        if (e.data.id !== request.id) return;
        
        if (e.data.type === 'decoded') {
          worker.worker.removeEventListener('message', handleMessage);
          this.pendingRequests.delete(request.id);
          this.activeRequests.delete(request.id);
          worker.busy = false;
          
          if (e.data.success) {
            request.resolve(e.data.data);
          } else {
            request.reject(new Error(e.data.error));
          }
          
          this.processQueue();
        } else if (e.data.type === 'progress') {
          if (request.options.onProgress) {
            request.options.onProgress(e.data.progress, e.data.status);
          }
        }
      };
      
      worker.worker.addEventListener('message', handleMessage);
    }
  }

  getAvailableWorker() {
    return this.workers.find(w => !w.busy) || null;
  }

  async decodeWithFallback(url, options = {}) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      
      img.onload = () => {
        const canvas = document.createElement('canvas');
        canvas.width = img.naturalWidth;
        canvas.height = img.naturalHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0);
        
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        
        resolve({
          imageData,
          width: canvas.width,
          height: canvas.height,
          decodedWith: 'ImageElement',
          hardwareAccelerated: false
        });
      };
      
      img.onerror = () => {
        reject(new Error('Failed to load image'));
      };
      
      img.src = url;
    });
  }

  async decodeToTexture(url, options = {}) {
    const result = await this.decode(url, options);
    
    const { imageData, width, height } = result;
    
    const glTexture = PIXI.Texture.fromBuffer(
      imageData.data,
      width,
      height,
      {
        mipmap: options.mipmap ?? false,
        scaleMode: options.scaleMode ?? PIXI.SCALE_MODES.LINEAR,
        wrapMode: PIXI.WRAP_MODES.CLAMP,
        format: PIXI.FORMATS.RGBA,
        type: PIXI.TYPES.UNSIGNED_BYTE
      }
    );
    
    glTexture.baseTexture.resource.decodeInfo = {
      decodedWith: result.decodedWith,
      hardwareAccelerated: result.hardwareAccelerated,
      mimeType: result.mimeType
    };
    
    return glTexture;
  }

  cancel(id) {
    const request = this.pendingRequests.get(id);
    if (request) {
      this.workers.forEach(w => {
        w.worker.postMessage({
          type: 'cancel',
          id
        });
      });
      this.pendingRequests.delete(id);
      this.activeRequests.delete(id);
      const queueIndex = this.requestQueue.indexOf(id);
      if (queueIndex !== -1) {
        this.requestQueue.splice(queueIndex, 1);
      }
      request.reject(new Error('Cancelled'));
    }
  }

  clearQueue() {
    this.requestQueue = [];
    this.pendingRequests.forEach((_, id) => this.cancel(id));
  }

  getStats() {
    return {
      ...this.stats,
      avgTime: this.stats.totalDecoded > 0 ? this.stats.totalTime / this.stats.totalDecoded : 0,
      pending: this.requestQueue.length,
      active: this.activeRequests.size,
      workers: this.workers.length,
      webCodecs: this.supportsWebCodecs,
      avif: this.supportsAVIF,
      fallbackMode: this.fallbackMode
    };
  }

  waitForReady() {
    return new Promise(resolve => {
      if (this.isReady) {
        resolve();
      } else {
        const check = () => {
          if (this.isReady) {
            resolve();
          } else {
            setTimeout(check, 50);
          }
        };
        check();
      }
    });
  }

  destroy() {
    this.clearQueue();
    this.workers.forEach(w => w.worker.terminate());
    this.workers = [];
    this.isReady = false;
  }
}

let instance = null;

export function getImageDecoderManager(options) {
  if (!instance) {
    instance = new ImageDecoderManager(options);
  }
  return instance;
}

export default ImageDecoderManager;

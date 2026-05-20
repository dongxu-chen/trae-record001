class ImageDecoderWorker {
  constructor() {
    this.pendingRequests = new Map();
    this.requestId = 0;
    this.decoderCache = new Map();
    this.isBusy = false;
    
    self.addEventListener('message', (e) => {
      this.handleMessage(e.data);
    });
  }

  handleMessage(data) {
    switch (data.type) {
      case 'decode':
        this.decodeImage(data);
        break;
      case 'cancel':
        this.cancelRequest(data.id);
        break;
      case 'clearCache':
        this.clearCache();
        break;
      default:
        console.warn('Unknown message type:', data.type);
    }
  }

  async decodeImage(data) {
    const { id, url, type, options = {} } = data;
    
    try {
      this.postProgress(id, 0.1, 'Fetching image data');
      
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const arrayBuffer = await response.arrayBuffer();
      
      this.postProgress(id, 0.3, 'Decoding with WebCodecs');
      
      const result = await this.decodeWithWebCodecs(arrayBuffer, type, options);
      
      this.postProgress(id, 1.0, 'Complete');
      
      self.postMessage({
        type: 'decoded',
        id,
        success: true,
        data: result
      }, [result.imageData.buffer]);
      
    } catch (error) {
      console.error('Decode error:', error);
      self.postMessage({
        type: 'decoded',
        id,
        success: false,
        error: error.message
      });
    } finally {
      this.pendingRequests.delete(id);
    }
  }

  async decodeWithWebCodecs(arrayBuffer, type, options) {
    if (typeof ImageDecoder === 'undefined') {
      throw new Error('WebCodecs ImageDecoder not supported');
    }

    const mimeType = this.detectMimeType(arrayBuffer, type);
    
    const decoder = new ImageDecoder({
      data: arrayBuffer,
      type: mimeType,
      preferAnimation: false,
      ...options
    });

    await decoder.completed;

    const result = await decoder.decode({
      frameIndex: 0,
      completeFramesOnly: true
    });

    const videoFrame = result.image;
    
    const canvas = new OffscreenCanvas(videoFrame.displayWidth, videoFrame.displayHeight);
    const ctx = canvas.getContext('2d');
    
    ctx.drawImage(videoFrame, 0, 0);
    videoFrame.close();
    
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    
    return {
      imageData,
      width: canvas.width,
      height: canvas.height,
      mimeType,
      hardwareAccelerated: this.isHardwareAccelerated(),
      decodedWith: 'WebCodecs'
    };
  }

  detectMimeType(arrayBuffer, hint) {
    const uint8 = new Uint8Array(arrayBuffer);
    
    const magicNumbers = [
      { magic: [0xFF, 0xD8, 0xFF], type: 'image/jpeg' },
      { magic: [0x89, 0x50, 0x4E, 0x47], type: 'image/png' },
      { magic: [0x52, 0x49, 0x46, 0x46], type: 'image/webp' },
      { magic: [0x00, 0x00, 0x00, 0x1C, 0x66, 0x74, 0x79, 0x70], type: 'image/avif' },
      { magic: [0x00, 0x00, 0x00, 0x20, 0x66, 0x74, 0x79, 0x70], type: 'image/avif' },
    ];
    
    for (const { magic, type } of magicNumbers) {
      if (magic.every((byte, i) => uint8[i] === byte)) {
        return type;
      }
    }
    
    return hint || 'image/jpeg';
  }

  isHardwareAccelerated() {
    try {
      const canvas = new OffscreenCanvas(1, 1);
      const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
      if (gl) {
        const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
        if (debugInfo) {
          const renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
          return /NVIDIA|AMD|Intel|Apple|Adreno|Mali/i.test(renderer);
        }
      }
    } catch (e) {
    }
    return false;
  }

  postProgress(id, progress, status) {
    self.postMessage({
      type: 'progress',
      id,
      progress,
      status
    });
  }

  cancelRequest(id) {
    const request = this.pendingRequests.get(id);
    if (request) {
      this.pendingRequests.delete(id);
    }
  }

  clearCache() {
    this.decoderCache.clear();
    self.postMessage({
      type: 'cacheCleared'
    });
  }
}

const worker = new ImageDecoderWorker();

self.postMessage({
  type: 'ready',
  supported: typeof ImageDecoder !== 'undefined',
  features: {
    webCodecs: typeof ImageDecoder !== 'undefined',
    avif: typeof ImageDecoder !== 'undefined' && (() => {
      try {
        return true;
      } catch (e) {
        return false;
      }
    })()
  }
});

import * as THREE from 'three';

export class BackgroundSystem {
  constructor() {
    this.mode = 'none';
    this.scene = null;
    this.renderer = null;
    
    this.planeMesh = null;
    this.backgroundMaterial = null;
    this.backgroundTexture = null;
    
    this.chromaKeyColor = { r: 0, g: 255, b: 0 };
    this.chromaKeyThreshold = 0.4;
    this.chromaKeySmoothness = 0.08;
    
    this.isActive = false;
    this.videoElement = null;
    this.processingCanvas = null;
    this.processingContext = null;
    
    this.backgrounds = new Map();
    this.currentBackgroundName = null;
    
    this.effectStrength = 1.0;
  }

  init(scene, renderer) {
    this.scene = scene;
    this.renderer = renderer;
    
    this.processingCanvas = document.createElement('canvas');
    this.processingCanvas.width = 640;
    this.processingCanvas.height = 480;
    this.processingContext = this.processingCanvas.getContext('2d', { willReadFrequently: true });
    
    this._createBackgroundPlane();
  }

  _createBackgroundPlane() {
    if (this.planeMesh) {
      this.scene.remove(this.planeMesh);
    }
    
    const geometry = new THREE.PlaneGeometry(20, 20);
    this.backgroundMaterial = new THREE.MeshBasicMaterial({
      color: 0x808080,
      side: THREE.DoubleSide,
      transparent: false,
      depthWrite: false
    });
    
    this.planeMesh = new THREE.Mesh(geometry, this.backgroundMaterial);
    this.planeMesh.position.z = -10;
    this.planeMesh.visible = false;
    
    this.scene.add(this.planeMesh);
  }

  setMode(mode) {
    const validModes = ['none', 'color', 'image', 'video', 'chromakey', 'blur', 'virtual'];
    
    if (!validModes.includes(mode)) {
      console.error(`Invalid background mode: ${mode}`);
      return false;
    }
    
    this.mode = mode;
    this._updatePlaneVisibility();
    this.isActive = mode !== 'none';
    
    return true;
  }

  _updatePlaneVisibility() {
    if (!this.planeMesh) return;
    
    this.planeMesh.visible = this.mode !== 'none';
  }

  setColor(color) {
    const threeColor = new THREE.Color(color);
    
    if (this.backgroundTexture) {
      this.backgroundTexture.dispose();
      this.backgroundTexture = null;
    }
    
    if (this.backgroundMaterial) {
      this.backgroundMaterial.color.copy(threeColor);
      this.backgroundMaterial.map = null;
      this.backgroundMaterial.needsUpdate = true;
    }
    
    this.setMode('color');
  }

  async setImage(url) {
    return new Promise((resolve, reject) => {
      const loader = new THREE.TextureLoader();
      loader.load(
        url,
        (texture) => {
          if (this.backgroundTexture) {
            this.backgroundTexture.dispose();
          }
          this.backgroundTexture = texture;
          texture.colorSpace = THREE.SRGBColorSpace;
          
          this._updatePlaneVisibility();
          
          if (this.backgroundMaterial) {
            this.backgroundMaterial.map = texture;
            this.backgroundMaterial.needsUpdate = true;
          }
          
          this.setMode('image');
          resolve(texture);
        },
        undefined,
        (error) => {
          reject(error);
        }
      );
    });
  }

  setVideo(videoElement) {
    if (!videoElement) return;
    this.videoElement = videoElement;
    
    const texture = new THREE.VideoTexture(videoElement);
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.minFilter = THREE.LinearFilter;
    texture.magFilter = THREE.LinearFilter;
    
    if (this.backgroundTexture) {
      this.backgroundTexture.dispose();
    }
    this.backgroundTexture = texture;
    
    if (this.backgroundMaterial) {
      this.backgroundMaterial.map = texture;
      this.backgroundMaterial.needsUpdate = true;
    }
    
    this.setMode('video');
  }

  setChromaKeyOptions(options = {}) {
    if (options.color !== undefined) {
      const color = new THREE.Color(options.color);
      this.chromaKeyColor = {
        r: color.r * 255,
        g: color.g * 255,
        b: color.b * 255
      };
    }
    if (options.threshold !== undefined) {
      this.chromaKeyThreshold = THREE.MathUtils.clamp(options.threshold, 0, 1);
    }
    if (options.smoothness !== undefined) {
      this.chromaKeySmoothness = THREE.MathUtils.clamp(options.smoothness, 0, 1);
    }
  }

  processFrame(sourceCanvas, targetCanvas) {
    if (this.mode !== 'chromakey') return;
    
    const sourceCtx = sourceCanvas.getContext('2d');
    const targetCtx = targetCanvas.getContext('2d');
    const width = sourceCanvas.width;
    const height = sourceCanvas.height;
    
    targetCanvas.width = width;
    targetCanvas.height = height;
    
    const imageData = sourceCtx.getImageData(0, 0, width, height);
    const data = imageData.data;
    
    for (let i = 0; i < data.length; i += 4) {
      const r = data[i];
      const g = data[i + 1];
      const b = data[i + 2];
      
      const distance = this._calculateChromaDistance(r, g, b);
      
      if (distance < this.chromaKeyThreshold) {
        const alpha = THREE.MathUtils.smoothstep(
          distance,
          this.chromaKeyThreshold - this.chromaKeySmoothness,
          this.chromaKeyThreshold
        );
        data[i + 3] = Math.floor(255 * alpha);
      }
    }
    
    targetCtx.putImageData(imageData, 0, 0);
  }

  _calculateChromaDistance(r, g, b) {
    const dr = r - this.chromaKeyColor.r;
    const dg = g - this.chromaKeyColor.g;
    const db = b - this.chromaKeyColor.b;
    
    return Math.sqrt(dr * dr + dg * dg + db * db) / 255;
  }

  setVirtualBackground(presetName) {
    if (!this.backgrounds.has(presetName)) {
      console.warn(`Background preset not found: ${presetName}`);
      return false;
    }
    
    const preset = this.backgrounds.get(presetName);
    
    if (preset.type === 'color') {
      this.setColor(preset.value);
    } else if (preset.type === 'image') {
      this.setImage(preset.value);
    }
    
    this.currentBackgroundName = presetName;
    return true;
  }

  registerBackground(name, type, value) {
    this.backgrounds.set(name, { type, value });
  }

  setVirtualScene(sceneDescription) {
    if (!this.renderer) return;
    
    this.setMode('virtual');
  }

  setEffectStrength(strength) {
    this.effectStrength = THREE.MathUtils.clamp(strength, 0, 1);
  }

  getMode() {
    return this.mode;
  }

  isEnabled() {
    return this.isActive && this.mode !== 'none';
  }

  getPlane() {
    return this.planeMesh;
  }

  update(deltaTime) {
    if (!this.isActive) return;
    
    if (this.planeMesh) {
      this.planeMesh.visible = this.mode !== 'none';
    }
  }

  dispose() {
    if (this.backgroundTexture) {
      this.backgroundTexture.dispose();
      this.backgroundTexture = null;
    }
    
    if (this.planeMesh) {
      this.scene.remove(this.planeMesh);
      if (this.planeMesh.geometry) {
        this.planeMesh.geometry.dispose();
      }
      if (this.planeMesh.material) {
        if (Array.isArray(this.planeMesh.material)) {
          this.planeMesh.material.forEach(m => m.dispose());
        } else {
          this.planeMesh.material.dispose();
        }
      }
      this.planeMesh = null;
    }
    
    if (this.processingCanvas) {
      this.processingCanvas = null;
      this.processingContext = null;
    }
    
    this.isActive = false;
    this.mode = 'none';
  }
}

export default BackgroundSystem;

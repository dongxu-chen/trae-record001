import * as THREE from 'three';
import { VRMLoader } from './vrm_loader.js';
import { FollowCamera } from './camera.js';
import { ExpressionSystem } from './expression.js';
import { ClothingSystem } from './clothing.js';
import { MotionCapture } from './mocap.js';
import { BackgroundSystem } from './background.js';
import { VideoRecorder } from './recorder.js';

class VTuberDressUpApp {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      throw new Error(`Container with id "${containerId}" not found`);
    }
    
    this.vrmLoader = null;
    this.followCamera = null;
    this.expressionSystem = null;
    this.clothingSystem = null;
    this.motionCapture = null;
    this.backgroundSystem = null;
    this.videoRecorder = null;
    this.vrm = null;
    
    this.clock = new THREE.Clock();
    this.animationId = null;
    
    this.applyHeadRotation = true;
    this.headRotationMultiplier = { x: 1.5, y: 1.5, z: 0.5 };
    this.headRotationSmoothness = 6.0;
    this.targetHeadRotation = { x: 0, y: 0, z: 0 };
    this.currentHeadRotation = { x: 0, y: 0, z: 0 };
    
    this._init();
  }

  _init() {
    this._setupRenderer();
    this._setupScene();
    this._setupLights();
    
    this.vrmLoader = new VRMLoader();
    this.followCamera = new FollowCamera(this.renderer);
    this.expressionSystem = new ExpressionSystem();
    this.clothingSystem = new ClothingSystem();
    this.backgroundSystem = new BackgroundSystem();
    this.motionCapture = new MotionCapture(this.expressionSystem);
    this.videoRecorder = new VideoRecorder();
    
    this.backgroundSystem.init(this.scene, this.renderer);
    this.motionCapture.setExpressionSystem(this.expressionSystem);
    
    this._setupMotionCaptureCallbacks();
    
    this._initEventListeners();
    this._start();
  }

  _setupRenderer() {
    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true
    });
    
    this.renderer.setSize(window.innerWidth, window.innerHeight);
    this.renderer.setPixelRatio(window.devicePixelRatio);
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.container.appendChild(this.renderer.domElement);
  }

  _setupScene() {
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0xf0f0f0);
  }

  _setupLights() {
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    this.scene.add(ambientLight);
    
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(1, 3, 2);
    this.scene.add(directionalLight);
    
    const fillLight = new THREE.DirectionalLight(0xffffff, 0.3);
    fillLight.position.set(-1, 1, -2);
    this.scene.add(fillLight);
  }

  _setupMotionCaptureCallbacks() {
    this.motionCapture.onFaceDetected = (detected) => {
      if (this.onFaceDetected) {
        this.onFaceDetected(detected);
      }
    };
    
    this.motionCapture.onLandmarksUpdate = (landmarks, headRotation) => {
      if (this.applyHeadRotation) {
        this.targetHeadRotation = {
          x: headRotation.x * this.headRotationMultiplier.x,
          y: headRotation.y * this.headRotationMultiplier.y,
          z: headRotation.z * this.headRotationMultiplier.z
        };
      }
    };
    
    this.motionCapture.onError = (error) => {
      console.error('MotionCapture error:', error);
      if (this.onError) {
        this.onError(error);
      }
    };
  }

  _initEventListeners() {
    window.addEventListener('resize', () => this._onResize());
  }

  _onResize() {
    this.renderer.setSize(window.innerWidth, window.innerHeight);
  }

  async loadVRM(url) {
    try {
      this.vrm = await this.vrmLoader.load(url);
      
      this.scene.add(this.vrm.scene);
      
      this.followCamera.setVRM(this.vrm);
      this.expressionSystem.setVRM(this.vrm);
      this.clothingSystem.setVRM(this.vrm);
      
      this.vrm.scene.position.y = -1.0;
      
      this._onVRMLoaded(this.vrm);
      
      return this.vrm;
    } catch (error) {
      console.error('Failed to load VRM:', error);
      throw error;
    }
  }

  _onVRMLoaded(vrm) {
    console.log('VRM loaded successfully:', vrm);
    
    this.expressionSystem.setBlinkEnabled(true);
  }

  _start() {
    this.clock.start();
    this._animate();
  }

  _animate() {
    this.animationId = requestAnimationFrame(() => this._animate());
    
    const deltaTime = this.clock.getDelta();
    
    if (this.vrm) {
      this.vrm.update(deltaTime);
    }
    
    if (this.followCamera) {
      this.followCamera.update(deltaTime);
    }
    
    if (this.expressionSystem) {
      this.expressionSystem.update(deltaTime);
    }
    
    if (this.motionCapture) {
      this.motionCapture.update(deltaTime);
    }
    
    this._updateHeadRotation(deltaTime);
    
    if (this.backgroundSystem) {
      this.backgroundSystem.update(deltaTime);
    }
    
    this._render();
  }

  _updateHeadRotation(deltaTime) {
    if (!this.applyHeadRotation || !this.vrm?.humanoid) return;
    
    const headBone = this.vrm.humanoid.getNormalizedBone('head');
    const neckBone = this.vrm.humanoid.getNormalizedBone('neck');
    
    if (!headBone) return;
    
    const lerpFactor = 1 - Math.exp(-this.headRotationSmoothness * deltaTime);
    
    this.currentHeadRotation.x = THREE.MathUtils.lerp(
      this.currentHeadRotation.x,
      this.targetHeadRotation.x,
      lerpFactor
    );
    this.currentHeadRotation.y = THREE.MathUtils.lerp(
      this.currentHeadRotation.y,
      this.targetHeadRotation.y,
      lerpFactor
    );
    this.currentHeadRotation.z = THREE.MathUtils.lerp(
      this.currentHeadRotation.z,
      this.targetHeadRotation.z,
      lerpFactor
    );
    
    if (headBone.node) {
      headBone.node.rotation.x = this.currentHeadRotation.x;
      headBone.node.rotation.y = this.currentHeadRotation.y;
      headBone.node.rotation.z = this.currentHeadRotation.z;
    }
  }

  _render() {
    this.renderer.render(this.scene, this.followCamera.getCamera());
  }

  async startMotionCapture(useFrontCamera = true) {
    if (!this.motionCapture) return false;
    
    const success = await this.motionCapture.start(useFrontCamera);
    if (success) {
      this.expressionSystem.enableFaceTracking(true);
    }
    
    return success;
  }

  stopMotionCapture() {
    if (this.motionCapture) {
      this.motionCapture.stop();
    }
    this.expressionSystem.enableFaceTracking(false);
    
    this.targetHeadRotation = { x: 0, y: 0, z: 0 };
    this.currentHeadRotation = { x: 0, y: 0, z: 0 };
  }

  isMotionCaptureActive() {
    return this.motionCapture?.isActive() || false;
  }

  calibrateMotionCapture() {
    if (this.motionCapture) {
      return this.motionCapture.calibrate();
    }
    return false;
  }

  setApplyHeadRotation(enabled) {
    this.applyHeadRotation = enabled;
    if (!enabled) {
      this.targetHeadRotation = { x: 0, y: 0, z: 0 };
    }
  }

  setHeadRotationMultiplier(x, y, z) {
    if (x !== undefined) this.headRotationMultiplier.x = x;
    if (y !== undefined) this.headRotationMultiplier.y = y;
    if (z !== undefined) this.headRotationMultiplier.z = z;
  }

  setHeadRotationSmoothness(smoothness) {
    this.headRotationSmoothness = Math.max(0.1, smoothness);
  }

  async startRecording(options = {}) {
    if (!this.videoRecorder) return false;
    
    try {
      this.videoRecorder.init(this.renderer.domElement, {
        fps: options.fps || 30,
        videoBitrate: options.videoBitrate || 5000000,
        includeMicAudio: options.includeMicAudio || false
      });
      
      return await this.videoRecorder.start();
    } catch (error) {
      console.error('Failed to start recording:', error);
      return false;
    }
  }

  pauseRecording() {
    if (this.videoRecorder) {
      this.videoRecorder.pause();
    }
  }

  resumeRecording() {
    if (this.videoRecorder) {
      this.videoRecorder.resume();
    }
  }

  stopRecording() {
    if (this.videoRecorder) {
      this.videoRecorder.stop();
    }
  }

  downloadRecording(filename = 'vtuber-recording.webm') {
    if (this.videoRecorder) {
      return this.videoRecorder.download(filename);
    }
    return false;
  }

  getRecordingState() {
    if (this.videoRecorder) {
      return this.videoRecorder.getRecordingState();
    }
    return null;
  }

  setRecordingMicAudio(enabled) {
    if (this.videoRecorder) {
      this.videoRecorder.setIncludeMicAudio(enabled);
    }
  }

  setBackgroundColor(color) {
    if (this.backgroundSystem) {
      this.backgroundSystem.setColor(color);
    }
  }

  async setBackgroundImage(url) {
    if (this.backgroundSystem) {
      return await this.backgroundSystem.setImage(url);
    }
  }

  setBackgroundVideo(videoElement) {
    if (this.backgroundSystem) {
      this.backgroundSystem.setVideo(videoElement);
    }
  }

  setChromaKeyOptions(options = {}) {
    if (this.backgroundSystem) {
      this.backgroundSystem.setChromaKeyOptions(options);
    }
  }

  disableBackground() {
    if (this.backgroundSystem) {
      this.backgroundSystem.setMode('none');
    }
  }

  setTalking(enabled) {
    this.expressionSystem.setTalking(enabled);
  }

  setBlinkEnabled(enabled) {
    this.expressionSystem.setBlinkEnabled(enabled);
  }

  forceBlink() {
    this.expressionSystem.forceBlink();
  }

  setExpression(name, value) {
    this.expressionSystem.setExpression(name, value);
  }

  changeMaterialColor(materialKey, color) {
    return this.clothingSystem.changeMaterialColor(materialKey, color);
  }

  changeMaterialOpacity(materialKey, opacity) {
    return this.clothingSystem.changeMaterialOpacity(materialKey, opacity);
  }

  async changeMaterialTexture(materialKey, textureUrl, textureType = 'map') {
    return this.clothingSystem.changeMaterialTexture(materialKey, textureUrl, textureType);
  }

  createPresetMaterial(presetName, options = {}) {
    return this.clothingSystem.createPresetMaterial(presetName, options);
  }

  applyPresetMaterial(materialKey, presetName) {
    return this.clothingSystem.applyPresetMaterial(materialKey, presetName);
  }

  getAllMaterials() {
    return this.clothingSystem.getAllMaterials();
  }

  getMeshNames() {
    return this.clothingSystem.getMeshNames();
  }

  toggleMeshVisibility(meshName, visible) {
    return this.clothingSystem.toggleMeshVisibility(meshName, visible);
  }

  restoreAllOriginalMaterials() {
    this.clothingSystem.restoreAllOriginalMaterials();
  }

  replaceMeshGeometry(meshName, newGeometry, preserveSkinning = true) {
    return this.clothingSystem.replaceMeshGeometry(meshName, newGeometry, preserveSkinning);
  }

  registerClothingItem(itemName, meshOrUrl, options = {}) {
    return this.clothingSystem.registerClothingItem(itemName, meshOrUrl, options);
  }

  equipClothing(itemName, slotName = 'default') {
    return this.clothingSystem.equipClothing(itemName, slotName);
  }

  unequipClothing(slotName) {
    return this.clothingSystem.unequipClothing(slotName);
  }

  setExpressionSmoothness(expressionName, smoothness) {
    this.expressionSystem.setExpressionSmoothness(expressionName, smoothness);
  }

  setGlobalExpressionSmoothness(smoothness) {
    this.expressionSystem.setGlobalSmoothness(smoothness);
  }

  forceResetExpressions() {
    this.expressionSystem.forceResetAllExpressions();
  }

  resetAllExpressions() {
    this.expressionSystem.resetAllExpressions();
  }

  getBoneByName(boneName) {
    return this.vrmLoader.getBoneByName(boneName);
  }

  getSkeletonByMesh(meshName) {
    return this.vrmLoader.getSkeletonByMesh(meshName);
  }

  getAllBones() {
    return this.vrmLoader.getAllBones();
  }

  getMotionCapture() {
    return this.motionCapture;
  }

  getBackgroundSystem() {
    return this.backgroundSystem;
  }

  getVideoRecorder() {
    return this.videoRecorder;
  }

  getExpressionSystem() {
    return this.expressionSystem;
  }

  getClothingSystem() {
    return this.clothingSystem;
  }

  dispose() {
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
      this.animationId = null;
    }
    
    if (this.vrmLoader) {
      this.vrmLoader.dispose();
    }
    
    if (this.followCamera) {
      this.followCamera.dispose();
    }
    
    if (this.motionCapture) {
      this.motionCapture.dispose();
    }
    
    if (this.backgroundSystem) {
      this.backgroundSystem.dispose();
    }
    
    if (this.videoRecorder) {
      this.videoRecorder.dispose();
    }
    
    if (this.renderer) {
      this.renderer.dispose();
      if (this.renderer.domElement && this.renderer.domElement.parentNode) {
        this.renderer.domElement.parentNode.removeChild(this.renderer.domElement);
      }
    }
  }
}

export default VTuberDressUpApp;
export { VTuberDressUpApp };

window.VTuberDressUpApp = VTuberDressUpApp;

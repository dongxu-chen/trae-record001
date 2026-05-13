import * as THREE from 'three';

const VIDEO_WIDTH = 640;
const VIDEO_HEIGHT = 480;
const VIDEO_FPS = 30;

export class MotionCapture {
  constructor(expressionSystem = null) {
    this.expressionSystem = expressionSystem;
    
    this.videoElement = null;
    this.canvasElement = null;
    this.canvasContext = null;
    this.stream = null;
    
    this.faceMesh = null;
    this.camera = null;
    this.isRunning = false;
    this.isInitialized = false;
    
    this.onLandmarksUpdate = null;
    this.onFaceDetected = null;
    this.onError = null;
    
    this.currentLandmarks = null;
    this.smoothedHeadRotation = { x: 0, y: 0, z: 0 };
    this.headRotationSmoothness = 8.0;
    
    this.rotationMultiplier = { x: 2.0, y: 2.0, z: 1.0 };
    this.rotationOffset = { x: 0, y: 0, z: 0 };
    
    this.calibrated = false;
    this.calibrationRotation = { x: 0, y: 0, z: 0 };
    
    this.targetHeadRotation = { x: 0, y: 0, z: 0 };
  }

  async init(options = {}) {
    if (this.isInitialized) return true;
    
    this.videoElement = document.createElement('video');
    this.videoElement.autoplay = true;
    this.videoElement.playsInline = true;
    this.videoElement.muted = true;
    this.videoElement.width = VIDEO_WIDTH;
    this.videoElement.height = VIDEO_HEIGHT;
    this.videoElement.style.display = 'none';
    
    this.canvasElement = document.createElement('canvas');
    this.canvasElement.width = VIDEO_WIDTH;
    this.canvasElement.height = VIDEO_HEIGHT;
    this.canvasElement.style.display = 'none';
    this.canvasContext = this.canvasElement.getContext('2d');
    
    document.body.appendChild(this.videoElement);
    document.body.appendChild(this.canvasElement);
    
    try {
      await this._loadMediaPipe();
      this.isInitialized = true;
      return true;
    } catch (error) {
      console.error('Failed to initialize MotionCapture:', error);
      if (this.onError) this.onError(error);
      return false;
    }
  }

  async _loadMediaPipe() {
    const { FaceMesh } = await import('@mediapipe/face_mesh');
    const { Camera } = await import('@mediapipe/camera_utils');
    
    this.faceMesh = new FaceMesh({
      locateFile: (file) => {
        return `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`;
      }
    });
    
    this.faceMesh.setOptions({
      maxNumFaces: 1,
      refineLandmarks: true,
      minDetectionConfidence: 0.5,
      minTrackingConfidence: 0.5
    });
    
    this.faceMesh.onResults((results) => this._onResults(results));
  }

  async start(useFrontCamera = true) {
    if (!this.isInitialized) {
      const success = await this.init();
      if (!success) return false;
    }
    
    if (this.isRunning) return true;
    
    try {
      const constraints = {
        video: {
          width: VIDEO_WIDTH,
          height: VIDEO_HEIGHT,
          facingMode: useFrontCamera ? 'user' : 'environment',
          frameRate: VIDEO_FPS
        },
        audio: false
      };
      
      this.stream = await navigator.mediaDevices.getUserMedia(constraints);
      this.videoElement.srcObject = this.stream;
      
      await this.videoElement.play();
      
      const { Camera } = await import('@mediapipe/camera_utils');
      this.camera = new Camera(this.videoElement, {
        onFrame: async () => {
          if (this.faceMesh) {
            await this.faceMesh.send({ image: this.videoElement });
          }
        },
        width: VIDEO_WIDTH,
        height: VIDEO_HEIGHT
      });
      
      await this.camera.start();
      this.isRunning = true;
      
      return true;
    } catch (error) {
      console.error('Failed to start camera:', error);
      if (this.onError) this.onError(error);
      return false;
    }
  }

  stop() {
    this.isRunning = false;
    
    if (this.camera) {
      this.camera.stop();
      this.camera = null;
    }
    
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    
    if (this.videoElement) {
      this.videoElement.pause();
      this.videoElement.srcObject = null;
    }
  }

  setExpressionSystem(expressionSystem) {
    this.expressionSystem = expressionSystem;
  }

  _onResults(results) {
    if (!results.multiFaceLandmarks || results.multiFaceLandmarks.length === 0) {
      this.currentLandmarks = null;
      if (this.onFaceDetected) this.onFaceDetected(false);
      return;
    }
    
    const landmarks = results.multiFaceLandmarks[0];
    this.currentLandmarks = landmarks;
    
    if (this.onFaceDetected) this.onFaceDetected(true);
    
    const headRotation = this._calculateHeadRotation(landmarks);
    this.targetHeadRotation = {
      x: (headRotation.x - this.calibrationRotation.x) * this.rotationMultiplier.x,
      y: (headRotation.y - this.calibrationRotation.y) * this.rotationMultiplier.y,
      z: (headRotation.z - this.calibrationRotation.z) * this.rotationMultiplier.z
    };
    
    if (this.expressionSystem) {
      this.expressionSystem.updateFaceLandmarks(
        landmarks,
        VIDEO_WIDTH,
        VIDEO_HEIGHT
      );
    }
    
    if (this.onLandmarksUpdate) {
      this.onLandmarksUpdate(landmarks, this.targetHeadRotation);
    }
  }

  _calculateHeadRotation(landmarks) {
    if (!landmarks || landmarks.length < 468) {
      return { x: 0, y: 0, z: 0 };
    }
    
    const noseTip = landmarks[1];
    const faceLeft = landmarks[234];
    const faceRight = landmarks[454];
    const faceTop = landmarks[10];
    const faceBottom = landmarks[152];
    
    const centerX = (faceLeft.x + faceRight.x) / 2;
    const centerY = (faceTop.y + faceBottom.y) / 2;
    
    const yaw = (noseTip.x - centerX) * 2;
    const pitch = (centerY - noseTip.y) * 2;
    
    const cheekL = landmarks[234];
    const cheekR = landmarks[454];
    const roll = Math.atan2(cheekR.y - cheekL.y, cheekR.x - cheekL.x);
    
    return {
      x: THREE.MathUtils.clamp(pitch, -0.5, 0.5),
      y: THREE.MathUtils.clamp(yaw, -0.5, 0.5),
      z: THREE.MathUtils.clamp(roll, -0.3, 0.3)
    };
  }

  update(deltaTime) {
    if (!this.currentLandmarks) return;
    
    const lerpFactor = 1 - Math.exp(-this.headRotationSmoothness * deltaTime);
    
    this.smoothedHeadRotation.x = THREE.MathUtils.lerp(
      this.smoothedHeadRotation.x,
      this.targetHeadRotation.x,
      lerpFactor
    );
    this.smoothedHeadRotation.y = THREE.MathUtils.lerp(
      this.smoothedHeadRotation.y,
      this.targetHeadRotation.y,
      lerpFactor
    );
    this.smoothedHeadRotation.z = THREE.MathUtils.lerp(
      this.smoothedHeadRotation.z,
      this.targetHeadRotation.z,
      lerpFactor
    );
  }

  calibrate() {
    if (!this.currentLandmarks) {
      console.warn('Cannot calibrate: no face detected');
      return false;
    }
    
    this.calibrationRotation = this._calculateHeadRotation(this.currentLandmarks);
    this.calibrated = true;
    return true;
  }

  resetCalibration() {
    this.calibrated = false;
    this.calibrationRotation = { x: 0, y: 0, z: 0 };
  }

  getSmoothedHeadRotation() {
    return { ...this.smoothedHeadRotation };
  }

  getTargetHeadRotation() {
    return { ...this.targetHeadRotation };
  }

  setRotationMultiplier(x, y, z) {
    if (x !== undefined) this.rotationMultiplier.x = x;
    if (y !== undefined) this.rotationMultiplier.y = y;
    if (z !== undefined) this.rotationMultiplier.z = z;
  }

  setRotationSmoothness(smoothness) {
    this.headRotationSmoothness = Math.max(0.1, smoothness);
  }

  isActive() {
    return this.isRunning;
  }

  getVideoElement() {
    return this.videoElement;
  }

  getCanvasElement() {
    return this.canvasElement;
  }

  drawDebugOverlay(context, width, height, drawPoints = true, drawMesh = false) {
    if (!this.currentLandmarks) return;
    
    context.save();
    context.clearRect(0, 0, width, height);
    
    if (drawMesh) {
      this._drawFaceMesh(context, width, height);
    }
    
    if (drawPoints) {
      this._drawKeyPoints(context, width, height);
    }
    
    context.restore();
  }

  _drawFaceMesh(context, width, height) {
    if (!this.currentLandmarks) return;
    
    const connections = [
      [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109],
      [33, 246, 161, 160, 159, 158, 157, 173, 133, 155, 154, 153, 145, 144, 163, 7, 33],
      [362, 398, 384, 385, 386, 387, 388, 466, 263, 382, 381, 380, 374, 373, 390, 249, 362],
      [13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95, 78, 191, 80, 81, 82, 13]
    ];
    
    context.strokeStyle = 'rgba(0, 255, 0, 0.5)';
    context.lineWidth = 1;
    
    connections.forEach(line => {
      context.beginPath();
      for (let i = 0; i < line.length; i++) {
        const point = this.currentLandmarks[line[i]];
        const x = point.x * width;
        const y = point.y * height;
        if (i === 0) {
          context.moveTo(x, y);
        } else {
          context.lineTo(x, y);
        }
      }
      context.stroke();
    });
  }

  _drawKeyPoints(context, width, height) {
    const keyPoints = [1, 33, 263, 13, 14, 10, 152];
    const colors = ['#ff0000', '#00ff00', '#00ff00', '#ffff00', '#ffff00', '#00ffff', '#00ffff'];
    
    keyPoints.forEach((idx, i) => {
      if (!this.currentLandmarks[idx]) return;
      const point = this.currentLandmarks[idx];
      context.fillStyle = colors[i];
      context.beginPath();
      context.arc(point.x * width, point.y * height, 4, 0, Math.PI * 2);
      context.fill();
    });
  }

  dispose() {
    this.stop();
    
    if (this.faceMesh) {
      this.faceMesh.close();
      this.faceMesh = null;
    }
    
    if (this.videoElement && this.videoElement.parentNode) {
      this.videoElement.parentNode.removeChild(this.videoElement);
    }
    if (this.canvasElement && this.canvasElement.parentNode) {
      this.canvasElement.parentNode.removeChild(this.canvasElement);
    }
    
    this.isInitialized = false;
  }
}

export default MotionCapture;

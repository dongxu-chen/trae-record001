class AIBehaviorDetector {
  constructor(config = {}) {
    this.videoElement = null;
    this.canvasElement = null;
    this.canvasCtx = null;
    this.isRunning = false;
    this.detectionInterval = null;
    this.pose = null;
    this.faceMesh = null;
    this.modelsLoaded = false;
    
    this.onAlert = config.onAlert || (() => {});
    this.onDetectionUpdate = config.onDetectionUpdate || (() => {});
    
    this.detectionFrequency = config.detectionFrequency || 1000;
    this.alertCooldown = {};
    this.cooldownPeriod = config.cooldownPeriod || 5000;
    
    this.headPoseHistory = [];
    this.maxHistoryLength = 30;
    
    this.lastHeadPosition = null;
    this.headMovementThreshold = 50;
    
    this.phoneDetectionThreshold = config.phoneDetectionThreshold || 0.6;
    this.lookingDownThreshold = config.lookingDownThreshold || 0.5;
    this.lookingAsideThreshold = config.lookingAsideThreshold || 0.5;
  }

  async loadModels() {
    try {
      const poseModule = await import('@mediapipe/pose');
      const faceMeshModule = await import('@mediapipe/face_mesh');
      
      this.pose = new poseModule.Pose({
        locateFile: (file) => {
          return `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`;
        }
      });
      
      this.pose.setOptions({
        modelComplexity: 1,
        smoothLandmarks: true,
        enableSegmentation: false,
        smoothSegmentation: false,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
      });
      
      this.faceMesh = new faceMeshModule.FaceMesh({
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
      
      this.pose.onResults(this.handlePoseResults.bind(this));
      this.faceMesh.onResults(this.handleFaceMeshResults.bind(this));
      
      this.modelsLoaded = true;
      console.log('AI行为检测模型加载完成');
    } catch (error) {
      console.error('模型加载失败:', error);
      console.log('将使用基础检测方法作为替代');
      this.modelsLoaded = false;
    }
  }

  setVideoElement(videoElement) {
    this.videoElement = videoElement;
    
    this.canvasElement = document.createElement('canvas');
    this.canvasElement.style.display = 'none';
    document.body.appendChild(this.canvasElement);
    this.canvasCtx = this.canvasElement.getContext('2d');
  }

  start() {
    if (this.isRunning) return;
    if (!this.videoElement) {
      console.error('请先设置视频元素');
      return;
    }
    
    this.isRunning = true;
    console.log('AI行为检测已启动');
    
    this.detectionLoop();
  }

  stop() {
    this.isRunning = false;
    if (this.detectionInterval) {
      clearInterval(this.detectionInterval);
      this.detectionInterval = null;
    }
    console.log('AI行为检测已停止');
  }

  async detectionLoop() {
    if (!this.isRunning) return;
    
    try {
      if (this.modelsLoaded && this.videoElement.readyState >= 2) {
        await this.pose.send({ image: this.videoElement });
        await this.faceMesh.send({ image: this.videoElement });
      } else {
        this.basicDetection();
      }
    } catch (error) {
      console.error('检测过程出错:', error);
    }
    
    this.detectionInterval = setTimeout(
      () => this.detectionLoop(),
      this.detectionFrequency
    );
  }

  handlePoseResults(results) {
    if (!results.poseLandmarks) return;
    
    const landmarks = results.poseLandmarks;
    
    this.detectHeadPose(landmarks);
    this.detectPhoneUsage(landmarks);
    this.detectHeadMovement(landmarks);
    
    this.onDetectionUpdate({
      type: 'pose',
      landmarks: landmarks
    });
  }

  handleFaceMeshResults(results) {
    if (!results.multiFaceLandmarks || results.multiFaceLandmarks.length === 0) {
      return;
    }
    
    const faceLandmarks = results.multiFaceLandmarks[0];
    
    this.detectGazeDirection(faceLandmarks);
    this.detectMultipleFaces(results.multiFaceLandmarks);
    
    this.onDetectionUpdate({
      type: 'face',
      landmarks: faceLandmarks
    });
  }

  detectHeadPose(landmarks) {
    const nose = landmarks[0];
    const leftEye = landmarks[2];
    const rightEye = landmarks[5];
    const leftShoulder = landmarks[11];
    const rightShoulder = landmarks[12];
    
    if (!nose || !leftEye || !rightEye || !leftShoulder || !rightShoulder) return;
    
    const eyeLevel = (leftEye.y + rightEye.y) / 2;
    const shoulderLevel = (leftShoulder.y + rightShoulder.y) / 2;
    const noseToEyeRatio = (nose.y - eyeLevel) / (shoulderLevel - eyeLevel);
    
    if (noseToEyeRatio > this.lookingDownThreshold) {
      this.triggerAlert(
        'head-down',
        '检测到低头行为',
        'danger',
        { noseToEyeRatio, threshold: this.lookingDownThreshold }
      );
    }
    
    const eyeXDiff = rightEye.x - leftEye.x;
    const noseXDiff = nose.x - (leftEye.x + rightEye.x) / 2;
    const headTurnRatio = Math.abs(noseXDiff / eyeXDiff);
    
    if (headTurnRatio > this.lookingAsideThreshold) {
      this.triggerAlert(
        'looking-aside',
        '检测到左顾右盼（可能交头接耳）',
        'danger',
        { headTurnRatio, threshold: this.lookingAsideThreshold }
      );
    }
  }

  detectPhoneUsage(landmarks) {
    const leftWrist = landmarks[15];
    const rightWrist = landmarks[16];
    const nose = landmarks[0];
    
    if (!leftWrist || !rightWrist || !nose) return;
    
    const leftHandToFace = Math.sqrt(
      Math.pow(leftWrist.x - nose.x, 2) + Math.pow(leftWrist.y - nose.y, 2)
    );
    const rightHandToFace = Math.sqrt(
      Math.pow(rightWrist.x - nose.x, 2) + Math.pow(rightWrist.y - nose.y, 2)
    );
    
    if (leftHandToFace < this.phoneDetectionThreshold || 
        rightHandToFace < this.phoneDetectionThreshold) {
      this.triggerAlert(
        'phone-usage',
        '检测到手部靠近面部（可能使用手机）',
        'danger',
        { leftHandToFace, rightHandToFace, threshold: this.phoneDetectionThreshold }
      );
    }
  }

  detectHeadMovement(landmarks) {
    const nose = landmarks[0];
    if (!nose) return;
    
    if (this.lastHeadPosition) {
      const movement = Math.sqrt(
        Math.pow(nose.x - this.lastHeadPosition.x, 2) + 
        Math.pow(nose.y - this.lastHeadPosition.y, 2)
      );
      
      this.headPoseHistory.push(movement);
      if (this.headPoseHistory.length > this.maxHistoryLength) {
        this.headPoseHistory.shift();
      }
      
      const avgMovement = this.headPoseHistory.reduce((a, b) => a + b, 0) / 
                          this.headPoseHistory.length;
      
      if (avgMovement > this.headMovementThreshold / 1000) {
        this.triggerAlert(
          'excessive-movement',
          '检测到频繁头部移动',
          'warning',
          { avgMovement, threshold: this.headMovementThreshold / 1000 }
        );
      }
    }
    
    this.lastHeadPosition = { x: nose.x, y: nose.y };
  }

  detectGazeDirection(faceLandmarks) {
    const leftEyeIris = faceLandmarks[468];
    const rightEyeIris = faceLandmarks[473];
    const leftEyeOuter = faceLandmarks[33];
    const rightEyeOuter = faceLandmarks[263];
    
    if (!leftEyeIris || !rightEyeIris || !leftEyeOuter || !rightEyeOuter) return;
    
    const leftGazeRatio = (leftEyeIris.x - leftEyeOuter.x) / (rightEyeOuter.x - leftEyeOuter.x);
    const rightGazeRatio = (rightEyeIris.x - leftEyeOuter.x) / (rightEyeOuter.x - leftEyeOuter.x);
    
    const gazeDirection = (leftGazeRatio + rightGazeRatio) / 2;
    
    if (gazeDirection < 0.3 || gazeDirection > 0.7) {
      this.triggerAlert(
        'abnormal-gaze',
        '检测到视线偏离屏幕',
        'warning',
        { gazeDirection }
      );
    }
  }

  detectMultipleFaces(faces) {
    if (faces.length > 1) {
      this.triggerAlert(
        'multiple-faces',
        `检测到多人画面（${faces.length}人），可能存在替考`,
        'danger',
        { faceCount: faces.length }
      );
    }
  }

  basicDetection() {
    if (!this.videoElement || !this.canvasCtx) return;
    
    this.canvasElement.width = this.videoElement.videoWidth;
    this.canvasElement.height = this.videoElement.videoHeight;
    
    this.canvasCtx.drawImage(
      this.videoElement,
      0, 0,
      this.canvasElement.width,
      this.canvasElement.height
    );
    
    const frame = this.canvasCtx.getImageData(
      0, 0,
      this.canvasElement.width,
      this.canvasElement.height
    );
    
    const brightness = this.calculateBrightness(frame);
    
    if (brightness < 30) {
      this.triggerAlert(
        'too-dark',
        '检测到环境光线过暗',
        'warning',
        { brightness }
      );
    }
  }

  calculateBrightness(imageData) {
    const data = imageData.data;
    let totalBrightness = 0;
    const step = Math.max(1, Math.floor(data.length / 1000));
    
    for (let i = 0; i < data.length; i += step * 4) {
      const r = data[i];
      const g = data[i + 1];
      const b = data[i + 2];
      totalBrightness += (r + g + b) / 3;
    }
    
    return totalBrightness / (data.length / (step * 4));
  }

  triggerAlert(type, message, severity = 'warning', details = {}) {
    const now = Date.now();
    const lastAlert = this.alertCooldown[type] || 0;
    
    if (now - lastAlert >= this.cooldownPeriod) {
      this.alertCooldown[type] = now;
      
      this.onAlert({
        type,
        message,
        severity,
        timestamp: new Date().toISOString(),
        details
      });
    }
  }

  destroy() {
    this.stop();
    if (this.canvasElement && this.canvasElement.parentNode) {
      this.canvasElement.parentNode.removeChild(this.canvasElement);
    }
    this.headPoseHistory = [];
    this.lastHeadPosition = null;
  }
}

export default AIBehaviorDetector;

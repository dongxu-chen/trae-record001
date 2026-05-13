import * as THREE from 'three';

const FACE_MESH_LANDMARKS = {
  LEFT_EYE_TOP: 159,
  LEFT_EYE_BOTTOM: 145,
  LEFT_EYE_LEFT: 33,
  LEFT_EYE_RIGHT: 133,
  RIGHT_EYE_TOP: 386,
  RIGHT_EYE_BOTTOM: 374,
  RIGHT_EYE_LEFT: 362,
  RIGHT_EYE_RIGHT: 263,
  MOUTH_TOP: 13,
  MOUTH_BOTTOM: 14,
  MOUTH_LEFT: 61,
  MOUTH_RIGHT: 291,
  NOSE_TIP: 1,
  LEFT_EYEBROW_INNER: 285,
  LEFT_EYEBROW_OUTER: 300,
  RIGHT_EYEBROW_INNER: 65,
  RIGHT_EYEBROW_OUTER: 46,
  CHEEK_LEFT: 234,
  CHEEK_RIGHT: 454,
  FACE_TOP: 10,
  FACE_BOTTOM: 152,
  FACE_LEFT: 234,
  FACE_RIGHT: 454
};

export class ExpressionSystem {
  constructor(vrm = null) {
    this.vrm = vrm;
    
    this.blinkLeftActive = false;
    this.blinkRightActive = false;
    this.blinkTimer = 0;
    this.blinkIntervalMin = 2.0;
    this.blinkIntervalMax = 6.0;
    this.blinkDuration = 0.15;
    this.nextBlinkTime = this._getRandomBlinkInterval();
    
    this.mouthTimer = 0;
    this.mouthOpenness = 0;
    this.talking = false;
    this.mouthSpeed = 8.0;
    this.mouthAmplitude = 1.0;
    
    this.expressions = new Map();
    
    this.targetValues = new Map();
    this.currentValues = new Map();
    this.defaultSmoothness = 8.0;
    this.perExpressionSmoothness = new Map();
    
    this.faceTrackingEnabled = false;
    this.currentFaceLandmarks = null;
    this.smoothedFaceData = {
      leftEyeOpen: 1,
      rightEyeOpen: 1,
      mouthOpen: 0,
      mouthWidth: 0,
      eyebrowRaise: 0,
      headRotation: { x: 0, y: 0, z: 0 }
    };
    
    this.faceTrackingSmoothness = 10.0;
    this.eyeOpennessMultiplier = 1.2;
    this.mouthOpennessMultiplier = 1.0;
    
    this.faceDataHistory = [];
    this.historyLength = 5;
    
    if (this.vrm) {
      this._initialize();
    }
  }

  setVRM(vrm) {
    this.vrm = vrm;
    this._initialize();
  }

  _initialize() {
    if (!this.vrm?.expressionManager) return;
    
    const presetMap = this.vrm.expressionManager.expressionPresetMap;
    if (presetMap) {
      this.expressions.clear();
      for (const [name, expr] of presetMap) {
        this.expressions.set(name, expr);
        if (!this.targetValues.has(name)) {
          this.targetValues.set(name, 0);
        }
        if (!this.currentValues.has(name)) {
          this.currentValues.set(name, 0);
        }
      }
    }
  }

  _getRandomBlinkInterval() {
    return THREE.MathUtils.randFloat(this.blinkIntervalMin, this.blinkIntervalMax);
  }

  enableFaceTracking(enabled = true) {
    this.faceTrackingEnabled = enabled;
  }

  isFaceTrackingEnabled() {
    return this.faceTrackingEnabled;
  }

  setFaceTrackingSmoothness(smoothness) {
    this.faceTrackingSmoothness = Math.max(0.1, smoothness);
  }

  setEyeOpennessMultiplier(multiplier) {
    this.eyeOpennessMultiplier = Math.max(0.1, multiplier);
  }

  setMouthOpennessMultiplier(multiplier) {
    this.mouthOpennessMultiplier = Math.max(0.1, multiplier);
  }

  updateFaceLandmarks(landmarks, imageWidth = 640, imageHeight = 480) {
    if (!landmarks || !landmarks.length) return;
    
    this.faceDataHistory.push({
      landmarks: [...landmarks],
      timestamp: Date.now()
    });
    
    if (this.faceDataHistory.length > this.historyLength) {
      this.faceDataHistory.shift();
    }
    
    this.currentFaceLandmarks = landmarks;
  }

  _getDistance(p1, p2) {
    return Math.sqrt(
      Math.pow(p1.x - p2.x, 2) +
      Math.pow(p1.y - p2.y, 2) +
      Math.pow(p1.z - p2.z, 2)
    );
  }

  _getAverageLandmark(index) {
    if (this.faceDataHistory.length === 0) return null;
    
    let x = 0, y = 0, z = 0;
    for (const frame of this.faceDataHistory) {
      const lm = frame.landmarks[index];
      if (lm) {
        x += lm.x;
        y += lm.y;
        z += lm.z || 0;
      }
    }
    
    const count = this.faceDataHistory.length;
    return {
      x: x / count,
      y: y / count,
      z: z / count
    };
  }

  _calculateEyeOpenness(topIdx, bottomIdx, leftIdx, rightIdx) {
    const top = this._getAverageLandmark(topIdx);
    const bottom = this._getAverageLandmark(bottomIdx);
    const left = this._getAverageLandmark(leftIdx);
    const right = this._getAverageLandmark(rightIdx);
    
    if (!top || !bottom || !left || !right) return 0.5;
    
    const eyeHeight = this._getDistance(top, bottom);
    const eyeWidth = this._getDistance(left, right);
    
    if (eyeWidth === 0) return 0.5;
    
    const ratio = eyeHeight / eyeWidth;
    
    const openRatio = 0.3;
    const closedRatio = 0.05;
    
    let openness = (ratio - closedRatio) / (openRatio - closedRatio);
    openness = THREE.MathUtils.clamp(openness * this.eyeOpennessMultiplier, 0, 1);
    
    return openness;
  }

  _calculateMouthOpenness() {
    const top = this._getAverageLandmark(FACE_MESH_LANDMARKS.MOUTH_TOP);
    const bottom = this._getAverageLandmark(FACE_MESH_LANDMARKS.MOUTH_BOTTOM);
    const left = this._getAverageLandmark(FACE_MESH_LANDMARKS.MOUTH_LEFT);
    const right = this._getAverageLandmark(FACE_MESH_LANDMARKS.MOUTH_RIGHT);
    
    if (!top || !bottom || !left || !right) return 0;
    
    const mouthHeight = this._getDistance(top, bottom);
    const mouthWidth = this._getDistance(left, right);
    
    if (mouthWidth === 0) return 0;
    
    const ratio = mouthHeight / mouthWidth;
    
    let openness = ratio / 0.4;
    openness = THREE.MathUtils.clamp(openness * this.mouthOpennessMultiplier, 0, 1);
    
    return openness;
  }

  _calculateMouthWidth() {
    const left = this._getAverageLandmark(FACE_MESH_LANDMARKS.MOUTH_LEFT);
    const right = this._getAverageLandmark(FACE_MESH_LANDMARKS.MOUTH_RIGHT);
    const faceLeft = this._getAverageLandmark(FACE_MESH_LANDMARKS.FACE_LEFT);
    const faceRight = this._getAverageLandmark(FACE_MESH_LANDMARKS.FACE_RIGHT);
    
    if (!left || !right || !faceLeft || !faceRight) return 0;
    
    const mouthWidth = this._getDistance(left, right);
    const faceWidth = this._getDistance(faceLeft, faceRight);
    
    if (faceWidth === 0) return 0;
    
    const ratio = mouthWidth / faceWidth;
    const normalizedWidth = (ratio - 0.35) / 0.15;
    
    return THREE.MathUtils.clamp(normalizedWidth, -1, 1);
  }

  _calculateEyebrowRaise() {
    const browInnerL = this._getAverageLandmark(FACE_MESH_LANDMARKS.LEFT_EYEBROW_INNER);
    const browInnerR = this._getAverageLandmark(FACE_MESH_LANDMARKS.RIGHT_EYEBROW_INNER);
    const eyeL = this._getAverageLandmark(FACE_MESH_LANDMARKS.LEFT_EYE_TOP);
    const eyeR = this._getAverageLandmark(FACE_MESH_LANDMARKS.RIGHT_EYE_TOP);
    const faceTop = this._getAverageLandmark(FACE_MESH_LANDMARKS.FACE_TOP);
    const faceBottom = this._getAverageLandmark(FACE_MESH_LANDMARKS.FACE_BOTTOM);
    
    if (!browInnerL || !browInnerR || !eyeL || !eyeR || !faceTop || !faceBottom) return 0;
    
    const faceHeight = this._getDistance(faceTop, faceBottom);
    const browL = (browInnerL.y - eyeL.y) / faceHeight;
    const browR = (browInnerR.y - eyeR.y) / faceHeight;
    
    const avgBrow = (browL + browR) / 2;
    const normalizedRaise = (avgBrow + 0.1) / 0.1;
    
    return THREE.MathUtils.clamp(normalizedRaise, 0, 1);
  }

  _calculateHeadRotation() {
    const noseTip = this._getAverageLandmark(FACE_MESH_LANDMARKS.NOSE_TIP);
    const faceLeft = this._getAverageLandmark(FACE_MESH_LANDMARKS.FACE_LEFT);
    const faceRight = this._getAverageLandmark(FACE_MESH_LANDMARKS.FACE_RIGHT);
    const faceTop = this._getAverageLandmark(FACE_MESH_LANDMARKS.FACE_TOP);
    const faceBottom = this._getAverageLandmark(FACE_MESH_LANDMARKS.FACE_BOTTOM);
    
    if (!noseTip || !faceLeft || !faceRight || !faceTop || !faceBottom) {
      return { x: 0, y: 0, z: 0 };
    }
    
    const centerX = (faceLeft.x + faceRight.x) / 2;
    const centerY = (faceTop.y + faceBottom.y) / 2;
    
    const yaw = (noseTip.x - centerX) * 2;
    const pitch = (centerY - noseTip.y) * 2;
    
    const cheekL = this._getAverageLandmark(FACE_MESH_LANDMARKS.CHEEK_LEFT);
    const cheekR = this._getAverageLandmark(FACE_MESH_LANDMARKS.CHEEK_RIGHT);
    let roll = 0;
    if (cheekL && cheekR) {
      roll = Math.atan2(cheekR.y - cheekL.y, cheekR.x - cheekL.x);
    }
    
    return {
      x: THREE.MathUtils.clamp(pitch, -0.5, 0.5),
      y: THREE.MathUtils.clamp(yaw, -0.5, 0.5),
      z: THREE.MathUtils.clamp(roll, -0.3, 0.3)
    };
  }

  _updateFromFaceTracking(deltaTime) {
    if (!this.faceTrackingEnabled || !this.currentFaceLandmarks) {
      return null;
    }
    
    const leftEyeOpen = this._calculateEyeOpenness(
      FACE_MESH_LANDMARKS.LEFT_EYE_TOP,
      FACE_MESH_LANDMARKS.LEFT_EYE_BOTTOM,
      FACE_MESH_LANDMARKS.LEFT_EYE_LEFT,
      FACE_MESH_LANDMARKS.LEFT_EYE_RIGHT
    );
    
    const rightEyeOpen = this._calculateEyeOpenness(
      FACE_MESH_LANDMARKS.RIGHT_EYE_TOP,
      FACE_MESH_LANDMARKS.RIGHT_EYE_BOTTOM,
      FACE_MESH_LANDMARKS.RIGHT_EYE_LEFT,
      FACE_MESH_LANDMARKS.RIGHT_EYE_RIGHT
    );
    
    const mouthOpen = this._calculateMouthOpenness();
    const mouthWidth = this._calculateMouthWidth();
    const eyebrowRaise = this._calculateEyebrowRaise();
    const headRotation = this._calculateHeadRotation();
    
    const lerpFactor = 1 - Math.exp(-this.faceTrackingSmoothness * deltaTime);
    
    this.smoothedFaceData.leftEyeOpen = THREE.MathUtils.lerp(
      this.smoothedFaceData.leftEyeOpen,
      leftEyeOpen,
      lerpFactor
    );
    this.smoothedFaceData.rightEyeOpen = THREE.MathUtils.lerp(
      this.smoothedFaceData.rightEyeOpen,
      rightEyeOpen,
      lerpFactor
    );
    this.smoothedFaceData.mouthOpen = THREE.MathUtils.lerp(
      this.smoothedFaceData.mouthOpen,
      mouthOpen,
      lerpFactor
    );
    this.smoothedFaceData.mouthWidth = THREE.MathUtils.lerp(
      this.smoothedFaceData.mouthWidth,
      mouthWidth,
      lerpFactor
    );
    this.smoothedFaceData.eyebrowRaise = THREE.MathUtils.lerp(
      this.smoothedFaceData.eyebrowRaise,
      eyebrowRaise,
      lerpFactor
    );
    
    this.smoothedFaceData.headRotation.x = THREE.MathUtils.lerp(
      this.smoothedFaceData.headRotation.x,
      headRotation.x,
      lerpFactor
    );
    this.smoothedFaceData.headRotation.y = THREE.MathUtils.lerp(
      this.smoothedFaceData.headRotation.y,
      headRotation.y,
      lerpFactor
    );
    this.smoothedFaceData.headRotation.z = THREE.MathUtils.lerp(
      this.smoothedFaceData.headRotation.z,
      headRotation.z,
      lerpFactor
    );
    
    this._applyFaceTrackingToExpressions();
    
    return this.smoothedFaceData;
  }

  _applyFaceTrackingToExpressions() {
    const blinkLeft = 1 - this.smoothedFaceData.leftEyeOpen;
    const blinkRight = 1 - this.smoothedFaceData.rightEyeOpen;
    
    this.targetValues.set('blinkLeft', blinkLeft);
    this.targetValues.set('blinkRight', blinkRight);
    
    this.targetValues.set('aa', this.smoothedFaceData.mouthOpen);
    
    if (this.smoothedFaceData.mouthWidth > 0.2) {
      this.targetValues.set('happy', this.smoothedFaceData.mouthWidth);
    }
    
    if (this.smoothedFaceData.eyebrowRaise > 0.3) {
      this.targetValues.set('surprised', this.smoothedFaceData.eyebrowRaise);
    }
  }

  getSmoothedFaceData() {
    return { ...this.smoothedFaceData };
  }

  getHeadRotation() {
    return { ...this.smoothedFaceData.headRotation };
  }

  setExpression(name, value, smoothness = null) {
    if (!this.vrm?.expressionManager) return;
    
    const clampedValue = THREE.MathUtils.clamp(value, 0, 1);
    this.targetValues.set(name, clampedValue);
    
    if (smoothness !== null) {
      this.perExpressionSmoothness.set(name, Math.max(0.1, smoothness));
    }
  }

  getExpression(name) {
    if (!this.vrm?.expressionManager) return 0;
    
    return this.currentValues.get(name) ?? 0;
  }

  getTargetValue(name) {
    return this.targetValues.get(name) ?? 0;
  }

  setGlobalSmoothness(smoothness) {
    this.defaultSmoothness = Math.max(0.1, smoothness);
  }

  setExpressionSmoothness(name, smoothness) {
    this.perExpressionSmoothness.set(name, Math.max(0.1, smoothness));
  }

  resetAllExpressions() {
    if (!this.vrm?.expressionManager) return;
    
    this.targetValues.forEach((value, name) => {
      this.targetValues.set(name, 0);
    });
    
    this.vrm.expressionManager.resetValues();
  }

  forceResetAllExpressions() {
    if (!this.vrm?.expressionManager) return;
    
    this.targetValues.forEach((value, name) => {
      this.targetValues.set(name, 0);
      this.currentValues.set(name, 0);
      this.vrm.expressionManager.setValue(name, 0);
    });
    
    this.vrm.expressionManager.resetValues();
  }

  setBlinkEnabled(enabled) {
    this.blinkLeftActive = enabled;
    this.blinkRightActive = enabled;
    
    if (!enabled && !this.faceTrackingEnabled) {
      this.targetValues.set('blinkLeft', 0);
      this.targetValues.set('blinkRight', 0);
    }
  }

  setBlinkInterval(min, max) {
    this.blinkIntervalMin = Math.max(0.5, min);
    this.blinkIntervalMax = Math.max(this.blinkIntervalMin, max);
  }

  forceBlink() {
    this.blinkTimer = this.blinkDuration;
    this.nextBlinkTime = this._getRandomBlinkInterval();
    
    this.targetValues.set('blinkLeft', 1);
    this.targetValues.set('blinkRight', 1);
  }

  setTalking(talking) {
    this.talking = talking;
    if (!talking && !this.faceTrackingEnabled) {
      this.targetValues.set('aa', 0);
    }
  }

  setMouthAmplitude(amplitude) {
    this.mouthAmplitude = THREE.MathUtils.clamp(amplitude, 0, 1);
  }

  setMouthSpeed(speed) {
    this.mouthSpeed = Math.max(0.1, speed);
  }

  _updateBlink(deltaTime) {
    if (!this.vrm?.expressionManager) return;
    if (this.faceTrackingEnabled) return;
    
    this.blinkTimer -= deltaTime;
    
    if (this.blinkTimer <= 0) {
      this.nextBlinkTime -= deltaTime;
      
      if (this.nextBlinkTime <= 0) {
        this.blinkTimer = this.blinkDuration;
        this.nextBlinkTime = this._getRandomBlinkInterval();
        
        if (this.blinkLeftActive) {
          this.targetValues.set('blinkLeft', 1);
        }
        if (this.blinkRightActive) {
          this.targetValues.set('blinkRight', 1);
        }
      }
    }
    
    if (this.blinkTimer > 0 && this.blinkTimer < this.blinkDuration * 0.5) {
      const t = (this.blinkDuration * 0.5 - this.blinkTimer) / (this.blinkDuration * 0.5);
      const fadeOut = 1 - t;
      
      if (this.blinkLeftActive) {
        this.targetValues.set('blinkLeft', fadeOut);
      }
      if (this.blinkRightActive) {
        this.targetValues.set('blinkRight', fadeOut);
      }
    }
  }

  _updateMouth(deltaTime) {
    if (!this.vrm?.expressionManager || !this.talking) return;
    if (this.faceTrackingEnabled) return;
    
    this.mouthTimer += deltaTime * this.mouthSpeed;
    
    let targetOpenness = (Math.sin(this.mouthTimer) + 1) / 2 * this.mouthAmplitude;
    targetOpenness = Math.max(0, targetOpenness - 0.3) / 0.7;
    targetOpenness = THREE.MathUtils.clamp(targetOpenness, 0, 1);
    
    this.targetValues.set('aa', targetOpenness);
  }

  _updateSmoothValues(deltaTime) {
    if (!this.vrm?.expressionManager) return;
    
    this.targetValues.forEach((target, name) => {
      const current = this.currentValues.get(name) ?? 0;
      
      if (Math.abs(target - current) < 0.001) {
        this.currentValues.set(name, target);
        this.vrm.expressionManager.setValue(name, target);
        return;
      }
      
      const smoothness = this.perExpressionSmoothness.get(name) ?? this.defaultSmoothness;
      const lerpFactor = 1 - Math.exp(-smoothness * deltaTime);
      
      const newValue = THREE.MathUtils.lerp(current, target, lerpFactor);
      const clampedNewValue = THREE.MathUtils.clamp(newValue, 0, 1);
      
      this.currentValues.set(name, clampedNewValue);
      this.vrm.expressionManager.setValue(name, clampedNewValue);
    });
  }

  update(deltaTime) {
    const safeDeltaTime = Math.min(deltaTime, 0.1);
    
    this._updateFromFaceTracking(safeDeltaTime);
    
    if (!this.faceTrackingEnabled) {
      this._updateBlink(safeDeltaTime);
      this._updateMouth(safeDeltaTime);
    }
    
    this._updateSmoothValues(safeDeltaTime);
    
    if (this.vrm?.expressionManager) {
      this.vrm.expressionManager.update();
    }
  }

  setHappy(value, smoothness = null) {
    this.setExpression('happy', THREE.MathUtils.clamp(value, 0, 1), smoothness);
  }

  setAngry(value, smoothness = null) {
    this.setExpression('angry', THREE.MathUtils.clamp(value, 0, 1), smoothness);
  }

  setSad(value, smoothness = null) {
    this.setExpression('sad', THREE.MathUtils.clamp(value, 0, 1), smoothness);
  }

  setSurprised(value, smoothness = null) {
    this.setExpression('surprised', THREE.MathUtils.clamp(value, 0, 1), smoothness);
  }

  setJoy(value, smoothness = null) {
    this.setExpression('joy', THREE.MathUtils.clamp(value, 0, 1), smoothness);
  }

  setFun(value, smoothness = null) {
    this.setExpression('fun', THREE.MathUtils.clamp(value, 0, 1), smoothness);
  }

  setA(value, smoothness = null) {
    this.setExpression('aa', THREE.MathUtils.clamp(value, 0, 1), smoothness);
  }

  setI(value, smoothness = null) {
    this.setExpression('ih', THREE.MathUtils.clamp(value, 0, 1), smoothness);
  }

  setU(value, smoothness = null) {
    this.setExpression('ou', THREE.MathUtils.clamp(value, 0, 1), smoothness);
  }

  setE(value, smoothness = null) {
    this.setExpression('ee', THREE.MathUtils.clamp(value, 0, 1), smoothness);
  }

  setO(value, smoothness = null) {
    this.setExpression('oh', THREE.MathUtils.clamp(value, 0, 1), smoothness);
  }

  setBlinkLeft(value, smoothness = null) {
    this.setExpression('blinkLeft', THREE.MathUtils.clamp(value, 0, 1), smoothness);
  }

  setBlinkRight(value, smoothness = null) {
    this.setExpression('blinkRight', THREE.MathUtils.clamp(value, 0, 1), smoothness);
  }
}

export default ExpressionSystem;

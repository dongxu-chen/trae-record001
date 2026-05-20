import * as faceapi from 'face-api.js';

class FaceVerification {
  constructor(config = {}) {
    this.modelsLoaded = false;
    this.referenceDescriptors = [];
    this.isVerified = false;
    
    this.similarityThreshold = config.similarityThreshold || 0.6;
    this.verificationInterval = config.verificationInterval || 3000;
    this.minReferenceSamples = config.minReferenceSamples || 3;
    this.maxReferenceSamples = config.maxReferenceSamples || 5;
    this.modelUrl = config.modelUrl || '/models';
    
    this.verificationTimer = null;
    this.onAlert = config.onAlert || (() => {});
    this.onVerificationUpdate = config.onVerificationUpdate || (() => {});
  }

  async loadModels() {
    if (this.modelsLoaded) return;

    try {
      await Promise.all([
        faceapi.nets.ssdMobilenetv1.loadFromUri(this.modelUrl),
        faceapi.nets.faceLandmark68Net.loadFromUri(this.modelUrl),
        faceapi.nets.faceRecognitionNet.loadFromUri(this.modelUrl)
      ]);
      
      this.modelsLoaded = true;
      console.log('FaceNet模型加载完成');
    } catch (error) {
      console.error('模型加载失败:', error);
      throw error;
    }
  }

  async detectFace(videoElement) {
    if (!this.modelsLoaded) {
      throw new Error('模型未加载');
    }

    const detection = await faceapi
      .detectSingleFace(videoElement, new faceapi.SsdMobilenetv1Options({
        minConfidence: 0.5
      }))
      .withFaceLandmarks()
      .withFaceDescriptor();

    return detection;
  }

  async captureReference(videoElement) {
    const detection = await this.detectFace(videoElement);
    
    if (!detection) {
      throw new Error('未检测到人脸');
    }

    if (this.referenceDescriptors.length < this.maxReferenceSamples) {
      this.referenceDescriptors.push(detection.descriptor);
    }

    return {
      success: true,
      samplesCaptured: this.referenceDescriptors.length,
      samplesRequired: this.minReferenceSamples
    };
  }

  isReadyForVerification() {
    return this.referenceDescriptors.length >= this.minReferenceSamples;
  }

  calculateSimilarity(descriptor1, descriptor2) {
    const distance = faceapi.euclideanDistance(descriptor1, descriptor2);
    const similarity = 1 - distance;
    return {
      distance,
      similarity,
      isMatch: distance <= this.similarityThreshold
    };
  }

  async verifyFace(videoElement) {
    if (!this.isReadyForVerification()) {
      return {
        success: false,
        message: '参考样本不足，请先采集更多人脸样本'
      };
    }

    const detection = await this.detectFace(videoElement);

    if (!detection) {
      return {
        success: false,
        verified: false,
        message: '未检测到人脸',
        type: 'no-face'
      };
    }

    const results = this.referenceDescriptors.map(refDesc =>
      this.calculateSimilarity(refDesc, detection.descriptor)
    );

    const bestMatch = results.reduce((best, current) =>
      current.similarity > best.similarity ? current : best
    );

    const avgSimilarity = results.reduce((sum, r) => sum + r.similarity, 0) / results.length;

    const isVerified = results.some(r => r.isMatch);

    return {
      success: true,
      verified: isVerified,
      similarity: avgSimilarity,
      bestSimilarity: bestMatch.similarity,
      distance: bestMatch.distance,
      threshold: this.similarityThreshold,
      samplesCompared: this.referenceDescriptors.length,
      type: isVerified ? 'success' : 'mismatch'
    };
  }

  startContinuousVerification(videoElement) {
    if (this.verificationTimer) {
      this.stopContinuousVerification();
    }

    this.verificationTimer = setInterval(async () => {
      try {
        const result = await this.verifyFace(videoElement);
        
        this.onVerificationUpdate(result);

        if (!result.verified && result.type === 'mismatch') {
          this.onAlert({
            type: 'face-mismatch',
            severity: 'high',
            message: `人脸验证失败，相似度: ${(result.similarity * 100).toFixed(1)}%`,
            timestamp: new Date().toISOString(),
            details: result
          });
        } else if (!result.verified && result.type === 'no-face') {
          this.onAlert({
            type: 'no-face',
            severity: 'medium',
            message: '未检测到人脸',
            timestamp: new Date().toISOString(),
            details: result
          });
        }
      } catch (error) {
        console.error('人脸验证出错:', error);
      }
    }, this.verificationInterval);
  }

  stopContinuousVerification() {
    if (this.verificationTimer) {
      clearInterval(this.verificationTimer);
      this.verificationTimer = null;
    }
  }

  setSimilarityThreshold(threshold) {
    this.similarityThreshold = Math.max(0, Math.min(1, threshold));
  }

  getSimilarityThreshold() {
    return this.similarityThreshold;
  }

  resetReference() {
    this.referenceDescriptors = [];
    this.isVerified = false;
  }

  destroy() {
    this.stopContinuousVerification();
    this.resetReference();
  }
}

export default FaceVerification;

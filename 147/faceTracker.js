class ImagePreprocessor {
    constructor() {
        this.canvas = document.createElement('canvas');
        this.ctx = this.canvas.getContext('2d');
        this.processedCanvas = document.createElement('canvas');
        this.processedCtx = this.processedCanvas.getContext('2d');
    }

    setSize(width, height) {
        this.canvas.width = width;
        this.canvas.height = height;
        this.processedCanvas.width = width;
        this.processedCanvas.height = height;
    }

    normalizeImage(imageSource) {
        const width = this.canvas.width;
        const height = this.canvas.height;
        
        this.ctx.drawImage(imageSource, 0, 0, width, height);
        const imageData = this.ctx.getImageData(0, 0, width, height);
        const data = imageData.data;

        this.applyBrightnessNormalization(data, width, height);
        this.applyHistogramEqualization(data, width, height);
        this.applyContrastEnhancement(data, width, height);

        this.processedCtx.putImageData(imageData, 0, 0);
        return this.processedCanvas;
    }

    applyBrightnessNormalization(data, width, height) {
        let totalBrightness = 0;
        const pixelCount = width * height;
        
        for (let i = 0; i < data.length; i += 4) {
            const brightness = (data[i] + data[i + 1] + data[i + 2]) / 3;
            totalBrightness += brightness;
        }
        
        const avgBrightness = totalBrightness / pixelCount;
        const targetBrightness = 128;
        const brightnessAdjust = targetBrightness - avgBrightness;
        
        for (let i = 0; i < data.length; i += 4) {
            data[i] = Math.min(255, Math.max(0, data[i] + brightnessAdjust));
            data[i + 1] = Math.min(255, Math.max(0, data[i + 1] + brightnessAdjust));
            data[i + 2] = Math.min(255, Math.max(0, data[i + 2] + brightnessAdjust));
        }
    }

    applyHistogramEqualization(data, width, height) {
        const histogram = new Array(256).fill(0);
        const pixelCount = width * height;
        
        for (let i = 0; i < data.length; i += 4) {
            const luminance = Math.round(
                0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2]
            );
            histogram[luminance]++;
        }
        
        const cdf = new Array(256).fill(0);
        cdf[0] = histogram[0];
        for (let i = 1; i < 256; i++) {
            cdf[i] = cdf[i - 1] + histogram[i];
        }
        
        const cdfMin = cdf.find(val => val > 0);
        const cdfRange = pixelCount - cdfMin;
        
        const lut = new Array(256).fill(0);
        for (let i = 0; i < 256; i++) {
            lut[i] = Math.round(((cdf[i] - cdfMin) / cdfRange) * 255);
        }
        
        for (let i = 0; i < data.length; i += 4) {
            const luminance = Math.round(
                0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2]
            );
            const newLuminance = lut[luminance];
            const ratio = luminance > 0 ? newLuminance / luminance : 1;
            
            data[i] = Math.min(255, Math.max(0, data[i] * ratio));
            data[i + 1] = Math.min(255, Math.max(0, data[i + 1] * ratio));
            data[i + 2] = Math.min(255, Math.max(0, data[i + 2] * ratio));
        }
    }

    applyContrastEnhancement(data, width, height) {
        const contrast = 1.3;
        const intercept = 128 * (1 - contrast);
        
        for (let i = 0; i < data.length; i += 4) {
            data[i] = Math.min(255, Math.max(0, data[i] * contrast + intercept));
            data[i + 1] = Math.min(255, Math.max(0, data[i + 1] * contrast + intercept));
            data[i + 2] = Math.min(255, Math.max(0, data[i + 2] * contrast + intercept));
        }
    }
}

class ARKitBlendShapeMapper {
    constructor() {
        this.ARKIT_BLENDSHAPES = {
            eyeBlinkLeft: 0,
            eyeBlinkRight: 0,
            eyeLookDownLeft: 0,
            eyeLookDownRight: 0,
            eyeLookInLeft: 0,
            eyeLookInRight: 0,
            eyeLookOutLeft: 0,
            eyeLookOutRight: 0,
            eyeLookUpLeft: 0,
            eyeLookUpRight: 0,
            eyeSquintLeft: 0,
            eyeSquintRight: 0,
            eyeWideLeft: 0,
            eyeWideRight: 0,
            jawForward: 0,
            jawLeft: 0,
            jawRight: 0,
            jawOpen: 0,
            mouthClose: 0,
            mouthFunnel: 0,
            mouthPucker: 0,
            mouthLeft: 0,
            mouthRight: 0,
            mouthSmileLeft: 0,
            mouthSmileRight: 0,
            mouthFrownLeft: 0,
            mouthFrownRight: 0,
            mouthDimpleLeft: 0,
            mouthDimpleRight: 0,
            mouthStretchLeft: 0,
            mouthStretchRight: 0,
            mouthRollLower: 0,
            mouthRollUpper: 0,
            mouthShrugLower: 0,
            mouthShrugUpper: 0,
            mouthPressLeft: 0,
            mouthPressRight: 0,
            mouthLowerDownLeft: 0,
            mouthLowerDownRight: 0,
            mouthUpperUpLeft: 0,
            mouthUpperUpRight: 0,
            browDownLeft: 0,
            browDownRight: 0,
            browInnerUp: 0,
            browOuterUpLeft: 0,
            browOuterUpRight: 0,
            cheekPuff: 0,
            cheekSquintLeft: 0,
            cheekSquintRight: 0,
            noseSneerLeft: 0,
            noseSneerRight: 0,
            tongueOut: 0
        };
        
        this.blendshapes = { ...this.ARKIT_BLENDSHAPES };
    }

    mapLandmarksToBlendshapes(landmarks) {
        if (!landmarks || landmarks.length === 0) return this.blendshapes;

        const lm = landmarks[0].keypoints;
        const normalized = this.normalizeLandmarks(lm);

        this.calculateEyeBlendshapes(normalized);
        this.calculateMouthBlendshapes(normalized);
        this.calculateBrowBlendshapes(normalized);
        this.calculateCheekBlendshapes(normalized);
        this.calculateJawBlendshapes(normalized);
        this.calculateNoseBlendshapes(normalized);

        return this.blendshapes;
    }

    normalizeLandmarks(lm) {
        const nose = lm[1];
        const faceWidth = this.distance(lm[234], lm[454]);
        const faceHeight = this.distance(lm[10], lm[152]);
        
        return lm.map(point => ({
            x: (point.x - nose.x) / faceWidth,
            y: (point.y - nose.y) / faceHeight,
            z: point.z / faceWidth
        }));
    }

    calculateEyeBlendshapes(lm) {
        const leftEyeTop = lm[159];
        const leftEyeBottom = lm[145];
        const leftEyeLeft = lm[33];
        const leftEyeRight = lm[133];
        const leftPupil = lm[468];
        
        const rightEyeTop = lm[386];
        const rightEyeBottom = lm[374];
        const rightEyeLeft = lm[362];
        const rightEyeRight = lm[263];
        const rightPupil = lm[473];

        const leftEyeOpen = this.distance(leftEyeTop, leftEyeBottom);
        const rightEyeOpen = this.distance(rightEyeTop, rightEyeBottom);
        const eyeHeightRef = this.distance(leftEyeLeft, leftEyeRight) * 0.4;

        this.blendshapes.eyeBlinkLeft = Math.max(0, Math.min(1, 1 - leftEyeOpen / eyeHeightRef));
        this.blendshapes.eyeBlinkRight = Math.max(0, Math.min(1, 1 - rightEyeOpen / eyeHeightRef));
        
        this.blendshapes.eyeWideLeft = Math.max(0, Math.min(1, (leftEyeOpen / eyeHeightRef - 1) * 2));
        this.blendshapes.eyeWideRight = Math.max(0, Math.min(1, (rightEyeOpen / eyeHeightRef - 1) * 2));

        this.blendshapes.eyeSquintLeft = Math.max(0, Math.min(1, (0.5 - leftEyeOpen / eyeHeightRef) * 2));
        this.blendshapes.eyeSquintRight = Math.max(0, Math.min(1, (0.5 - rightEyeOpen / eyeHeightRef) * 2));

        const leftEyeCenterY = (leftEyeTop.y + leftEyeBottom.y) / 2;
        const rightEyeCenterY = (rightEyeTop.y + rightEyeBottom.y) / 2;
        
        this.blendshapes.eyeLookUpLeft = Math.max(0, Math.min(1, (leftEyeCenterY - leftPupil.y) * 10));
        this.blendshapes.eyeLookUpRight = Math.max(0, Math.min(1, (rightEyeCenterY - rightPupil.y) * 10));
        this.blendshapes.eyeLookDownLeft = Math.max(0, Math.min(1, (leftPupil.y - leftEyeCenterY) * 10));
        this.blendshapes.eyeLookDownRight = Math.max(0, Math.min(1, (rightPupil.y - rightEyeCenterY) * 10));

        const leftEyeCenterX = (leftEyeLeft.x + leftEyeRight.x) / 2;
        const rightEyeCenterX = (rightEyeLeft.x + rightEyeRight.x) / 2;
        
        this.blendshapes.eyeLookInLeft = Math.max(0, Math.min(1, (leftPupil.x - leftEyeCenterX) * 10));
        this.blendshapes.eyeLookInRight = Math.max(0, Math.min(1, (rightEyeCenterX - rightPupil.x) * 10));
        this.blendshapes.eyeLookOutLeft = Math.max(0, Math.min(1, (leftEyeCenterX - leftPupil.x) * 10));
        this.blendshapes.eyeLookOutRight = Math.max(0, Math.min(1, (rightPupil.x - rightEyeCenterX) * 10));
    }

    calculateMouthBlendshapes(lm) {
        const mouthTop = lm[13];
        const mouthBottom = lm[14];
        const mouthLeft = lm[61];
        const mouthRight = lm[291];
        const upperLipTop = lm[12];
        const upperLipBottom = lm[11];
        const lowerLipTop = lm[15];
        const lowerLipBottom = lm[16];

        const mouthHeight = this.distance(mouthTop, mouthBottom);
        const mouthWidth = this.distance(mouthLeft, mouthRight);

        this.blendshapes.jawOpen = Math.max(0, Math.min(1, mouthHeight * 3));
        this.blendshapes.mouthClose = Math.max(0, Math.min(1, 1 - mouthHeight * 3));

        const lipCornerLeft = lm[61];
        const lipCornerRight = lm[291];
        const mouthCenterY = (mouthTop.y + mouthBottom.y) / 2;
        
        const smileLeft = Math.max(0, (mouthCenterY - lipCornerLeft.y) * 5);
        const smileRight = Math.max(0, (mouthCenterY - lipCornerRight.y) * 5);
        
        this.blendshapes.mouthSmileLeft = Math.min(1, smileLeft);
        this.blendshapes.mouthSmileRight = Math.min(1, smileRight);

        this.blendshapes.mouthFrownLeft = Math.max(0, Math.min(1, (lipCornerLeft.y - mouthCenterY) * 5));
        this.blendshapes.mouthFrownRight = Math.max(0, Math.min(1, (lipCornerRight.y - mouthCenterY) * 5));

        const lipThickness = this.distance(upperLipTop, lowerLipBottom);
        this.blendshapes.mouthFunnel = Math.max(0, Math.min(1, (lipThickness - mouthHeight) * 4));
        this.blendshapes.mouthPucker = Math.max(0, Math.min(1, (0.5 - mouthWidth) * 2));

        this.blendshapes.mouthLeft = Math.max(0, Math.min(1, (lipCornerLeft.x - lipCornerRight.x) * 2));
        this.blendshapes.mouthRight = Math.max(0, Math.min(1, (lipCornerRight.x - lipCornerLeft.x) * 2));

        const upperLipRaise = upperLipTop.y - lm[1].y;
        const lowerLipDrop = lowerLipBottom.y - lm[1].y;
        
        this.blendshapes.mouthUpperUpLeft = Math.max(0, Math.min(1, -upperLipRaise * 3));
        this.blendshapes.mouthUpperUpRight = Math.max(0, Math.min(1, -upperLipRaise * 3));
        this.blendshapes.mouthLowerDownLeft = Math.max(0, Math.min(1, lowerLipDrop * 2));
        this.blendshapes.mouthLowerDownRight = Math.max(0, Math.min(1, lowerLipDrop * 2));

        const lipPressDistance = this.distance(upperLipBottom, lowerLipTop);
        this.blendshapes.mouthPressLeft = Math.max(0, Math.min(1, 1 - lipPressDistance * 10));
        this.blendshapes.mouthPressRight = Math.max(0, Math.min(1, 1 - lipPressDistance * 10));

        this.blendshapes.mouthDimpleLeft = Math.max(0, Math.min(1, smileLeft * 0.5));
        this.blendshapes.mouthDimpleRight = Math.max(0, Math.min(1, smileRight * 0.5));

        this.blendshapes.mouthStretchLeft = Math.max(0, Math.min(1, mouthWidth * 0.8 - 0.3));
        this.blendshapes.mouthStretchRight = Math.max(0, Math.min(1, mouthWidth * 0.8 - 0.3));

        this.blendshapes.mouthRollUpper = Math.max(0, Math.min(1, -upperLipRaise * 2));
        this.blendshapes.mouthRollLower = Math.max(0, Math.min(1, lowerLipDrop * 1.5));

        this.blendshapes.mouthShrugUpper = Math.max(0, Math.min(1, -upperLipRaise * 2.5));
        this.blendshapes.mouthShrugLower = Math.max(0, Math.min(1, lowerLipDrop * 1.2));
    }

    calculateBrowBlendshapes(lm) {
        const browLeftInner = lm[285];
        const browRightInner = lm[55];
        const browLeftOuter = lm[300];
        const browRightOuter = lm[70];
        const noseBridge = lm[6];

        const browInnerHeight = (browLeftInner.y + browRightInner.y) / 2 - noseBridge.y;
        const browLeftOuterHeight = browLeftOuter.y - noseBridge.y;
        const browRightOuterHeight = browRightOuter.y - noseBridge.y;

        this.blendshapes.browInnerUp = Math.max(0, Math.min(1, -browInnerHeight * 4));
        this.blendshapes.browOuterUpLeft = Math.max(0, Math.min(1, -browLeftOuterHeight * 4));
        this.blendshapes.browOuterUpRight = Math.max(0, Math.min(1, -browRightOuterHeight * 4));

        this.blendshapes.browDownLeft = Math.max(0, Math.min(1, browLeftOuterHeight * 4));
        this.blendshapes.browDownRight = Math.max(0, Math.min(1, browRightOuterHeight * 4));
    }

    calculateCheekBlendshapes(lm) {
        const leftCheek = lm[454];
        const rightCheek = lm[234];
        const nose = lm[1];

        const leftCheekHeight = nose.y - leftCheek.y;
        const rightCheekHeight = nose.y - rightCheek.y;

        this.blendshapes.cheekPuff = Math.max(0, Math.min(1, (leftCheekHeight + rightCheekHeight) * 2));
        this.blendshapes.cheekSquintLeft = Math.max(0, Math.min(1, leftCheekHeight * 3));
        this.blendshapes.cheekSquintRight = Math.max(0, Math.min(1, rightCheekHeight * 3));
    }

    calculateJawBlendshapes(lm) {
        const jaw = lm[152];
        const chin = lm[152];
        const nose = lm[1];

        const jawForward = nose.z - chin.z;
        this.blendshapes.jawForward = Math.max(0, Math.min(1, jawForward * 2));

        const jawLeft = lm[152].x - lm[1].x;
        this.blendshapes.jawLeft = Math.max(0, Math.min(1, -jawLeft * 5));
        this.blendshapes.jawRight = Math.max(0, Math.min(1, jawLeft * 5));
    }

    calculateNoseBlendshapes(lm) {
        const noseLeft = lm[388];
        const noseRight = lm[148];
        const noseTip = lm[1];

        const leftSneer = noseTip.y - noseLeft.y;
        const rightSneer = noseTip.y - noseRight.y;

        this.blendshapes.noseSneerLeft = Math.max(0, Math.min(1, leftSneer * 4));
        this.blendshapes.noseSneerRight = Math.max(0, Math.min(1, rightSneer * 4));
    }

    distance(p1, p2) {
        return Math.sqrt(
            Math.pow(p1.x - p2.x, 2) +
            Math.pow(p1.y - p2.y, 2) +
            Math.pow((p1.z || 0) - (p2.z || 0), 2)
        );
    }

    getBlendshapes() {
        return this.blendshapes;
    }
}

class FaceTracker {
    constructor(videoId, canvasId) {
        this.video = document.getElementById(videoId);
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.model = null;
        this.isRunning = false;
        this.showLandmarks = true;
        this.onFaceData = null;
        this.onBlendshapes = null;
        
        this.preprocessor = new ImagePreprocessor();
        this.blendshapeMapper = new ARKitBlendShapeMapper();
        
        this.resize();
        window.addEventListener('resize', () => this.resize());
    }
    
    resize() {
        const rect = this.video.getBoundingClientRect();
        this.canvas.width = rect.width * window.devicePixelRatio;
        this.canvas.height = rect.height * window.devicePixelRatio;
        this.ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
        this.width = rect.width;
        this.height = rect.height;
        this.preprocessor.setSize(this.video.videoWidth || 640, this.video.videoHeight || 480);
    }
    
    async loadModel() {
        try {
            this.log('加载面部追踪模型...');
            const model = faceLandmarksDetection.SupportedModels.MediaPipeFaceMesh;
            const detectorConfig = {
                runtime: 'tfjs',
                refineLandmarks: true,
                maxFaces: 1
            };
            this.model = await faceLandmarksDetection.createDetector(model, detectorConfig);
            this.log('面部追踪模型加载完成');
            return true;
        } catch (error) {
            this.log('模型加载失败: ' + error.message);
            console.error(error);
            return false;
        }
    }
    
    async startCamera() {
        try {
            this.log('请求摄像头权限...');
            const stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: 640,
                    height: 480,
                    facingMode: 'user'
                }
            });
            
            this.video.srcObject = stream;
            await this.video.play();
            
            this.resize();
            this.preprocessor.setSize(this.video.videoWidth, this.video.videoHeight);
            this.isRunning = true;
            this.log('摄像头已开启');
            
            this.detectFace();
            
            return true;
        } catch (error) {
            this.log('摄像头开启失败: ' + error.message);
            console.error(error);
            return false;
        }
    }
    
    stopCamera() {
        this.isRunning = false;
        if (this.video.srcObject) {
            this.video.srcObject.getTracks().forEach(track => track.stop());
            this.video.srcObject = null;
        }
        this.ctx.clearRect(0, 0, this.width, this.height);
        this.log('摄像头已关闭');
    }
    
    async detectFace() {
        if (!this.isRunning || !this.model) return;
        
        try {
            const processedImage = this.preprocessor.normalizeImage(this.video);
            
            const faces = await this.model.estimateFaces(processedImage);
            
            if (faces.length > 0) {
                this.drawLandmarks(faces);
                
                const blendshapes = this.blendshapeMapper.mapLandmarksToBlendshapes(faces);
                
                if (this.onFaceData) {
                    this.onFaceData(faces, blendshapes);
                }
                
                if (this.onBlendshapes) {
                    this.onBlendshapes(blendshapes);
                }
            }
        } catch (error) {
            console.error('面部检测错误:', error);
        }
        
        if (this.isRunning) {
            requestAnimationFrame(() => this.detectFace());
        }
    }
    
    drawLandmarks(faces) {
        this.ctx.clearRect(0, 0, this.width, this.height);
        
        if (!this.showLandmarks || faces.length === 0) return;
        
        const scaleX = this.width / this.video.videoWidth;
        const scaleY = this.height / this.video.videoHeight;
        
        for (const face of faces) {
            const keypoints = face.keypoints;
            
            this.ctx.fillStyle = 'rgba(0, 255, 0, 0.5)';
            for (let i = 0; i < keypoints.length; i++) {
                const kp = keypoints[i];
                this.ctx.beginPath();
                this.ctx.arc(kp.x * scaleX, kp.y * scaleY, 1, 0, Math.PI * 2);
                this.ctx.fill();
            }
            
            this.drawFeature(keypoints, [159, 145, 153, 158], 'rgba(255, 0, 0, 0.8)', scaleX, scaleY);
            this.drawFeature(keypoints, [386, 374, 380, 385], 'rgba(255, 0, 0, 0.8)', scaleX, scaleY);
            
            this.drawFeature(keypoints, [13, 14, 61, 291], 'rgba(0, 0, 255, 0.8)', scaleX, scaleY);
        }
    }
    
    drawFeature(keypoints, indices, color, scaleX, scaleY) {
        this.ctx.fillStyle = color;
        for (const idx of indices) {
            const kp = keypoints[idx];
            this.ctx.beginPath();
            this.ctx.arc(kp.x * scaleX, kp.y * scaleY, 3, 0, Math.PI * 2);
            this.ctx.fill();
        }
    }
    
    setShowLandmarks(show) {
        this.showLandmarks = show;
    }
    
    log(message) {
        const debugInfo = document.getElementById('debugInfo');
        if (debugInfo) {
            const timestamp = new Date().toLocaleTimeString();
            debugInfo.textContent = `[${timestamp}] ${message}\n` + debugInfo.textContent;
        }
    }
}
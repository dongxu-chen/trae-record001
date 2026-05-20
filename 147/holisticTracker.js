class HolisticTracker {
    constructor(videoId, canvasId) {
        this.video = document.getElementById(videoId);
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.holistic = null;
        this.camera = null;
        this.isRunning = false;
        this.showSkeleton = true;
        this.trackingMode = 3;
        
        this.backend = 'webgpu';
        this.modelComplexity = 1;
        this.enableSmoothing = true;
        this.maxNumFaces = 1;
        
        this.onResults = null;
        this.onFaceResults = null;
        this.onPoseResults = null;
        this.onHandResults = null;
        
        this.frameCount = 0;
        this.lastFpsTime = 0;
        this.currentFps = 0;
        this.inferenceTime = 0;
        
        this.smoothingBuffers = {};
        this.smoothingFactor = 0.4;
        
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
    }
    
    async initialize() {
        try {
            this.log('初始化 MediaPipe Holistic...');
            this.log(`目标后端: ${this.backend.toUpperCase()}`);
            
            const holisticOptions = {
                locateFile: (file) => {
                    return `https://cdn.jsdelivr.net/npm/@mediapipe/holistic@0.5.1675469240/${file}`;
                }
            };
            
            this.holistic = new Holistic(holisticOptions);
            
            this.holistic.setOptions({
                modelComplexity: this.modelComplexity,
                smoothLandmarks: this.enableSmoothing,
                enableSegmentation: false,
                smoothSegmentation: false,
                refineFaceLandmarks: true,
                minDetectionConfidence: 0.5,
                minTrackingConfidence: 0.5
            });
            
            this.holistic.onResults((results) => this.handleResults(results));
            
            this.log('Holistic 模型初始化完成');
            return true;
        } catch (error) {
            this.log(`初始化失败: ${error.message}`);
            console.error(error);
            return false;
        }
    }
    
    async startCamera() {
        try {
            this.log('请求摄像头权限...');
            
            this.camera = new Camera(this.video, {
                onFrame: async () => {
                    const startTime = performance.now();
                    await this.holistic.send({ image: this.video });
                    this.inferenceTime = Math.round(performance.now() - startTime);
                    this.updateFps();
                },
                width: 1280,
                height: 720
            });
            
            await this.camera.start();
            this.isRunning = true;
            this.log('摄像头已启动，追踪开始');
            
            return true;
        } catch (error) {
            this.log(`摄像头启动失败: ${error.message}`);
            return false;
        }
    }
    
    stop() {
        if (this.camera) {
            this.camera.stop();
        }
        this.isRunning = false;
        this.ctx.clearRect(0, 0, this.width, this.height);
        this.log('追踪已停止');
    }
    
    handleResults(results) {
        this.ctx.save();
        this.ctx.clearRect(0, 0, this.width, this.height);
        this.ctx.drawImage(results.image, 0, 0, this.width, this.height);
        
        if (this.showSkeleton) {
            this.drawResults(results);
        }
        
        this.ctx.restore();
        
        const processedResults = this.processResults(results);
        
        if (this.onResults) {
            this.onResults(processedResults);
        }
        
        this.updateStatus(processedResults);
    }
    
    processResults(results) {
        const processed = {
            faceLandmarks: results.faceLandmarks || null,
            poseLandmarks: results.poseLandmarks || null,
            leftHandLandmarks: results.leftHandLandmarks || null,
            rightHandLandmarks: results.rightHandLandmarks || null,
            timestamp: performance.now()
        };
        
        if (this.enableSmoothing) {
            processed.smoothed = this.smoothLandmarks(processed);
        }
        
        return processed;
    }
    
    smoothLandmarks(results) {
        const smoothed = {};
        
        if (results.poseLandmarks) {
            smoothed.pose = this.smoothLandmarkArray(results.poseLandmarks, 'pose');
        }
        
        if (results.leftHandLandmarks) {
            smoothed.leftHand = this.smoothLandmarkArray(results.leftHandLandmarks, 'leftHand');
        }
        
        if (results.rightHandLandmarks) {
            smoothed.rightHand = this.smoothLandmarkArray(results.rightHandLandmarks, 'rightHand');
        }
        
        if (results.faceLandmarks) {
            smoothed.face = this.smoothLandmarkArray(results.faceLandmarks, 'face');
        }
        
        return smoothed;
    }
    
    smoothLandmarkArray(landmarks, bufferKey) {
        if (!this.smoothingBuffers[bufferKey]) {
            this.smoothingBuffers[bufferKey] = landmarks.map(lm => ({ ...lm }));
            return landmarks;
        }
        
        const buffer = this.smoothingBuffers[bufferKey];
        const result = [];
        
        for (let i = 0; i < landmarks.length; i++) {
            result.push({
                x: buffer[i].x * (1 - this.smoothingFactor) + landmarks[i].x * this.smoothingFactor,
                y: buffer[i].y * (1 - this.smoothingFactor) + landmarks[i].y * this.smoothingFactor,
                z: buffer[i].z * (1 - this.smoothingFactor) + landmarks[i].z * this.smoothingFactor,
                visibility: landmarks[i].visibility
            });
            buffer[i] = { ...result[i] };
        }
        
        return result;
    }
    
    drawResults(results) {
        if (results.faceLandmarks && this.trackingMode >= 1) {
            drawConnectors(this.ctx, results.faceLandmarks, FACEMESH_TESSELATION, {
                color: '#C0C0C070',
                lineWidth: 1
            });
        }
        
        if (results.poseLandmarks && this.trackingMode >= 2) {
            drawConnectors(this.ctx, results.poseLandmarks, POSE_CONNECTIONS, {
                color: '#00FF00',
                lineWidth: 4
            });
            drawLandmarks(this.ctx, results.poseLandmarks, {
                color: '#FF0000',
                lineWidth: 2,
                radius: 3
            });
        }
        
        if (results.leftHandLandmarks && this.trackingMode >= 3) {
            drawConnectors(this.ctx, results.leftHandLandmarks, HAND_CONNECTIONS, {
                color: '#CC0000',
                lineWidth: 5
            });
            drawLandmarks(this.ctx, results.leftHandLandmarks, {
                color: '#00FF00',
                lineWidth: 2,
                radius: 3
            });
        }
        
        if (results.rightHandLandmarks && this.trackingMode >= 3) {
            drawConnectors(this.ctx, results.rightHandLandmarks, HAND_CONNECTIONS, {
                color: '#00CC00',
                lineWidth: 5
            });
            drawLandmarks(this.ctx, results.rightHandLandmarks, {
                color: '#FF0000',
                lineWidth: 2,
                radius: 3
            });
        }
    }
    
    updateStatus(results) {
        document.getElementById('fpsValue').textContent = this.currentFps;
        document.getElementById('inferenceTime').textContent = this.inferenceTime;
        document.getElementById('backendType').textContent = this.backend.toUpperCase();
        
        document.getElementById('poseStatus').textContent = results.poseLandmarks ? '✓ 检测中' : '未检测';
        document.getElementById('handStatus').textContent = 
            (results.leftHandLandmarks || results.rightHandLandmarks) ? '✓ 检测中' : '未检测';
    }
    
    updateFps() {
        this.frameCount++;
        const now = performance.now();
        
        if (now - this.lastFpsTime >= 1000) {
            this.currentFps = this.frameCount;
            this.frameCount = 0;
            this.lastFpsTime = now;
        }
    }
    
    setTrackingMode(mode) {
        this.trackingMode = mode;
        const modeNames = ['', '仅面部', '面部+身体', '全身(含手)'];
        this.log(`切换追踪模式: ${modeNames[mode]}`);
    }
    
    setBackend(backend) {
        this.backend = backend;
        this.log(`设置计算后端: ${backend.toUpperCase()}`);
    }
    
    setModelComplexity(level) {
        this.modelComplexity = level;
        const levels = ['轻量', '中等', '完整'];
        this.log(`设置模型复杂度: ${levels[level]}`);
    }
    
    setSmoothing(enabled) {
        this.enableSmoothing = enabled;
        if (!enabled) {
            this.smoothingBuffers = {};
        }
        this.log(`动作平滑: ${enabled ? '启用' : '禁用'}`);
    }
    
    setShowSkeleton(show) {
        this.showSkeleton = show;
    }
    
    log(message) {
        const debugInfo = document.getElementById('debugInfo');
        if (debugInfo) {
            const timestamp = new Date().toLocaleTimeString();
            const newContent = `<div style="color: #00ff00">[${timestamp}] ${message}</div>` + debugInfo.innerHTML;
            debugInfo.innerHTML = newContent.substring(0, 5000);
        }
    }
}

const POSE_CONNECTIONS = [
    [11,12],[11,23],[12,24],[23,24],
    [23,25],[24,26],[25,27],[26,28],
    [27,29],[28,30],[29,31],[30,32],
    [27,31],[28,32],[11,13],[12,14],
    [13,15],[14,16],[15,17],[16,18],
    [15,19],[16,20],[15,21],[16,22],
    [17,19],[18,20],[9,10],[0,1],
    [1,2],[2,3],[3,7],[0,4],[4,5],
    [5,6],[6,8],[9,11],[10,12]
];

const HAND_CONNECTIONS = [
    [0,1],[1,2],[2,3],[3,4],
    [0,5],[5,6],[6,7],[7,8],
    [0,9],[9,10],[10,11],[11,12],
    [0,13],[13,14],[14,15],[15,16],
    [0,17],[17,18],[18,19],[19,20]
];

const FACEMESH_TESSELATION = [];
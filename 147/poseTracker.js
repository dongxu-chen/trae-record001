class PoseTracker {
    constructor(videoId, canvasId) {
        this.video = document.getElementById(videoId);
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.holistic = null;
        this.isRunning = false;
        this.showLandmarks = true;
        this.captureMode = 'face';
        
        this.onPoseData = null;
        this.onHolisticData = null;
        
        this.poseData = {
            poseLandmarks: null,
            leftHandLandmarks: null,
            rightHandLandmarks: null,
            faceLandmarks: null
        };
        
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
    
    async loadModel() {
        try {
            this.log('加载MediaPipe Holistic模型...');
            
            this.holistic = new Holistic({
                locateFile: (file) => {
                    return `https://cdn.jsdelivr.net/npm/@mediapipe/holistic@0.5.1675469240/${file}`;
                }
            });
            
            this.holistic.setOptions({
                modelComplexity: 1,
                smoothLandmarks: true,
                enableSegmentation: false,
                smoothSegmentation: true,
                refineFaceLandmarks: true,
                minDetectionConfidence: 0.5,
                minTrackingConfidence: 0.5
            });
            
            this.holistic.onResults((results) => this.onResults(results));
            
            this.log('MediaPipe Holistic模型加载完成');
            return true;
        } catch (error) {
            this.log('模型加载失败: ' + error.message);
            console.error(error);
            return false;
        }
    }
    
    setCaptureMode(mode) {
        this.captureMode = mode;
        this.log(`切换到${mode === 'face' ? '仅面部' : '全身动捕'}模式`);
    }
    
    async startCamera() {
        try {
            this.log('请求摄像头权限...');
            const stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: 640,
                    height: 480,
                    facingMode: 'user'
                },
                audio: false
            });
            
            this.video.srcObject = stream;
            await this.video.play();
            
            this.resize();
            this.isRunning = true;
            this.log('摄像头已开启');
            
            this.detectLoop();
            
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
    
    async detectLoop() {
        if (!this.isRunning) return;
        
        try {
            await this.holistic.send({image: this.video});
        } catch (error) {
            console.error('检测错误:', error);
        }
        
        requestAnimationFrame(() => this.detectLoop());
    }
    
    onResults(results) {
        this.ctx.clearRect(0, 0, this.width, this.height);
        
        if (!this.showLandmarks) return;
        
        this.ctx.save();
        this.ctx.scale(this.width / this.video.videoWidth, this.height / this.video.videoHeight);
        
        if (results.poseLandmarks && this.captureMode === 'holistic') {
            this.drawConnectors(results.poseLandmarks, POSE_CONNECTIONS, {color: '#00FF00', lineWidth: 4});
            this.drawLandmarks(results.poseLandmarks, {color: '#FF0000', lineWidth: 2});
        }
        
        if (results.faceLandmarks && this.captureMode === 'holistic') {
            this.drawConnectors(results.faceLandmarks, FACEMESH_TESSELATION, {color: '#C0C0C070', lineWidth: 1});
        }
        
        if (results.leftHandLandmarks && this.captureMode === 'holistic') {
            this.drawConnectors(results.leftHandLandmarks, HAND_CONNECTIONS, {color: '#CC0000', lineWidth: 5});
            this.drawLandmarks(results.leftHandLandmarks, {color: '#00FF00', lineWidth: 2});
        }
        
        if (results.rightHandLandmarks && this.captureMode === 'holistic') {
            this.drawConnectors(results.rightHandLandmarks, HAND_CONNECTIONS, {color: '#00CC00', lineWidth: 5});
            this.drawLandmarks(results.rightHandLandmarks, {color: '#FF0000', lineWidth: 2});
        }
        
        this.ctx.restore();
        
        this.poseData = {
            poseLandmarks: results.poseLandmarks,
            leftHandLandmarks: results.leftHandLandmarks,
            rightHandLandmarks: results.rightHandLandmarks,
            faceLandmarks: results.faceLandmarks
        };
        
        if (this.onPoseData) {
            this.onPoseData(this.poseData);
        }
    }
    
    drawConnectors(landmarks, connections, style) {
        if (!landmarks) return;
        drawConnectors(this.ctx, landmarks, connections, style);
    }
    
    drawLandmarks(landmarks, style) {
        if (!landmarks) return;
        drawLandmarks(this.ctx, landmarks, style);
    }
    
    setShowLandmarks(show) {
        this.showLandmarks = show;
    }
    
    getPoseData() {
        return this.poseData;
    }
    
    log(message) {
        const debugInfo = document.getElementById('debugInfo');
        if (debugInfo) {
            const timestamp = new Date().toLocaleTimeString();
            const newContent = `<div style="color: #00ffff">[${timestamp}] ${message}</div>` + debugInfo.innerHTML;
            debugInfo.innerHTML = newContent.substring(0, 3000);
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
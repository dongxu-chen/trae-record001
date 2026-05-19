class DigitalHumanApp4 {
    constructor() {
        this.holisticTracker = null;
        this.avatarRenderer = null;
        this.skeletonMapper = null;
        this.multiPersonManager = null;
        
        this.isInitialized = false;
        this.isTracking = false;
        
        this.init();
    }
    
    async init() {
        this.log('🚀 启动数字人系统 v4.0 - MediaPipe Holistic');
        
        try {
            this.log('初始化 Three.js 渲染器...');
            this.avatarRenderer = new ThreeJSAvatar('threejs-container');
            
            this.log('初始化骨骼映射器...');
            this.skeletonMapper = new SkeletonMapper();
            
            this.log('初始化多人管理器...');
            this.multiPersonManager = new MultiPersonManager(4);
            
            this.log('初始化 MediaPipe Holistic...');
            this.holisticTracker = new HolisticTracker('inputVideo', 'poseCanvas');
            this.holisticTracker.onResults = (results) => this.handleTrackingResults(results);
            
            await this.holisticTracker.initialize();
            
            this.setupEventListeners();
            
            this.isInitialized = true;
            this.log('✅ 系统初始化完成！');
            this.log('📹 点击"开启摄像头"开始全身动捕');
            
        } catch (error) {
            this.log(`❌ 初始化失败: ${error.message}`);
            console.error(error);
        }
    }
    
    setupEventListeners() {
        document.getElementById('startCameraBtn').addEventListener('click', async () => {
            if (!this.isInitialized) {
                this.log('⚠️ 系统尚未初始化完成');
                return;
            }
            
            document.getElementById('startCameraBtn').disabled = true;
            
            const success = await this.holisticTracker.startCamera();
            if (success) {
                this.isTracking = true;
                document.getElementById('stopCameraBtn').disabled = false;
                this.log('📹 摄像头已启动，开始追踪');
            } else {
                document.getElementById('startCameraBtn').disabled = false;
            }
        });
        
        document.getElementById('stopCameraBtn').addEventListener('click', () => {
            this.holisticTracker.stop();
            this.isTracking = false;
            document.getElementById('startCameraBtn').disabled = false;
            document.getElementById('stopCameraBtn').disabled = true;
            this.log('⏹️ 追踪已停止');
        });
        
        document.querySelectorAll('.mode-btn').forEach((btn, index) => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.holisticTracker.setTrackingMode(index + 1);
            });
        });
        
        document.querySelectorAll('.avatar-option').forEach(option => {
            option.addEventListener('click', () => {
                document.querySelectorAll('.avatar-option').forEach(o => o.classList.remove('selected'));
                option.classList.add('selected');
                const model = option.dataset.model;
                this.avatarRenderer.changeModel(model);
            });
        });
        
        document.getElementById('avatarScale').addEventListener('input', (e) => {
            const scale = parseFloat(e.target.value);
            this.avatarRenderer.setScale(scale);
            document.getElementById('scaleValue').textContent = scale.toFixed(1) + 'x';
        });
        
        document.querySelectorAll('.backend-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.backend-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const backend = btn.dataset.backend;
                this.holisticTracker.setBackend(backend);
            });
        });
        
        document.getElementById('modelComplexity').addEventListener('input', (e) => {
            const level = parseInt(e.target.value);
            const labels = ['快速', '中等', '完整'];
            this.holisticTracker.setModelComplexity(level);
            document.getElementById('complexityValue').textContent = labels[level];
        });
        
        document.getElementById('enableSmoothing').addEventListener('change', (e) => {
            this.holisticTracker.setSmoothing(e.target.checked);
        });
        
        document.getElementById('showSkeleton').addEventListener('change', (e) => {
            this.holisticTracker.setShowSkeleton(e.target.checked);
        });
        
        document.querySelectorAll('.person-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.person-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const personIndex = parseInt(btn.dataset.person);
                this.multiPersonManager.selectPerson(personIndex);
            });
        });
        
        document.getElementById('resetCamera').addEventListener('click', () => {
            this.avatarRenderer.resetCamera();
            this.log('🎥 相机已重置');
        });
        
        document.getElementById('toggleWireframe').addEventListener('click', () => {
            const isWireframe = this.avatarRenderer.toggleWireframe();
            this.log(`🔲 线框模式: ${isWireframe ? '开启' : '关闭'}`);
        });
        
        document.getElementById('toggleSkeleton').addEventListener('click', () => {
            const showSkeleton = this.avatarRenderer.toggleSkeleton();
            this.log(`🦴 骨骼显示: ${showSkeleton ? '开启' : '关闭'}`);
        });
        
        setInterval(() => {
            this.updateDebugInfo();
        }, 500);
    }
    
    handleTrackingResults(results) {
        if (!results) return;
        
        const timestamp = performance.now();
        const persons = this.multiPersonManager.processDetections(results, timestamp);
        
        document.getElementById('personCount').textContent = this.multiPersonManager.getActiveCount();
        
        persons.forEach((person, index) => {
            if (person.active && person.poseData) {
                this.avatarRenderer.setAvatarActive(index, true);
                this.avatarRenderer.updateAvatarPose(index, person.poseData);
                
                if (person.faceData) {
                    const blendshapes = this.skeletonMapper.calculateFaceBlendshapes(person.faceData);
                    this.multiPersonManager.setPersonBlendshapes(index, blendshapes);
                    this.avatarRenderer.updateFaceBlendshapes(index, blendshapes);
                }
            } else {
                this.avatarRenderer.setAvatarActive(index, false);
            }
        });
    }
    
    updateDebugInfo() {
        const skeletonDebug = document.getElementById('skeletonDebug');
        if (!skeletonDebug) return;
        
        const debugInfo = this.multiPersonManager.getDebugInfo();
        
        let html = '';
        debugInfo.forEach(person => {
            const statusColor = person.active ? 'color: #00ff00;' : 'color: #666;';
            html += `<div style="${statusColor}">
                ${person.label}: ${person.active ? '✓ 追踪中' : '未激活'} 
                (${person.confidence}%)
            </div>`;
        });
        
        skeletonDebug.innerHTML = html;
    }
    
    log(message) {
        const debugInfo = document.getElementById('debugInfo');
        if (debugInfo) {
            const timestamp = new Date().toLocaleTimeString();
            const newContent = `<div style="color: #00ff00">[${timestamp}] ${message}</div>` + debugInfo.innerHTML;
            debugInfo.innerHTML = newContent.substring(0, 8000);
        }
    }
}

window.addEventListener('DOMContentLoaded', () => {
    if (typeof THREE !== 'undefined' && typeof Holistic !== 'undefined') {
        window.app = new DigitalHumanApp4();
    } else {
        console.error('必要的库未加载');
        
        const checkInterval = setInterval(() => {
            if (typeof THREE !== 'undefined' && typeof Holistic !== 'undefined') {
                clearInterval(checkInterval);
                window.app = new DigitalHumanApp4();
            }
        }, 100);
    }
});

window.addEventListener('beforeunload', () => {
    if (window.app && window.app.holisticTracker) {
        window.app.holisticTracker.stop();
    }
    if (window.app && window.app.avatarRenderer) {
        window.app.avatarRenderer.dispose();
    }
});
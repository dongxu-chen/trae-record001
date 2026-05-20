class DigitalHumanApp {
    constructor() {
        this.faceTracker = null;
        this.poseTracker = null;
        this.avatarRenderer = null;
        this.backgroundManager = null;
        this.streamManager = null;
        this.ttsManager = null;
        this.captureMode = 'face';
        this.showDebugInfo = true;
        this.init();
    }
    
    async init() {
        this.log('🚀 初始化数字人系统 v3.0...');
        
        this.avatarRenderer = new AvatarRenderer('avatarCanvas');
        this.backgroundManager = new BackgroundManager(document.getElementById('avatarCanvas'));
        
        this.overrideAvatarRender();
        this.avatarRenderer.render();
        
        this.ttsManager = new TTSManager();
        this.setupTTSCallbacks();
        
        this.poseTracker = new PoseTracker('inputVideo', 'poseCanvas');
        await this.poseTracker.loadModel();
        
        this.faceTracker = new FaceTracker('inputVideo', 'faceCanvas');
        await this.faceTracker.loadModel();
        
        this.streamManager = new StreamManager();
        this.setupStreamCallbacks();
        
        this.setupEventListeners();
        
        this.startStatusUpdate();
        
        this.addBlendshapeDebugPanel();
        
        this.log('✅ 系统初始化完成！');
        this.log('🎭 功能: 面部追踪 + 全身动捕 + 多模型切换 + 背景替换 + 直播推流');
    }
    
    overrideAvatarRender() {
        const originalRender = this.avatarRenderer.render.bind(this.avatarRenderer);
        this.avatarRenderer.render = () => {
            this.backgroundManager.drawBackground();
            originalRender();
            requestAnimationFrame(() => this.avatarRenderer.render());
        };
    }
    
    setupTTSCallbacks() {
        this.ttsManager.onStart = () => {
            this.log('🎤 开始朗读...');
        };
        
        this.ttsManager.onEnd = () => {
            this.log('🎤 朗读结束');
            document.getElementById('speakBtn').disabled = false;
            document.getElementById('stopSpeakBtn').disabled = true;
        };
        
        this.ttsManager.onMouthShapeUpdate = (mouthShape, time) => {
            this.avatarRenderer.setAudioMouthShape(mouthShape);
        };
    }
    
    setupStreamCallbacks() {
        this.streamManager.onStreamStateChange = (isStreaming) => {
            document.getElementById('startStreamBtn').disabled = isStreaming;
            document.getElementById('stopStreamBtn').disabled = !isStreaming;
            document.getElementById('streamStatus').textContent = isStreaming ? '正在推流' : '未连接';
        };
        
        this.streamManager.onViewerCountChange = (count) => {
            document.getElementById('viewUrl').textContent = `${count} 人观看`;
        };
    }
    
    setupEventListeners() {
        const startCameraBtn = document.getElementById('startCameraBtn');
        const stopCameraBtn = document.getElementById('stopCameraBtn');
        
        startCameraBtn.addEventListener('click', async () => {
            startCameraBtn.disabled = true;
            
            const tracker = this.captureMode === 'holistic' ? this.poseTracker : this.faceTracker;
            tracker.onPoseData = (poseData) => this.onPoseDetected(poseData);
            tracker.onFaceData = (faces, blendshapes) => this.onFaceDetected(faces, blendshapes);
            
            const success = await tracker.startCamera();
            if (success) {
                stopCameraBtn.disabled = false;
            } else {
                startCameraBtn.disabled = false;
            }
        });
        
        stopCameraBtn.addEventListener('click', () => {
            if (this.captureMode === 'holistic') {
                this.poseTracker.stopCamera();
            } else {
                this.faceTracker.stopCamera();
            }
            startCameraBtn.disabled = false;
            stopCameraBtn.disabled = true;
        });
        
        document.getElementById('showLandmarks').addEventListener('change', (e) => {
            this.faceTracker.setShowLandmarks(e.target.checked);
            this.poseTracker.setShowLandmarks(e.target.checked);
        });
        
        document.getElementById('faceOnlyBtn').addEventListener('click', () => {
            this.setCaptureMode('face');
        });
        
        document.getElementById('holisticBtn').addEventListener('click', () => {
            this.setCaptureMode('holistic');
        });
        
        document.querySelectorAll('.avatar-option').forEach(option => {
            option.addEventListener('click', () => {
                document.querySelectorAll('.avatar-option').forEach(o => o.classList.remove('selected'));
                option.classList.add('selected');
                const model = option.dataset.model;
                this.avatarRenderer.setModel(model);
                this.log(`🎨 切换形象: ${this.getModelName(model)}`);
            });
        });
        
        document.getElementById('avatarScale').addEventListener('input', (e) => {
            const scale = parseFloat(e.target.value);
            this.avatarRenderer.setScale(scale);
            document.getElementById('scaleValue').textContent = scale.toFixed(1) + 'x';
        });
        
        document.getElementById('bgDefaultBtn').addEventListener('click', () => this.setBackgroundMode('default'));
        document.getElementById('bgGreenBtn').addEventListener('click', () => this.setBackgroundMode('green'));
        document.getElementById('bgBlueBtn').addEventListener('click', () => this.setBackgroundMode('blue'));
        document.getElementById('bgImageBtn').addEventListener('click', () => this.setBackgroundMode('image'));
        
        document.getElementById('selectBgImageBtn').addEventListener('click', () => {
            document.getElementById('bgImageInput').click();
        });
        
        document.getElementById('bgImageInput').addEventListener('change', async (e) => {
            if (e.target.files.length > 0) {
                try {
                    await this.backgroundManager.setCustomImage(e.target.files[0]);
                    this.setBackgroundMode('image');
                } catch (error) {
                    this.log(`❌ 图片加载失败: ${error.message}`);
                }
            }
        });
        
        document.getElementById('bgBlur').addEventListener('input', (e) => {
            const blur = parseInt(e.target.value);
            this.backgroundManager.setBlur(blur);
            document.getElementById('blurValue').textContent = blur + 'px';
        });
        
        const speakBtn = document.getElementById('speakBtn');
        const stopSpeakBtn = document.getElementById('stopSpeakBtn');
        const ttsText = document.getElementById('ttsText');
        
        ttsText.addEventListener('input', async () => {
            const rate = parseFloat(document.getElementById('speechRate').value);
            const pitch = parseFloat(document.getElementById('speechPitch').value);
            await this.ttsManager.preloadText(ttsText.value, rate, pitch);
        });
        
        speakBtn.addEventListener('click', async () => {
            const text = ttsText.value.trim();
            if (!text) {
                this.log('⚠️ 请输入要朗读的文字');
                return;
            }
            
            const rate = parseFloat(document.getElementById('speechRate').value);
            const pitch = parseFloat(document.getElementById('speechPitch').value);
            
            speakBtn.disabled = true;
            stopSpeakBtn.disabled = false;
            
            try {
                await this.ttsManager.speak(text, rate, pitch);
            } catch (e) {
                this.log(`❌ 朗读出错: ${e.message}`);
                speakBtn.disabled = false;
                stopSpeakBtn.disabled = true;
            }
        });
        
        stopSpeakBtn.addEventListener('click', () => {
            this.ttsManager.stop();
            speakBtn.disabled = false;
            stopSpeakBtn.disabled = true;
        });
        
        document.getElementById('speechRate').addEventListener('input', (e) => {
            document.getElementById('rateValue').textContent = parseFloat(e.target.value).toFixed(1);
        });
        
        document.getElementById('speechPitch').addEventListener('input', (e) => {
            document.getElementById('pitchValue').textContent = parseFloat(e.target.value).toFixed(1);
        });
        
        document.getElementById('audioSync').addEventListener('change', (e) => {
            this.avatarRenderer.enableAudioSync(e.target.checked);
            this.log(e.target.checked ? '✅ 已启用音频口型同步' : '❌ 已禁用音频口型同步');
        });
        
        document.getElementById('startStreamBtn').addEventListener('click', async () => {
            const streamKey = document.getElementById('streamKey').value;
            const success = await this.streamManager.startStream(
                document.getElementById('avatarCanvas'),
                streamKey
            );
            
            if (success) {
                const previewContainer = document.querySelector('.stream-preview');
                if (previewContainer) {
                    previewContainer.style.display = 'block';
                    const previewVideo = document.getElementById('streamOutput');
                    previewVideo.srcObject = this.streamManager.getStream();
                }
            }
        });
        
        document.getElementById('stopStreamBtn').addEventListener('click', () => {
            this.streamManager.stopStream();
            const previewContainer = document.querySelector('.stream-preview');
            if (previewContainer) {
                previewContainer.style.display = 'none';
            }
        });
    }
    
    setCaptureMode(mode) {
        this.captureMode = mode;
        this.poseTracker.setCaptureMode(mode);
        
        document.querySelectorAll('.mode-btn').forEach(btn => btn.classList.remove('active'));
        if (mode === 'face') {
            document.getElementById('faceOnlyBtn').classList.add('active');
        } else {
            document.getElementById('holisticBtn').classList.add('active');
        }
        
        document.getElementById('captureMode').textContent = mode === 'face' ? '仅面部' : '全身动捕';
        this.log(`🎬 切换捕捉模式: ${mode === 'face' ? '仅面部' : '全身动捕'}`);
    }
    
    setBackgroundMode(mode) {
        document.querySelectorAll('.bg-btn').forEach(btn => btn.classList.remove('active'));
        
        switch (mode) {
            case 'default':
                document.getElementById('bgDefaultBtn').classList.add('active');
                break;
            case 'green':
                document.getElementById('bgGreenBtn').classList.add('active');
                break;
            case 'blue':
                document.getElementById('bgBlueBtn').classList.add('active');
                break;
            case 'image':
                document.getElementById('bgImageBtn').classList.add('active');
                break;
        }
        
        this.backgroundManager.setMode(mode);
    }
    
    onFaceDetected(faces, blendshapes) {
        this.avatarRenderer.updateFaceData(faces);
        if (blendshapes) {
            this.avatarRenderer.updateBlendshapes(blendshapes);
        }
        
        if (this.showDebugInfo && blendshapes) {
            this.updateBlendshapeDebug(blendshapes);
        }
    }
    
    onPoseDetected(poseData) {
        this.avatarRenderer.updatePoseData(poseData);
        
        if (poseData && poseData.poseLandmarks) {
            document.getElementById('poseStatus').textContent = '已检测';
        } else {
            document.getElementById('poseStatus').textContent = '未检测';
        }
        
        if (this.showDebugInfo && poseData && poseData.poseLandmarks) {
            this.updatePoseDebug(poseData);
        }
    }
    
    addBlendshapeDebugPanel() {
        const debugPanel = document.querySelector('.debug-panel');
        if (!debugPanel) return;
        
        const blendshapePanel = document.createElement('div');
        blendshapePanel.id = 'blendshapeDebug';
        blendshapePanel.style.marginTop = '10px';
        blendshapePanel.style.fontSize = '10px';
        blendshapePanel.style.display = 'grid';
        blendshapePanel.style.gridTemplateColumns = 'repeat(3, 1fr)';
        blendshapePanel.style.gap = '2px';
        blendshapePanel.style.maxHeight = '120px';
        blendshapePanel.style.overflowY = 'auto';
        debugPanel.appendChild(blendshapePanel);
        
        const posePanel = document.createElement('div');
        posePanel.id = 'poseDebug';
        posePanel.style.marginTop = '10px';
        posePanel.style.fontSize = '10px';
        posePanel.style.color = '#00ffff';
        debugPanel.appendChild(posePanel);
    }
    
    updateBlendshapeDebug(blendshapes) {
        const panel = document.getElementById('blendshapeDebug');
        if (!panel) return;
        
        const keyBlendshapes = [
            'eyeBlinkLeft', 'eyeBlinkRight',
            'jawOpen', 'mouthSmileLeft', 'mouthSmileRight',
            'browInnerUp', 'browOuterUpLeft', 'browOuterUpRight'
        ];
        
        let html = '';
        for (const key of keyBlendshapes) {
            const value = blendshapes[key] || 0;
            const percent = Math.round(value * 100);
            const color = percent > 50 ? '#00ff00' : percent > 20 ? '#ffff00' : '#888';
            const displayName = key.replace(/([A-Z])/g, ' $1').trim().replace(/^./, str => str.toUpperCase());
            html += `<div style="color: ${color}">${displayName}: ${percent}%</div>`;
        }
        
        panel.innerHTML = html;
    }
    
    updatePoseDebug(poseData) {
        const panel = document.getElementById('poseDebug');
        if (!panel || !poseData || !poseData.poseLandmarks) return;
        
        const landmarks = poseData.poseLandmarks;
        const nose = landmarks[0];
        const leftShoulder = landmarks[11];
        const rightShoulder = landmarks[12];
        
        if (nose && leftShoulder && rightShoulder) {
            const shoulderWidth = Math.abs(leftShoulder.x - rightShoulder.x);
            const poseConfidence = (leftShoulder.visibility + rightShoulder.visibility) / 2;
            
            panel.innerHTML = `
                <div>📍 肩部宽度: ${(shoulderWidth * 100).toFixed(1)}%</div>
                <div>🎯 姿势置信度: ${(poseConfidence * 100).toFixed(1)}%</div>
                <div>👐 左手: ${poseData.leftHandLandmarks ? '检测' : '未检测'}</div>
                <div>👐 右手: ${poseData.rightHandLandmarks ? '检测' : '未检测'}</div>
            `;
        }
    }
    
    startStatusUpdate() {
        setInterval(() => {
            const mouthOpen = this.avatarRenderer.getMouthOpenValue();
            document.getElementById('mouthOpenValue').textContent = Math.round(mouthOpen * 100) + '%';
            
            const isBlinking = this.avatarRenderer.isBlinking();
            document.getElementById('blinkValue').textContent = isBlinking ? '眨眼中' : '正常';
        }, 100);
    }
    
    getModelName(model) {
        const names = {
            'cartoon': '卡通人物',
            'realistic': '真人风格',
            'robot': '机器人',
            'anime': '动漫风格'
        };
        return names[model] || model;
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

window.addEventListener('DOMContentLoaded', () => {
    window.app = new DigitalHumanApp();
});

window.addEventListener('resize', () => {
    if (window.app && window.app.avatarRenderer) {
        setTimeout(() => {
            window.app.avatarRenderer.resize();
            window.app.avatarRenderer.initAvatar();
            if (window.app.backgroundManager) {
                window.app.backgroundManager.initDefaultBackground();
            }
        }, 100);
    }
});
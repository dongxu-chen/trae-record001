class TFJSHandDetector {
    constructor() {
        this.model = null;
        this.isInitialized = false;
        this.useWebGL = true;
        this.lastInferenceTime = 0;
        this.targetFPS = 30;
        this.frameInterval = 1000 / this.targetFPS;
    }

    async init() {
        console.log('初始化 TensorFlow.js 手部检测...');
        
        await this.loadTFJS();
        await this.setBackend();
        await this.loadModel();
        
        this.isInitialized = true;
        console.log('TensorFlow.js 手部检测初始化完成！');
    }

    async loadTFJS() {
        if (!window.tf) {
            return new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = 'https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@4.14.0/dist/tf.min.js';
                script.onload = resolve;
                script.onerror = reject;
                document.head.appendChild(script);
            });
        }
    }

    async setBackend() {
        const backends = ['webgl', 'wasm', 'cpu'];
        
        for (const backend of backends) {
            try {
                await window.tf.setBackend(backend);
                await window.tf.ready();
                console.log(`使用后端: ${backend}`);
                break;
            } catch (e) {
                console.warn(`后端 ${backend} 不可用，尝试下一个`);
            }
        }

        if (window.tf.getBackend() === 'webgl') {
            window.tf.ENV.set('WEBGL_PACK', true);
            window.tf.ENV.set('WEBGL_FORCE_F16_TEXTURES', true);
        }
    }

    async loadModel() {
        console.log('加载手部检测模型...');
        
        this.model = await window.handPoseDetection.createDetector(
            window.handPoseDetection.SupportedModels.MediaPipeHands,
            {
                runtime: 'tfjs',
                modelType: 'lite',
                maxHands: 2,
                detectorModelUrl: 'https://storage.googleapis.com/tfjs-models/savedmodel/handpose/detector/model.json',
                landmarkModelUrl: 'https://storage.googleapis.com/tfjs-models/savedmodel/handpose/landmark/model.json'
            }
        );
        
        console.log('模型加载完成！');
    }

    async detectHands(videoFrame) {
        if (!this.isInitialized) {
            throw new Error('检测器未初始化');
        }

        const now = performance.now();
        if (now - this.lastInferenceTime < this.frameInterval) {
            return null;
        }

        const startTime = performance.now();
        
        const hands = await window.tf.tidy(() => {
            return this.model.estimateHands(videoFrame, {
                flipHorizontal: false,
                staticImageMode: false
            });
        });

        const inferenceTime = performance.now() - startTime;
        this.lastInferenceTime = performance.now();

        console.log(`检测耗时: ${inferenceTime.toFixed(1)}ms`);

        if (inferenceTime > 30) {
            console.warn(`警告: 检测耗时超过 30ms 目标`);
        }

        return {
            multiHandLandmarks: hands.map(hand => ({
                landmarks: hand.keypoints.map(kp => ({
                    x: kp.x / videoFrame.width,
                    y: kp.y / videoFrame.height,
                    z: kp.z ? kp.z / videoFrame.width : 0
                })),
                handedness: hand.handedness === 'Right' ? 1.0 : 0.0,
                confidence: hand.score || 1.0
            })),
            inferenceTime
        };
    }

    isReady() {
        return this.isInitialized && this.model !== null;
    }

    dispose() {
        if (this.model) {
            this.model.dispose();
            this.model = null;
        }
        this.isInitialized = false;
    }
}

class OfflineModelManager {
    constructor() {
        this.dbName = 'TFJSModels';
        this.storeName = 'models';
        this.modelFiles = {};
    }

    async initDB() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, 1);
            
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                if (!db.objectStoreNames.contains(this.storeName)) {
                    db.createObjectStore(this.storeName);
                }
            };

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    async saveModel(modelName, modelUrl) {
        try {
            const response = await fetch(modelUrl);
            const modelData = await response.json();
            
            const weightsUrl = modelUrl.replace('model.json', 'group1-shard1of1.bin');
            const weightsResponse = await fetch(weightsUrl);
            const weightsData = await weightsResponse.arrayBuffer();
            
            const db = await this.initDB();
            const transaction = db.transaction([this.storeName], 'readwrite');
            const store = transaction.objectStore(this.storeName);
            
            await new Promise((resolve, reject) => {
                const putRequest = store.put({
                    modelJson: modelData,
                    weightsData: new Uint8Array(weightsData)
                }, modelName);
                
                putRequest.onsuccess = resolve;
                putRequest.onerror = reject;
            });
            
            console.log(`模型 ${modelName} 已保存到本地`);
        } catch (error) {
            console.error('保存模型失败:', error);
        }
    }

    async loadModel(modelName) {
        try {
            const db = await this.initDB();
            const transaction = db.transaction([this.storeName], 'readonly');
            const store = transaction.objectStore(this.storeName);
            
            const data = await new Promise((resolve, reject) => {
                const getRequest = store.get(modelName);
                getRequest.onsuccess = () => resolve(getRequest.result);
                getRequest.onerror = reject;
            });
            
            if (!data) {
                console.log(`模型 ${modelName} 未在本地找到`);
                return null;
            }
            
            console.log(`从本地加载模型 ${modelName}`);
            
            const modelArtifacts = {
                modelTopology: data.modelJson.modelTopology,
                weightSpecs: data.modelJson.weightsManifest[0].weights,
                weightData: data.weightsData
            };
            
            return modelArtifacts;
        } catch (error) {
            console.error('加载本地模型失败:', error);
            return null;
        }
    }

    async hasModel(modelName) {
        const db = await this.initDB();
        const transaction = db.transaction([this.storeName], 'readonly');
        const store = transaction.objectStore(this.storeName);
        
        return new Promise((resolve) => {
            const getRequest = store.get(modelName);
            getRequest.onsuccess = () => resolve(getRequest.result !== undefined);
            getRequest.onerror = () => resolve(false);
        });
    }
}

class PerformanceMonitor {
    constructor() {
        this.fpsHistory = [];
        this.inferenceTimeHistory = [];
        this.lastFrameTime = 0;
        this.frameCount = 0;
        this.lastReportTime = 0;
        this.reportInterval = 5000;
    }

    recordFrame() {
        const now = performance.now();
        if (this.lastFrameTime > 0) {
            const delta = now - this.lastFrameTime;
            const fps = 1000 / delta;
            this.fpsHistory.push(fps);
            if (this.fpsHistory.length > 100) {
                this.fpsHistory.shift();
            }
        }
        this.lastFrameTime = now;
        this.frameCount++;
    }

    recordInferenceTime(time) {
        this.inferenceTimeHistory.push(time);
        if (this.inferenceTimeHistory.length > 100) {
            this.inferenceTimeHistory.shift();
        }
    }

    getStats() {
        const avgFPS = this.fpsHistory.length > 0 
            ? this.fpsHistory.reduce((a, b) => a + b, 0) / this.fpsHistory.length 
            : 0;
        
        const avgInferenceTime = this.inferenceTimeHistory.length > 0
            ? this.inferenceTimeHistory.reduce((a, b) => a + b, 0) / this.inferenceTimeHistory.length
            : 0;
        
        const maxInferenceTime = this.inferenceTimeHistory.length > 0
            ? Math.max(...this.inferenceTimeHistory)
            : 0;
        
        return {
            avgFPS: avgFPS.toFixed(1),
            avgInferenceTime: avgInferenceTime.toFixed(1),
            maxInferenceTime: maxInferenceTime.toFixed(1),
            totalFrames: this.frameCount
        };
    }

    shouldReport() {
        const now = performance.now();
        if (now - this.lastReportTime > this.reportInterval) {
            this.lastReportTime = now;
            return true;
        }
        return false;
    }

    printReport() {
        const stats = this.getStats();
        console.log(`
========== 性能报告 ==========
平均 FPS: ${stats.avgFPS}
平均推理时间: ${stats.avgInferenceTime}ms
最大推理时间: ${stats.maxInferenceTime}ms
总帧数: ${stats.totalFrames}
目标: < 30ms/帧
==============================
        `);
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { TFJSHandDetector, OfflineModelManager, PerformanceMonitor };
}

class HandDetector {
    constructor() {
        this.palmEngine = null;
        this.landmarkEngine = null;
        this.isInitialized = false;
        this.palmModelUrl = 'https://storage.googleapis.com/tfweb/models/palm_detection.tflite';
        this.landmarkModelUrl = 'https://storage.googleapis.com/tfweb/models/hand_landmark.tflite';
    }

    async init() {
        console.log('初始化手部检测管道...');
        
        await this.loadTFLiteRuntime();
        
        this.palmEngine = new TFLiteEngine();
        this.palmEngine.modelUrl = this.palmModelUrl;
        this.palmEngine.localModelName = 'palm_detection_tflite';
        this.palmEngine.inputSize = [192, 192];
        await this.palmEngine.init();
        
        this.landmarkEngine = new OptimizedTFLiteEngine();
        this.landmarkEngine.modelUrl = this.landmarkModelUrl;
        this.landmarkEngine.localModelName = 'hand_landmark_tflite';
        this.landmarkEngine.inputSize = [224, 224];
        this.landmarkEngine.initOffscreenCanvas();
        await this.landmarkEngine.init();
        
        this.isInitialized = true;
        console.log('手部检测管道初始化完成！');
    }

    async loadTFLiteRuntime() {
        if (!window.tflite) {
            return new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = 'https://cdn.jsdelivr.net/npm/@tensorflow/tfjs-tflite@0.0.1-alpha.9/dist/tflite.min.js';
                script.onload = resolve;
                script.onerror = reject;
                document.head.appendChild(script);
            });
        }
    }

    async detectHands(videoFrame, maxHands = 2) {
        if (!this.isInitialized) {
            throw new Error('检测器未初始化');
        }

        const startTime = performance.now();
        
        const palms = await this.detectPalms(videoFrame);
        const results = [];
        
        for (let i = 0; i < Math.min(palms.length, maxHands); i++) {
            const palm = palms[i];
            const croppedImage = this.cropHandRegion(videoFrame, palm);
            const landmarkResult = await this.landmarkEngine.inferOptimized(croppedImage);
            
            if (landmarkResult.landmarks) {
                const landmarks = this.transformLandmarks(landmarkResult.landmarks, palm);
                results.push({
                    landmarks,
                    handedness: landmarkResult.handedness,
                    confidence: landmarkResult.confidence,
                    boundingBox: palm.bbox
                });
            }
        }

        const totalTime = performance.now() - startTime;
        console.log(`手部检测总耗时: ${totalTime.toFixed(1)}ms`);
        
        return {
            multiHandLandmarks: results,
            inferenceTime: totalTime
        };
    }

    async detectPalms(imageData) {
        const result = await this.palmEngine.infer(imageData);
        return this.decodePalmDetections(result.rawOutput);
    }

    decodePalmDetections(outputData) {
        const palms = [];
        const confidenceThreshold = 0.7;
        const numAnchors = 2944;
        
        for (let i = 0; i < numAnchors; i++) {
            const confidence = this.sigmoid(outputData[i * 19]);
            
            if (confidence > confidenceThreshold) {
                const centerX = outputData[i * 19 + 1];
                const centerY = outputData[i * 19 + 2];
                const width = outputData[i * 19 + 3];
                const height = outputData[i * 19 + 4];
                
                palms.push({
                    confidence,
                    center: { x: centerX, y: centerY },
                    size: { width, height },
                    bbox: {
                        x: centerX - width / 2,
                        y: centerY - height / 2,
                        width,
                        height
                    }
                });
            }
        }
        
        return this.nonMaxSuppression(palms, 0.5);
    }

    nonMaxSuppression(palms, iouThreshold) {
        if (palms.length === 0) return [];
        
        palms.sort((a, b) => b.confidence - a.confidence);
        
        const result = [];
        const suppressed = new Set();
        
        for (let i = 0; i < palms.length; i++) {
            if (suppressed.has(i)) continue;
            
            result.push(palms[i]);
            
            for (let j = i + 1; j < palms.length; j++) {
                if (suppressed.has(j)) continue;
                
                const iou = this.calculateIOU(palms[i].bbox, palms[j].bbox);
                if (iou > iouThreshold) {
                    suppressed.add(j);
                }
            }
        }
        
        return result;
    }

    calculateIOU(box1, box2) {
        const x1 = Math.max(box1.x, box2.x);
        const y1 = Math.max(box1.y, box2.y);
        const x2 = Math.min(box1.x + box1.width, box2.x + box2.width);
        const y2 = Math.min(box1.y + box1.height, box2.y + box2.height);
        
        const intersection = Math.max(0, x2 - x1) * Math.max(0, y2 - y1);
        const area1 = box1.width * box1.height;
        const area2 = box2.width * box2.height;
        const union = area1 + area2 - intersection;
        
        return intersection / union;
    }

    cropHandRegion(imageData, palm) {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        const padding = palm.size.width * 0.3;
        const x = Math.max(0, (palm.bbox.x - padding) * imageData.width);
        const y = Math.max(0, (palm.bbox.y - padding) * imageData.height);
        const width = Math.min(imageData.width - x, (palm.bbox.width + padding * 2) * imageData.width);
        const height = Math.min(imageData.height - y, (palm.bbox.height + padding * 2) * imageData.height);
        
        canvas.width = this.landmarkEngine.inputSize[0];
        canvas.height = this.landmarkEngine.inputSize[1];
        
        ctx.drawImage(imageData, x, y, width, height, 0, 0, canvas.width, canvas.height);
        
        return canvas;
    }

    transformLandmarks(landmarks, palm) {
        const padding = palm.size.width * 0.3;
        const scaleX = palm.bbox.width + padding * 2;
        const scaleY = palm.bbox.height + padding * 2;
        const offsetX = palm.bbox.x - padding;
        const offsetY = palm.bbox.y - padding;
        
        return landmarks.map(lm => ({
            x: lm.x * scaleX + offsetX,
            y: lm.y * scaleY + offsetY,
            z: lm.z * scaleX
        }));
    }

    sigmoid(x) {
        return 1 / (1 + Math.exp(-x));
    }

    isReady() {
        return this.isInitialized;
    }

    dispose() {
        if (this.palmEngine) this.palmEngine.dispose();
        if (this.landmarkEngine) this.landmarkEngine.dispose();
        this.isInitialized = false;
    }
}

class WebAssemblyHandDetector extends HandDetector {
    constructor() {
        super();
        this.worker = null;
        this.useWorker = typeof Worker !== 'undefined';
    }

    async initWithWorker() {
        if (this.useWorker) {
            console.log('使用 Web Worker 进行推理');
            this.initWorker();
        }
        await this.init();
    }

    initWorker() {
        const workerCode = `
            importScripts('https://cdn.jsdelivr.net/npm/@tensorflow/tfjs-tflite@0.0.1-alpha.9/dist/tflite.min.js');
            
            let interpreter = null;
            let modelLoaded = false;
            
            self.onmessage = async (e) => {
                switch (e.data.type) {
                    case 'loadModel':
                        try {
                            const tfliteModel = new Uint8Array(e.data.modelBuffer);
                            interpreter = new self.tflite.Interpreter({
                                model: tfliteModel,
                                numThreads: 4
                            });
                            modelLoaded = true;
                            self.postMessage({ type: 'modelLoaded' });
                        } catch (error) {
                            self.postMessage({ type: 'error', error: error.message });
                        }
                        break;
                        
                    case 'infer':
                        if (!modelLoaded) {
                            self.postMessage({ type: 'error', error: 'Model not loaded' });
                            return;
                        }
                        
                        try {
                            interpreter.setInputTensor(0, e.data.inputData);
                            interpreter.invoke();
                            const output = interpreter.getOutputTensor(0);
                            self.postMessage({ 
                                type: 'result', 
                                output: Array.from(output)
                            });
                        } catch (error) {
                            self.postMessage({ type: 'error', error: error.message });
                        }
                        break;
                }
            };
        `;
        
        const blob = new Blob([workerCode], { type: 'application/javascript' });
        const workerUrl = URL.createObjectURL(blob);
        this.worker = new Worker(workerUrl);
        
        this.worker.onmessage = (e) => {
            console.log('Worker message:', e.data);
        };
        
        this.worker.onerror = (error) => {
            console.error('Worker error:', error);
        };
    }

    async detectHandsParallel(videoFrame, maxHands = 2) {
        const startTime = performance.now();
        
        const palmPromise = this.detectPalms(videoFrame);
        const palms = await palmPromise;
        
        const landmarkPromises = palms.slice(0, maxHands).map(palm => {
            const croppedImage = this.cropHandRegion(videoFrame, palm);
            return this.landmarkEngine.inferOptimized(croppedImage);
        });
        
        const landmarkResults = await Promise.all(landmarkPromises);
        
        const results = palms.slice(0, maxHands).map((palm, i) => ({
            landmarks: this.transformLandmarks(landmarkResults[i].landmarks, palm),
            handedness: landmarkResults[i].handedness,
            confidence: landmarkResults[i].confidence,
            boundingBox: palm.bbox
        }));
        
        const totalTime = performance.now() - startTime;
        console.log(`并行检测总耗时: ${totalTime.toFixed(1)}ms`);
        
        return {
            multiHandLandmarks: results,
            inferenceTime: totalTime
        };
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { HandDetector, WebAssemblyHandDetector };
}

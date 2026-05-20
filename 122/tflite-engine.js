class TFLiteEngine {
    constructor() {
        this.interpreter = null;
        this.modelLoaded = false;
        this.inputTensor = null;
        this.outputTensors = {};
        this.modelUrl = 'https://storage.googleapis.com/tfweb/models/hand_landmark.tflite';
        this.localModelName = 'hand_landmark_tflite';
        this.inputSize = [224, 224];
        this.numLandmarks = 21;
    }

    async init() {
        console.log('初始化 TFLite 引擎...');
        
        if (!window.TFLite) {
            await this.loadTFLiteRuntime();
        }

        const modelBuffer = await this.loadModel();
        await this.createInterpreter(modelBuffer);
        
        this.modelLoaded = true;
        console.log('TFLite 引擎初始化完成！');
    }

    async loadTFLiteRuntime() {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/@tensorflow/tfjs-tflite@0.0.1-alpha.9/dist/tflite.min.js';
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    async loadModel() {
        const cached = await this.getCachedModel();
        if (cached) {
            console.log('从本地缓存加载模型');
            return cached;
        }

        console.log('从网络下载模型...');
        const response = await fetch(this.modelUrl);
        const arrayBuffer = await response.arrayBuffer();
        await this.cacheModel(arrayBuffer);
        return arrayBuffer;
    }

    async getCachedModel() {
        if (!('indexedDB' in window)) {
            return null;
        }

        return new Promise((resolve) => {
            const request = indexedDB.open('TFLiteModels', 1);
            
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                if (!db.objectStoreNames.contains('models')) {
                    db.createObjectStore('models');
                }
            };

            request.onsuccess = (event) => {
                const db = event.target.result;
                const transaction = db.transaction(['models'], 'readonly');
                const store = transaction.objectStore('models');
                const getRequest = store.get(this.localModelName);
                
                getRequest.onsuccess = () => {
                    resolve(getRequest.result || null);
                };
                
                getRequest.onerror = () => resolve(null);
            };

            request.onerror = () => resolve(null);
        });
    }

    async cacheModel(arrayBuffer) {
        if (!('indexedDB' in window)) {
            return;
        }

        return new Promise((resolve) => {
            const request = indexedDB.open('TFLiteModels', 1);
            
            request.onsuccess = (event) => {
                const db = event.target.result;
                const transaction = db.transaction(['models'], 'readwrite');
                const store = transaction.objectStore('models');
                const putRequest = store.put(arrayBuffer, this.localModelName);
                
                putRequest.onsuccess = () => {
                    console.log('模型已缓存到本地');
                    resolve();
                };
                
                putRequest.onerror = () => resolve();
            };
        });
    }

    async createInterpreter(modelBuffer) {
        const tfliteModel = new Uint8Array(modelBuffer);
        
        this.interpreter = new window.tflite.Interpreter({
            model: tfliteModel,
            numThreads: 4
        });

        const inputDetails = this.interpreter.getInputDetails();
        const outputDetails = this.interpreter.getOutputDetails();
        
        this.inputTensor = inputDetails[0];
        
        outputDetails.forEach((detail, index) => {
            this.outputTensors[detail.name] = detail;
        });

        console.log('输入张量:', this.inputTensor);
        console.log('输出张量:', Object.keys(this.outputTensors));
    }

    preprocessImage(imageData) {
        const startTime = performance.now();
        
        const canvas = document.createElement('canvas');
        canvas.width = this.inputSize[0];
        canvas.height = this.inputSize[1];
        const ctx = canvas.getContext('2d');
        
        ctx.drawImage(imageData, 0, 0, this.inputSize[0], this.inputSize[1]);
        
        const imageDataArr = ctx.getImageData(0, 0, this.inputSize[0], this.inputSize[1]);
        const data = imageDataArr.data;
        
        const inputData = new Float32Array(this.inputSize[0] * this.inputSize[1] * 3);
        
        let idx = 0;
        for (let i = 0; i < data.length; i += 4) {
            inputData[idx++] = (data[i] - 127.5) / 127.5;
            inputData[idx++] = (data[i + 1] - 127.5) / 127.5;
            inputData[idx++] = (data[i + 2] - 127.5) / 127.5;
        }

        console.log(`预处理耗时: ${(performance.now() - startTime).toFixed(1)}ms`);
        return inputData;
    }

    async infer(imageData) {
        if (!this.modelLoaded) {
            throw new Error('模型未加载完成');
        }

        const startTime = performance.now();
        
        const inputData = this.preprocessImage(imageData);
        
        this.interpreter.setInputTensor(0, inputData);
        
        const inferStart = performance.now();
        this.interpreter.invoke();
        const inferTime = performance.now() - inferStart;
        
        const landmarks = this.getLandmarks();
        const handedness = this.getHandedness();
        const confidence = this.getConfidence();
        
        const totalTime = performance.now() - startTime;
        
        console.log(`推理耗时: ${inferTime.toFixed(1)}ms, 总耗时: ${totalTime.toFixed(1)}ms`);
        
        return {
            landmarks,
            handedness,
            confidence,
            inferenceTime: inferTime,
            totalTime
        };
    }

    getLandmarks() {
        const outputName = Object.keys(this.outputTensors).find(name => 
            name.includes('landmark') || name.includes('lm')
        );
        
        if (!outputName) return null;
        
        const outputData = this.interpreter.getOutputTensor(
            this.outputTensors[outputName].index
        );
        
        const landmarks = [];
        for (let i = 0; i < this.numLandmarks; i++) {
            landmarks.push({
                x: outputData[i * 3] / this.inputSize[0],
                y: outputData[i * 3 + 1] / this.inputSize[1],
                z: outputData[i * 3 + 2] / this.inputSize[0]
            });
        }
        
        return landmarks;
    }

    getHandedness() {
        const outputName = Object.keys(this.outputTensors).find(name => 
            name.includes('handedness') || name.includes('hand')
        );
        
        if (!outputName) return 0.5;
        
        const outputData = this.interpreter.getOutputTensor(
            this.outputTensors[outputName].index
        );
        
        return outputData[0];
    }

    getConfidence() {
        const outputName = Object.keys(this.outputTensors).find(name => 
            name.includes('score') || name.includes('confidence')
        );
        
        if (!outputName) return 1.0;
        
        const outputData = this.interpreter.getOutputTensor(
            this.outputTensors[outputName].index
        );
        
        return outputData[0];
    }

    isReady() {
        return this.modelLoaded;
    }

    dispose() {
        if (this.interpreter) {
            this.interpreter.dispose();
            this.interpreter = null;
        }
        this.modelLoaded = false;
    }
}

class OptimizedTFLiteEngine extends TFLiteEngine {
    constructor() {
        super();
        this.offscreenCanvas = null;
        this.offscreenCtx = null;
        this.wasmOptimized = true;
    }

    initOffscreenCanvas() {
        if (typeof OffscreenCanvas !== 'undefined') {
            this.offscreenCanvas = new OffscreenCanvas(this.inputSize[0], this.inputSize[1]);
            this.offscreenCtx = this.offscreenCanvas.getContext('2d', { 
                willReadFrequently: true 
            });
        }
    }

    preprocessImageOptimized(imageData) {
        const startTime = performance.now();
        
        const ctx = this.offscreenCtx || document.createElement('canvas').getContext('2d');
        const canvas = ctx.canvas;
        canvas.width = this.inputSize[0];
        canvas.height = this.inputSize[1];
        
        ctx.drawImage(imageData, 0, 0, this.inputSize[0], this.inputSize[1]);
        
        const imageDataArr = ctx.getImageData(0, 0, this.inputSize[0], this.inputSize[1]);
        const data = imageDataArr.data;
        
        const inputData = new Float32Array(this.inputSize[0] * this.inputSize[1] * 3);
        
        if (this.wasmOptimized && typeof WebAssembly !== 'undefined') {
            this.optimizedNormalization(data, inputData);
        } else {
            let idx = 0;
            for (let i = 0; i < data.length; i += 4) {
                inputData[idx++] = (data[i] - 127.5) / 127.5;
                inputData[idx++] = (data[i + 1] - 127.5) / 127.5;
                inputData[idx++] = (data[i + 2] - 127.5) / 127.5;
            }
        }

        console.log(`优化预处理耗时: ${(performance.now() - startTime).toFixed(1)}ms`);
        return inputData;
    }

    optimizedNormalization(rgbaData, float32Data) {
        const len = rgbaData.length;
        let floatIdx = 0;
        
        for (let i = 0; i < len; i += 4) {
            float32Data[floatIdx++] = (rgbaData[i] - 127.5) * 0.00784313725;
            float32Data[floatIdx++] = (rgbaData[i + 1] - 127.5) * 0.00784313725;
            float32Data[floatIdx++] = (rgbaData[i + 2] - 127.5) * 0.00784313725;
        }
    }

    async inferOptimized(imageData) {
        if (!this.modelLoaded) {
            throw new Error('模型未加载完成');
        }

        const startTime = performance.now();
        
        const inputData = this.preprocessImageOptimized(imageData);
        this.interpreter.setInputTensor(0, inputData);
        
        const inferStart = performance.now();
        this.interpreter.invoke();
        const inferTime = performance.now() - inferStart;
        
        const landmarks = this.getLandmarks();
        
        const totalTime = performance.now() - startTime;
        
        if (totalTime > 30) {
            console.warn(`总耗时 ${totalTime.toFixed(1)}ms 超过目标 30ms`);
        }
        
        return {
            landmarks,
            handedness: this.getHandedness(),
            confidence: this.getConfidence(),
            inferenceTime: inferTime,
            totalTime
        };
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { TFLiteEngine, OptimizedTFLiteEngine };
}

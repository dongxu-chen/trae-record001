var lightEstimation = {
    isEnabled: false,
    analysisCanvas: null,
    analysisCtx: null,
    lastBrightness: 0,
    smoothBrightness: 0,
    analysisInterval: null,
    analysisFrequency: 500,
    smoothingFactor: 0.9,
    
    minAmbient: 0.5,
    maxAmbient: 2.5,
    minDirectional: 0.3,
    maxDirectional: 2.0,
    
    baseAmbient: 1.5,
    baseDirectional: 1.0,
    
    currentAmbient: 1.5,
    currentDirectional: 1.0,
    
    init: function() {
        this.createAnalysisCanvas();
        this.setupUI();
    },
    
    createAnalysisCanvas: function() {
        this.analysisCanvas = document.createElement('canvas');
        this.analysisCanvas.width = 64;
        this.analysisCanvas.height = 64;
        this.analysisCtx = this.analysisCanvas.getContext('2d', { willReadFrequently: true });
    },
    
    setupUI: function() {
        var self = this;
        
        var container = document.createElement('div');
        container.id = 'light-controls';
        container.style.cssText = 'position: absolute; bottom: 100px; right: 10px; background: rgba(0, 0, 0, 0.7); padding: 10px; border-radius: 5px; color: white; font-size: 12px; z-index: 100; min-width: 180px;';
        
        var title = document.createElement('div');
        title.style.cssText = 'font-weight: bold; margin-bottom: 10px;';
        title.textContent = '环境光估计';
        container.appendChild(title);
        
        var label = document.createElement('label');
        label.style.cssText = 'display: flex; align-items: center; cursor: pointer; user-select: none;';
        
        var checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = 'enable-light-estimation';
        checkbox.style.cssText = 'margin-right: 8px; cursor: pointer;';
        
        checkbox.addEventListener('change', function() {
            if (this.checked) {
                self.enable();
            } else {
                self.disable();
            }
        });
        
        label.appendChild(checkbox);
        label.appendChild(document.createTextNode('启用自适应光照'));
        container.appendChild(label);
        
        var brightnessDisplay = document.createElement('div');
        brightnessDisplay.id = 'brightness-display';
        brightnessDisplay.style.cssText = 'margin-top: 10px; font-size: 11px; color: #aaa;';
        brightnessDisplay.innerHTML = '<div>环境亮度: <span id="brightness-value">--</span></div><div>环境光强度: <span id="ambient-value">--</span></div><div>方向光强度: <span id="directional-value">--</span></div>';
        container.appendChild(brightnessDisplay);
        
        var resetButton = document.createElement('button');
        resetButton.textContent = '重置光照';
        resetButton.style.cssText = 'margin-top: 10px; padding: 6px 12px; background: #2196F3; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 11px; width: 100%;';
        resetButton.addEventListener('click', function() {
            self.reset();
        });
        container.appendChild(resetButton);
        
        document.body.appendChild(container);
    },
    
    enable: function() {
        if (this.isEnabled) return;
        
        this.isEnabled = true;
        this.startAnalysis();
    },
    
    disable: function() {
        if (!this.isEnabled) return;
        
        this.isEnabled = false;
        this.stopAnalysis();
        this.reset();
    },
    
    startAnalysis: function() {
        var self = this;
        
        this.analysisInterval = setInterval(function() {
            self.analyzeBrightness();
        }, this.analysisFrequency);
    },
    
    stopAnalysis: function() {
        if (this.analysisInterval) {
            clearInterval(this.analysisInterval);
            this.analysisInterval = null;
        }
    },
    
    analyzeBrightness: function() {
        if (!arScene.arToolkitSource || !arScene.arToolkitSource.domElement) {
            return;
        }
        
        var video = arScene.arToolkitSource.domElement;
        var videoElement = video.video || video;
        
        if (!videoElement || videoElement.readyState < 2) {
            return;
        }
        
        try {
            var width = this.analysisCanvas.width;
            var height = this.analysisCanvas.height;
            
            this.analysisCtx.drawImage(videoElement, 0, 0, width, height);
            
            var imageData = this.analysisCtx.getImageData(0, 0, width, height);
            var data = imageData.data;
            
            var totalBrightness = 0;
            var pixelCount = data.length / 4;
            
            for (var i = 0; i < data.length; i += 4) {
                var r = data[i];
                var g = data[i + 1];
                var b = data[i + 2];
                
                var brightness = r * 0.299 + g * 0.587 + b * 0.114;
                totalBrightness += brightness;
            }
            
            var averageBrightness = totalBrightness / pixelCount;
            var normalizedBrightness = averageBrightness / 255;
            
            this.smoothBrightness = this.smoothBrightness * this.smoothingFactor + normalizedBrightness * (1 - this.smoothingFactor);
            this.lastBrightness = normalizedBrightness;
            
            this.adjustLighting(this.smoothBrightness);
            this.updateDisplay();
            
        } catch (e) {
            console.warn('亮度分析失败:', e);
        }
    },
    
    adjustLighting: function(brightness) {
        var invertedBrightness = 1 - brightness;
        
        var ambientRange = this.maxAmbient - this.minAmbient;
        var directionalRange = this.maxDirectional - this.minDirectional;
        
        var targetAmbient = this.minAmbient + invertedBrightness * ambientRange;
        var targetDirectional = this.minDirectional + invertedBrightness * directionalRange;
        
        this.currentAmbient = this.currentAmbient * this.smoothingFactor + targetAmbient * (1 - this.smoothingFactor);
        this.currentDirectional = this.currentDirectional * this.smoothingFactor + targetDirectional * (1 - this.smoothingFactor);
        
        arScene.updateLighting(this.currentAmbient, this.currentDirectional);
    },
    
    reset: function() {
        this.currentAmbient = this.baseAmbient;
        this.currentDirectional = this.baseDirectional;
        this.smoothBrightness = 0;
        
        arScene.resetLighting();
    },
    
    updateDisplay: function() {
        var brightnessEl = document.getElementById('brightness-value');
        var ambientEl = document.getElementById('ambient-value');
        var directionalEl = document.getElementById('directional-value');
        
        if (brightnessEl) {
            brightnessEl.textContent = Math.round(this.smoothBrightness * 100) + '%';
        }
        if (ambientEl) {
            ambientEl.textContent = this.currentAmbient.toFixed(2);
        }
        if (directionalEl) {
            directionalEl.textContent = this.currentDirectional.toFixed(2);
        }
    },
    
    getBrightness: function() {
        return this.smoothBrightness;
    },
    
    isActive: function() {
        return this.isEnabled;
    }
};
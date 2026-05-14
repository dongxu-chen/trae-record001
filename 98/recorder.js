var recorder = {
    recordRTC: null,
    isRecording: false,
    startTime: null,
    timerInterval: null,
    recordedBlob: null,
    
    options: {
        mimeType: 'video/webm;codecs=vp9',
        bitsPerSecond: 2500000,
        frameRate: 30
    },
    
    init: function() {
        this.setupUI();
    },
    
    setupUI: function() {
        var self = this;
        
        var container = document.createElement('div');
        container.id = 'recorder-controls';
        container.style.cssText = `
            position: absolute;
            top: 60px;
            right: 10px;
            background: rgba(0, 0, 0, 0.7);
            padding: 10px;
            border-radius: 5px;
            color: white;
            font-size: 12px;
            z-index: 100;
            min-width: 150px;
        `;
        
        var title = document.createElement('div');
        title.style.cssText = 'font-weight: bold; margin-bottom: 10px;';
        title.textContent = '录屏控制';
        container.appendChild(title);
        
        var buttonContainer = document.createElement('div');
        buttonContainer.style.cssText = 'display: flex; gap: 10px; margin-bottom: 10px;';
        
        this.recordButton = document.createElement('button');
        this.recordButton.id = 'record-btn';
        this.recordButton.style.cssText = `
            padding: 8px 16px;
            background: #f44336;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            font-weight: bold;
        `;
        this.recordButton.textContent = '开始录制';
        this.recordButton.addEventListener('click', function() {
            if (self.isRecording) {
                self.stopRecording();
            } else {
                self.startRecording();
            }
        });
        buttonContainer.appendChild(this.recordButton);
        
        this.downloadButton = document.createElement('button');
        this.downloadButton.id = 'download-btn';
        this.downloadButton.style.cssText = `
            padding: 8px 16px;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            font-weight: bold;
            display: none;
        `;
        this.downloadButton.textContent = '下载视频';
        this.downloadButton.addEventListener('click', function() {
            self.downloadRecording();
        });
        buttonContainer.appendChild(this.downloadButton);
        
        container.appendChild(buttonContainer);
        
        this.timerDisplay = document.createElement('div');
        this.timerDisplay.id = 'recording-timer';
        this.timerDisplay.style.cssText = 'text-align: center; font-size: 14px; font-family: monospace;';
        this.timerDisplay.textContent = '00:00:00';
        container.appendChild(this.timerDisplay);
        
        this.statusDisplay = document.createElement('div');
        this.statusDisplay.id = 'recording-status';
        this.statusDisplay.style.cssText = 'text-align: center; margin-top: 5px; font-size: 11px; color: #aaa;';
        this.statusDisplay.textContent = '准备就绪';
        container.appendChild(this.statusDisplay);
        
        var videoPreview = document.createElement('div');
        videoPreview.id = 'video-preview';
        videoPreview.style.cssText = 'margin-top: 10px; display: none;';
        
        this.previewVideo = document.createElement('video');
        this.previewVideo.id = 'preview-video';
        this.previewVideo.style.cssText = 'width: 100%; max-width: 200px; border-radius: 4px;';
        this.previewVideo.controls = true;
        videoPreview.appendChild(this.previewVideo);
        container.appendChild(videoPreview);
        
        document.body.appendChild(container);
    },
    
    startRecording: function() {
        var self = this;
        
        if (typeof RecordRTC === 'undefined') {
            this.showStatus('RecordRTC 库未加载', 'error');
            return;
        }
        
        var canvas = document.getElementById('ar-canvas');
        if (!canvas) {
            this.showStatus('找不到画布元素', 'error');
            return;
        }
        
        var canvasStream;
        
        try {
            if (canvas.captureStream) {
                canvasStream = canvas.captureStream(this.options.frameRate);
            } else if (canvas.mozCaptureStream) {
                canvasStream = canvas.mozCaptureStream(this.options.frameRate);
            } else {
                this.showStatus('浏览器不支持画布录制', 'error');
                return;
            }
        } catch (e) {
            console.error('获取画布流失败:', e);
            this.showStatus('无法获取画布流: ' + e.message, 'error');
            return;
        }
        
        var finalStream = canvasStream;
        
        this.recordRTC = RecordRTC(finalStream, {
            type: 'video',
            mimeType: this.options.mimeType,
            bitsPerSecond: this.options.bitsPerSecond,
            frameRate: this.options.frameRate,
            canvas: {
                width: canvas.width,
                height: canvas.height
            }
        });
        
        this.recordRTC.startRecording();
        
        this.isRecording = true;
        this.startTime = Date.now();
        this.recordedBlob = null;
        
        this.updateRecordButton();
        this.startTimer();
        this.showStatus('正在录制...', 'recording');
        this.downloadButton.style.display = 'none';
        this.previewVideo.style.display = 'none';
        
        window.dispatchEvent(new CustomEvent('recording-started'));
    },
    
    stopRecording: function() {
        var self = this;
        
        if (!this.recordRTC || !this.isRecording) {
            return;
        }
        
        this.recordRTC.stopRecording(function() {
            self.recordedBlob = self.recordRTC.getBlob();
            
            self.isRecording = false;
            self.stopTimer();
            self.updateRecordButton();
            self.showStatus('录制完成', 'success');
            
            self.previewVideo.src = URL.createObjectURL(self.recordedBlob);
            document.getElementById('video-preview').style.display = 'block';
            self.downloadButton.style.display = 'inline-block';
            
            window.dispatchEvent(new CustomEvent('recording-stopped', {
                detail: {
                    blob: self.recordedBlob,
                    duration: (Date.now() - self.startTime) / 1000
                }
            }));
        });
    },
    
    startTimer: function() {
        var self = this;
        
        this.timerInterval = setInterval(function() {
            var elapsed = Date.now() - self.startTime;
            self.timerDisplay.textContent = self.formatTime(elapsed);
        }, 100);
    },
    
    stopTimer: function() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    },
    
    formatTime: function(ms) {
        var hours = Math.floor(ms / 3600000);
        var minutes = Math.floor((ms % 3600000) / 60000);
        var seconds = Math.floor((ms % 60000) / 1000);
        var centiseconds = Math.floor((ms % 1000) / 10);
        
        return [
            hours.toString().padStart(2, '0'),
            minutes.toString().padStart(2, '0'),
            seconds.toString().padStart(2, '0')
        ].join(':');
    },
    
    updateRecordButton: function() {
        if (this.isRecording) {
            this.recordButton.textContent = '停止录制';
            this.recordButton.style.background = '#9C27B0';
        } else {
            this.recordButton.textContent = '开始录制';
            this.recordButton.style.background = '#f44336';
        }
    },
    
    showStatus: function(message, type) {
        this.statusDisplay.textContent = message;
        
        switch(type) {
            case 'error':
                this.statusDisplay.style.color = '#f44336';
                break;
            case 'recording':
                this.statusDisplay.style.color = '#f44336';
                this.statusDisplay.style.fontWeight = 'bold';
                break;
            case 'success':
                this.statusDisplay.style.color = '#4CAF50';
                this.statusDisplay.style.fontWeight = 'bold';
                break;
            default:
                this.statusDisplay.style.color = '#aaa';
                this.statusDisplay.style.fontWeight = 'normal';
        }
    },
    
    downloadRecording: function() {
        if (!this.recordedBlob) {
            this.showStatus('没有可下载的录制', 'error');
            return;
        }
        
        var timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
        var filename = 'ar-recording-' + timestamp + '.webm';
        
        this.recordRTC.save(filename);
        
        this.showStatus('视频已下载', 'success');
    },
    
    getRecordedBlob: function() {
        return this.recordedBlob;
    },
    
    isRecordingActive: function() {
        return this.isRecording;
    },
    
    toggleRecording: function() {
        if (this.isRecording) {
            this.stopRecording();
        } else {
            this.startRecording();
        }
    }
};
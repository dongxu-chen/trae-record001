class TimelineManager {
    constructor(viewer, updateCallback) {
        this.viewer = viewer;
        this.updateCallback = updateCallback;
        
        this.currentTime = new Date();
        this.startTime = new Date();
        this.baseTime = new Date();
        
        this.speed = 1.0;
        this.isPlaying = true;
        this.isRunning = false;
        
        this.animationId = null;
        this.lastFrameTime = 0;
        
        this.minSpeed = -1000;
        this.maxSpeed = 1000;
        
        this.timeStep = 1000;
        
        this.listeners = [];
    }
    
    start() {
        if (this.isRunning) return;
        
        this.isRunning = true;
        this.lastFrameTime = performance.now();
        this.baseTime = new Date();
        this.currentTime = new Date(this.baseTime.getTime());
        this.speedMultiplier = this.speed;
        
        this.animate();
        
        if (this.updateCallback) {
            this.updateCallback(this.currentTime);
        }
    }
    
    stop() {
        this.isRunning = false;
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
    }
    
    animate() {
        if (!this.isRunning) return;
        
        const currentFrameTime = performance.now();
        const deltaRealTime = currentFrameTime - this.lastFrameTime;
        this.lastFrameTime = currentFrameTime;
        
        if (this.isPlaying) {
            const effectiveSpeed = this.speedMultiplier || this.speed || 1.0;
            const deltaSimulationTime = deltaRealTime * effectiveSpeed;
            this.currentTime = new Date(this.currentTime.getTime() + deltaSimulationTime);
            
            if (this.updateCallback) {
                this.updateCallback(this.currentTime);
            }
            
            this.notifyListeners('timechange', this.currentTime);
        }
        
        this.animationId = requestAnimationFrame(() => this.animate());
    }
    
    play() {
        this.isPlaying = true;
        this.notifyListeners('play');
    }
    
    pause() {
        this.isPlaying = false;
        this.notifyListeners('pause');
    }
    
    toggle() {
        if (this.isPlaying) {
            this.pause();
        } else {
            this.play();
        }
    }
    
    reset() {
        this.currentTime = new Date(this.startTime.getTime());
        this.baseTime = new Date();
        
        if (this.updateCallback) {
            this.updateCallback(this.currentTime);
        }
        
        this.notifyListeners('reset', this.currentTime);
    }
    
    setSpeed(speed) {
        this.speed = Math.max(this.minSpeed, Math.min(this.maxSpeed, speed));
        this.speedMultiplier = this.speed;
        this.notifyListeners('speedchange', this.speed);
    }
    
    getSpeed() {
        return this.speed;
    }
    
    setTime(date) {
        this.currentTime = new Date(date.getTime());
        
        if (this.updateCallback) {
            this.updateCallback(this.currentTime);
        }
        
        this.notifyListeners('timechange', this.currentTime);
    }
    
    getTime() {
        return new Date(this.currentTime.getTime());
    }
    
    addTime(milliseconds) {
        this.currentTime = new Date(this.currentTime.getTime() + milliseconds);
        
        if (this.updateCallback) {
            this.updateCallback(this.currentTime);
        }
        
        this.notifyListeners('timechange', this.currentTime);
    }
    
    subtractTime(milliseconds) {
        this.addTime(-milliseconds);
    }
    
    isPlaying() {
        return this.isPlaying;
    }
    
    addEventListener(event, callback) {
        if (!this.listeners[event]) {
            this.listeners[event] = [];
        }
        this.listeners[event].push(callback);
    }
    
    removeEventListener(event, callback) {
        if (!this.listeners[event]) return;
        
        const index = this.listeners[event].indexOf(callback);
        if (index !== -1) {
            this.listeners[event].splice(index, 1);
        }
    }
    
    notifyListeners(event, data) {
        if (!this.listeners[event]) return;
        
        this.listeners[event].forEach(callback => {
            try {
                callback(data);
            } catch (error) {
                console.error(`Error in listener for event ${event}:`, error);
            }
        });
    }
    
    formatTime(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        const seconds = String(date.getSeconds()).padStart(2, '0');
        
        return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
    }
    
    formatTimeUTC(date) {
        const year = date.getUTCFullYear();
        const month = String(date.getUTCMonth() + 1).padStart(2, '0');
        const day = String(date.getUTCDate()).padStart(2, '0');
        const hours = String(date.getUTCHours()).padStart(2, '0');
        const minutes = String(date.getUTCMinutes()).padStart(2, '0');
        const seconds = String(date.getUTCSeconds()).padStart(2, '0');
        
        return `${year}-${month}-${day} ${hours}:${minutes}:${seconds} UTC`;
    }
    
    getJulianDate(date = this.currentTime) {
        const year = date.getUTCFullYear();
        const month = date.getUTCMonth() + 1;
        const day = date.getUTCDate();
        const hour = date.getUTCHours();
        const minute = date.getUTCMinutes();
        const second = date.getUTCSeconds();
        
        let a = Math.floor((14 - month) / 12);
        let y = year + 4800 - a;
        let m = month + 12 * a - 3;
        
        let JDN = day + Math.floor((153 * m + 2) / 5) + 365 * y + 
                  Math.floor(y / 4) - Math.floor(y / 100) + 
                  Math.floor(y / 400) - 32045;
        
        let JD = JDN + (hour - 12) / 24 + minute / 1440 + second / 86400;
        
        return JD;
    }
    
    getGreenwichMeanSiderealTime(date = this.currentTime) {
        const jd = this.getJulianDate(date);
        const T = (jd - 2451545.0) / 36525.0;
        
        let GMST = 280.46061837 + 360.98564736629 * (jd - 2451545.0) +
                   0.000387933 * T * T - T * T * T / 38710000.0;
        
        GMST = ((GMST % 360) + 360) % 360;
        
        return GMST;
    }
    
    stepForward(seconds = 60) {
        this.addTime(seconds * 1000);
    }
    
    stepBackward(seconds = 60) {
        this.subtractTime(seconds * 1000);
    }
    
    jumpToNow() {
        this.currentTime = new Date();
        this.baseTime = new Date();
        
        if (this.updateCallback) {
            this.updateCallback(this.currentTime);
        }
        
        this.notifyListeners('timechange', this.currentTime);
    }
    
    setTimeRange(startDate, endDate) {
        this.startTime = new Date(startDate.getTime());
        this.endTime = new Date(endDate.getTime());
        
        this.notifyListeners('timerangechange', {
            start: this.startTime,
            end: this.endTime
        });
    }
    
    destroy() {
        this.stop();
        this.listeners = [];
    }
}

class TimeDisplay {
    constructor(timelineManager, elementId) {
        this.timelineManager = timelineManager;
        this.element = document.getElementById(elementId);
        
        if (!this.element) {
            console.warn(`Element with id ${elementId} not found`);
        }
        
        this.timelineManager.addEventListener('timechange', () => this.update());
    }
    
    update() {
        if (!this.element) return;
        
        const time = this.timelineManager.getTime();
        const localTime = this.timelineManager.formatTime(time);
        const utcTime = this.timelineManager.formatTimeUTC(time);
        
        this.element.innerHTML = `
            <div>本地时间: ${localTime}</div>
            <div>UTC 时间: ${utcTime}</div>
        `;
    }
}

class SpeedControl {
    constructor(timelineManager, sliderId, displayId) {
        this.timelineManager = timelineManager;
        this.slider = document.getElementById(sliderId);
        this.display = document.getElementById(displayId);
        
        if (!this.slider || !this.display) {
            console.warn('Slider or display element not found');
            return;
        }
        
        this.setupSlider();
        
        this.timelineManager.addEventListener('speedchange', (speed) => {
            this.updateDisplay(speed);
        });
    }
    
    setupSlider() {
        this.slider.addEventListener('input', (e) => {
            const value = parseInt(e.target.value);
            let speed = this.mapSliderToSpeed(value);
            
            this.timelineManager.setSpeed(speed);
            this.updateDisplay(speed);
        });
    }
    
    mapSliderToSpeed(sliderValue) {
        if (sliderValue === 0) return 0;
        
        const absValue = Math.abs(sliderValue);
        const sign = sliderValue > 0 ? 1 : -1;
        
        let speed;
        if (absValue <= 10) {
            speed = absValue;
        } else {
            speed = Math.pow(10, (absValue - 10) / 15);
        }
        
        return speed * sign;
    }
    
    updateDisplay(speed) {
        if (!this.display) return;
        
        let displayText;
        if (Math.abs(speed) < 1) {
            displayText = speed.toFixed(2) + 'x';
        } else if (Math.abs(speed) < 10) {
            displayText = speed.toFixed(1) + 'x';
        } else {
            displayText = Math.round(speed) + 'x';
        }
        
        this.display.textContent = displayText;
    }
}

class PlaybackControls {
    constructor(timelineManager, playId, pauseId, resetId) {
        this.timelineManager = timelineManager;
        this.playBtn = document.getElementById(playId);
        this.pauseBtn = document.getElementById(pauseId);
        this.resetBtn = document.getElementById(resetId);
        
        this.setupEvents();
    }
    
    setupEvents() {
        if (this.playBtn) {
            this.playBtn.addEventListener('click', () => {
                this.timelineManager.play();
            });
        }
        
        if (this.pauseBtn) {
            this.pauseBtn.addEventListener('click', () => {
                this.timelineManager.pause();
            });
        }
        
        if (this.resetBtn) {
            this.resetBtn.addEventListener('click', () => {
                this.timelineManager.reset();
            });
        }
        
        this.timelineManager.addEventListener('play', () => {
            this.updateButtonStates();
        });
        
        this.timelineManager.addEventListener('pause', () => {
            this.updateButtonStates();
        });
    }
    
    updateButtonStates() {
        if (this.playBtn) {
            this.playBtn.disabled = this.timelineManager.isPlaying();
        }
        if (this.pauseBtn) {
            this.pauseBtn.disabled = !this.timelineManager.isPlaying();
        }
    }
}

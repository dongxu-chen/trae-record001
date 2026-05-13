const PLAYBACK_SPEEDS = {
  slow: 0.5,
  normal: 1,
  fast: 2,
  veryFast: 5
};

export class TimelineManager {
  constructor(dataStore, options = {}) {
    this.dataStore = dataStore;
    this.options = {
      container: options.container || document.body,
      windowSize: options.windowSize || 3600000,
      stepSize: options.stepSize || 60000,
      speed: options.speed || PLAYBACK_SPEEDS.normal,
      onUpdate: options.onUpdate || null,
      onPlayStateChange: options.onPlayStateChange || null
    };
    
    this.isPlaying = false;
    this.currentTime = 0;
    this.startTime = 0;
    this.endTime = 0;
    this.animationFrameId = null;
    this.lastFrameTime = 0;
    this._timeIndices = null;
    this._sortedTimestamps = null;
    
    this._initialize();
    this._createUI();
  }

  _initialize() {
    if (!this.dataStore || !this.dataStore.timestamps) {
      console.warn('⚠️ 数据中没有时间戳信息，时间轴功能受限');
      const now = Date.now();
      this.startTime = now - 86400000;
      this.endTime = now;
      this.currentTime = this.startTime;
      return;
    }

    const { timestamps, count } = this.dataStore;
    const timeIndices = [];
    
    let minTime = Infinity;
    let maxTime = -Infinity;
    
    for (let i = 0; i < count; i++) {
      const ts = timestamps[i];
      if (ts > 0) {
        timeIndices.push({ timestamp: ts, index: i });
        minTime = Math.min(minTime, ts);
        maxTime = Math.max(maxTime, ts);
      }
    }
    
    timeIndices.sort((a, b) => a.timestamp - b.timestamp);
    
    this._timeIndices = timeIndices;
    this._sortedTimestamps = timeIndices.map(t => t.timestamp);
    
    if (minTime < Infinity) {
      this.startTime = minTime;
      this.endTime = maxTime;
      this.currentTime = minTime;
    } else {
      const now = Date.now();
      this.startTime = now - 86400000;
      this.endTime = now;
      this.currentTime = this.startTime;
    }
    
    console.log(`✅ 时间轴初始化完成: ${this._formatTimeRange()}`);
  }

  _createUI() {
    const container = this.options.container;
    
    this.timelineUI = document.createElement('div');
    this.timelineUI.className = 'timeline-container';
    this.timelineUI.innerHTML = `
      <div class="timeline-header">
        <button class="timeline-btn" id="tl-play-pause" title="播放/暂停">
          <span id="tl-play-icon">▶</span>
        </button>
        <button class="timeline-btn" id="tl-step-back" title="后退一步">
          ◀◀
        </button>
        <button class="timeline-btn" id="tl-step-forward" title="前进一步">
          ▶▶
        </button>
        <button class="timeline-btn" id="tl-reset" title="重置">
          ⏮
        </button>
        <select class="timeline-speed" id="tl-speed">
          <option value="0.5">0.5x</option>
          <option value="1" selected>1x</option>
          <option value="2">2x</option>
          <option value="5">5x</option>
          <option value="10">10x</option>
        </select>
      </div>
      <div class="timeline-slider-container">
        <input type="range" class="timeline-slider" id="tl-slider" min="0" max="1000" value="0">
        <div class="timeline-time-display">
          <span id="tl-current-time">--</span>
          <span class="timeline-separator">|</span>
          <span id="tl-window-info">窗口: --</span>
        </div>
      </div>
    `;
    
    container.appendChild(this.timelineUI);
    this._bindEvents();
  }

  _bindEvents() {
    const playPauseBtn = this.timelineUI.querySelector('#tl-play-pause');
    const stepBackBtn = this.timelineUI.querySelector('#tl-step-back');
    const stepForwardBtn = this.timelineUI.querySelector('#tl-step-forward');
    const resetBtn = this.timelineUI.querySelector('#tl-reset');
    const speedSelect = this.timelineUI.querySelector('#tl-speed');
    const slider = this.timelineUI.querySelector('#tl-slider');
    
    playPauseBtn.addEventListener('click', () => this.togglePlay());
    stepBackBtn.addEventListener('click', () => this.stepBackward());
    stepForwardBtn.addEventListener('click', () => this.stepForward());
    resetBtn.addEventListener('click', () => this.reset());
    
    speedSelect.addEventListener('change', (e) => {
      this.options.speed = parseFloat(e.target.value);
    });
    
    slider.addEventListener('input', (e) => {
      const ratio = parseInt(e.target.value) / 1000;
      this.setTime(this.startTime + ratio * (this.endTime - this.startTime));
    });
    
    slider.addEventListener('change', (e) => {
      const ratio = parseInt(e.target.value) / 1000;
      this.setTime(this.startTime + ratio * (this.endTime - this.startTime));
      this._triggerUpdate();
    });
  }

  togglePlay() {
    if (this.isPlaying) {
      this.pause();
    } else {
      this.play();
    }
  }

  play() {
    if (this.isPlaying) return;
    
    this.isPlaying = true;
    this.lastFrameTime = performance.now();
    this._updatePlayButton();
    
    if (this.options.onPlayStateChange) {
      this.options.onPlayStateChange(true);
    }
    
    this._animate();
  }

  pause() {
    if (!this.isPlaying) return;
    
    this.isPlaying = false;
    
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
    
    this._updatePlayButton();
    
    if (this.options.onPlayStateChange) {
      this.options.onPlayStateChange(false);
    }
  }

  reset() {
    this.pause();
    this.currentTime = this.startTime;
    this._updateUI();
    this._triggerUpdate();
  }

  stepForward() {
    this.pause();
    this.currentTime = Math.min(this.currentTime + this.options.stepSize, this.endTime);
    this._updateUI();
    this._triggerUpdate();
  }

  stepBackward() {
    this.pause();
    this.currentTime = Math.max(this.currentTime - this.options.stepSize, this.startTime);
    this._updateUI();
    this._triggerUpdate();
  }

  setTime(time) {
    const wasPlaying = this.isPlaying;
    if (wasPlaying) this.pause();
    
    this.currentTime = Math.max(this.startTime, Math.min(time, this.endTime));
    this._updateUI();
    
    if (wasPlaying) this.play();
  }

  setWindowSize(windowSize) {
    this.options.windowSize = windowSize;
    this._updateUI();
    this._triggerUpdate();
  }

  _animate() {
    if (!this.isPlaying) return;
    
    const now = performance.now();
    const deltaMs = (now - this.lastFrameTime) * this.options.speed;
    this.lastFrameTime = now;
    
    this.currentTime += deltaMs;
    
    if (this.currentTime >= this.endTime) {
      this.currentTime = this.endTime;
      this.pause();
    }
    
    this._updateUI();
    this._triggerUpdate();
    
    if (this.isPlaying) {
      this.animationFrameId = requestAnimationFrame(() => this._animate());
    }
  }

  _updatePlayButton() {
    const icon = this.timelineUI.querySelector('#tl-play-icon');
    if (icon) {
      icon.textContent = this.isPlaying ? '⏸' : '▶';
    }
  }

  _updateUI() {
    const slider = this.timelineUI.querySelector('#tl-slider');
    const currentTimeEl = this.timelineUI.querySelector('#tl-current-time');
    const windowInfoEl = this.timelineUI.querySelector('#tl-window-info');
    
    if (slider) {
      const ratio = (this.currentTime - this.startTime) / (this.endTime - this.startTime);
      slider.value = Math.round(ratio * 1000);
    }
    
    if (currentTimeEl) {
      currentTimeEl.textContent = this._formatDate(this.currentTime);
    }
    
    if (windowInfoEl) {
      const windowMinutes = Math.round(this.options.windowSize / 60000);
      windowInfoEl.textContent = `窗口: ${windowMinutes} 分钟`;
    }
  }

  _triggerUpdate() {
    if (this.options.onUpdate) {
      const timeWindow = {
        startTime: this.currentTime - this.options.windowSize,
        endTime: this.currentTime,
        currentTime: this.currentTime,
        totalDuration: this.endTime - this.startTime,
        progress: (this.currentTime - this.startTime) / (this.endTime - this.startTime)
      };
      this.options.onUpdate(timeWindow);
    }
  }

  getPointsInWindow() {
    if (!this._timeIndices || !this._sortedTimestamps) {
      return this.dataStore;
    }
    
    const windowStart = this.currentTime - this.options.windowSize;
    const windowEnd = this.currentTime;
    
    let startIdx = this._binarySearch(this._sortedTimestamps, windowStart);
    let endIdx = this._binarySearch(this._sortedTimestamps, windowEnd);
    
    const { positions, values, categories, timestamps } = this.dataStore;
    const count = endIdx - startIdx;
    
    if (count <= 0) {
      return {
        count: 0,
        positions: new Float64Array(),
        values: new Float32Array(),
        categories: new Uint8Array(),
        timestamps: new Float64Array(),
        bounds: null
      };
    }
    
    const filteredPositions = new Float64Array(count * 2);
    const filteredValues = new Float32Array(count);
    const filteredCategories = new Uint8Array(count);
    const filteredTimestamps = new Float64Array(count);
    
    let minLng = Infinity, maxLng = -Infinity;
    let minLat = Infinity, maxLat = -Infinity;
    let minVal = Infinity, maxVal = -Infinity;
    
    for (let i = 0; i < count; i++) {
      const originalIdx = this._timeIndices[startIdx + i].index;
      
      const lng = positions[originalIdx * 2];
      const lat = positions[originalIdx * 2 + 1];
      const val = values[originalIdx];
      
      filteredPositions[i * 2] = lng;
      filteredPositions[i * 2 + 1] = lat;
      filteredValues[i] = val;
      filteredCategories[i] = categories[originalIdx];
      filteredTimestamps[i] = timestamps[originalIdx];
      
      minLng = Math.min(minLng, lng);
      maxLng = Math.max(maxLng, lng);
      minLat = Math.min(minLat, lat);
      maxLat = Math.max(maxLat, lat);
      minVal = Math.min(minVal, val);
      maxVal = Math.max(maxVal, val);
    }
    
    return {
      count,
      positions: filteredPositions,
      values: filteredValues,
      categories: filteredCategories,
      timestamps: filteredTimestamps,
      bounds: {
        minLng, maxLng,
        minLat, maxLat,
        minValue: minVal,
        maxValue: maxVal,
        centerLng: (minLng + maxLng) / 2,
        centerLat: (minLat + maxLat) / 2
      }
    };
  }

  _binarySearch(arr, target) {
    let left = 0;
    let right = arr.length;
    
    while (left < right) {
      const mid = Math.floor((left + right) / 2);
      if (arr[mid] < target) {
        left = mid + 1;
      } else {
        right = mid;
      }
    }
    
    return left;
  }

  _formatTimeRange() {
    return `${this._formatDate(this.startTime)} ~ ${this._formatDate(this.endTime)}`;
  }

  _formatDate(timestamp) {
    if (!timestamp || timestamp <= 0) return '--';
    const date = new Date(timestamp);
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  getState() {
    return {
      isPlaying: this.isPlaying,
      currentTime: this.currentTime,
      startTime: this.startTime,
      endTime: this.endTime,
      windowSize: this.options.windowSize,
      speed: this.options.speed,
      progress: (this.currentTime - this.startTime) / (this.endTime - this.startTime)
    };
  }

  destroy() {
    this.pause();
    
    if (this.timelineUI && this.timelineUI.parentNode) {
      this.timelineUI.parentNode.removeChild(this.timelineUI);
    }
    
    this.dataStore = null;
    this._timeIndices = null;
    this._sortedTimestamps = null;
    this.timelineUI = null;
  }
}

export function createTimelineManager(dataStore, options) {
  return new TimelineManager(dataStore, options);
}

export { PLAYBACK_SPEEDS };

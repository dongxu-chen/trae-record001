const EventEmitter = require('events');

class Segment {
  constructor(bizType, maxId, step) {
    this.bizType = bizType;
    this.maxId = maxId;
    this.currentId = maxId - step + 1;
    this.step = step;
    this.remaining = step;
    this.createTime = Date.now();
  }

  nextId() {
    if (this.remaining <= 0) {
      return null;
    }
    const id = this.currentId;
    this.currentId++;
    this.remaining--;
    return id;
  }

  getIdlePercentage() {
    return this.remaining / this.step;
  }
}

class SegmentBuffer extends EventEmitter {
  constructor(bizType, step = 1000, nextLoadThreshold = 0.2) {
    super();
    this.bizType = bizType;
    this.step = step;
    this.nextLoadThreshold = nextLoadThreshold;
    this.currentBuffer = null;
    this.nextBuffer = null;
    this.currentIndex = 0;
    this.isLoadingNext = false;
    this.maxValue = 9007199254740991;
  }

  init(firstMaxId) {
    this.currentBuffer = new Segment(this.bizType, firstMaxId, this.step);
    console.log(`号段[${this.bizType}]初始化完成: ${this.currentBuffer.currentId} - ${this.currentBuffer.maxId}`);
  }

  async nextId(loadNextSegmentCallback) {
    if (!this.currentBuffer) {
      throw new Error('号段缓冲区未初始化');
    }

    const currentIdlePercentage = this.currentBuffer.getIdlePercentage();
    if (currentIdlePercentage <= this.nextLoadThreshold && 
        !this.isLoadingNext && 
        this.nextBuffer === null) {
      this.isLoadingNext = true;
      console.log(`号段[${this.bizType}]剩余${Math.floor(currentIdlePercentage * 100)}%，开始预加载下一号段`);
      
      try {
        if (loadNextSegmentCallback) {
          const nextMaxId = await loadNextSegmentCallback(this.bizType, this.step);
          this.nextBuffer = new Segment(this.bizType, nextMaxId, this.step);
          console.log(`号段[${this.bizType}]预加载完成: ${this.nextBuffer.currentId} - ${this.nextBuffer.maxId}`);
        }
      } catch (error) {
        console.error(`号段[${this.bizType}]预加载失败:`, error);
      } finally {
        this.isLoadingNext = false;
      }
    }

    let id = this.currentBuffer.nextId();
    if (id === null) {
      if (this.nextBuffer === null) {
        console.log(`号段[${this.bizType}]耗尽，等待加载下一号段...`);
        if (loadNextSegmentCallback) {
          const nextMaxId = await loadNextSegmentCallback(this.bizType, this.step);
          this.nextBuffer = new Segment(this.bizType, nextMaxId, this.step);
        } else {
          throw new Error('号段已耗尽且无加载回调');
        }
      }
      
      this.switchBuffer();
      id = this.currentBuffer.nextId();
      console.log(`号段[${this.bizType}]已切换到新号段: ${this.currentBuffer.currentId} - ${this.currentBuffer.maxId}`);
    }

    return id;
  }

  switchBuffer() {
    this.currentBuffer = this.nextBuffer;
    this.nextBuffer = null;
    this.currentIndex = (this.currentIndex + 1) % 2;
    this.emit('bufferSwitched', this.currentBuffer);
  }

  getCurrentSegment() {
    return this.currentBuffer;
  }

  getNextSegment() {
    return this.nextBuffer;
  }

  getStatus() {
    return {
      bizType: this.bizType,
      current: this.currentBuffer ? {
        start: this.currentBuffer.currentId - this.currentBuffer.step + this.currentBuffer.remaining,
        end: this.currentBuffer.maxId,
        remaining: this.currentBuffer.remaining
      } : null,
      next: this.nextBuffer ? {
        start: this.nextBuffer.currentId,
        end: this.nextBuffer.maxId
      } : null,
      isLoadingNext: this.isLoadingNext
    };
  }
}

module.exports = { Segment, SegmentBuffer };
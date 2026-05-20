const EventEmitter = require('events');
const crypto = require('crypto');

class Segment {
  constructor(bizTag, maxId, step) {
    this.bizTag = bizTag;
    this.maxId = maxId;
    this.minId = maxId - step + 1;
    this.currentId = this.minId;
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

  getUsedCount() {
    return this.step - this.remaining;
  }
}

class SegmentBuffer {
  constructor(bizTag) {
    this.bizTag = bizTag;
    this.buffers = [null, null];
    this.currentIndex = 0;
    this.nextLoadThreshold = 0.1;
    this.isLoadingNext = false;
    this.initOk = false;
    this.lock = false;
  }

  getCurrentSegment() {
    return this.buffers[this.currentIndex];
  }

  getNextSegment() {
    return this.buffers[(this.currentIndex + 1) % 2];
  }

  setCurrentSegment(segment) {
    this.buffers[this.currentIndex] = segment;
    this.initOk = true;
  }

  setNextSegment(segment) {
    this.buffers[(this.currentIndex + 1) % 2] = segment;
  }

  switchSegment() {
    if (this.getNextSegment() === null) {
      return false;
    }
    this.currentIndex = (this.currentIndex + 1) % 2;
    return true;
  }

  needLoadNextSegment() {
    const current = this.getCurrentSegment();
    if (!current) return true;
    if (!this.initOk) return true;
    if (this.getNextSegment() !== null) return false;
    if (this.isLoadingNext) return false;
    return current.getIdlePercentage() <= this.nextLoadThreshold;
  }
}

class LeafSegmentManager extends EventEmitter {
  constructor(zkClient, options = {}) {
    super();
    this.zkClient = zkClient;
    this.segmentBuffers = new Map();
    this.defaultStep = options.defaultStep || 1000;
    this.leafBasePath = '/leaf/segments';
    this.bizTagsPath = '/leaf/biz_tags';
    this.metrics = {
      totalIds: 0,
      segmentLoads: 0,
      segmentSwitches: 0,
      loadErrors: 0
    };
    this.initialized = false;
  }

  async init() {
    await this.ensureZkPath();
    await this.registerDefaultBizTags();
    this.initialized = true;
    console.log('[Leaf] 号段管理器初始化完成');
  }

  async ensureZkPath() {
    const paths = [this.leafBasePath, this.bizTagsPath];
    for (const path of paths) {
      await new Promise((resolve, reject) => {
        this.zkClient.exists(path, (error, stat) => {
          if (error) return reject(error);
          if (stat) return resolve();
          
          this.zkClient.mkdirp(path, (error) => {
            if (error) return reject(error);
            resolve();
          });
        });
      });
    }
  }

  async registerDefaultBizTags() {
    const defaultTags = [
      { tag: 'order', step: 1000, prefix: 'ORD' },
      { tag: 'user', step: 1000, prefix: 'USR' },
      { tag: 'product', step: 1000, prefix: 'PRD' },
      { tag: 'payment', step: 1000, prefix: 'PAY' },
      { tag: 'default', step: 1000, prefix: 'ID' }
    ];

    for (const tagConfig of defaultTags) {
      await this.registerBizTag(tagConfig.tag, tagConfig.step, tagConfig.prefix);
    }
  }

  async registerBizTag(bizTag, step = 1000, prefix = '') {
    const bizTagPath = `${this.bizTagsPath}/${bizTag}`;
    const segmentPath = `${this.leafBasePath}/${bizTag}`;

    const exists = await new Promise((resolve) => {
      this.zkClient.exists(bizTagPath, (error, stat) => {
        resolve(!!stat);
      });
    });

    if (!exists) {
      const data = JSON.stringify({
        bizTag,
        step,
        prefix,
        maxId: step,
        createTime: Date.now(),
        updateTime: Date.now()
      });

      await Promise.all([
        new Promise((resolve, reject) => {
          this.zkClient.create(bizTagPath, Buffer.from(data), (error) => {
            if (error) return reject(error);
            resolve();
          });
        }),
        new Promise((resolve, reject) => {
          this.zkClient.create(segmentPath, Buffer.from(step.toString()), (error) => {
            if (error) return reject(error);
            resolve();
          });
        })
      ]);

      console.log(`[Leaf] 注册业务Tag: ${bizTag}, step: ${step}, prefix: ${prefix}`);
    }
  }

  async getBizTagConfig(bizTag) {
    const bizTagPath = `${this.bizTagsPath}/${bizTag}`;
    return new Promise((resolve, reject) => {
      this.zkClient.getData(bizTagPath, (error, data) => {
        if (error) return reject(error);
        resolve(JSON.parse(data.toString()));
      });
    });
  }

  async updateMaxId(bizTag, step) {
    const segmentPath = `${this.leafBasePath}/${bizTag}`;
    const bizTagPath = `${this.bizTagsPath}/${bizTag}`;

    return new Promise((resolve, reject) => {
      this.zkClient.getData(segmentPath, (error, data) => {
        if (error) return reject(error);

        const currentMaxId = parseInt(data.toString(), 10);
        const newMaxId = currentMaxId + step;

        this.zkClient.setData(segmentPath, Buffer.from(newMaxId.toString()), -1, (error) => {
          if (error) return reject(error);

          this.zkClient.getData(bizTagPath, (error, bizData) => {
            if (error) return reject(error);
            
            const config = JSON.parse(bizData.toString());
            config.maxId = newMaxId;
            config.updateTime = Date.now();
            
            this.zkClient.setData(bizTagPath, Buffer.from(JSON.stringify(config)), -1, (error) => {
              if (error) return reject(error);
              resolve(newMaxId);
            });
          });
        });
      });
    });
  }

  async loadSegment(bizTag) {
    let segmentBuffer = this.segmentBuffers.get(bizTag);
    
    if (!segmentBuffer) {
      segmentBuffer = new SegmentBuffer(bizTag);
      this.segmentBuffers.set(bizTag, segmentBuffer);
    }

    while (segmentBuffer.lock) {
      await new Promise(resolve => setTimeout(resolve, 10));
    }

    segmentBuffer.lock = true;

    try {
      const config = await this.getBizTagConfig(bizTag);
      const newMaxId = await this.updateMaxId(bizTag, config.step);
      const segment = new Segment(bizTag, newMaxId, config.step);

      if (!segmentBuffer.initOk) {
        segmentBuffer.setCurrentSegment(segment);
        console.log(`[Leaf] ${bizTag} 初始号段加载: ${segment.minId} - ${segment.maxId}`);
      } else {
        segmentBuffer.setNextSegment(segment);
        console.log(`[Leaf] ${bizTag} 下一号段预加载: ${segment.minId} - ${segment.maxId}`);
      }

      this.metrics.segmentLoads++;
      this.emit('segmentLoaded', { bizTag, minId: segment.minId, maxId: segment.maxId });

      return segment;
    } catch (error) {
      this.metrics.loadErrors++;
      console.error(`[Leaf] ${bizTag} 号段加载失败:`, error.message);
      throw error;
    } finally {
      segmentBuffer.lock = false;
      segmentBuffer.isLoadingNext = false;
    }
  }

  async loadNextSegmentIfNeeded(segmentBuffer, bizTag) {
    if (!segmentBuffer.needLoadNextSegment()) {
      return;
    }

    segmentBuffer.isLoadingNext = true;
    
    setImmediate(async () => {
      try {
        await this.loadSegment(bizTag);
      } catch (error) {
        console.error(`[Leaf] 异步预加载号段失败: ${bizTag}`, error.message);
      }
    });
  }

  async nextId(bizTag = 'default') {
    const startTime = process.hrtime();

    if (!this.initialized) {
      throw new Error('Leaf号段管理器未初始化');
    }

    let segmentBuffer = this.segmentBuffers.get(bizTag);
    
    if (!segmentBuffer) {
      await this.loadSegment(bizTag);
      segmentBuffer = this.segmentBuffers.get(bizTag);
    }

    await this.loadNextSegmentIfNeeded(segmentBuffer, bizTag);

    let segment = segmentBuffer.getCurrentSegment();
    let id = segment.nextId();

    if (id === null) {
      while (segmentBuffer.lock) {
        await new Promise(resolve => setTimeout(resolve, 10));
      }

      segmentBuffer.lock = true;

      try {
        segment = segmentBuffer.getCurrentSegment();
        id = segment.nextId();

        if (id === null) {
          if (!segmentBuffer.switchSegment()) {
            console.log(`[Leaf] ${bizTag} 号段耗尽，同步加载...`);
            await this.loadSegment(bizTag);
            segmentBuffer.switchSegment();
          }

          segment = segmentBuffer.getCurrentSegment();
          id = segment.nextId();
          this.metrics.segmentSwitches++;
          
          console.log(`[Leaf] ${bizTag} 切换到新号段: ${segment.minId} - ${segment.maxId}`);
          this.emit('segmentSwitched', { bizTag, minId: segment.minId, maxId: segment.maxId });
        }
      } finally {
        segmentBuffer.lock = false;
      }
    }

    this.metrics.totalIds++;
    
    const diff = process.hrtime(startTime);
    const latencyMs = (diff[0] * 1e9 + diff[1]) / 1e6;

    this.emit('idGenerated', { bizTag, id, latencyMs });

    return id;
  }

  async getSegmentStatus(bizTag = null) {
    if (bizTag) {
      const segmentBuffer = this.segmentBuffers.get(bizTag);
      if (!segmentBuffer) return null;

      const current = segmentBuffer.getCurrentSegment();
      const next = segmentBuffer.getNextSegment();
      const config = await this.getBizTagConfig(bizTag);

      return {
        bizTag,
        prefix: config.prefix,
        step: config.step,
        current: current ? {
          minId: current.minId,
          maxId: current.maxId,
          currentId: current.currentId,
          remaining: current.remaining,
          idlePercentage: current.getIdlePercentage()
        } : null,
        next: next ? {
          minId: next.minId,
          maxId: next.maxId,
          remaining: next.remaining
        } : null,
        isLoadingNext: segmentBuffer.isLoadingNext
      };
    }

    const statuses = {};
    for (const tag of this.segmentBuffers.keys()) {
      statuses[tag] = await this.getSegmentStatus(tag);
    }
    return statuses;
  }

  getMetrics() {
    return { ...this.metrics };
  }

  async getAllBizTags() {
    return new Promise((resolve, reject) => {
      this.zkClient.getChildren(this.bizTagsPath, async (error, children) => {
        if (error) return reject(error);

        const tags = [];
        for (const child of children) {
          try {
            const config = await this.getBizTagConfig(child);
            tags.push(config);
          } catch (e) {
            tags.push({ bizTag: child, error: e.message });
          }
        }
        resolve(tags);
      });
    });
  }
}

module.exports = { Segment, SegmentBuffer, LeafSegmentManager };
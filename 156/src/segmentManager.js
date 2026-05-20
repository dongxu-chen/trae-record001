const { SegmentBuffer } = require('./segmentBuffer');
const config = require('../config');

class SegmentManager {
  constructor(zkClient) {
    this.zkClient = zkClient;
    this.segmentBuffers = new Map();
    this.defaultStep = 1000;
    this.segmentBasePath = config.zookeeper.basePath + '/segments';
    this.workerCapacityPath = config.zookeeper.basePath + '/worker_capacity';
    this.maxWorkerId = config.snowflake.maxWorkerId;
    this.currentWorkerCount = 0;
  }

  async init() {
    await this.ensurePath(this.segmentBasePath);
    await this.ensurePath(this.workerCapacityPath);
    await this.initWorkerCapacity();
    console.log('号段管理器初始化完成');
  }

  async ensurePath(path) {
    return new Promise((resolve, reject) => {
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

  async initWorkerCapacity() {
    const capacityPath = this.workerCapacityPath + '/current';
    return new Promise((resolve, reject) => {
      this.zkClient.exists(capacityPath, (error, stat) => {
        if (error) return reject(error);
        
        if (!stat) {
          this.zkClient.create(capacityPath, Buffer.from('1'), (error) => {
            if (error) return reject(error);
            this.currentWorkerCount = 1;
            console.log(`Worker容量初始化: 1/1024`);
            resolve();
          });
        } else {
          this.zkClient.getData(capacityPath, (error, data) => {
            if (error) return reject(error);
            this.currentWorkerCount = parseInt(data.toString(), 10) || 1;
            console.log(`当前Worker容量: ${this.currentWorkerCount}/1024`);
            resolve();
          });
        }
      });
    });
  }

  async expandWorkerCapacity(targetCount) {
    if (targetCount > this.maxWorkerId + 1) {
      throw new Error(`Worker数量不能超过${this.maxWorkerId + 1}`);
    }
    
    if (targetCount <= this.currentWorkerCount) {
      return this.currentWorkerCount;
    }

    const capacityPath = this.workerCapacityPath + '/current';
    return new Promise((resolve, reject) => {
      this.zkClient.setData(capacityPath, Buffer.from(targetCount.toString()), -1, (error) => {
        if (error) return reject(error);
        this.currentWorkerCount = targetCount;
        console.log(`Worker容量已扩展: ${targetCount}/1024`);
        resolve(targetCount);
      });
    });
  }

  getWorkerCapacity() {
    return {
      current: this.currentWorkerCount,
      max: this.maxWorkerId + 1,
      remaining: this.maxWorkerId + 1 - this.currentWorkerCount
    };
  }

  async getOrCreateSegment(bizType, step = this.defaultStep) {
    if (this.segmentBuffers.has(bizType)) {
      return this.segmentBuffers.get(bizType);
    }

    const segmentPath = `${this.segmentBasePath}/${bizType}`;
    await this.ensurePath(segmentPath);

    const maxIdPath = `${segmentPath}/max_id`;
    
    const firstMaxId = await this.getAndUpdateMaxId(maxIdPath, step);
    
    const segmentBuffer = new SegmentBuffer(bizType, step);
    segmentBuffer.init(firstMaxId);
    
    this.segmentBuffers.set(bizType, segmentBuffer);
    return segmentBuffer;
  }

  async getAndUpdateMaxId(path, step) {
    return new Promise((resolve, reject) => {
      this.zkClient.exists(path, (error, stat) => {
        if (error) return reject(error);
        
        if (!stat) {
          const initialMaxId = step;
          this.zkClient.create(path, Buffer.from(initialMaxId.toString()), (error) => {
            if (error) return reject(error);
            resolve(initialMaxId);
          });
        } else {
          this.zkClient.getData(path, (error, data) => {
            if (error) return reject(error);
            
            const currentMaxId = parseInt(data.toString(), 10) || 0;
            const newMaxId = currentMaxId + step;
            
            this.zkClient.setData(path, Buffer.from(newMaxId.toString()), -1, (error) => {
              if (error) return reject(error);
              resolve(newMaxId);
            });
          });
        }
      });
    });
  }

  async loadNextSegment(bizType, step) {
    const segmentPath = `${this.segmentBasePath}/${bizType}/max_id`;
    return await this.getAndUpdateMaxId(segmentPath, step);
  }

  async nextId(bizType) {
    const segmentBuffer = await this.getOrCreateSegment(bizType);
    const id = await segmentBuffer.nextId((type, step) => this.loadNextSegment(type, step));
    return id;
  }

  getSegmentStatus(bizType) {
    const segmentBuffer = this.segmentBuffers.get(bizType);
    if (!segmentBuffer) {
      return null;
    }
    return segmentBuffer.getStatus();
  }

  getAllSegmentStatus() {
    const status = {};
    for (const [bizType, buffer] of this.segmentBuffers.entries()) {
      status[bizType] = buffer.getStatus();
    }
    return status;
  }
}

module.exports = SegmentManager;
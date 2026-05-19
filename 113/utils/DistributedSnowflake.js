const redis = require('../config/redis');
require('dotenv').config();

class DistributedSnowflake {
  constructor() {
    this.twepoch = 1609459200000n;
    
    this.workerIdBits = 5n;
    this.datacenterIdBits = 5n;
    this.maxWorkerId = -1n ^ (-1n << this.workerIdBits);
    this.maxDatacenterId = -1n ^ (-1n << this.datacenterIdBits);
    this.sequenceBits = 12n;
    
    this.workerIdShift = this.sequenceBits;
    this.datacenterIdShift = this.sequenceBits + this.workerIdBits;
    this.timestampLeftShift = this.sequenceBits + this.workerIdBits + this.datacenterIdBits;
    this.sequenceMask = -1n ^ (-1n << this.sequenceBits);
    
    this.workerId = 0n;
    this.datacenterId = BigInt(process.env.SNOWFLAKE_DATACENTER_ID || 1);
    this.sequence = 0n;
    this.lastTimestamp = -1n;
    
    this.initialized = false;
    this.workerIdKey = process.env.SNOWFLAKE_WORKER_ID_REDIS_KEY || 'snowflake:worker:id';
    this.heartbeatKey = 'snowflake:worker:heartbeat:';
    this.leaseDuration = 60000;
  }

  async init() {
    if (this.initialized) return;
    
    this.workerId = await this.acquireWorkerId();
    console.log(`DistributedSnowflake initialized: datacenter=${this.datacenterId}, worker=${this.workerId}`);
    
    this.startHeartbeat();
    this.initialized = true;
  }

  async acquireWorkerId() {
    const redisKey = this.workerIdKey;
    
    for (let candidateId = 0; candidateId <= Number(this.maxWorkerId); candidateId++) {
      const lockKey = `${redisKey}:lock:${candidateId}`;
      const acquired = await redis.set(lockKey, '1', {
        NX: true,
        PX: this.leaseDuration
      });
      
      if (acquired) {
        await redis.hSet(redisKey, String(candidateId), process.pid.toString());
        console.log(`Acquired worker ID: ${candidateId}`);
        return BigInt(candidateId);
      }
    }
    
    throw new Error('No available worker IDs. Max workers reached.');
  }

  startHeartbeat() {
    setInterval(async () => {
      const lockKey = `${this.workerIdKey}:lock:${this.workerId}`;
      await redis.set(lockKey, process.pid.toString(), {
        PX: this.leaseDuration
      });
    }, this.leaseDuration / 2);
  }

  tilNextMillis(lastTimestamp) {
    let timestamp = this.timeGen();
    while (timestamp <= lastTimestamp) {
      timestamp = this.timeGen();
    }
    return timestamp;
  }

  timeGen() {
    return BigInt(Date.now());
  }

  nextId() {
    if (!this.initialized) {
      throw new Error('Snowflake not initialized. Call init() first.');
    }

    let timestamp = this.timeGen();
    
    if (timestamp < this.lastTimestamp) {
      throw new Error(`Clock moved backwards. Refusing to generate id for ${this.lastTimestamp - timestamp} milliseconds`);
    }
    
    if (this.lastTimestamp === timestamp) {
      this.sequence = (this.sequence + 1n) & this.sequenceMask;
      if (this.sequence === 0n) {
        timestamp = this.tilNextMillis(this.lastTimestamp);
      }
    } else {
      this.sequence = 0n;
    }
    
    this.lastTimestamp = timestamp;
    
    return ((timestamp - this.twepoch) << this.timestampLeftShift) |
           (this.datacenterId << this.datacenterIdShift) |
           (this.workerId << this.workerIdShift) |
           this.sequence;
  }

  nextShortCode() {
    const id = this.nextId();
    return this.idToBase62(id);
  }

  idToBase62(id) {
    const CHARS = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ';
    let num = id;
    let code = '';
    const base = 62n;
    
    while (num > 0n) {
      const remainder = num % base;
      code = CHARS[Number(remainder)] + code;
      num = num / base;
    }
    
    const length = parseInt(process.env.SHORT_CODE_LENGTH) || 8;
    return code.padStart(length, '0');
  }

  parseId(id) {
    const timestamp = (id >> this.timestampLeftShift) + this.twepoch;
    const datacenterId = (id >> this.datacenterIdShift) & this.maxDatacenterId;
    const workerId = (id >> this.workerIdShift) & this.maxWorkerId;
    const sequence = id & this.sequenceMask;
    
    return {
      timestamp: Number(timestamp),
      datacenterId: Number(datacenterId),
      workerId: Number(workerId),
      sequence: Number(sequence),
      date: new Date(Number(timestamp))
    };
  }
}

const snowflake = new DistributedSnowflake();

module.exports = {
  DistributedSnowflake,
  snowflake,
  generateShortCode: () => snowflake.nextShortCode(),
  generateId: () => snowflake.nextId()
};

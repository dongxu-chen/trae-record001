const config = require('../config');

class Snowflake {
  constructor(workerId, onClockBackward = null) {
    this.epoch = config.snowflake.epoch;
    this.workerIdBits = config.snowflake.workerIdBits;
    this.sequenceBits = config.snowflake.sequenceBits;
    this.maxWorkerId = config.snowflake.maxWorkerId;
    this.maxSequence = config.snowflake.maxSequence;
    this.workerIdShift = this.sequenceBits;
    this.timestampShift = this.sequenceBits + this.workerIdBits;
    this.maxClockBackwardMs = 500;
    
    if (workerId > this.maxWorkerId || workerId < 0) {
      throw new Error(`workerId 必须在 0 到 ${this.maxWorkerId} 之间`);
    }
    
    this.workerId = workerId;
    this.sequence = 0;
    this.lastTimestamp = -1;
    this.onClockBackward = onClockBackward;
  }
  
  tilNextMillis(lastTimestamp) {
    let timestamp = this.currentTimestamp();
    while (timestamp <= lastTimestamp) {
      timestamp = this.currentTimestamp();
    }
    return timestamp;
  }
  
  currentTimestamp() {
    return Date.now();
  }
  
  async waitForClockCatchup(offsetMs) {
    return new Promise((resolve) => {
      setTimeout(resolve, offsetMs);
    });
  }
  
  async nextId() {
    let timestamp = this.currentTimestamp();
    
    if (timestamp < this.lastTimestamp) {
      const offset = this.lastTimestamp - timestamp;
      
      if (offset <= this.maxClockBackwardMs) {
        console.log(`时钟回拨 ${offset}ms，等待恢复...`);
        await this.waitForClockCatchup(offset);
        timestamp = this.currentTimestamp();
        
        if (timestamp < this.lastTimestamp) {
          throw new Error(`时钟回拨等待后仍未恢复，回拨时间: ${offset}ms`);
        }
      } else {
        console.log(`时钟回拨 ${offset}ms，超过阈值，尝试重新获取Worker ID...`);
        if (this.onClockBackward) {
          const newWorkerId = await this.onClockBackward(this.workerId, offset);
          if (newWorkerId !== null && newWorkerId !== undefined) {
            this.workerId = newWorkerId;
            this.lastTimestamp = -1;
            this.sequence = 0;
            console.log(`成功切换到新Worker ID: ${newWorkerId}`);
            return this.nextId();
          }
        }
        throw new Error(`时钟回拨超过阈值，回拨时间: ${offset}ms`);
      }
    }
    
    if (this.lastTimestamp === timestamp) {
      this.sequence = (this.sequence + 1) & this.maxSequence;
      if (this.sequence === 0) {
        timestamp = this.tilNextMillis(this.lastTimestamp);
      }
    } else {
      this.sequence = 0;
    }
    
    this.lastTimestamp = timestamp;
    
    const id = BigInt(timestamp - this.epoch) << BigInt(this.timestampShift) |
               BigInt(this.workerId) << BigInt(this.workerIdShift) |
               BigInt(this.sequence);
    
    return id.toString();
  }
  
  parseId(id) {
    const idBigInt = BigInt(id);
    const timestamp = Number((idBigInt >> BigInt(this.timestampShift)) & BigInt((1n << 41n) - 1n)) + this.epoch;
    const workerId = Number((idBigInt >> BigInt(this.workerIdShift)) & BigInt(this.maxWorkerId));
    const sequence = Number(idBigInt & BigInt(this.maxSequence));
    
    return {
      id: id,
      timestamp: timestamp,
      date: new Date(timestamp).toISOString(),
      workerId: workerId,
      sequence: sequence
    };
  }
  
  getWorkerId() {
    return this.workerId;
  }
}

module.exports = Snowflake;
class Snowflake {
  constructor(workerId = 1, datacenterId = 1) {
    this.twepoch = 1609459200000;
    
    this.workerIdBits = 5;
    this.datacenterIdBits = 5;
    this.maxWorkerId = -1 ^ (-1 << this.workerIdBits);
    this.maxDatacenterId = -1 ^ (-1 << this.datacenterIdBits);
    this.sequenceBits = 12;
    
    this.workerIdShift = this.sequenceBits;
    this.datacenterIdShift = this.sequenceBits + this.workerIdBits;
    this.timestampLeftShift = this.sequenceBits + this.workerIdBits + this.datacenterIdBits;
    this.sequenceMask = -1 ^ (-1 << this.sequenceBits);
    
    if (workerId > this.maxWorkerId || workerId < 0) {
      throw new Error(`worker Id can't be greater than ${this.maxWorkerId} or less than 0`);
    }
    if (datacenterId > this.maxDatacenterId || datacenterId < 0) {
      throw new Error(`datacenter Id can't be greater than ${this.maxDatacenterId} or less than 0`);
    }
    
    this.workerId = workerId;
    this.datacenterId = datacenterId;
    this.sequence = 0;
    this.lastTimestamp = -1;
  }

  tilNextMillis(lastTimestamp) {
    let timestamp = this.timeGen();
    while (timestamp <= lastTimestamp) {
      timestamp = this.timeGen();
    }
    return timestamp;
  }

  timeGen() {
    return Date.now();
  }

  nextId() {
    let timestamp = this.timeGen();
    
    if (timestamp < this.lastTimestamp) {
      throw new Error(`Clock moved backwards. Refusing to generate id for ${this.lastTimestamp - timestamp} milliseconds`);
    }
    
    if (this.lastTimestamp === timestamp) {
      this.sequence = (this.sequence + 1) & this.sequenceMask;
      if (this.sequence === 0) {
        timestamp = this.tilNextMillis(this.lastTimestamp);
      }
    } else {
      this.sequence = 0;
    }
    
    this.lastTimestamp = timestamp;
    
    return ((timestamp - this.twepoch) << this.timestampLeftShift) |
           (this.datacenterId << this.datacenterIdShift) |
           (this.workerId << this.workerIdShift) |
           this.sequence;
  }
}

const CHARS = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ';

const idToShortCode = (id) => {
  let num = BigInt(id);
  let code = '';
  const base = BigInt(CHARS.length);
  
  while (num > 0) {
    const remainder = num % base;
    code = CHARS[Number(remainder)] + code;
    num = num / base;
  }
  
  return code.padStart(8, '0');
};

const snowflake = new Snowflake(1, 1);

const generateUniqueShortCode = () => {
  const id = snowflake.nextId();
  return idToShortCode(id);
};

module.exports = { Snowflake, generateUniqueShortCode };
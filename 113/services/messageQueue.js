const redis = require('../config/redis');

const QUEUE_KEY = 'analytics:queue';
const BATCH_SIZE = 100;
const FLUSH_INTERVAL = 5000;

class MessageQueue {
  constructor() {
    this.batch = [];
    this.flushTimer = null;
  }

  async enqueue(message) {
    await redis.rPush(QUEUE_KEY, JSON.stringify(message));
  }

  async dequeue(count = BATCH_SIZE) {
    const messages = await redis.lRange(QUEUE_KEY, 0, count - 1);
    if (messages.length > 0) {
      await redis.lTrim(QUEUE_KEY, messages.length, -1);
    }
    return messages.map(msg => JSON.parse(msg));
  }

  async getQueueLength() {
    return await redis.lLen(QUEUE_KEY);
  }

  async clearQueue() {
    await redis.del(QUEUE_KEY);
  }
}

module.exports = new MessageQueue();
const { clickhouse } = require('../config/clickhouse');
const messageQueue = require('./messageQueue');

const BATCH_SIZE = 500;
const CONSUME_INTERVAL = 3000;
const MAX_RETRY = 3;

class BatchConsumer {
  constructor() {
    this.isRunning = false;
    this.timer = null;
  }

  async processBatch() {
    try {
      const messages = await messageQueue.dequeue(BATCH_SIZE);
      
      if (messages.length === 0) {
        return;
      }

      console.log(`Consuming ${messages.length} analytics records...`);

      await clickhouse.insert({
        table: 'access_logs',
        values: messages,
        format: 'JSONEachRow'
      });

      console.log(`Successfully inserted ${messages.length} records`);
    } catch (error) {
      console.error('Batch consumption error:', error);
    }
  }

  start() {
    if (this.isRunning) {
      console.log('Batch consumer already running');
      return;
    }

    this.isRunning = true;
    console.log('Batch consumer started');

    this.timer = setInterval(async () => {
      await this.processBatch();
    }, CONSUME_INTERVAL);

    this.processBatch();
  }

  stop() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
    this.isRunning = false;
    console.log('Batch consumer stopped');
  }

  async flush() {
    let queueLength = await messageQueue.getQueueLength();
    while (queueLength > 0) {
      console.log(`Flushing remaining ${queueLength} records...`);
      await this.processBatch();
      queueLength = await messageQueue.getQueueLength();
    }
  }
}

module.exports = new BatchConsumer();
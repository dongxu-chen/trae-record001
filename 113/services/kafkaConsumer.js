const { consumer, initConsumer } = require('../config/kafka');
const { clickhouse } = require('../config/clickhouse');
require('dotenv').config();

const BATCH_SIZE = 1000;
const FLUSH_INTERVAL = 3000;

class KafkaClickHouseConsumer {
  constructor() {
    this.running = false;
    this.heatmapBatch = [];
    this.accessBatch = [];
    this.flushTimer = null;
    this.stats = {
      totalConsumed: 0,
      totalInserted: 0,
      heatmapBatches: 0,
      accessBatches: 0,
      avgLatency: 0
    };
  }

  async start() {
    if (this.running) return;
    
    const topics = [
      process.env.KAFKA_TOPIC_HEATMAP || 'heatmap-clicks',
      process.env.KAFKA_TOPIC_ACCESS || 'access-logs'
    ];
    
    await initConsumer(topics);
    
    this.running = true;
    this.startPeriodicFlush();
    
    console.log('Kafka ClickHouse Consumer started');
    
    await consumer.run({
      eachMessage: async ({ topic, partition, message }) => {
        await this.handleMessage(topic, message);
      }
    });
  }

  async handleMessage(topic, message) {
    try {
      const data = JSON.parse(message.value.toString());
      const now = Date.now();
      const latency = now - (data._producerTimestamp || now);
      
      this.stats.avgLatency = (this.stats.avgLatency * this.stats.totalConsumed + latency) / 
                              (this.stats.totalConsumed + 1);
      this.stats.totalConsumed++;
      
      if (topic === process.env.KAFKA_TOPIC_HEATMAP) {
        this.heatmapBatch.push(this.normalizeHeatmapData(data));
      } else if (topic === process.env.KAFKA_TOPIC_ACCESS) {
        this.accessBatch.push(this.normalizeAccessData(data));
      }
      
      if (this.heatmapBatch.length >= BATCH_SIZE || this.accessBatch.length >= BATCH_SIZE) {
        await this.flush();
      }
      
      if (this.stats.totalConsumed % 1000 === 0) {
        console.log(`Consumer progress: ${this.stats.totalConsumed} messages, avg latency: ${Math.round(this.stats.avgLatency)}ms`);
      }
      
    } catch (error) {
      console.error('Error handling Kafka message:', error.message);
    }
  }

  normalizeHeatmapData(data) {
    return {
      fingerprint: data.fingerprint || '',
      session_id: data.sessionId || '',
      url: data.pageInfo?.url || '',
      path: data.path || data.pageInfo?.path || '/',
      x: data.x || 0,
      y: data.y || 0,
      absolute_x: data.absoluteX || data.x || 0,
      absolute_y: data.absoluteY || data.y || 0,
      scroll_x: data.scrollX || 0,
      scroll_y: data.scrollY || 0,
      viewport_width: data.pageInfo?.viewportWidth || 0,
      viewport_height: data.pageInfo?.viewportHeight || 0,
      target: data.target || '',
      target_id: data.id || '',
      target_class: data.className || ''
    };
  }

  normalizeAccessData(data) {
    return {
      short_code: data.shortCode || '',
      long_url: data.longUrl || '',
      ip: data.ip || '',
      user_agent: data.userAgent || '',
      referer: data.referer || '',
      country: data.country || '',
      region: data.region || '',
      city: data.city || '',
      browser: data.browser || '',
      os: data.os || '',
      device: data.device || ''
    };
  }

  startPeriodicFlush() {
    this.flushTimer = setInterval(async () => {
      if (this.heatmapBatch.length > 0 || this.accessBatch.length > 0) {
        await this.flush();
      }
    }, FLUSH_INTERVAL);
  }

  async flush() {
    try {
      const promises = [];
      
      if (this.heatmapBatch.length > 0) {
        promises.push(this.insertHeatmapBatch());
      }
      
      if (this.accessBatch.length > 0) {
        promises.push(this.insertAccessBatch());
      }
      
      await Promise.all(promises);
      
    } catch (error) {
      console.error('Flush error:', error);
    }
  }

  async insertHeatmapBatch() {
    try {
      await clickhouse.insert({
        table: 'heatmap_clicks',
        values: this.heatmapBatch,
        format: 'JSONEachRow'
      });
      
      this.stats.totalInserted += this.heatmapBatch.length;
      this.stats.heatmapBatches++;
      
      console.log(`Inserted ${this.heatmapBatch.length} heatmap records into ClickHouse`);
      this.heatmapBatch = [];
      
    } catch (error) {
      console.error('Error inserting heatmap batch:', error.message);
    }
  }

  async insertAccessBatch() {
    try {
      await clickhouse.insert({
        table: 'access_logs',
        values: this.accessBatch,
        format: 'JSONEachRow'
      });
      
      this.stats.totalInserted += this.accessBatch.length;
      this.stats.accessBatches++;
      
      console.log(`Inserted ${this.accessBatch.length} access records into ClickHouse`);
      this.accessBatch = [];
      
    } catch (error) {
      console.error('Error inserting access batch:', error.message);
    }
  }

  async stop() {
    this.running = false;
    
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
    }
    
    await this.flush();
    await consumer.stop();
    
    console.log('Kafka ClickHouse Consumer stopped');
    console.log(`Stats: consumed=${this.stats.totalConsumed}, inserted=${this.stats.totalInserted}, avg latency=${Math.round(this.stats.avgLatency)}ms`);
  }
}

const consumerInstance = new KafkaClickHouseConsumer();

process.on('SIGINT', async () => {
  await consumerInstance.stop();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  await consumerInstance.stop();
  process.exit(0);
});

if (require.main === module) {
  consumerInstance.start().catch(console.error);
}

module.exports = consumerInstance;

const { flinkConsumer, initFlinkConsumer } = require('../config/kafka');
const redis = require('../config/redis');
require('dotenv').config();

const WINDOW_SECONDS = parseInt(process.env.REALTIME_AGGREGATE_WINDOW_SECONDS) || 10;
const EXPIRE_SECONDS = parseInt(process.env.REALTIME_HEATMAP_EXPIRE_SECONDS) || 3600;
const GRID_SIZE = 20;

class FlinkRealTimeAggregator {
  constructor() {
    this.windows = new Map();
    this.running = false;
    this.stats = {
      totalProcessed: 0,
      totalWindows: 0,
      avgLatency: 0
    };
  }

  async start() {
    if (this.running) return;
    
    const topics = [
      process.env.KAFKA_TOPIC_HEATMAP || 'heatmap-clicks'
    ];
    
    await initFlinkConsumer(topics);
    
    this.running = true;
    console.log('Flink Real-time Aggregator started');
    
    this.startWindowProcessing();
    
    await flinkConsumer.run({
      eachMessage: async ({ topic, partition, message }) => {
        await this.processMessage(message);
      }
    });
  }

  async processMessage(message) {
    try {
      const data = JSON.parse(message.value.toString());
      const now = Date.now();
      const latency = now - (data._producerTimestamp || now);
      
      this.stats.avgLatency = (this.stats.avgLatency * this.stats.totalProcessed + latency) / 
                              (this.stats.totalProcessed + 1);
      this.stats.totalProcessed++;
      
      const windowKey = this.getWindowKey(data.path || 'global');
      
      if (!this.windows.has(windowKey)) {
        this.windows.set(windowKey, {
          startTime: now,
          heatmap: new Map(),
          uvSet: new Set(),
          mvSet: new Set(),
          clicks: 0,
          targets: new Map()
        });
      }
      
      const window = this.windows.get(windowKey);
      
      const gridX = Math.floor((data.absoluteX || data.x || 0) / GRID_SIZE) * GRID_SIZE;
      const gridY = Math.floor((data.absoluteY || data.y || 0) / GRID_SIZE) * GRID_SIZE;
      const pointKey = `${gridX},${gridY}`;
      
      window.heatmap.set(pointKey, (window.heatmap.get(pointKey) || 0) + 1);
      window.uvSet.add(data.fingerprint);
      window.mvSet.add(`${data.fingerprint}:${data.sessionId}`);
      window.clicks++;
      
      if (data.target) {
        const targetKey = `${data.target}:${data.id || ''}:${data.className || ''}`;
        window.targets.set(targetKey, (window.targets.get(targetKey) || 0) + 1);
      }
      
      if (this.stats.totalProcessed % 1000 === 0) {
        console.log(`Flink processed: ${this.stats.totalProcessed}, avg latency: ${Math.round(this.stats.avgLatency)}ms`);
      }
      
    } catch (error) {
      console.error('Error processing Kafka message:', error.message);
    }
  }

  getWindowKey(path) {
    const now = Date.now();
    const windowStart = Math.floor(now / (WINDOW_SECONDS * 1000)) * WINDOW_SECONDS * 1000;
    return `${path}:${windowStart}`;
  }

  startWindowProcessing() {
    setInterval(async () => {
      await this.processWindows();
    }, WINDOW_SECONDS * 1000);
  }

  async processWindows() {
    const now = Date.now();
    const windowCutoff = now - (WINDOW_SECONDS * 1000);
    
    for (const [windowKey, window] of this.windows.entries()) {
      if (window.startTime < windowCutoff) {
        await this.flushWindow(windowKey, window);
        this.windows.delete(windowKey);
        this.stats.totalWindows++;
      }
    }
  }

  async flushWindow(windowKey, window) {
    try {
      const [path, timestamp] = windowKey.split(':');
      const now = Date.now();
      
      const pipeline = redis.pipeline();
      
      const heatmapKey = `realtime:heatmap:${path}`;
      for (const [pointKey, count] of window.heatmap.entries()) {
        pipeline.hIncrBy(heatmapKey, pointKey, count);
      }
      pipeline.expire(heatmapKey, EXPIRE_SECONDS);
      
      const uvmKey = `realtime:uvm:${path}`;
      pipeline.hIncrBy(uvmKey, 'uv', window.uvSet.size);
      pipeline.hIncrBy(uvmKey, 'mv', window.mvSet.size);
      pipeline.hIncrBy(uvmKey, 'clicks', window.clicks);
      pipeline.hSet(uvmKey, 'lastUpdate', now.toString());
      pipeline.expire(uvmKey, EXPIRE_SECONDS);
      
      const targetsKey = `realtime:targets:${path}`;
      for (const [targetKey, count] of window.targets.entries()) {
        pipeline.hIncrBy(targetsKey, targetKey, count);
      }
      pipeline.expire(targetsKey, EXPIRE_SECONDS);
      
      const globalKey = 'realtime:uvm:global';
      pipeline.hIncrBy(globalKey, 'uv', window.uvSet.size);
      pipeline.hIncrBy(globalKey, 'mv', window.mvSet.size);
      pipeline.hIncrBy(globalKey, 'clicks', window.clicks);
      pipeline.expire(globalKey, EXPIRE_SECONDS);
      
      pipeline.set(`realtime:latency:last`, Math.round(this.stats.avgLatency));
      
      await pipeline.exec();
      
      console.log(`Window flushed: ${path}, clicks=${window.clicks}, uv=${window.uvSet.size}, latency=${Math.round(this.stats.avgLatency)}ms`);
      
    } catch (error) {
      console.error('Error flushing window:', error);
    }
  }

  stop() {
    this.running = false;
    flinkConsumer.stop();
    console.log('Flink Real-time Aggregator stopped');
  }
}

const aggregator = new FlinkRealTimeAggregator();

process.on('SIGINT', async () => {
  aggregator.stop();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  aggregator.stop();
  process.exit(0);
});

if (require.main === module) {
  aggregator.start().catch(console.error);
}

module.exports = aggregator;

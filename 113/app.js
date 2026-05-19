const express = require('express');
const cors = require('cors');
const path = require('path');
require('dotenv').config();

const { initClickHouse } = require('./config/clickhouse');
const { initProducer, disconnectProducer } = require('./config/kafka');
const { snowflake } = require('./utils/DistributedSnowflake');
const analyticsMiddleware = require('./middlewares/analytics');
const { redirectToLongUrl } = require('./controllers/shortlinkController');
const shortlinkRoutes = require('./routes/shortlink');
const statsRoutes = require('./routes/stats');
const heatmapRoutes = require('./routes/heatmap');
const ttlService = require('./services/ttlService');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, 'public')));

app.use('/api/shortlink', shortlinkRoutes);
app.use('/api/stats', statsRoutes);
app.use('/api/heatmap', heatmapRoutes);

app.get('/demo', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'demo.html'));
});

app.get('/:shortCode', analyticsMiddleware, redirectToLongUrl);

app.get('/', (req, res) => {
  res.json({
    message: 'Shortlink Analytics System v4.0',
    architecture: 'Snowflake + Kafka + Flink + ClickHouse + Redis',
    features: [
      'Distributed Snowflake unique shortcode generation',
      'Kafka message queue for async analytics processing',
      'Real-time window aggregation (Flink-style processing)',
      'Dual-read architecture: Redis (realtime) + ClickHouse (historical)',
      'ClickHouse materialized views for hourly/daily stats',
      '1-year TTL for shortlinks',
      'Canvas fingerprinting for UVM analysis',
      'Real-time heatmap visualization < 3s end-to-end latency'
    ],
    endpoints: {
      createShortlink: 'POST /api/shortlink/create { longUrl: string }',
      getStats: 'GET /api/stats?shortCode=&startDate=&endDate=',
      heatmapTrack: 'POST /api/heatmap/track',
      heatmapData: 'GET /api/heatmap/data?path=',
      uvmStats: 'GET /api/heatmap/uvm-stats',
      heatmapOverlay: 'POST /api/heatmap/overlay',
      demo: 'GET /demo',
      redirect: 'GET /:shortCode'
    }
  });
});

(async () => {
  await initClickHouse();
  
  try {
    await initProducer();
    console.log('Kafka Producer initialized');
  } catch (e) {
    console.warn('Kafka Producer init failed, running in fallback mode:', e.message);
  }
  
  try {
    await snowflake.init();
    console.log('Snowflake ID generator initialized');
  } catch (e) {
    console.warn('Snowflake init failed, will use simple shortcode:', e.message);
  }
  
  ttlService.startCleanupScheduler();
  
  app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
    console.log(`Demo available at http://localhost:${PORT}/demo`);
  });
})();

process.on('SIGTERM', async () => {
  console.log('SIGTERM received, shutting down gracefully...');
  ttlService.stopCleanupScheduler();
  await disconnectProducer();
  process.exit(0);
});

process.on('SIGINT', async () => {
  console.log('SIGINT received, shutting down gracefully...');
  ttlService.stopCleanupScheduler();
  await disconnectProducer();
  process.exit(0);
});
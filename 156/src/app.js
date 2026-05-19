const express = require('express');
const config = require('../config');
const ZooKeeperManager = require('./zookeeperManager');
const { LeafSegmentManager } = require('./leafSegmentManager');
const IDFormatter = require('./idFormatter');
const MetricsCollector = require('./metricsCollector');
const leafRoutes = require('./routes/leafRoutes');

const app = express();
const zkManager = new ZooKeeperManager();
let leafManager = null;
let idFormatter = null;
let metrics = null;

app.use(express.json());

app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    version: '2.0.0',
    mode: 'leaf-segment',
    zkConnected: zkManager.getConnectionState(),
    timestamp: Date.now()
  });
});

async function setupMetrics() {
  metrics = new MetricsCollector();
  console.log('[Metrics] Prometheus指标收集器已初始化');
  
  zkManager.client.on('state', (state) => {
    metrics.setZkConnectionStatus(state === 'connected' || state === 'syncConnected');
  });
}

function setupLeafEvents() {
  leafManager.on('idGenerated', ({ bizTag, id, latencyMs }) => {
    metrics.recordIdGenerated(bizTag, latencyMs);
  });

  leafManager.on('segmentLoaded', ({ bizTag }) => {
    metrics.recordSegmentLoad(bizTag);
  });

  leafManager.on('segmentSwitched', ({ bizTag }) => {
    metrics.recordSegmentSwitch(bizTag);
    
    setImmediate(async () => {
      try {
        const status = await leafManager.getSegmentStatus(bizTag);
        if (status && status.current) {
          metrics.recordSegmentRemaining(bizTag, status.current.remaining);
        }
      } catch (error) {
        console.error('[Metrics] 更新剩余ID数失败:', error.message);
      }
    });
  });

  setInterval(async () => {
    try {
      const statuses = await leafManager.getSegmentStatus();
      for (const bizTag in statuses) {
        if (statuses[bizTag] && statuses[bizTag].current) {
          metrics.recordSegmentRemaining(bizTag, statuses[bizTag].current.remaining);
        }
      }
    } catch (error) {
      console.error('[Metrics] 定期更新剩余ID数失败:', error.message);
    }
  }, 5000);
}

async function startServer() {
  try {
    console.log('='.repeat(60));
    console.log('  Leaf 分布式ID生成器 - 号段模式');
    console.log('='.repeat(60));

    console.log('\n[1/5] 正在连接ZooKeeper...');
    await zkManager.connect();
    console.log('[OK] ZooKeeper连接成功');

    console.log('\n[2/5] 正在初始化Leaf号段管理器...');
    leafManager = new LeafSegmentManager(zkManager.client);
    await leafManager.init();
    console.log('[OK] Leaf号段管理器初始化成功');

    console.log('\n[3/5] 正在初始化ID格式化器...');
    idFormatter = new IDFormatter();
    console.log('[OK] ID格式化器初始化成功');

    console.log('\n[4/5] 正在初始化Prometheus监控...');
    await setupMetrics();
    setupLeafEvents();
    console.log('[OK] Prometheus监控初始化成功');

    console.log('\n[5/5] 正在注册路由...');
    app.use('/api/v1/id', leafRoutes(leafManager, idFormatter, metrics));
    console.log('[OK] 路由注册成功');

    const port = config.server.port;
    app.listen(port, () => {
      console.log('\n' + '='.repeat(60));
      console.log(`  服务已启动 - 端口: ${port}`);
      console.log('='.repeat(60));
      console.log('\nAPI 端点:');
      console.log(`  GET /health`);
      console.log(`  GET /api/v1/id/next?bizTag=order&format=1`);
      console.log(`  GET /api/v1/id/batch/100?bizTag=user`);
      console.log(`  GET /api/v1/id/segment/status`);
      console.log(`  GET /api/v1/id/biz/tags`);
      console.log(`  POST /api/v1/id/biz/register`);
      console.log(`  GET /api/v1/id/metrics          - Prometheus指标`);
      console.log(`  GET /api/v1/id/metrics/json     - JSON格式指标`);
      console.log(`  GET /api/v1/id/benchmark/10000  - 性能压测`);
      console.log('\n默认业务Tag: order, user, product, payment, default');
      console.log('\n' + '='.repeat(60));
    });

  } catch (error) {
    console.error('\n[ERROR] 启动服务失败:', error.message);
    console.error(error.stack);
    process.exit(1);
  }
}

process.on('SIGINT', () => {
  console.log('\n正在关闭服务...');
  zkManager.close();
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('\n正在关闭服务...');
  zkManager.close();
  process.exit(0);
});

startServer();
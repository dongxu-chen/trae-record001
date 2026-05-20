const express = require('express');
const router = express.Router();
const { benchmarkRateLimit } = require('../middleware/tokenBucket');

module.exports = (leafManager, idFormatter, metrics) => {
  const measureRequest = (req, res, next) => {
    const start = process.hrtime();
    const end = res.end;
    res.end = function(...args) {
      const diff = process.hrtime(start);
      const latencyMs = (diff[0] * 1e9 + diff[1]) / 1e6;
      metrics.recordHttpRequest(
        req.method,
        req.route ? req.route.path : req.path,
        res.statusCode,
        latencyMs
      );
      end.apply(this, args);
    };
    next();
  };

  router.get('/next', measureRequest, async (req, res) => {
    try {
      const bizTag = req.query.bizTag || 'default';
      const format = req.query.format;

      const id = await leafManager.nextId(bizTag);
      
      const result = {
        success: true,
        id: id.toString(),
        bizTag: bizTag,
        idType: 'segment'
      };

      if (format) {
        const config = await leafManager.getBizTagConfig(bizTag);
        result.prefix = config.prefix;
        result.formattedId = idFormatter.format(id, bizTag);
        result.shortId = idFormatter.shortId(id, bizTag);
        result.humanReadable = idFormatter.humanReadable(id, bizTag);
      }

      res.json(result);
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  });

  router.get('/batch/:count', measureRequest, async (req, res) => {
    try {
      const count = parseInt(req.params.count, 10);
      const bizTag = req.query.bizTag || 'default';
      const format = req.query.format;

      if (isNaN(count) || count <= 0 || count > 10000) {
        return res.status(400).json({
          success: false,
          error: '数量必须在1-10000之间'
        });
      }

      const ids = [];
      for (let i = 0; i < count; i++) {
        ids.push(await leafManager.nextId(bizTag));
      }

      const result = {
        success: true,
        count: ids.length,
        bizTag: bizTag,
        ids: ids.map(id => id.toString())
      };

      if (format) {
        const config = await leafManager.getBizTagConfig(bizTag);
        result.prefix = config.prefix;
        result.formattedIds = ids.map(id => idFormatter.format(id, bizTag));
      }

      res.json(result);
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  });

  router.get('/segment/status', measureRequest, async (req, res) => {
    try {
      const bizTag = req.query.bizTag;
      const status = await leafManager.getSegmentStatus(bizTag);
      
      res.json({
        success: true,
        data: status
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  });

  router.get('/biz/tags', measureRequest, async (req, res) => {
    try {
      const tags = await leafManager.getAllBizTags();
      
      res.json({
        success: true,
        data: tags
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  });

  router.post('/biz/register', measureRequest, async (req, res) => {
    try {
      const { bizTag, step = 1000, prefix = '' } = req.body;
      
      if (!bizTag) {
        return res.status(400).json({
          success: false,
          error: 'bizTag不能为空'
        });
      }

      await leafManager.registerBizTag(bizTag, step, prefix);
      
      res.json({
        success: true,
        message: `业务Tag ${bizTag} 注册成功`,
        data: { bizTag, step, prefix }
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  });

  router.get('/metrics', async (req, res) => {
    try {
      res.set('Content-Type', metrics.getContentType());
      res.end(await metrics.getMetrics());
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  });

  router.get('/metrics/json', measureRequest, (req, res) => {
    try {
      const metricsData = metrics.getMetricsJSON();
      const leafMetrics = leafManager.getMetrics();
      
      res.json({
        success: true,
        timestamp: Date.now(),
        prometheus: metricsData,
        leaf: leafMetrics,
        qpsStats: metrics.getQPSStats()
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  });

  router.get('/benchmark/:count', benchmarkRateLimit, measureRequest, async (req, res) => {
    try {
      const count = parseInt(req.params.count, 10);
      const bizTag = req.query.bizTag || 'default';

      if (isNaN(count) || count <= 0 || count > 1000000) {
        return res.status(400).json({
          success: false,
          error: '数量必须在1-1000000之间'
        });
      }

      const startTime = process.hrtime();
      for (let i = 0; i < count; i++) {
        await leafManager.nextId(bizTag);
      }
      const diff = process.hrtime(startTime);
      const elapsedMs = (diff[0] * 1e9 + diff[1]) / 1e6;
      const throughput = Math.round(count / (elapsedMs / 1000));

      res.json({
        success: true,
        benchmark: {
          type: 'leaf-segment',
          bizTag: bizTag,
          count: count,
          elapsedMs: Math.round(elapsedMs * 100) / 100,
          throughputPerSecond: throughput,
          avgNsPerId: Math.round((elapsedMs * 1e6) / count)
        }
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  });

  return router;
};
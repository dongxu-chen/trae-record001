const express = require('express');
const router = express.Router();
const { benchmarkRateLimit } = require('../middleware/tokenBucket');

module.exports = (snowflake, segmentManager, idFormatter) => {
  router.get('/next', async (req, res) => {
    try {
      const bizType = req.query.bizType || 'default';
      const format = req.query.format;
      
      const id = await snowflake.nextId();
      
      let result = {
        success: true,
        id: id,
        workerId: snowflake.getWorkerId(),
        bizType: bizType
      };

      if (format) {
        result.formattedId = idFormatter.format(id, bizType);
        result.shortId = idFormatter.shortId(id, bizType);
        result.humanReadable = idFormatter.humanReadable(id, bizType);
      }

      res.json(result);
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  });

  router.get('/segment/next', async (req, res) => {
    try {
      const bizType = req.query.bizType || 'default';
      const format = req.query.format;
      const step = parseInt(req.query.step, 10) || 1000;

      const id = await segmentManager.nextId(bizType, step);

      let result = {
        success: true,
        id: id,
        bizType: bizType,
        idType: 'segment'
      };

      if (format) {
        result.formattedId = idFormatter.format(id, bizType);
        result.shortId = idFormatter.shortId(id, bizType);
        result.humanReadable = idFormatter.humanReadable(id, bizType);
      }

      res.json(result);
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  });

  router.get('/segment/batch/:count', async (req, res) => {
    try {
      const count = parseInt(req.params.count, 10);
      const bizType = req.query.bizType || 'default';
      
      if (isNaN(count) || count <= 0 || count > 10000) {
        return res.status(400).json({
          success: false,
          error: '数量必须在1-10000之间'
        });
      }

      const ids = [];
      for (let i = 0; i < count; i++) {
        ids.push(await segmentManager.nextId(bizType));
      }

      res.json({
        success: true,
        count: ids.length,
        bizType: bizType,
        ids: ids
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  });

  router.get('/segment/status', async (req, res) => {
    try {
      const bizType = req.query.bizType;
      
      let status;
      if (bizType) {
        status = segmentManager.getSegmentStatus(bizType);
      } else {
        status = segmentManager.getAllSegmentStatus();
      }

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

  router.get('/worker/capacity', (req, res) => {
    try {
      const capacity = segmentManager.getWorkerCapacity();
      res.json({
        success: true,
        data: capacity
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  });

  router.post('/worker/expand', async (req, res) => {
    try {
      const targetCount = parseInt(req.body.targetCount, 10);
      
      if (isNaN(targetCount) || targetCount <= 0) {
        return res.status(400).json({
          success: false,
          error: '请提供有效的目标数量'
        });
      }

      const result = await segmentManager.expandWorkerCapacity(targetCount);
      
      res.json({
        success: true,
        data: {
          newCapacity: result,
          maxCapacity: segmentManager.maxWorkerId + 1
        }
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  });

  router.get('/batch/:count', async (req, res) => {
    try {
      const count = parseInt(req.params.count, 10);
      const bizType = req.query.bizType || 'default';
      const format = req.query.format;
      
      if (isNaN(count) || count <= 0 || count > 10000) {
        return res.status(400).json({
          success: false,
          error: '数量必须在1-10000之间'
        });
      }

      const ids = [];
      for (let i = 0; i < count; i++) {
        const id = await snowflake.nextId();
        ids.push(id);
      }

      const result = {
        success: true,
        count: ids.length,
        ids: ids
      };

      if (format) {
        result.formattedIds = ids.map(id => idFormatter.format(id, bizType));
      }

      res.json(result);
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  });

  router.get('/parse/:id', (req, res) => {
    try {
      const id = req.params.id;
      const parsed = snowflake.parseId(id);
      const formattedParse = idFormatter.parse(id);
      
      res.json({
        success: true,
        data: {
          snowflake: parsed,
          formatted: formattedParse
        }
      });
    } catch (error) {
      try {
        const formattedParse = idFormatter.parse(req.params.id);
        res.json({
          success: true,
          data: {
            formatted: formattedParse
          }
        });
      } catch (e) {
        res.status(400).json({
          success: false,
          error: '无效的ID格式'
        });
      }
    }
  });

  router.get('/format/:id', (req, res) => {
    try {
      const id = req.params.id;
      const bizType = req.query.bizType || 'default';
      
      res.json({
        success: true,
        data: {
          original: id,
          formatted: idFormatter.format(BigInt(id), bizType),
          short: idFormatter.shortId(BigInt(id), bizType),
          humanReadable: idFormatter.humanReadable(BigInt(id), bizType)
        }
      });
    } catch (error) {
      res.status(400).json({
        success: false,
        error: error.message
      });
    }
  });

  router.get('/benchmark/:count', benchmarkRateLimit, async (req, res) => {
    try {
      const count = parseInt(req.params.count, 10);
      const type = req.query.type || 'snowflake';
      
      if (isNaN(count) || count <= 0 || count > 1000000) {
        return res.status(400).json({
          success: false,
          error: '数量必须在1-1000000之间'
        });
      }

      const startTime = process.hrtime();
      
      if (type === 'segment') {
        for (let i = 0; i < count; i++) {
          await segmentManager.nextId('benchmark');
        }
      } else {
        for (let i = 0; i < count; i++) {
          await snowflake.nextId();
        }
      }
      
      const diff = process.hrtime(startTime);
      const elapsedMs = (diff[0] * 1e9 + diff[1]) / 1e6;
      const throughput = Math.round(count / (elapsedMs / 1000));

      res.json({
        success: true,
        benchmark: {
          type: type,
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
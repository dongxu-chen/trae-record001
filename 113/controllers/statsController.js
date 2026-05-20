const { clickhouse } = require('../config/clickhouse');
const ttlService = require('../services/ttlService');
const messageQueue = require('../services/messageQueue');

const getStats = async (req, res) => {
  try {
    const { shortCode, startDate, endDate } = req.query;

    let whereClause = '1=1';
    const mvWhereClause = '1=1';

    if (shortCode) {
      whereClause += ` AND short_code = '${shortCode}'`;
    }

    if (startDate) {
      whereClause += ` AND timestamp >= '${startDate}'`;
    }

    if (endDate) {
      whereClause += ` AND timestamp <= '${endDate}'`;
    }

    const [pvResult, uvResult, countryResult, regionResult, cityResult, browserResult, osResult, deviceResult, recentLogs, hourlyStats, ttlStats, queueStats] = await Promise.all([
      clickhouse.query({
        query: `SELECT sum(pv) as pv FROM stats_hourly WHERE ${whereClause.replace('timestamp', 'hour')}`,
        format: 'JSONEachRow'
      }).catch(() => clickhouse.query({
        query: `SELECT count(*) as pv FROM access_logs WHERE ${whereClause}`,
        format: 'JSONEachRow'
      })),
      clickhouse.query({
        query: `SELECT sum(uv) as uv FROM stats_hourly WHERE ${whereClause.replace('timestamp', 'hour')}`,
        format: 'JSONEachRow'
      }).catch(() => clickhouse.query({
        query: `SELECT count(DISTINCT ip) as uv FROM access_logs WHERE ${whereClause}`,
        format: 'JSONEachRow'
      })),
      clickhouse.query({
        query: `SELECT country, count(*) as count FROM access_logs WHERE ${whereClause} GROUP BY country ORDER BY count DESC LIMIT 10`,
        format: 'JSONEachRow'
      }),
      clickhouse.query({
        query: `SELECT region, count(*) as count FROM access_logs WHERE ${whereClause} GROUP BY region ORDER BY count DESC LIMIT 10`,
        format: 'JSONEachRow'
      }),
      clickhouse.query({
        query: `SELECT city, count(*) as count FROM access_logs WHERE ${whereClause} GROUP BY city ORDER BY count DESC LIMIT 10`,
        format: 'JSONEachRow'
      }),
      clickhouse.query({
        query: `SELECT browser, count(*) as count FROM access_logs WHERE ${whereClause} GROUP BY browser ORDER BY count DESC LIMIT 10`,
        format: 'JSONEachRow'
      }),
      clickhouse.query({
        query: `SELECT os, count(*) as count FROM access_logs WHERE ${whereClause} GROUP BY os ORDER BY count DESC LIMIT 10`,
        format: 'JSONEachRow'
      }),
      clickhouse.query({
        query: `SELECT device, count(*) as count FROM access_logs WHERE ${whereClause} GROUP BY device ORDER BY count DESC`,
        format: 'JSONEachRow'
      }),
      clickhouse.query({
        query: `SELECT * FROM access_logs WHERE ${whereClause} ORDER BY timestamp DESC LIMIT 50`,
        format: 'JSONEachRow'
      }),
      clickhouse.query({
        query: `SELECT hour, sum(pv) as pv, sum(uv) as uv FROM stats_hourly WHERE ${whereClause.replace('timestamp', 'hour')} GROUP BY hour ORDER BY hour DESC LIMIT 24`,
        format: 'JSONEachRow'
      }).catch(() => ({ json: async () => [] })),
      ttlService.getStats(),
      messageQueue.getQueueLength()
    ]);

    const pvData = await pvResult.json();
    const uvData = await uvResult.json();
    const countryData = await countryResult.json();
    const regionData = await regionResult.json();
    const cityData = await cityResult.json();
    const browserData = await browserResult.json();
    const osData = await osResult.json();
    const deviceData = await deviceResult.json();
    const logsData = await recentLogs.json();
    const hourlyData = await hourlyStats.json();

    res.json({
      pv: parseInt(pvData[0]?.pv || 0),
      uv: parseInt(uvData[0]?.uv || 0),
      distribution: {
        country: countryData,
        region: regionData,
        city: cityData
      },
      browser: browserData,
      os: osData,
      device: deviceData,
      recentLogs: logsData,
      hourlyStats: hourlyData,
      system: {
        shortlinks: ttlStats,
        pendingQueue: queueStats
      }
    });
  } catch (error) {
    console.error('Get stats error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};

module.exports = { getStats };
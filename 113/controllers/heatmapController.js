const { clickhouse } = require('../config/clickhouse');
const redis = require('../config/redis');
const { sendHeatmapClick } = require('../config/kafka');
require('dotenv').config();

const trackHeatmap = async (req, res) => {
  try {
    const { fingerprint, sessionId, pageInfo, clicks } = req.body;

    if (!fingerprint || !clicks || !Array.isArray(clicks)) {
      return res.status(400).json({ error: 'Invalid data' });
    }

    const kafkaPromises = clicks.map(click => 
      sendHeatmapClick({
        fingerprint,
        sessionId,
        pageInfo,
        path: pageInfo?.path,
        ...click
      })
    );
    
    await Promise.all(kafkaPromises);

    res.json({ 
      success: true, 
      recorded: clicks.length,
      _meta: {
        transport: 'kafka',
        latencyTarget: process.env.END_TO_END_LATENCY_TARGET_MS + 'ms'
      }
    });
  } catch (error) {
    console.error('Heatmap track error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};

const getHeatmapData = async (req, res) => {
  try {
    const { path = 'global', startDate, endDate, resolution = 'high' } = req.query;

    const realtimeData = await getRealtimeHeatmap(path);
    
    const hasRealtimeData = realtimeData.heatmap.length > 0 || realtimeData.uvm.uv > 0;
    
    let historicalData = {
      heatmap: [],
      uvm: { uv: 0, mv: 0, totalClicks: 0 },
      topTargets: []
    };

    if (!hasRealtimeData || startDate || endDate) {
      historicalData = await getHistoricalHeatmap(path, startDate, endDate, resolution);
    }

    const mergedData = mergeHeatmapData(realtimeData, historicalData);

    const latency = await redis.get('realtime:latency:last');

    res.json({
      ...mergedData,
      _meta: {
        source: hasRealtimeData ? 'redis-realtime + clickhouse-historical' : 'clickhouse-only',
        latencyMs: parseInt(latency) || 0,
        targetLatencyMs: process.env.END_TO_END_LATENCY_TARGET_MS,
        timestamp: Date.now()
      }
    });
  } catch (error) {
    console.error('Get heatmap error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};

const getRealtimeHeatmap = async (path) => {
  try {
    const pipeline = redis.pipeline();
    
    const heatmapKey = `realtime:heatmap:${path}`;
    const uvmKey = `realtime:uvm:${path}`;
    const targetsKey = `realtime:targets:${path}`;
    
    pipeline.hGetAll(heatmapKey);
    pipeline.hGetAll(uvmKey);
    pipeline.hGetAll(targetsKey);
    
    const [heatmapRaw, uvmRaw, targetsRaw] = await pipeline.exec();
    
    const heatmap = Object.entries(heatmapRaw[1] || {}).map(([key, value]) => {
      const [x, y] = key.split(',').map(Number);
      return { x, y, value: parseInt(value) };
    });

    const targets = Object.entries(targetsRaw[1] || {})
      .map(([key, value]) => {
        const [target, id, className] = key.split(':');
        return {
          target,
          target_id: id,
          target_class: className,
          click_count: parseInt(value)
        };
      })
      .sort((a, b) => b.click_count - a.click_count)
      .slice(0, 20);

    return {
      heatmap,
      uvm: {
        uv: parseInt(uvmRaw[1]?.uv || 0),
        mv: parseInt(uvmRaw[1]?.mv || 0),
        totalClicks: parseInt(uvmRaw[1]?.clicks || 0)
      },
      topTargets: targets
    };
  } catch (error) {
    console.error('Get realtime heatmap error:', error);
    return {
      heatmap: [],
      uvm: { uv: 0, mv: 0, totalClicks: 0 },
      topTargets: []
    };
  }
};

const getHistoricalHeatmap = async (path, startDate, endDate, resolution) => {
  try {
    let whereClause = '1=1';
    if (path && path !== 'global') {
      whereClause += ` AND path = '${path}'`;
    }
    if (startDate) {
      whereClause += ` AND timestamp >= '${startDate}'`;
    }
    if (endDate) {
      whereClause += ` AND timestamp <= '${endDate}'`;
    }

    const gridSize = resolution === 'high' ? 10 : resolution === 'medium' ? 20 : 40;

    const [clicksResult, uvmResult, topTargets] = await Promise.all([
      clickhouse.query({
        query: `
          SELECT 
            intDiv(absolute_x, {gridSize:Int32}) * {gridSize:Int32} as grid_x,
            intDiv(absolute_y, {gridSize:Int32}) * {gridSize:Int32} as grid_y,
            count() as weight
          FROM heatmap_clicks
          WHERE ${whereClause}
          GROUP BY grid_x, grid_y
          ORDER BY weight DESC
        `,
        query_params: { gridSize },
        format: 'JSONEachRow'
      }),
      clickhouse.query({
        query: `
          SELECT
            uniq(fingerprint) as uv,
            uniq(session_id) as mv,
            count() as total_clicks
          FROM heatmap_clicks
          WHERE ${whereClause}
        `,
        format: 'JSONEachRow'
      }),
      clickhouse.query({
        query: `
          SELECT
            target,
            target_id,
            target_class,
            count() as click_count
          FROM heatmap_clicks
          WHERE ${whereClause}
          GROUP BY target, target_id, target_class
          ORDER BY click_count DESC
          LIMIT 20
        `,
        format: 'JSONEachRow'
      })
    ]);

    const clicks = await clicksResult.json();
    const uvm = await uvmResult.json();
    const targets = await topTargets.json();

    return {
      heatmap: clicks.map(c => ({
        x: c.grid_x,
        y: c.grid_y,
        value: c.weight
      })),
      uvm: {
        uv: parseInt(uvm[0]?.uv || 0),
        mv: parseInt(uvm[0]?.mv || 0),
        totalClicks: parseInt(uvm[0]?.total_clicks || 0)
      },
      topTargets: targets
    };
  } catch (error) {
    console.error('Get historical heatmap error:', error);
    return {
      heatmap: [],
      uvm: { uv: 0, mv: 0, totalClicks: 0 },
      topTargets: []
    };
  }
};

const mergeHeatmapData = (realtime, historical) => {
  const pointMap = new Map();
  
  historical.heatmap.forEach(point => {
    pointMap.set(`${point.x},${point.y}`, point.value);
  });
  
  realtime.heatmap.forEach(point => {
    const key = `${point.x},${point.y}`;
    pointMap.set(key, (pointMap.get(key) || 0) + point.value);
  });
  
  const heatmap = Array.from(pointMap.entries()).map(([key, value]) => {
    const [x, y] = key.split(',').map(Number);
    return { x, y, value };
  });

  const targetMap = new Map();
  historical.topTargets.forEach(t => {
    const key = `${t.target}:${t.target_id}:${t.target_class}`;
    targetMap.set(key, t.click_count);
  });
  realtime.topTargets.forEach(t => {
    const key = `${t.target}:${t.target_id}:${t.target_class}`;
    targetMap.set(key, (targetMap.get(key) || 0) + t.click_count);
  });
  
  const topTargets = Array.from(targetMap.entries())
    .map(([key, click_count]) => {
      const [target, target_id, target_class] = key.split(':');
      return { target, target_id, target_class, click_count };
    })
    .sort((a, b) => b.click_count - a.click_count)
    .slice(0, 20);

  return {
    heatmap,
    uvm: {
      uv: realtime.uvm.uv + historical.uvm.uv,
      mv: realtime.uvm.mv + historical.uvm.mv,
      totalClicks: realtime.uvm.totalClicks + historical.uvm.totalClicks
    },
    topTargets
  };
};

const getUVMStats = async (req, res) => {
  try {
    const { path, startDate, endDate, granularity = 'hourly' } = req.query;

    const [realtimeGlobal, historicalResult] = await Promise.all([
      redis.hGetAll('realtime:uvm:global'),
      getHistoricalUVMStats(path, startDate, endDate, granularity)
    ]);

    historicalResult.realtime = {
      uv: parseInt(realtimeGlobal?.uv || 0),
      mv: parseInt(realtimeGlobal?.mv || 0),
      totalClicks: parseInt(realtimeGlobal?.clicks || 0)
    };

    const latency = await redis.get('realtime:latency:last');
    historicalResult._meta = {
      latencyMs: parseInt(latency) || 0,
      timestamp: Date.now()
    };

    res.json(historicalResult);
  } catch (error) {
    console.error('Get UVM stats error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};

const getHistoricalUVMStats = async (path, startDate, endDate, granularity) => {
  try {
    let whereClause = '1=1';
    if (path && path !== 'global') {
      whereClause += ` AND path = '${path}'`;
    }
    if (startDate) {
      whereClause += ` AND timestamp >= '${startDate}'`;
    }
    if (endDate) {
      whereClause += ` AND timestamp <= '${endDate}'`;
    }

    const dateFunc = granularity === 'daily' ? 'toStartOfDay' : 
                      granularity === 'weekly' ? 'toStartOfWeek' : 'toStartOfHour';

    const [trendResult, topVisitors, deviceStats, browserStats] = await Promise.all([
      clickhouse.query({
        query: `
          SELECT
            ${dateFunc}(timestamp) as time,
            uniq(fingerprint) as uv,
            uniq(session_id) as sessions,
            count() as clicks
          FROM heatmap_clicks
          WHERE ${whereClause}
          GROUP BY time
          ORDER BY time DESC
          LIMIT 100
        `,
        format: 'JSONEachRow'
      }),
      clickhouse.query({
        query: `
          SELECT
            fingerprint,
            count() as click_count,
            uniq(session_id) as session_count,
            max(timestamp) as last_visit
          FROM heatmap_clicks
          WHERE ${whereClause}
          GROUP BY fingerprint
          ORDER BY click_count DESC
          LIMIT 50
        `,
        format: 'JSONEachRow'
      }),
      clickhouse.query({
        query: `
          SELECT
            device,
            uniq(fingerprint) as uv,
            count() as clicks
          FROM visitor_sessions
          GROUP BY device
          ORDER BY uv DESC
        `,
        format: 'JSONEachRow'
      }),
      clickhouse.query({
        query: `
          SELECT
            browser,
            uniq(fingerprint) as uv,
            count() as clicks
          FROM visitor_sessions
          GROUP BY browser
          ORDER BY uv DESC
          LIMIT 10
        `,
        format: 'JSONEachRow'
      })
    ]);

    const trend = await trendResult.json();
    const visitors = await topVisitors.json();
    const devices = await deviceStats.json();
    const browsers = await browserStats.json();

    return {
      trend,
      topVisitors: visitors,
      deviceStats: devices,
      browserStats: browsers
    };
  } catch (error) {
    console.error('Get historical UVM stats error:', error);
    return {
      trend: [],
      topVisitors: [],
      deviceStats: [],
      browserStats: []
    };
  }
};

const generateHeatmapOverlay = async (req, res) => {
  try {
    const { path, startDate, endDate, width = 1920, height = 1080 } = req.body;

    const realtimeData = await getRealtimeHeatmap(path || 'global');

    let whereClause = '1=1';
    if (path && path !== 'global') {
      whereClause += ` AND path = '${path}'`;
    }
    if (startDate) {
      whereClause += ` AND timestamp >= '${startDate}'`;
    }
    if (endDate) {
      whereClause += ` AND timestamp <= '${endDate}'`;
    }

    const result = await clickhouse.query({
      query: `
        SELECT absolute_x as x, absolute_y as y, count() as weight
        FROM heatmap_clicks
        WHERE ${whereClause}
        GROUP BY x, y
      `,
      format: 'JSONEachRow'
    });

    const historicalPoints = await result.json();
    
    const pointMap = new Map();
    historicalPoints.forEach(p => pointMap.set(`${p.x},${p.y}`, p.weight));
    realtimeData.heatmap.forEach(p => pointMap.set(`${p.x},${p.y}`, (pointMap.get(`${p.x},${p.y}`) || 0) + p.value));
    
    const points = Array.from(pointMap.entries()).map(([key, weight]) => {
      const [x, y] = key.split(',').map(Number);
      return { x, y, weight };
    });

    const svg = generateHeatmapSVG(points, width, height);

    res.setHeader('Content-Type', 'image/svg+xml');
    res.setHeader('Content-Disposition', 'attachment; filename="heatmap.svg"');
    res.send(svg);
  } catch (error) {
    console.error('Generate heatmap error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};

const generateHeatmapSVG = (points, width, height) => {
  const maxWeight = Math.max(...points.map(p => p.weight), 1);
  const radius = 30;

  let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`;

  svg += `<defs>
    <radialGradient id="heatGradient">
      <stop offset="0%" stop-color="#ff0000" stop-opacity="0.8"/>
      <stop offset="50%" stop-color="#ff6600" stop-opacity="0.5"/>
      <stop offset="100%" stop-color="#ffff00" stop-opacity="0"/>
    </radialGradient>
  </defs>`;

  svg += `<rect width="100%" height="100%" fill="rgba(0,0,0,0.1)"/>`;

  points.forEach(point => {
    const opacity = Math.min(point.weight / maxWeight, 1);
    const pointRadius = radius * (0.5 + opacity * 0.5);
    
    svg += `<circle
      cx="${point.x}"
      cy="${point.y}"
      r="${pointRadius}"
      fill="url(#heatGradient)"
      opacity="${opacity * 0.8}"
    />`;
  });

  svg += `<style>
    .legend { font-family: Arial; font-size: 12px; }
  </style>`;

  svg += `<rect x="20" y="${height - 60}" width="200" height="30" fill="white" stroke="#ccc" rx="5"/>`;
  svg += `<text x="30" y="${height - 40}" class="legend">实时热力图 (Redis + ClickHouse 双读)</text>`;
  svg += `<circle cx="150" cy="${height - 45}" r="10" fill="url(#heatGradient)"/>`;

  svg += `</svg>`;

  return svg;
};

module.exports = {
  trackHeatmap,
  getHeatmapData,
  getUVMStats,
  generateHeatmapOverlay
};

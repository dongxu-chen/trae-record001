require('dotenv').config();
const express = require('express');
const cors = require('cors');
const axios = require('axios');

const app = express();
const PORT = process.env.PORT || 5000;
const GAODE_API_KEY = process.env.GAODE_API_KEY;

app.use(cors());
app.use(express.json());

const ROUTE_STRATEGIES = {
  time_shortest: { strategy: 10, name: '时间最短', color: '#27ae60' },
  distance_shortest: { strategy: 12, name: '距离最短', color: '#3498db' },
  no_highway: { strategy: 11, name: '避开高速', color: '#e67e22' }
};

const urlCache = new Map();
const routeCache = new Map();

function convertToGaodeCoord(lng, lat) {
  return `${lng},${lat}`;
}

function parseGaodeCoord(coordStr) {
  const [lng, lat] = coordStr.split(',').map(Number);
  return { lng, lat };
}

function haversineDistance(p1, p2) {
  const R = 6371000;
  const dLat = (p2.lat - p1.lat) * Math.PI / 180;
  const dLng = (p2.lng - p1.lng) * Math.PI / 180;
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(p1.lat * Math.PI / 180) * Math.cos(p2.lat * Math.PI / 180) *
    Math.sin(dLng / 2) * Math.sin(dLng / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

function findClosestPointIndex(target, points) {
  if (!points || points.length === 0) return 0;
  
  let minDist = Infinity;
  let closestIdx = 0;
  
  points.forEach((p, idx) => {
    const dist = haversineDistance(target, p);
    if (dist < minDist) {
      minDist = dist;
      closestIdx = idx;
    }
  });
  
  return closestIdx;
}

async function fetchRouteData(origin, destination, waypoints, strategy) {
  const originStr = convertToGaodeCoord(origin.lng, origin.lat);
  const destinationStr = convertToGaodeCoord(destination.lng, destination.lat);

  let url = `https://restapi.amap.com/v3/direction/driving?key=${GAODE_API_KEY}&origin=${originStr}&destination=${destinationStr}&extensions=all&strategy=${strategy}`;

  if (waypoints.length > 0) {
    const waypointsStr = waypoints
      .filter(wp => wp && wp.lng && wp.lat)
      .map(wp => convertToGaodeCoord(wp.lng, wp.lat))
      .join(';');
    if (waypointsStr) {
      url += `&waypoints=${waypointsStr}`;
    }
  }

  const response = await axios.get(url);
  return response.data;
}

function processRouteData(data, origin, destination, waypoints) {
  const route = data.route;
  const paths = route.paths || [];

  if (paths.length === 0) {
    return null;
  }

  const bestPath = paths[0];
  const steps = bestPath.steps || [];

  const routeSteps = steps.map(step => ({
    instruction: step.instruction,
    distance: parseInt(step.distance) || 0,
    duration: parseInt(step.duration) || 0,
    startLocation: parseGaodeCoord(step.polyline.split(';')[0]),
    endLocation: parseGaodeCoord(step.polyline.split(';').pop()),
    roadName: step.road || step.assistant_action || '',
    action: step.action || ''
  }));

  const pathCoordinates = [];
  const pathCoordsForCalc = [];
  steps.forEach(step => {
    const polyline = step.polyline || '';
    const points = polyline.split(';').map(coordStr => {
      const [lng, lat] = coordStr.split(',').map(Number);
      return [lat, lng];
    });
    pathCoordinates.push(...points);
    points.forEach(p => pathCoordsForCalc.push({ lat: p[0], lng: p[1] }));
  });

  const allPoints = [origin, ...waypoints.filter(wp => wp && wp.lng && wp.lat), destination];

  const pointIndices = allPoints.map(point => findClosestPointIndex(point, pathCoordsForCalc));
  pointIndices.sort((a, b) => a - b);

  const segments = [];
  let calculatedTotalDistance = 0;
  const apiTotalDistance = parseInt(bestPath.distance) || 0;
  const apiTotalDuration = parseInt(bestPath.duration) || 0;

  for (let i = 0; i < allPoints.length - 1; i++) {
    const startIdx = pointIndices[i];
    const endIdx = pointIndices[i + 1];
    
    let segmentDistance = 0;
    if (startIdx < endIdx && pathCoordsForCalc.length > 1) {
      for (let j = startIdx; j < endIdx && j < pathCoordsForCalc.length - 1; j++) {
        segmentDistance += haversineDistance(
          pathCoordsForCalc[j],
          pathCoordsForCalc[j + 1]
        );
      }
    } else {
      segmentDistance = haversineDistance(allPoints[i], allPoints[i + 1]);
    }
    
    calculatedTotalDistance += segmentDistance;
    segments.push({
      from: allPoints[i],
      to: allPoints[i + 1],
      distance: segmentDistance,
      duration: 0,
      fromIndex: i,
      toIndex: i + 1
    });
  }

  if (calculatedTotalDistance > 0 && apiTotalDistance > 0) {
    const ratio = apiTotalDistance / calculatedTotalDistance;
    segments.forEach(seg => {
      seg.distance = Math.round(seg.distance * ratio);
    });
  }

  let cumulativeDistance = 0;
  segments.forEach(seg => {
    cumulativeDistance += seg.distance;
    const timeRatio = cumulativeDistance / apiTotalDistance;
    seg.duration = Math.round(apiTotalDuration * timeRatio) - 
      Math.round(apiTotalDuration * (cumulativeDistance - seg.distance) / apiTotalDistance);
  });

  return {
    totalDistance: apiTotalDistance || calculatedTotalDistance,
    totalDuration: apiTotalDuration,
    taxiCost: parseFloat(bestPath.taxi_cost) || 0,
    pathCoordinates,
    steps: routeSteps,
    segments,
    origin,
    destination,
    waypoints: waypoints.filter(wp => wp && wp.lng && wp.lat)
  };
}

app.post('/api/route', async (req, res) => {
  try {
    const { origin, destination, waypoints = [] } = req.body;

    if (!origin || !origin.lng || !origin.lat) {
      return res.status(400).json({ error: '起点坐标无效' });
    }
    if (!destination || !destination.lng || !destination.lat) {
      return res.status(400).json({ error: '终点坐标无效' });
    }
    if (waypoints.length > 10) {
      return res.status(400).json({ error: '途经点最多10个' });
    }

    const data = await fetchRouteData(origin, destination, waypoints, 10);

    if (data.status !== '1') {
      return res.status(400).json({ error: data.info || '路线规划失败' });
    }

    const route = processRouteData(data, origin, destination, waypoints);
    
    if (!route) {
      return res.status(400).json({ error: '未找到可行路线' });
    }

    res.json({
      success: true,
      route
    });

  } catch (error) {
    console.error('路线规划错误:', error.message);
    res.status(500).json({ error: '服务器内部错误' });
  }
});

app.post('/api/route/multi', async (req, res) => {
  try {
    const { origin, destination, waypoints = [] } = req.body;

    if (!origin || !origin.lng || !origin.lat) {
      return res.status(400).json({ error: '起点坐标无效' });
    }
    if (!destination || !destination.lng || !destination.lat) {
      return res.status(400).json({ error: '终点坐标无效' });
    }
    if (waypoints.length > 10) {
      return res.status(400).json({ error: '途经点最多10个' });
    }

    const routePromises = Object.entries(ROUTE_STRATEGIES).map(async ([key, config]) => {
      try {
        const data = await fetchRouteData(origin, destination, waypoints, config.strategy);
        
        if (data.status !== '1') {
          return { key, strategy: key, name: config.name, color: config.color, error: data.info, success: false };
        }

        const route = processRouteData(data, origin, destination, waypoints);
        
        if (!route) {
          return { key, strategy: key, name: config.name, color: config.color, error: '未找到路线', success: false };
        }

        return { key, strategy: key, name: config.name, color: config.color, ...route, success: true };
      } catch (err) {
        console.error(`路线规划失败 [${config.name}]:`, err.message);
        return { key, strategy: key, name: config.name, color: config.color, error: err.message, success: false };
      }
    });

    const results = await Promise.all(routePromises);
    const successfulRoutes = results.filter(r => r.success);

    if (successfulRoutes.length === 0) {
      return res.status(400).json({ error: '所有路线规划均失败', details: results });
    }

    res.json({
      success: true,
      routes: results,
      defaultRoute: successfulRoutes[0].key
    });

  } catch (error) {
    console.error('多路线规划错误:', error.message);
    res.status(500).json({ error: '服务器内部错误' });
  }
});

app.post('/api/share/generate', (req, res) => {
  try {
    const { origin, destination, waypoints = [], strategy = 'time_shortest' } = req.body;
    
    if (!origin || !destination) {
      return res.status(400).json({ error: '起终点信息不完整' });
    }

    const routeData = {
      o: origin,
      d: destination,
      w: waypoints.filter(wp => wp && wp.lng && wp.lat),
      s: strategy
    };

    const encoded = Buffer.from(JSON.stringify(routeData)).toString('base64');
    const shortId = Math.random().toString(36).substring(2, 10);

    urlCache.set(shortId, encoded);
    routeCache.set(shortId, routeData);

    const shortUrl = `${req.headers.origin || 'http://localhost:3000'}/?r=${shortId}`;

    res.json({
      success: true,
      shortId,
      shortUrl,
      encoded
    });
  } catch (error) {
    console.error('生成分享链接错误:', error.message);
    res.status(500).json({ error: '生成分享链接失败' });
  }
});

app.get('/api/share/:id', (req, res) => {
  try {
    const { id } = req.params;
    
    let routeData = routeCache.get(id);
    
    if (!routeData) {
      const encoded = urlCache.get(id);
      if (encoded) {
        routeData = JSON.parse(Buffer.from(encoded, 'base64').toString());
        routeCache.set(id, routeData);
      }
    }

    if (!routeData) {
      return res.status(404).json({ error: '分享链接不存在或已过期' });
    }

    res.json({
      success: true,
      route: {
        origin: routeData.o,
        destination: routeData.d,
        waypoints: routeData.w,
        strategy: routeData.s
      }
    });
  } catch (error) {
    console.error('解析分享链接错误:', error.message);
    res.status(500).json({ error: '解析分享链接失败' });
  }
});

app.get('/api/share/decode/:encoded', (req, res) => {
  try {
    const { encoded } = req.params;
    const decoded = JSON.parse(Buffer.from(encoded, 'base64').toString());
    
    res.json({
      success: true,
      route: {
        origin: decoded.o,
        destination: decoded.d,
        waypoints: decoded.w,
        strategy: decoded.s
      }
    });
  } catch (error) {
    console.error('解码分享链接错误:', error.message);
    res.status(400).json({ error: '分享链接格式无效' });
  }
});

app.get('/api/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    gaodeConfigured: !!GAODE_API_KEY,
    cacheSize: urlCache.size
  });
});

app.listen(PORT, () => {
  console.log(`货运路线规划服务运行在 http://localhost:${PORT}`);
  console.log(`高德API配置状态: ${GAODE_API_KEY ? '已配置' : '未配置'}`);
  console.log(`可用策略: ${Object.values(ROUTE_STRATEGIES).map(s => s.name).join(', ')}`);
});

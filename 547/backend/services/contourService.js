class ContourService {
  constructor() {
    this.marchingSquaresTable = this.initMarchingSquaresTable();
  }

  initMarchingSquaresTable() {
    return [
      [],
      [[3, 0], [0, 1]],
      [[0, 1], [1, 2]],
      [[3, 0], [1, 2]],
      [[1, 2], [2, 3]],
      [[[3, 0], [0, 1]], [[2, 3], [1, 2]]],
      [[0, 1], [2, 3]],
      [[3, 0], [2, 3]],
      [[2, 3], [3, 0]],
      [[2, 3], [0, 1]],
      [[[0, 1], [1, 2]], [[3, 0], [2, 3]]],
      [[1, 2], [2, 3]],
      [[1, 2], [3, 0]],
      [[0, 1], [1, 2]],
      [[0, 1], [3, 0]],
      []
    ];
  }

  generateSampleDEM(width = 100, height = 100) {
    const dem = {
      width,
      height,
      bounds: {
        west: 116.0,
        east: 116.5,
        south: 39.5,
        north: 40.0
      },
      data: []
    };

    const centerX = width / 2;
    const centerY = height / 2;
    const maxRadius = Math.min(width, height) / 2;

    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const dx = x - centerX;
        const dy = y - centerY;
        const distance = Math.sqrt(dx * dx + dy * dy);
        const normalizedDist = distance / maxRadius;
        
        let elevation = Math.sin(normalizedDist * Math.PI * 4) * 250;
        elevation += Math.sin(x * 0.08) * 80 + Math.cos(y * 0.08) * 80;
        elevation += Math.sin(x * 0.03 + y * 0.05) * 60;
        elevation += Math.cos(x * 0.05 - y * 0.03) * 40;
        elevation += 500;
        
        dem.data.push(Math.max(0, elevation));
      }
    }

    return dem;
  }

  pixelToGeo(dem, x, y) {
    const lon = dem.bounds.west + (x / dem.width) * (dem.bounds.east - dem.bounds.west);
    const lat = dem.bounds.north - (y / dem.height) * (dem.bounds.north - dem.bounds.south);
    return [lon, lat];
  }

  interpolate(a, b, level) {
    if (Math.abs(a - b) < 0.0001) return 0;
    return (level - a) / (b - a);
  }

  getContourPoints(dem, level, x, y) {
    const idx = y * dem.width + x;
    const values = [
      dem.data[idx],
      dem.data[idx + 1],
      dem.data[idx + 1 + dem.width],
      dem.data[idx + dem.width]
    ];

    let squareIndex = 0;
    for (let i = 0; i < 4; i++) {
      if (values[i] >= level) squareIndex |= (1 << i);
    }

    const edgeSets = this.marchingSquaresTable[squareIndex];
    if (!edgeSets || edgeSets.length === 0) return [];

    const points = [];
    const corners = [
      [x, y], [x + 1, y], [x + 1, y + 1], [x, y + 1]
    ];

    const interpolateEdge = (edge) => {
      const [p1, p2] = [corners[edge[0]], corners[edge[1]]];
      const [v1, v2] = [values[edge[0]], values[edge[1]]];
      const t = this.interpolate(v1, v2, level);
      
      const px = p1[0] + t * (p2[0] - p1[0]);
      const py = p1[1] + t * (p2[1] - p1[1]);
      
      return this.pixelToGeo(dem, px, py);
    };

    const isPointDuplicate = (pt, existingPoints) => {
      for (const ep of existingPoints) {
        if (this.pointsEqual(pt, ep, 0.000001)) {
          return true;
        }
      }
      return false;
    };

    if (edgeSets.length === 2 && Array.isArray(edgeSets[0][0])) {
      for (const edges of edgeSets) {
        const segmentPoints = [];
        for (const edge of edges) {
          const pt = interpolateEdge(edge);
          if (!isPointDuplicate(pt, segmentPoints)) {
            segmentPoints.push(pt);
          }
        }
        if (segmentPoints.length === 2) {
          points.push(...segmentPoints);
        }
      }
    } else {
      for (const edge of edgeSets) {
        const pt = interpolateEdge(edge);
        if (!isPointDuplicate(pt, points)) {
          points.push(pt);
        }
      }
    }

    return points;
  }

  calculateLineLength(coords) {
    let length = 0;
    for (let i = 1; i < coords.length; i++) {
      const dx = coords[i][0] - coords[i - 1][0];
      const dy = coords[i][1] - coords[i - 1][1];
      length += Math.sqrt(dx * dx + dy * dy);
    }
    return length;
  }

  calculateGradient(dem, x, y) {
    const idx = y * dem.width + x;
    const center = dem.data[idx];
    
    let sumDiff = 0;
    let count = 0;
    
    if (x > 0) {
      sumDiff += Math.abs(center - dem.data[idx - 1]);
      count++;
    }
    if (x < dem.width - 1) {
      sumDiff += Math.abs(center - dem.data[idx + 1]);
      count++;
    }
    if (y > 0) {
      sumDiff += Math.abs(center - dem.data[idx - dem.width]);
      count++;
    }
    if (y < dem.height - 1) {
      sumDiff += Math.abs(center - dem.data[idx + dem.width]);
      count++;
    }
    
    return count > 0 ? sumDiff / count : 0;
  }

  calculateAverageGradient(dem, coords) {
    let totalGradient = 0;
    let count = 0;
    
    for (const coord of coords) {
      const x = Math.floor((coord[0] - dem.bounds.west) / (dem.bounds.east - dem.bounds.west) * dem.width);
      const y = Math.floor((dem.bounds.north - coord[1]) / (dem.bounds.north - dem.bounds.south) * dem.height);
      
      if (x >= 0 && x < dem.width && y >= 0 && y < dem.height) {
        totalGradient += this.calculateGradient(dem, x, y);
        count++;
      }
    }
    
    return count > 0 ? totalGradient / count : 0;
  }

  calculateLineAngle(coords) {
    if (coords.length < 2) return 0;
    
    const midIndex = Math.floor(coords.length / 2);
    const start = coords[Math.max(0, midIndex - 2)];
    const end = coords[Math.min(coords.length - 1, midIndex + 2)];
    
    const dx = end[0] - start[0];
    const dy = end[1] - start[1];
    
    let angle = Math.atan2(dy, dx) * (180 / Math.PI);
    
    if (angle > 90) angle -= 180;
    if (angle < -90) angle += 180;
    
    return angle;
  }

  filterShortContours(contours, minLengthPixels = 3) {
    const filtered = {
      type: 'FeatureCollection',
      features: []
    };
    
    for (const feature of contours.features) {
      if (feature.geometry.type === 'LineString') {
        const coords = feature.geometry.coordinates;
        if (coords.length >= minLengthPixels) {
          filtered.features.push(feature);
        }
      }
    }
    
    return filtered;
  }

  extractContours(dem, interval, minLength = 3) {
    const contours = {
      type: 'FeatureCollection',
      features: []
    };

    const minElevation = Math.min(...dem.data);
    const maxElevation = Math.max(...dem.data);
    
    const startLevel = Math.ceil(minElevation / interval) * interval;
    const levels = [];
    
    for (let level = startLevel; level <= maxElevation; level += interval) {
      levels.push(level);
    }

    for (const level of levels) {
      const segments = this.extractLevelSegments(dem, level);
      const lineStrings = this.connectSegments(segments, minLength);
      
      for (const lineString of lineStrings) {
        if (lineString.length >= minLength) {
          const angle = this.calculateLineAngle(lineString);
          contours.features.push({
            type: 'Feature',
            geometry: {
              type: 'LineString',
              coordinates: lineString
            },
            properties: {
              elevation: level,
              angle: angle,
              pointCount: lineString.length
            }
          });
        }
      }
    }

    return contours;
  }

  extractLevelSegments(dem, level) {
    const segments = [];
    
    for (let y = 0; y < dem.height - 1; y++) {
      for (let x = 0; x < dem.width - 1; x++) {
        const points = this.getContourPoints(dem, level, x, y);
        if (points.length >= 2) {
          for (let i = 0; i < points.length; i += 2) {
            if (i + 1 < points.length) {
              segments.push([points[i], points[i + 1]]);
            }
          }
        }
      }
    }
    
    return segments;
  }

  pointsEqual(p1, p2, tolerance = 0.00001) {
    const dx = Math.abs(p1[0] - p2[0]);
    const dy = Math.abs(p1[1] - p2[1]);
    return dx < tolerance && dy < tolerance;
  }

  connectSegments(segments, minLength) {
    if (segments.length === 0) return [];
    
    const lineStrings = [];
    const used = new Array(segments.length).fill(false);
    const tolerance = 0.0001;
    
    const pointsClose = (p1, p2) => {
      const dx = Math.abs(p1[0] - p2[0]);
      const dy = Math.abs(p1[1] - p2[1]);
      return dx < tolerance && dy < tolerance;
    };
    
    for (let i = 0; i < segments.length; i++) {
      if (used[i]) continue;
      
      const lineString = [...segments[i]];
      used[i] = true;
      
      let extended = true;
      let iterations = 0;
      const maxIterations = segments.length * 2;
      
      while (extended && iterations < maxIterations) {
        extended = false;
        iterations++;
        
        const start = lineString[0];
        const end = lineString[lineString.length - 1];
        
        for (let j = 0; j < segments.length; j++) {
          if (used[j]) continue;
          
          const seg = segments[j];
          
          if (pointsClose(seg[0], end)) {
            if (!pointsClose(seg[1], end)) {
              lineString.push(seg[1]);
            }
            used[j] = true;
            extended = true;
            break;
          } else if (pointsClose(seg[1], end)) {
            if (!pointsClose(seg[0], end)) {
              lineString.push(seg[0]);
            }
            used[j] = true;
            extended = true;
            break;
          } else if (pointsClose(seg[0], start)) {
            if (!pointsClose(seg[1], start)) {
              lineString.unshift(seg[1]);
            }
            used[j] = true;
            extended = true;
            break;
          } else if (pointsClose(seg[1], start)) {
            if (!pointsClose(seg[0], start)) {
              lineString.unshift(seg[0]);
            }
            used[j] = true;
            extended = true;
            break;
          }
        }
      }
      
      if (lineString.length >= minLength) {
        const finalPoints = [];
        for (let k = 0; k < lineString.length; k++) {
          if (k === 0 || !pointsClose(lineString[k], lineString[k - 1])) {
            finalPoints.push(lineString[k]);
          }
        }
        
        if (finalPoints.length >= minLength) {
          lineStrings.push(finalPoints);
        }
      }
    }
    
    return lineStrings;
  }

  smoothContours(contours, iterations = 1, dem = null, adaptive = false) {
    if (iterations <= 0) return contours;

    const smoothed = JSON.parse(JSON.stringify(contours));

    for (let iter = 0; iter < iterations; iter++) {
      for (const feature of smoothed.features) {
        if (feature.geometry.type === 'LineString') {
          const coords = feature.geometry.coordinates;
          
          if (adaptive && dem) {
            const gradient = this.calculateAverageGradient(dem, coords);
            const normalizedGradient = Math.min(1, Math.abs(gradient) / 80);
            
            const adaptiveIterations = Math.max(0, Math.floor(iterations * Math.pow(1 - normalizedGradient, 1.5)));
            
            let smoothedCoords = coords;
            for (let i = 0; i < adaptiveIterations; i++) {
              smoothedCoords = this.smoothLine(smoothedCoords);
            }
            
            feature.geometry.coordinates = smoothedCoords;
            feature.properties.gradient = gradient;
            feature.properties.adaptiveSmoothing = adaptiveIterations;
          } else {
            feature.geometry.coordinates = this.smoothLine(coords);
          }
        }
      }
    }

    return smoothed;
  }

  smoothLine(coords) {
    if (coords.length < 3) return coords;

    const result = [coords[0]];

    for (let i = 1; i < coords.length - 1; i++) {
      const prev = coords[i - 1];
      const curr = coords[i];
      const next = coords[i + 1];

      const smoothed = [
        (prev[0] + 2 * curr[0] + next[0]) / 4,
        (prev[1] + 2 * curr[1] + next[1]) / 4
      ];

      result.push(smoothed);
    }

    result.push(coords[coords.length - 1]);
    return result;
  }

  chaikinSmooth(coords, iterations = 1) {
    let result = [...coords];
    
    for (let iter = 0; iter < iterations; iter++) {
      const smoothed = [result[0]];
      
      for (let i = 0; i < result.length - 1; i++) {
        const p0 = result[i];
        const p1 = result[i + 1];
        
        const q = [
          0.75 * p0[0] + 0.25 * p1[0],
          0.75 * p0[1] + 0.25 * p1[1]
        ];
        const r = [
          0.25 * p0[0] + 0.75 * p1[0],
          0.25 * p0[1] + 0.75 * p1[1]
        ];
        
        smoothed.push(q, r);
      }
      
      smoothed.push(result[result.length - 1]);
      result = smoothed;
    }
    
    return result;
  }

  parseASC(content) {
    const lines = content.trim().split('\n');
    let header = {};
    let dataStart = 0;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim().toLowerCase();
      if (line.startsWith('ncols')) {
        header.ncols = parseInt(line.split(/\s+/)[1]);
      } else if (line.startsWith('nrows')) {
        header.nrows = parseInt(line.split(/\s+/)[1]);
      } else if (line.startsWith('xllcorner') || line.startsWith('xllcenter')) {
        header.xll = parseFloat(line.split(/\s+/)[1]);
      } else if (line.startsWith('yllcorner') || line.startsWith('yllcenter')) {
        header.yll = parseFloat(line.split(/\s+/)[1]);
      } else if (line.startsWith('cellsize')) {
        header.cellsize = parseFloat(line.split(/\s+/)[1]);
      } else if (line.startsWith('nodata_value')) {
        header.nodata = parseFloat(line.split(/\s+/)[1]);
      } else {
        dataStart = i;
        break;
      }
    }

    const data = [];
    for (let i = dataStart; i < lines.length; i++) {
      const values = lines[i].trim().split(/\s+/).map(v => parseFloat(v));
      data.push(...values);
    }

    return {
      width: header.ncols,
      height: header.nrows,
      bounds: {
        west: header.xll,
        east: header.xll + header.ncols * header.cellsize,
        south: header.yll,
        north: header.yll + header.nrows * header.cellsize
      },
      data: data
    };
  }

  parseGeoJSON(content) {
    const geojson = JSON.parse(content);
    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;

    const extractCoords = (geom) => {
      if (!geom) return;
      if (geom.type === 'Point') {
        minX = Math.min(minX, geom.coordinates[0]);
        maxX = Math.max(maxX, geom.coordinates[0]);
        minY = Math.min(minY, geom.coordinates[1]);
        maxY = Math.max(maxY, geom.coordinates[1]);
      } else if (geom.type === 'LineString' || geom.type === 'MultiPoint') {
        for (const c of geom.coordinates) {
          minX = Math.min(minX, c[0]);
          maxX = Math.max(maxX, c[0]);
          minY = Math.min(minY, c[1]);
          maxY = Math.max(maxY, c[1]);
        }
      } else if (geom.type === 'Polygon' || geom.type === 'MultiLineString') {
        for (const ring of geom.coordinates) {
          for (const c of ring) {
            minX = Math.min(minX, c[0]);
            maxX = Math.max(maxX, c[0]);
            minY = Math.min(minY, c[1]);
            maxY = Math.max(maxY, c[1]);
          }
        }
      }
    };

    if (geojson.type === 'FeatureCollection') {
      for (const f of geojson.features) {
        extractCoords(f.geometry);
      }
    } else if (geojson.type === 'Feature') {
      extractCoords(geojson.geometry);
    } else {
      extractCoords(geojson);
    }

    return { minX, maxX, minY, maxY, geojson };
  }

  generateSampleContours(interval, smoothing, enableLabels, labelInterval, minLength = 3, adaptiveSmoothing = true) {
    const dem = this.generateSampleDEM(150, 150);
    let contours = this.extractContours(dem, interval, minLength);
    
    if (smoothing > 0) {
      contours = this.smoothContours(contours, Math.floor(smoothing), dem, adaptiveSmoothing);
    }

    return {
      contours,
      bounds: {
        west: dem.bounds.west,
        east: dem.bounds.east,
        south: dem.bounds.south,
        north: dem.bounds.north
      }
    };
  }
}

module.exports = ContourService;

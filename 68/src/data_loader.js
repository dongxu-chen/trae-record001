const DEFAULT_CSV_PATH = './data/points.csv';

const STRIDE = 5;

export async function loadCSVData(filePath = DEFAULT_CSV_PATH, options = {}) {
  const {
    onProgress = null,
    chunkSize = 50000,
    transform = null,
    preallocate = 1000000
  } = options;

  try {
    const response = await fetch(filePath);
    
    if (!response.ok) {
      throw new Error(`无法加载数据文件: ${response.status} ${response.statusText}`);
    }

    const totalSize = response.headers.get('content-length');
    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    
    let received = 0;
    let csvBuffer = '';
    let isFirstChunk = true;
    let headers = null;
    let headerIndices = null;
    
    let capacity = preallocate;
    let positions = new Float64Array(capacity * 2);
    let values = new Float32Array(capacity);
    let categories = new Uint8Array(capacity);
    let timestamps = new Float64Array(capacity);
    let validCount = 0;
    
    const categoryMap = new Map();
    let nextCategoryId = 0;
    
    const updateProgress = () => {
      if (onProgress && totalSize) {
        const progress = Math.min((received / totalSize) * 100, 100);
        onProgress(progress, received, parseInt(totalSize));
      }
    };

    const ensureCapacity = (required) => {
      if (required <= capacity) return;
      const newCapacity = Math.max(capacity * 2, required);
      
      const newPositions = new Float64Array(newCapacity * 2);
      newPositions.set(positions);
      positions = newPositions;
      
      const newValues = new Float32Array(newCapacity);
      newValues.set(values);
      values = newValues;
      
      const newCategories = new Uint8Array(newCapacity);
      newCategories.set(categories);
      categories = newCategories;
      
      const newTimestamps = new Float64Array(newCapacity);
      newTimestamps.set(timestamps);
      timestamps = newTimestamps;
      
      capacity = newCapacity;
    };

    const parseHeaders = (headerLine) => {
      headers = headerLine.split(',').map(h => h.trim().toLowerCase());
      headerIndices = {
        lng: findColumnIndex(headers, ['longitude', 'lng', 'x']),
        lat: findColumnIndex(headers, ['latitude', 'lat', 'y']),
        value: findColumnIndex(headers, ['value', 'height', 'z']),
        category: findColumnIndex(headers, ['category', 'type']),
        timestamp: findColumnIndex(headers, ['timestamp', 'time', 'date'])
      };
    };

    const findColumnIndex = (headers, candidates) => {
      for (const candidate of candidates) {
        const idx = headers.indexOf(candidate);
        if (idx !== -1) return idx;
      }
      return -1;
    };

    const parseAndStoreRows = (rowsText) => {
      const lines = rowsText.split('\n');
      
      for (const line of lines) {
        if (!line || line.trim() === '') continue;
        
        const cols = splitCSVLine(line);
        if (cols.length < 2) continue;
        
        const lng = parseFloat(cols[headerIndices.lng]);
        const lat = parseFloat(cols[headerIndices.lat]);
        
        if (isNaN(lng) || isNaN(lat) || 
            lng < -180 || lng > 180 || 
            lat < -90 || lat > 90) {
          continue;
        }
        
        ensureCapacity(validCount + 1);
        
        const idx = validCount;
        positions[idx * 2] = lng;
        positions[idx * 2 + 1] = lat;
        
        if (headerIndices.value !== -1 && cols[headerIndices.value]) {
          values[idx] = parseFloat(cols[headerIndices.value]) || 0;
        } else {
          values[idx] = 0;
        }
        
        if (headerIndices.category !== -1 && cols[headerIndices.category]) {
          const cat = cols[headerIndices.category].trim();
          if (!categoryMap.has(cat)) {
            categoryMap.set(cat, nextCategoryId++);
          }
          categories[idx] = categoryMap.get(cat);
        } else {
          categories[idx] = 255;
        }
        
        if (headerIndices.timestamp !== -1 && cols[headerIndices.timestamp]) {
          const ts = Date.parse(cols[headerIndices.timestamp]);
          timestamps[idx] = isNaN(ts) ? 0 : ts;
        } else {
          timestamps[idx] = 0;
        }
        
        validCount++;
      }
    };

    while (true) {
      const { done, value } = await reader.read();
      
      if (done) {
        if (csvBuffer) {
          parseAndStoreRows(csvBuffer);
        }
        break;
      }

      const chunk = decoder.decode(value, { stream: true });
      received += value.length;

      if (isFirstChunk) {
        csvBuffer += chunk;
        const firstNewline = csvBuffer.indexOf('\n');
        if (firstNewline !== -1) {
          const headerLine = csvBuffer.substring(0, firstNewline).trim();
          parseHeaders(headerLine);
          csvBuffer = csvBuffer.substring(firstNewline + 1);
          isFirstChunk = false;
        }
        continue;
      }

      csvBuffer += chunk;
      
      const lastNewline = csvBuffer.lastIndexOf('\n');
      if (lastNewline !== -1) {
        const parseablePart = csvBuffer.substring(0, lastNewline + 1);
        csvBuffer = csvBuffer.substring(lastNewline + 1);
        parseAndStoreRows(parseablePart);
        updateProgress();
      }
    }

    const finalPositions = positions.slice(0, validCount * 2);
    const finalValues = values.slice(0, validCount);
    const finalCategories = categories.slice(0, validCount);
    const finalTimestamps = timestamps.slice(0, validCount);

    const categoryReverseMap = new Map();
    categoryMap.forEach((id, name) => categoryReverseMap.set(id, name));

    const bounds = calculateBoundsFromArrays(finalPositions, finalValues, validCount);

    const dataStore = {
      count: validCount,
      positions: finalPositions,
      values: finalValues,
      categories: finalCategories,
      timestamps: finalTimestamps,
      categoryMap: categoryReverseMap,
      bounds,
      getPoint: (index) => getPointFromArrays(index, finalPositions, finalValues, finalCategories, finalTimestamps, categoryReverseMap),
      getPointsAsArray: () => pointsToArray(finalPositions, finalValues, finalCategories, finalTimestamps, categoryReverseMap, validCount),
      memoryUsage: estimateMemoryUsage(validCount)
    };

    updateProgress();
    
    if (validCount === 0) {
      throw new Error('CSV 文件中没有有效数据点');
    }
    
    console.log(`✅ 数据加载完成: ${validCount.toLocaleString()} 点, 内存约 ${dataStore.memoryUsage}`);
    
    return dataStore;
  } catch (error) {
    console.error('加载 CSV 数据失败:', error);
    throw error;
  }
}

function splitCSVLine(line) {
  const result = [];
  let current = '';
  let inQuotes = false;
  
  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    
    if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === ',' && !inQuotes) {
      result.push(current.trim());
      current = '';
    } else {
      current += char;
    }
  }
  result.push(current.trim());
  
  return result;
}

function getPointFromArrays(index, positions, values, categories, timestamps, categoryReverseMap) {
  const lng = positions[index * 2];
  const lat = positions[index * 2 + 1];
  const value = values[index];
  const categoryId = categories[index];
  const timestamp = timestamps[index];
  
  return {
    id: index,
    longitude: lng,
    latitude: lat,
    value,
    category: categoryId !== 255 ? categoryReverseMap.get(categoryId) : null,
    timestamp: timestamp !== 0 ? timestamp : null
  };
}

function pointsToArray(positions, values, categories, timestamps, categoryReverseMap, count) {
  const arr = new Array(count);
  for (let i = 0; i < count; i++) {
    arr[i] = getPointFromArrays(i, positions, values, categories, timestamps, categoryReverseMap);
  }
  return arr;
}

function calculateBoundsFromArrays(positions, values, count) {
  if (count === 0) return null;

  let minLng = Infinity, maxLng = -Infinity;
  let minLat = Infinity, maxLat = -Infinity;
  let minVal = Infinity, maxVal = -Infinity;

  for (let i = 0; i < count; i++) {
    const lng = positions[i * 2];
    const lat = positions[i * 2 + 1];
    const val = values[i];
    
    minLng = Math.min(minLng, lng);
    maxLng = Math.max(maxLng, lng);
    minLat = Math.min(minLat, lat);
    maxLat = Math.max(maxLat, lat);
    minVal = Math.min(minVal, val);
    maxVal = Math.max(maxVal, val);
  }

  return {
    minLng, maxLng,
    minLat, maxLat,
    minValue: minVal,
    maxValue: maxVal,
    centerLng: (minLng + maxLng) / 2,
    centerLat: (minLat + maxLat) / 2
  };
}

function estimateMemoryUsage(count) {
  const bytes = count * (16 + 4 + 1 + 8);
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function generateSampleData(count = 100000, options = {}) {
  const {
    centerLng = 116.4074,
    centerLat = 39.9042,
    spread = 0.5
  } = options;

  const positions = new Float64Array(count * 2);
  const values = new Float32Array(count);
  const categories = new Uint8Array(count);
  const timestamps = new Float64Array(count);
  
  const categoryNames = ['A', 'B', 'C', 'D'];
  const categoryReverseMap = new Map([
    [0, 'A'], [1, 'B'], [2, 'C'], [3, 'D']
  ]);
  const now = Date.now();

  for (let i = 0; i < count; i++) {
    const angle = Math.random() * Math.PI * 2;
    const radius = Math.pow(Math.random(), 0.5) * spread;
    
    positions[i * 2] = centerLng + Math.cos(angle) * radius;
    positions[i * 2 + 1] = centerLat + Math.sin(angle) * radius;
    values[i] = Math.random() * 100;
    categories[i] = Math.floor(Math.random() * 4);
    timestamps[i] = now - Math.random() * 86400000;
    
    if (i % 100000 === 0 && i > 0) {
      console.log(`已生成 ${i.toLocaleString()} / ${count.toLocaleString()} 点...`);
    }
  }

  const bounds = calculateBoundsFromArrays(positions, values, count);

  const result = {
    count,
    positions,
    values,
    categories,
    timestamps,
    categoryMap: categoryReverseMap,
    bounds,
    getPoint: (index) => getPointFromArrays(index, positions, values, categories, timestamps, categoryReverseMap),
    getPointsAsArray: () => pointsToArray(positions, values, categories, timestamps, categoryReverseMap, count),
    memoryUsage: estimateMemoryUsage(count)
  };
  
  console.log(`🎲 示例数据生成完成: ${count.toLocaleString()} 点, 内存约 ${result.memoryUsage}`);
  
  return result;
}

export function calculateBounds(points) {
  if (!points || points.length === 0) return null;
  
  let minLng = Infinity, maxLng = -Infinity;
  let minLat = Infinity, maxLat = -Infinity;
  let minVal = Infinity, maxVal = -Infinity;

  for (const p of points) {
    minLng = Math.min(minLng, p.longitude);
    maxLng = Math.max(maxLng, p.longitude);
    minLat = Math.min(minLat, p.latitude);
    maxLat = Math.max(maxLat, p.latitude);
    minVal = Math.min(minVal, p.value || 0);
    maxVal = Math.max(maxVal, p.value || 0);
  }

  return {
    minLng, maxLng,
    minLat, maxLat,
    minValue: minVal,
    maxValue: maxVal,
    centerLng: (minLng + maxLng) / 2,
    centerLat: (minLat + maxLat) / 2
  };
}

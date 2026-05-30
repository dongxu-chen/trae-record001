const ContourService = require('./services/contourService');

const contourService = new ContourService();

const dem = contourService.generateSampleDEM(20, 20);
console.log(`DEM尺寸: ${dem.width}x${dem.height}`);
console.log(`高程范围: ${Math.min(...dem.data).toFixed(2)} - ${Math.max(...dem.data).toFixed(2)}`);

const level = 500;
console.log(`\n检查高程 ${level}m 的等高线:`);

let segmentCount = 0;
for (let y = 0; y < dem.height - 1; y++) {
  for (let x = 0; x < dem.width - 1; x++) {
    const idx = y * dem.width + x;
    const values = [
      dem.data[idx],
      dem.data[idx + 1],
      dem.data[idx + 1 + dem.width],
      dem.data[idx + dem.width]
    ];
    
    const minV = Math.min(...values);
    const maxV = Math.max(...values);
    
    if (level >= minV && level <= maxV) {
      const points = contourService.getContourPoints(dem, level, x, y);
      if (points.length > 0) {
        console.log(`  单元格 (${x},${y}): values=[${values.map(v=>v.toFixed(1)).join(',')}] -> ${points.length} 个点`);
        segmentCount++;
      }
    }
  }
}

console.log(`\n总计找到 ${segmentCount} 个包含等高线的单元格`);

if (segmentCount > 0) {
  console.log(`\n测试提取线段:`);
  const segments = contourService.extractLevelSegments(dem, level);
  console.log(`提取到 ${segments.length} 个线段`);
  
  const lineStrings = contourService.connectSegments(segments, 2);
  console.log(`连接成 ${lineStrings.length} 条等高线`);
  
  for (let i = 0; i < lineStrings.length; i++) {
    console.log(`  线 ${i}: ${lineStrings[i].length} 个点`);
  }
}

console.log(`\n测试完整提取所有等高线:`);
const allContours = contourService.extractContours(dem, 50, 2);
console.log(`提取到 ${allContours.features.length} 条等高线`);
for (const f of allContours.features) {
  console.log(`  ${f.properties.elevation}m: ${f.geometry.coordinates.length} 个点`);
}

const ContourService = require('./services/contourService');

const contourService = new ContourService();

console.log('生成示例DEM...');
const dem = contourService.generateSampleDEM(150, 150);
console.log(`DEM尺寸: ${dem.width}x${dem.height}`);
console.log(`高程范围: ${Math.min(...dem.data)} - ${Math.max(...dem.data)}`);

console.log('\n测试提取等高线...');
const interval = 50;
const minElevation = Math.min(...dem.data);
const maxElevation = Math.max(...dem.data);
const startLevel = Math.ceil(minElevation / interval) * interval;
console.log(`等高距: ${interval}m, 起始高程: ${startLevel}m, 最大高程: ${maxElevation}m`);

let totalContours = 0;
for (let level = startLevel; level <= maxElevation; level += interval) {
  console.log(`\n处理高程: ${level}m`);
  const segments = contourService.extractLevelSegments(dem, level);
  const lineStrings = contourService.connectSegments(segments, 2);
  console.log(`  找到 ${lineStrings.length} 条等高线 (${segments.length} 个线段)`);
  for (let i = 0; i < lineStrings.length; i++) {
    console.log(`  线 ${i}: ${lineStrings[i].length} 个点`);
  }
  totalContours += lineStrings.length;
}

console.log(`\n总计: ${totalContours} 条等高线`);

console.log('\n测试完整extractContours...');
const contours = contourService.extractContours(dem, 50, 2);
console.log(`提取到 ${contours.features.length} 条等高线`);
if (contours.features.length > 0) {
  console.log('前3条:');
  for (let i = 0; i < Math.min(3, contours.features.length); i++) {
    const f = contours.features[i];
    console.log(`  ${f.properties.elevation}m - ${f.geometry.coordinates.length} 个点, 角度: ${f.properties.angle}°`);
  }
}

console.log('\n测试自适应平滑...');
const smoothed = contourService.smoothContours(contours, 2, dem, true);
console.log(`平滑后 ${smoothed.features.length} 条等高线`);
if (smoothed.features.length > 0) {
  for (let i = 0; i < Math.min(3, smoothed.features.length); i++) {
    const f = smoothed.features[i];
    console.log(`  ${f.properties.elevation}m - 梯度: ${f.properties.gradient?.toFixed(2)}, 平滑级别: ${f.properties.adaptiveSmoothing}`);
  }
}

import { writeFileSync, mkdirSync, existsSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

function generateCSVData(count, options = {}) {
  const {
    centerLng = 116.4074,
    centerLat = 39.9042,
    spread = 0.5,
    seed = Date.now()
  } = options;

  let seedVal = seed;
  const random = () => {
    seedVal = (seedVal * 9301 + 49297) % 233280;
    return seedVal / 233280;
  };

  const headers = ['id,longitude,latitude,value,category,timestamp'];
  const rows = [];
  const categories = ['A', 'B', 'C', 'D'];
  const now = Date.now();

  for (let i = 0; i < count; i++) {
    const angle = random() * Math.PI * 2;
    const radius = Math.pow(random(), 0.5) * spread;
    
    const lng = centerLng + Math.cos(angle) * radius;
    const lat = centerLat + Math.sin(angle) * radius;
    const value = Math.floor(random() * 1000) / 10;
    const category = categories[Math.floor(random() * categories.length)];
    const timestamp = now - Math.floor(random() * 86400000);

    rows.push(`${i},${lng.toFixed(6)},${lat.toFixed(6)},${value.toFixed(1)},${category},${new Date(timestamp).toISOString()}`);

    if (rows.length % 10000 === 0) {
      console.log(`已生成 ${i + 1} / ${count} 个点...`);
    }
  }

  return headers.concat(rows).join('\n');
}

function main() {
  const args = process.argv.slice(2);
  const count = parseInt(args[0]) || 100000;
  const outputFile = args[1] || join(__dirname, '..', 'data', 'points.csv');

  console.log(`\n🚀 开始生成 ${count.toLocaleString()} 个点的数据...\n`);
  console.log(`输出文件: ${outputFile}\n`);

  const dataDir = dirname(outputFile);
  if (!existsSync(dataDir)) {
    mkdirSync(dataDir, { recursive: true });
    console.log(`📁 创建数据目录: ${dataDir}`);
  }

  const startTime = Date.now();
  const csvContent = generateCSVData(count);

  console.log(`\n💾 正在写入文件...`);
  writeFileSync(outputFile, csvContent, 'utf-8');

  const endTime = Date.now();
  const duration = (endTime - startTime) / 1000;
  const fileSize = (Buffer.byteLength(csvContent, 'utf-8') / 1024 / 1024).toFixed(2);

  console.log(`\n✅ 数据生成完成!`);
  console.log(`   - 总点数: ${count.toLocaleString()}`);
  console.log(`   - 文件大小: ${fileSize} MB`);
  console.log(`   - 耗时: ${duration.toFixed(2)} 秒`);
  console.log(`   - 输出路径: ${outputFile}\n`);
}

main();

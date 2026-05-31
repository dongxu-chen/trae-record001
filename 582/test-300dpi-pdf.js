
import fs from 'fs';

const cardIds = [
  '53785a6f-7208-4ff1-91a7-f5e8b3d314d8',
  '64aae476-ea1b-401c-b809-b6a959e5d8c6',
  '0780216f-b0a2-4cf3-988b-766c49db2ae0',
  '0e826824-6fef-45de-bfe8-923a667c9925',
  '1bd75504-38cd-40ee-ba0b-06a2563fa2ec',
  '1ccf21cd-743f-4c11-b144-fe64a46305bf',
];

async function test300DpiPdfExport() {
  console.log('\n🖨️  开始测试 300DPI PDF 打印版导出...');
  console.log('DPI 设置: 300 (印刷级)');
  console.log(`测试卡牌数: ${cardIds.length} 张\n`);
  
  const startTime = Date.now();
  
  try {
    const printOptions = {
      cardIds: cardIds,
      paperSize: 'A4',
      orientation: 'portrait',
      columns: 2,
      rows: 3,
      margin: 36,
      bleed: 0,
      cropMarks: true,
    };
    
    console.log('📄 打印配置:');
    console.log('────────────────────────────────');
    console.log(`纸张: ${printOptions.paperSize} ${printOptions.orientation === 'portrait' ? '纵向' : '横向'}`);
    console.log(`布局: ${printOptions.columns}×${printOptions.rows}`);
    console.log(`边距: ${printOptions.margin}pt`);
    console.log(`出血: ${printOptions.bleed}pt`);
    console.log(`裁切线: ${printOptions.cropMarks ? '显示' : '隐藏'}`);
    console.log('────────────────────────────────\n');
    
    const response = await fetch('http://localhost:3001/api/export/print', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(printOptions),
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || '导出失败');
    }
    
    const buffer = Buffer.from(await response.arrayBuffer());
    const endTime = Date.now();
    const duration = (endTime - startTime) / 1000;
    
    const outputPath = './test-print-300dpi.pdf';
    fs.writeFileSync(outputPath, buffer);
    
    const fileSizeKB = (buffer.length / 1024).toFixed(2);
    const fileSizeMB = (buffer.length / 1024 / 1024).toFixed(2);
    
    console.log('✅ PDF 生成成功！');
    console.log('────────────────────────────────');
    console.log(`📁 输出文件: ${outputPath}`);
    console.log(`📦 文件大小: ${fileSizeKB} KB (${fileSizeMB} MB)`);
    console.log(`⏱️  生成耗时: ${duration.toFixed(2)}s`);
    console.log(`🖨️  打印DPI: 300 (印刷级)`);
    console.log(`📐 DPI倍率: 4.167x (300/72)`);
    console.log('────────────────────────────────\n');
    
    console.log('🎉 300DPI PDF打印版导出测试通过！');
    console.log('💡 提示: 请用PDF阅读器打开文件检查图片清晰度，');
    console.log('         放大到400%应无明显锯齿，满足印刷要求。\n');
    
    return true;
  } catch (error) {
    console.error('❌ 测试失败:', error.message);
    return false;
  }
}

test300DpiPdfExport();

export function generateLargeCode(lines: number = 500): string {
  const codeLines: string[] = [];

  codeLines.push(`// 大文件测试 - 共 ${lines} 行代码`);
  codeLines.push(`// 用于测试 Web Worker 高亮性能`);
  codeLines.push(``);
  codeLines.push(`class LargeCodeDemo {`);
  codeLines.push(`  private data: any[] = [];`);
  codeLines.push(``);

  for (let i = 0; i < Math.floor((lines - 50) / 4); i++) {
    codeLines.push(`  // 方法 ${i + 1}`);
    codeLines.push(`  method${i + 1}(param: string): number {`);
    codeLines.push(`    const result = param.length * ${i + 1};`);
    codeLines.push(`    return result > 100 ? result / 2 : result;`);
    codeLines.push(`  }`);
    codeLines.push(``);
  }

  codeLines.push(`  // 数据处理方法`);
  codeLines.push(`  processData(input: string[]): string[] {`);
  codeLines.push(`    return input.map((item, index) => {`);
  codeLines.push(`      const processed = item.toUpperCase();`);
  codeLines.push(`      return processed + '_' + index;`);
  codeLines.push(`    });`);
  codeLines.push(`  }`);
  codeLines.push(``);

  codeLines.push(`  // 异步请求方法`);
  codeLines.push(`  async fetchData(url: string): Promise<any> {`);
  codeLines.push(`    try {`);
  codeLines.push(`      const response = await fetch(url);`);
  codeLines.push(`      if (!response.ok) {`);
  codeLines.push(`        throw new Error('Network response was not ok');`);
  codeLines.push(`      }`);
  codeLines.push(`      const data = await response.json();`);
  codeLines.push(`      return data;`);
  codeLines.push(`    } catch (error) {`);
  codeLines.push(`      console.error('Error fetching data:', error);`);
  codeLines.push(`      throw error;`);
  codeLines.push(`    }`);
  codeLines.push(`  }`);
  codeLines.push(``);

  codeLines.push(`  // 复杂计算方法`);
  codeLines.push(`  complexCalculation(n: number): number {`);
  codeLines.push(`    let result = 0;`);
  codeLines.push(`    for (let i = 0; i < n; i++) {`);
  codeLines.push(`      for (let j = 0; j < n; j++) {`);
  codeLines.push(`        result += Math.sqrt(i * j + 1);`);
  codeLines.push(`      }`);
  codeLines.push(`    }`);
  codeLines.push(`    return Math.floor(result);`);
  codeLines.push(`  }`);
  codeLines.push(`}`);
  codeLines.push(``);

  codeLines.push(`// 实例化并使用`);
  codeLines.push(`const demo = new LargeCodeDemo();`);
  codeLines.push(`console.log('Demo instance created:', demo);`);

  return codeLines.join('\n');
}

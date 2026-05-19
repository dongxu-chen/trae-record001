import Prism from 'prismjs';
import 'prismjs/components/prism-javascript';
import { LezerParser } from '../lezer/parser';
import { SyntaxHighlighter } from '../lezer/highlighter';

export interface BenchmarkResult {
  name: string;
  lezerTime: number;
  prismTime: number;
  improvement: number;
  codeLength: number;
  lineCount: number;
}

export interface BenchmarkOptions {
  iterations?: number;
  warmup?: boolean;
  languages?: string[];
}

function generateCode(lineCount: number): string {
  const lines: string[] = [];
  const patterns = [
    'const x = 42;',
    'function foo(a, b) { return a + b; }',
    'if (condition) {',
    '  console.log(\"hello\");',
    '} else {',
    '  return null;',
    '}',
    'class MyClass {',
    '  constructor(name) {',
    '    this.name = name;',
    '  }',
    '  method() {',
    '    return this.name.toUpperCase();',
    '  }',
    '}',
    'const arr = [1, 2, 3, 4, 5];',
    'const obj = { key: "value", nested: { a: 1 } };',
    'export default MyClass;',
  ];

  for (let i = 0; i < lineCount; i++) {
    lines.push(patterns[i % patterns.length]);
  }
  return lines.join('\n');
}

export async function benchmarkLezer(code: string, language: string = 'javascript', iterations: number = 1): Promise<number> {
  const parser = new LezerParser(language);
  let totalTime = 0;

  for (let i = 0; i < iterations; i++) {
    const start = performance.now();
    const parseResult = parser.parse(code);
    const highlighter = new SyntaxHighlighter(parseResult.tree, code);
    highlighter.renderToLines();
    totalTime += performance.now() - start;
  }

  return totalTime / iterations;
}

export async function benchmarkPrism(code: string, language: string = 'javascript', iterations: number = 1): Promise<number> {
  let totalTime = 0;

  for (let i = 0; i < iterations; i++) {
    const start = performance.now();
    Prism.highlight(code, Prism.languages[language], language);
    totalTime += performance.now() - start;
  }

  return totalTime / iterations;
}

export async function runBenchmark(options: BenchmarkOptions = {}): Promise<BenchmarkResult[]> {
  const { iterations = 5, warmup = true } = options;
  const results: BenchmarkResult[] = [];

  const lineCounts = [10, 100, 500, 1000, 2000];

  if (warmup) {
    console.log('Warming up...');
    const warmupCode = generateCode(100);
    await benchmarkLezer(warmupCode, 'javascript', 3);
    await benchmarkPrism(warmupCode, 'javascript', 3);
  }

  console.log('\nRunning benchmarks...');
  console.log('='.repeat(80));

  for (const lineCount of lineCounts) {
    const code = generateCode(lineCount);

    console.log(`\nCode size: ${lineCount} lines, ${code.length} chars`);

    const lezerTime = await benchmarkLezer(code, 'javascript', iterations);
    const prismTime = await benchmarkPrism(code, 'javascript', iterations);

    const improvement = ((prismTime - lezerTime) / prismTime * 100;

    console.log(`  Lezer:    ${lezerTime.toFixed(2)}ms`);
    console.log(`  Prism.js:  ${prismTime.toFixed(2)}ms`);
    console.log(`  Speedup:   ${improvement > 0 ? '+' : ''}${improvement.toFixed(1)}%`);

    results.push({
      name: `${lineCount} lines`,
      lezerTime,
      prismTime,
      improvement,
      codeLength: code.length,
      lineCount,
    });
  }

  console.log('\n' + '='.repeat(80));

  return results;
}

export function printBenchmarkTable(results: BenchmarkResult[]): string {
  const headers = ['Test Case', 'Lezer (ms)', 'Prism.js (ms)', 'Improvement (%)'];
  const rows = results.map(r => [
    r.name,
    r.lezerTime.toFixed(2),
    r.prismTime.toFixed(2),
    (r.improvement > 0 ? '+' : '') + r.improvement.toFixed(1),
  ]);

  const colWidths = headers.map((h, i) => Math.max(h.length, ...rows.map(r => r[i].length)));

  let output = '';
  output += '┌' + colWidths.map(w => '─'.repeat(w + 2)).join('┬') + '┐\n';
  output += '│' + headers.map((h, i) => ` ${h.padEnd(colWidths[i])} `).join('│') + '│\n';
  output += '├' + colWidths.map(w => '─'.repeat(w + 2)).join('┼') + '┤\n';

  for (const row of rows) {
    output += '│' + row.map((cell, i) => ` ${cell.padStart(colWidths[i])} `).join('│') + '│\n';
  }

  output += '└' + colWidths.map(w => '─'.repeat(w + 2)).join('┴') + '┘\n';

  return output;
}

export function generateSummary(results: BenchmarkResult[]): { averageImprovement: number; totalLezer: number; totalPrism: number } {
  const totalLezer = results.reduce((sum, r) => sum + r.lezerTime, 0);
  const totalPrism = results.reduce((sum, r) => sum + r.prismTime, 0);
  const averageImprovement = ((totalPrism - totalLezer) / totalPrism * 100;

  return {
    averageImprovement,
    totalLezer,
    totalPrism,
  };
}

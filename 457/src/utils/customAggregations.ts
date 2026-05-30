import { CustomAggregation, DataRow } from '@/types';

export const defaultCustomAggregations: CustomAggregation[] = [
  {
    id: 'weighted_avg',
    name: '加权平均',
    description: '按权重计算平均值',
    code: `
// values: 当前单元格的数值数组
// data: 对应的原始数据行数组
// field: 当前计算的字段名
function weightedAvg(values, data, field) {
  if (values.length === 0) return 0;
  // 假设数据中有"销量"字段作为权重
  let totalWeight = 0;
  let weightedSum = 0;
  data.forEach((row, i) => {
    const weight = Number(row['销量']) || 1;
    weightedSum += values[i] * weight;
    totalWeight += weight;
  });
  return totalWeight > 0 ? weightedSum / totalWeight : 0;
}
return weightedAvg(values, data, field);
    `.trim(),
  },
  {
    id: 'median',
    name: '中位数',
    description: '计算中位数',
    code: `
function median(values) {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 0) {
    return (sorted[mid - 1] + sorted[mid]) / 2;
  }
  return sorted[mid];
}
return median(values);
    `.trim(),
  },
  {
    id: 'growth_rate',
    name: '增长率',
    description: '计算同比/环比增长率',
    code: `
// 需要按日期排序后计算
function growthRate(values, data, field) {
  if (values.length < 2) return 0;
  // 按日期排序
  const sorted = data.map((row, i) => ({
    value: values[i],
    date: row['日期']
  })).sort((a, b) => String(a.date).localeCompare(String(b.date)));
  
  const first = sorted[0].value;
  const last = sorted[sorted.length - 1].value;
  if (first === 0) return 0;
  return ((last - first) / first) * 100;
}
return growthRate(values, data, field);
    `.trim(),
  },
];

export class SafeSandbox {
  private whitelist: Set<string>;

  constructor() {
    this.whitelist = new Set([
      'Math', 'Number', 'String', 'Array', 'Object',
      'parseInt', 'parseFloat', 'isNaN', 'isFinite',
      'JSON', 'Date', 'Map', 'Set',
    ]);
  }

  execute(
    code: string,
    context: {
      values: number[];
      data: DataRow[];
      field: string;
      [key: string]: any;
    }
  ): number {
    try {
      const allowedGlobals = Array.from(this.whitelist).reduce((acc, key) => {
        acc[key] = (globalThis as any)[key];
        return acc;
      }, {} as Record<string, any>);

      const sandbox = {
        ...allowedGlobals,
        ...context,
        console: {
          log: () => {},
          error: () => {},
          warn: () => {},
        },
      };

      const sandboxKeys = Object.keys(sandbox);
      const sandboxValues = Object.values(sandbox);

      const wrappedCode = `
        "use strict";
        ${code}
      `;

      const fn = new Function(...sandboxKeys, wrappedCode);
      const result = fn(...sandboxValues);

      if (typeof result === 'number') {
        return isFinite(result) ? result : 0;
      }
      if (typeof result === 'string') {
        const parsed = parseFloat(result);
        return isFinite(parsed) ? parsed : 0;
      }
      return 0;
    } catch (error) {
      console.error('Custom aggregation error:', error);
      return 0;
    }
  }

  validate(code: string): { valid: boolean; error?: string } {
    try {
      const forbiddenPatterns = [
        /eval\s*\(/,
        /Function\s*\(/,
        /new\s+Function/,
        /window\./,
        /document\./,
        /globalThis/,
        /fetch\s*\(/,
        /XMLHttpRequest/,
        /import\s+/,
        /require\s*\(/,
        /\$\{/,
        /setTimeout/,
        /setInterval/,
      ];

      for (const pattern of forbiddenPatterns) {
        if (pattern.test(code)) {
          return {
            valid: false,
            error: `代码中包含不允许的内容: ${pattern.toString()}`,
          };
        }
      }

      const testContext = {
        values: [1, 2, 3, 4, 5],
        data: [{ test: 1 }, { test: 2 }, { test: 3 }, { test: 4 }, { test: 5 }],
        field: 'test',
      };

      const result = this.execute(code, testContext);
      if (typeof result !== 'number') {
        return {
          valid: false,
          error: '函数必须返回一个数字',
        };
      }

      return { valid: true };
    } catch (error: any) {
      return {
        valid: false,
        error: error.message || '语法错误',
      };
    }
  }
}

export const sandbox = new SafeSandbox();

export const executeCustomAggregation = (
  code: string,
  values: number[],
  data: DataRow[],
  field: string
): number => {
  return sandbox.execute(code, { values, data, field });
};

export const validateCustomAggregation = (
  code: string
): { valid: boolean; error?: string } => {
  return sandbox.validate(code);
};

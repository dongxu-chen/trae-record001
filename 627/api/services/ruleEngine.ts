import type { DataQualityRule, RuleExecutionResult } from '../../shared/types.js';

export interface MockTableData {
  [tableName: string]: Array<Record<string, unknown>>;
}

const DEFAULT_SAMPLE_RATE = 0.2;
const MIN_SAMPLE_SIZE = 50;

const mockData: MockTableData = {
  users: [
    { id: 1, name: '张三', email: 'zhangsan@example.com', age: 25, department_id: 1 },
    { id: 2, name: '李四', email: 'lisi@example.com', age: 30, department_id: 1 },
    { id: 3, name: '王五', email: null, age: 28, department_id: 2 },
    { id: 4, name: '赵六', email: 'zhaoliu@example.com', age: 35, department_id: 99 },
    { id: 5, name: '', email: 'user5@example.com', age: -5, department_id: 1 },
    { id: 6, name: '孙七', email: 'sunqi@example.com', age: 42, department_id: 3 },
    { id: 7, name: '周八', email: null, age: 27, department_id: 2 },
    { id: 8, name: '吴九', email: 'wujiu@example.com', age: 33, department_id: 1 },
    { id: 9, name: '郑十', email: 'zhengshi@example.com', age: 29, department_id: 4 },
    { id: 10, name: '陈一', email: 'chenyi@example.com', age: 31, department_id: 99 },
    { id: 11, name: '林二', email: null, age: 26, department_id: 1 },
    { id: 12, name: '黄三', email: 'huangsan@example.com', age: 38, department_id: 2 },
  ],
  departments: [
    { id: 1, name: '技术部' },
    { id: 2, name: '市场部' },
    { id: 3, name: '财务部' },
  ],
  orders: [
    { id: 1001, user_id: 1, amount: 1500, status: 'completed' },
    { id: 1002, user_id: 2, amount: 2300, status: 'pending' },
    { id: 1003, user_id: 99, amount: 500, status: 'completed' },
    { id: 1004, user_id: 3, amount: 0, status: 'cancelled' },
    { id: 1005, user_id: 5, amount: 800, status: 'completed' },
    { id: 1006, user_id: 99, amount: 1200, status: 'pending' },
    { id: 1007, user_id: 7, amount: 350, status: 'completed' },
    { id: 1008, user_id: 88, amount: 900, status: 'cancelled' },
    { id: 1009, user_id: 1, amount: 2100, status: 'completed' },
    { id: 1010, user_id: 10, amount: 600, status: 'pending' },
  ],
};

function getTableData(tableName: string): Array<Record<string, unknown>> {
  return mockData[tableName] || [];
}

function sampleArray<T>(arr: T[], sampleRate: number): T[] {
  if (arr.length <= MIN_SAMPLE_SIZE) return arr;
  const sampleSize = Math.max(MIN_SAMPLE_SIZE, Math.ceil(arr.length * sampleRate));
  const step = Math.floor(arr.length / sampleSize);
  const result: T[] = [];
  for (let i = 0; i < arr.length && result.length < sampleSize; i += step) {
    result.push(arr[i]);
  }
  return result;
}

export function executeNullCheckRule(
  rule: DataQualityRule,
  tableData: Array<Record<string, unknown>>
): RuleExecutionResult {
  const issues: RuleExecutionResult['issues'] = [];
  const allowNull = rule.config.nullCheck?.allowNull ?? false;

  tableData.forEach((row, index) => {
    const value = row[rule.columnName];
    const isNull = value === null || value === undefined || value === '';

    if (!allowNull && isNull) {
      issues.push({
        ruleId: rule.id,
        ruleName: rule.name,
        tableName: rule.tableName,
        columnName: rule.columnName,
        rowIdentifier: `row_${index}_${row.id ?? index}`,
        issueType: 'null_check',
        description: `列 ${rule.columnName} 存在空值`,
      });
    }
  });

  return {
    ruleId: rule.id,
    ruleName: rule.name,
    success: issues.length === 0,
    totalRecords: tableData.length,
    failedRecords: issues.length,
    issues,
  };
}

export function executeUniquenessRule(
  rule: DataQualityRule,
  tableData: Array<Record<string, unknown>>
): RuleExecutionResult {
  const issues: RuleExecutionResult['issues'] = [];
  const columns = rule.config.uniqueness?.columns || [rule.columnName];
  const seen = new Map<string, number[]>();

  tableData.forEach((row, index) => {
    const key = columns.map(col => String(row[col] ?? '')).join('|');
    if (seen.has(key)) {
      seen.get(key)!.push(index);
    } else {
      seen.set(key, [index]);
    }
  });

  seen.forEach((indices, key) => {
    if (indices.length > 1) {
      indices.forEach(index => {
        const row = tableData[index];
        issues.push({
          ruleId: rule.id,
          ruleName: rule.name,
          tableName: rule.tableName,
          columnName: columns.join(','),
          rowIdentifier: `row_${index}_${row.id ?? index}`,
          issueType: 'uniqueness',
          description: `唯一键 [${key}] 重复，出现 ${indices.length} 次`,
        });
      });
    }
  });

  return {
    ruleId: rule.id,
    ruleName: rule.name,
    success: issues.length === 0,
    totalRecords: tableData.length,
    failedRecords: issues.length,
    issues,
  };
}

export function executeValueRangeRule(
  rule: DataQualityRule,
  tableData: Array<Record<string, unknown>>
): RuleExecutionResult {
  const issues: RuleExecutionResult['issues'] = [];
  const config = rule.config.valueRange;

  tableData.forEach((row, index) => {
    const value = row[rule.columnName];
    let failed = false;
    let description = '';

    if (config?.min !== undefined && config?.min !== null) {
      const numValue = Number(value);
      if (numValue < config.min) {
        failed = true;
        description = `值 ${numValue} 小于最小值 ${config.min}`;
      }
    }

    if (!failed && config?.max !== undefined && config?.max !== null) {
      const numValue = Number(value);
      if (numValue > config.max) {
        failed = true;
        description = `值 ${numValue} 大于最大值 ${config.max}`;
      }
    }

    if (!failed && config?.allowedValues && config.allowedValues.length > 0) {
      if (!config.allowedValues.includes(String(value))) {
        failed = true;
        description = `值 ${value} 不在允许列表中`;
      }
    }

    if (!failed && config?.pattern) {
      const regex = new RegExp(config.pattern);
      if (!regex.test(String(value))) {
        failed = true;
        description = `值 ${value} 不匹配正则模式`;
      }
    }

    if (failed) {
      issues.push({
        ruleId: rule.id,
        ruleName: rule.name,
        tableName: rule.tableName,
        columnName: rule.columnName,
        rowIdentifier: `row_${index}_${row.id ?? index}`,
        issueType: 'value_range',
        description,
      });
    }
  });

  return {
    ruleId: rule.id,
    ruleName: rule.name,
    success: issues.length === 0,
    totalRecords: tableData.length,
    failedRecords: issues.length,
    issues,
  };
}

export function executeDependencyRule(
  rule: DataQualityRule,
  tableData: Array<Record<string, unknown>>
): RuleExecutionResult {
  const issues: RuleExecutionResult['issues'] = [];
  const config = rule.config.dependency;

  if (!config?.targetTable || !config?.targetColumn) {
    return {
      ruleId: rule.id,
      ruleName: rule.name,
      success: false,
      totalRecords: tableData.length,
      failedRecords: 0,
      issues: [],
    };
  }

  const sampleRate = config.sampleRate ?? DEFAULT_SAMPLE_RATE;
  const sampledData = sampleArray(tableData, sampleRate);
  const isSampled = sampledData.length < tableData.length;

  const targetData = getTableData(config.targetTable);
  const targetValues = new Set(targetData.map(row => String(row[config.targetColumn] ?? '')));

  let sampleFailedCount = 0;

  sampledData.forEach((row, index) => {
    const sourceValue = String(row[config.sourceColumn] ?? '');
    if (sourceValue && !targetValues.has(sourceValue)) {
      sampleFailedCount++;
      issues.push({
        ruleId: rule.id,
        ruleName: rule.name,
        tableName: rule.tableName,
        columnName: config.sourceColumn,
        rowIdentifier: `row_${index}_${row.id ?? index}`,
        issueType: 'dependency',
        description: `外键值 ${sourceValue} 在 ${config.targetTable}.${config.targetColumn} 中不存在`,
      });
    }
  });

  if (isSampled && sampleFailedCount > 0) {
    const sampleFailRate = sampleFailedCount / sampledData.length;
    const estimatedFailedRecords = Math.round(sampleFailRate * tableData.length);
    return {
      ruleId: rule.id,
      ruleName: rule.name,
      success: false,
      totalRecords: tableData.length,
      failedRecords: estimatedFailedRecords,
      issues,
    };
  }

  return {
    ruleId: rule.id,
    ruleName: rule.name,
    success: sampleFailedCount === 0,
    totalRecords: tableData.length,
    failedRecords: isSampled ? Math.round((sampleFailedCount / sampledData.length) * tableData.length) : sampleFailedCount,
    issues,
  };
}

export function executeRule(rule: DataQualityRule): RuleExecutionResult {
  const tableData = getTableData(rule.tableName);

  switch (rule.type) {
    case 'null_check':
      return executeNullCheckRule(rule, tableData);
    case 'uniqueness':
      return executeUniquenessRule(rule, tableData);
    case 'value_range':
      return executeValueRangeRule(rule, tableData);
    case 'dependency':
      return executeDependencyRule(rule, tableData);
    default:
      return {
        ruleId: rule.id,
        ruleName: rule.name,
        success: false,
        totalRecords: 0,
        failedRecords: 0,
        issues: [],
      };
  }
}

export function executeRules(rules: DataQualityRule[]): {
  results: RuleExecutionResult[];
  totalRecords: number;
  failedRecords: number;
  qualityScore: number;
} {
  const results = rules.map(rule => executeRule(rule));
  const totalRecords = results.reduce((sum, r) => sum + r.totalRecords, 0);
  const failedRecords = results.reduce((sum, r) => sum + r.failedRecords, 0);
  const qualityScore = totalRecords > 0
    ? Math.round(((totalRecords - failedRecords) / totalRecords) * 10000) / 100
    : 100;

  return { results, totalRecords, failedRecords, qualityScore };
}

export function getAvailableTables(): string[] {
  return Object.keys(mockData);
}

export function getTableColumns(tableName: string): string[] {
  const data = mockData[tableName];
  if (!data || data.length === 0) return [];
  return Object.keys(data[0]);
}

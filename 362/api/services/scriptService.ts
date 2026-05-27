import type { CleaningRules, ColumnStats } from '../../src/types';

export function generatePythonScript(
  rules: CleaningRules,
  columns: string[],
  columnStats: ColumnStats[],
  filename: string = 'your_data.csv'
): string {
  const lines: string[] = [];

  lines.push('#!/usr/bin/env python3');
  lines.push('# -*- coding: utf-8 -*-');
  lines.push('"""');
  lines.push('数据清洗脚本 - 由 DataCleaner Pro 生成');
  lines.push(`生成时间: ${new Date().toLocaleString('zh-CN')}`);
  lines.push(`源文件: ${filename}`);
  lines.push('"""');
  lines.push('');
  lines.push('import pandas as pd');
  lines.push('import numpy as np');
  lines.push('from scipy import stats');
  lines.push('');

  if (rules.normalize.enabled) {
    lines.push('from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler');
    lines.push('');
  }

  lines.push('# ==================== 1. 读取数据 ====================');
  lines.push(`df = pd.read_csv('${filename}')`);
  lines.push(`print(f"原始数据形状: {df.shape}")`);
  lines.push('');

  if (rules.removeDuplicates.enabled) {
    lines.push('# ==================== 2. 删除重复值 ====================');
    const subset = rules.removeDuplicates.columns && rules.removeDuplicates.columns.length > 0
      ? `subset=[${rules.removeDuplicates.columns.map(c => `'${c}'`).join(', ')}]`
      : '';
    const keep = rules.removeDuplicates.keep === false ? 'keep=False' : `keep='${rules.removeDuplicates.keep}'`;
    const params = [subset, keep].filter(Boolean).join(', ');
    lines.push(`before_count = len(df)`);
    lines.push(`df = df.drop_duplicates(${params})`);
    lines.push(`after_count = len(df)`);
    lines.push(`print(f"删除重复值: {before_count - after_count} 行")`);
    lines.push('');
  }

  if (rules.handleMissing.enabled) {
    lines.push('# ==================== 3. 缺失值处理 ====================');

    for (let i = 0; i < columns.length; i++) {
      const colName = columns[i];
      const colConfig = rules.handleMissing.columns[colName];
      const method = colConfig?.method || rules.handleMissing.defaultMethod;
      const value = colConfig?.value;
      const colStat = columnStats[i];

      if (colStat && colStat.missingCount > 0) {
        lines.push(`# ${colName}: 缺失 ${colStat.missingCount} 个 (${colStat.missingPercent.toFixed(2)}%)`);

        switch (method) {
          case 'mean':
            lines.push(`df['${colName}'] = df['${colName}'].fillna(df['${colName}'].mean())`);
            break;
          case 'median':
            lines.push(`df['${colName}'] = df['${colName}'].fillna(df['${colName}'].median())`);
            break;
          case 'mode':
            lines.push(`df['${colName}'] = df['${colName}'].fillna(df['${colName}'].mode()[0])`);
            break;
          case 'interpolate':
            lines.push(`df['${colName}'] = df['${colName}'].interpolate(method='linear')`);
            break;
          case 'ffill':
            lines.push(`df['${colName}'] = df['${colName}'].ffill()`);
            break;
          case 'bfill':
            lines.push(`df['${colName}'] = df['${colName}'].bfill()`);
            break;
          case 'constant':
            const constValue = typeof value === 'string' ? `'${value}'` : value;
            lines.push(`df['${colName}'] = df['${colName}'].fillna(${constValue})`);
            break;
        }
        lines.push('');
      }
    }
  }

  if (rules.detectOutliers.enabled) {
    lines.push('# ==================== 4. 异常值处理 ====================');

    for (let i = 0; i < columns.length; i++) {
      const colName = columns[i];
      const colConfig = rules.detectOutliers.columns[colName];
      const method = colConfig?.method || rules.detectOutliers.defaultMethod;
      const threshold = colConfig?.threshold || rules.detectOutliers.defaultThreshold;
      const action = colConfig?.action || 'remove';
      const colStat = columnStats[i];

      if (colStat && colStat.type === 'numeric') {
        lines.push(`# ${colName}: ${method === 'zscore' ? 'Z-score' : 'IQR'} 方法, 阈值=${threshold}`);

        if (method === 'zscore') {
          lines.push(`z_scores = np.abs(stats.zscore(df['${colName}'].dropna()))`);
          lines.push(`outlier_mask = z_scores > ${threshold}`);
        } else {
          lines.push(`Q1 = df['${colName}'].quantile(0.25)`);
          lines.push(`Q3 = df['${colName}'].quantile(0.75)`);
          lines.push(`IQR = Q3 - Q1`);
          lines.push(`lower_bound = Q1 - ${threshold} * IQR`);
          lines.push(`upper_bound = Q3 + ${threshold} * IQR`);
          lines.push(`outlier_mask = (df['${colName}'] < lower_bound) | (df['${colName}'] > upper_bound)`);
        }

        if (action === 'remove') {
          lines.push(`outlier_count = outlier_mask.sum()`);
          lines.push(`df = df[~outlier_mask]`);
          lines.push(`print(f"删除 ${colName} 异常值: {outlier_count} 个")`);
        } else if (action === 'cap') {
          if (method === 'zscore') {
            lines.push(`mean_val = df['${colName}'].mean()`);
            lines.push(`std_val = df['${colName}'].std()`);
            lines.push(`lower_cap = mean_val - ${threshold} * std_val`);
            lines.push(`upper_cap = mean_val + ${threshold} * std_val`);
          } else {
            lines.push(`lower_cap = Q1 - ${threshold} * IQR`);
            lines.push(`upper_cap = Q3 + ${threshold} * IQR`);
          }
          lines.push(`df['${colName}'] = df['${colName}'].clip(lower=lower_cap, upper=upper_cap)`);
          lines.push(`print(f"盖帽处理 ${colName} 异常值: {outlier_mask.sum()} 个")`);
        } else {
          lines.push(`df['${colName}_is_outlier'] = outlier_mask`);
          lines.push(`print(f"标记 ${colName} 异常值: {outlier_mask.sum()} 个")`);
        }
        lines.push('');
      }
    }
  }

  if (rules.normalize.enabled) {
    lines.push('# ==================== 5. 数据标准化 ====================');

    for (let i = 0; i < columns.length; i++) {
      const colName = columns[i];
      const colConfig = rules.normalize.columns[colName];
      const method = colConfig?.method || rules.normalize.defaultMethod;
      const colStat = columnStats[i];

      if (colStat && colStat.type === 'numeric') {
        lines.push(`# ${colName}: ${method === 'minmax' ? 'Min-Max' : method === 'zscore' ? 'Z-score' : 'Robust'} 标准化`);

        if (method === 'minmax') {
          lines.push(`scaler = MinMaxScaler()`);
        } else if (method === 'zscore') {
          lines.push(`scaler = StandardScaler()`);
        } else {
          lines.push(`scaler = RobustScaler()`);
        }
        lines.push(`df['${colName}'] = scaler.fit_transform(df[['${colName}']])`);
        lines.push('');
      }
    }
  }

  lines.push('# ==================== 6. 保存结果 ====================');
  lines.push(`print(f"清洗后数据形状: {df.shape}")`);
  lines.push(`df.to_csv('cleaned_data.csv', index=False)`);
  lines.push(`print("清洗完成，结果已保存到 cleaned_data.csv")`);
  lines.push('');
  lines.push('if __name__ == "__main__":');
  lines.push('    print("数据清洗脚本执行完成")');

  return lines.join('\n');
}

export function generateSampleData(name: string): { columns: string[]; data: any[][] } {
  const samples: Record<string, { columns: string[]; data: any[][] }> = {
    sales: {
      columns: ['日期', '销售额', '客流量', '客单价', '区域', '销售员'],
      data: [
        ['2024-01-01', 12500, 156, 80.13, '华东', '张三'],
        ['2024-01-02', null, 189, 85.20, '华东', '李四'],
        ['2024-01-03', 18900, 234, 80.77, '华北', '王五'],
        ['2024-01-04', 15600, 178, 87.64, '华南', '张三'],
        ['2024-01-05', 15600, 178, 87.64, '华南', '张三'],
        ['2024-01-06', 23400, 267, 87.64, '华北', '李四'],
        ['2024-01-07', null, null, null, '华东', '王五'],
        ['2024-01-08', 17800, 198, 89.90, '华南', '张三'],
        ['2024-01-09', 999999, 245, 95.50, '华北', '李四'],
        ['2024-01-10', 21000, 234, 89.74, '华东', '王五'],
        ['2024-01-11', 16700, 189, 88.36, '华南', '张三'],
        ['2024-01-12', 19800, 223, 88.79, '华北', '李四'],
        ['2024-01-13', '', 201, 82.59, '华东', '王五'],
        ['2024-01-14', 24500, 278, 88.13, '华南', '张三'],
        ['2024-01-15', 18900, 212, 89.15, '华北', '李四'],
      ],
    },
    customers: {
      columns: ['客户ID', '年龄', '收入', '消费等级', '注册时间', '是否活跃'],
      data: [
        ['C001', 28, 85000, 'A', '2023-01-15', 'true'],
        ['C002', 35, 120000, 'S', '2022-06-20', 'true'],
        ['C003', null, 65000, 'B', '2023-03-10', 'false'],
        ['C004', 42, 95000, 'A', '2022-11-05', 'true'],
        ['C005', 31, 78000, 'B', '2023-05-18', 'true'],
        ['C006', 28, 85000, 'A', '2023-01-15', 'true'],
        ['C007', 55, 200000, 'S', '2021-09-30', 'true'],
        ['C008', null, null, 'C', '2023-07-22', 'false'],
        ['C009', 38, 110000, 'A', '2022-08-14', 'true'],
        ['C010', 25, 60000, 'C', '2023-09-01', 'true'],
        ['C011', 999, 72000, 'B', '2023-02-28', 'false'],
        ['C012', 45, 150000, 'S', '2022-04-10', 'true'],
        ['C013', 33, 88000, 'A', '2023-06-15', 'true'],
        ['C014', 29, 75000, 'B', '2023-08-20', 'true'],
        ['C015', 50, 180000, 'S', '2021-12-01', 'true'],
      ],
    },
    sensor: {
      columns: ['时间', '温度', '湿度', '压力', '振动', '设备ID'],
      data: [
        ['2024-01-01 00:00', 24.5, 65.2, 101.3, 0.5, 'DEV001'],
        ['2024-01-01 01:00', 24.7, 64.8, 101.5, 0.6, 'DEV001'],
        ['2024-01-01 02:00', null, 64.5, 101.2, 0.4, 'DEV001'],
        ['2024-01-01 03:00', 23.9, 66.1, 101.0, 0.5, 'DEV001'],
        ['2024-01-01 04:00', 23.5, 67.0, 100.8, 0.8, 'DEV001'],
        ['2024-01-01 05:00', 23.3, 67.5, 100.9, 0.7, 'DEV001'],
        ['2024-01-01 06:00', 23.3, 67.5, 100.9, 0.7, 'DEV001'],
        ['2024-01-01 07:00', 25.1, 63.9, 101.4, 0.5, 'DEV001'],
        ['2024-01-01 08:00', 26.8, 60.5, 101.8, 0.6, 'DEV001'],
        ['2024-01-01 09:00', 28.5, 55.2, 102.1, 1.2, 'DEV001'],
        ['2024-01-01 10:00', 100.0, 50.1, 102.5, 5.8, 'DEV001'],
        ['2024-01-01 11:00', 29.8, 48.9, 102.3, 1.5, 'DEV001'],
        ['2024-01-01 12:00', 30.2, 47.8, 102.0, 1.8, 'DEV001'],
        ['2024-01-01 13:00', null, null, null, null, 'DEV001'],
        ['2024-01-01 14:00', 29.5, 49.5, 101.8, 1.3, 'DEV001'],
      ],
    },
  };

  return samples[name] || samples.sales;
}

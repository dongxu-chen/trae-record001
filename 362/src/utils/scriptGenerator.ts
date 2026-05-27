import type { CleaningRules, ColumnStats } from '../types';

export function generateRequirements(): string {
  const requirements = [
    'pandas>=2.0.0',
    'numpy>=1.24.0',
    'scipy>=1.10.0',
    'scikit-learn>=1.2.0',
    '',
  ];

  return requirements.join('\n');
}

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
  lines.push('数据清洗脚本');
  lines.push(`生成时间: ${new Date().toLocaleString('zh-CN')}`);
  lines.push(`源文件: ${filename}`);
  lines.push('');
  lines.push('运行前请安装依赖:');
  lines.push('  pip install -r requirements.txt');
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

  lines.push('# ==================== 2. 数据类型检测 ====================');
  lines.push('# 自动检测日期列并转换');
  for (let i = 0; i < columns.length; i++) {
    const colName = columns[i];
    const colStat = columnStats[i];
    if (colStat && colStat.type === 'date') {
      lines.push(`df['${colName}'] = pd.to_datetime(df['${colName}'], errors='coerce')`);
    }
  }
  lines.push('');

  if (rules.removeDuplicates.enabled) {
    lines.push('# ==================== 3. 删除重复值 ====================');
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
    lines.push('# ==================== 4. 缺失值处理 ====================');

    for (let i = 0; i < columns.length; i++) {
      const colName = columns[i];
      const colConfig = rules.handleMissing.columns[colName];
      const method = colConfig?.method || rules.handleMissing.defaultMethod;
      const value = colConfig?.value;
      const colStat = columnStats[i];

      if (colStat && colStat.missingCount > 0) {
        lines.push(`# ${colName}: 缺失 ${colStat.missingCount} 个 (${colStat.missingPercent.toFixed(2)}%)`);

        const isDateColumn = colStat.type === 'date';

        switch (method) {
          case 'mean':
            if (isDateColumn) {
              lines.push(`# 日期列使用中位数填充`);
              lines.push(`df['${colName}'] = df['${colName}'].fillna(df['${colName}'].median())`);
            } else {
              lines.push(`df['${colName}'] = df['${colName}'].fillna(df['${colName}'].mean())`);
            }
            break;
          case 'median':
            lines.push(`df['${colName}'] = df['${colName}'].fillna(df['${colName}'].median())`);
            break;
          case 'mode':
            if (isDateColumn) {
              lines.push(`mode_val = df['${colName}'].mode()`);
              lines.push(`if len(mode_val) > 0:`);
              lines.push(`    df['${colName}'] = df['${colName}'].fillna(mode_val[0])`);
            } else {
              lines.push(`df['${colName}'] = df['${colName}'].fillna(df['${colName}'].mode()[0])`);
            }
            break;
          case 'interpolate':
            if (isDateColumn) {
              lines.push(`# 日期列按时间顺序插值`);
              lines.push(`df = df.sort_values('${colName}')`);
              lines.push(`df['${colName}'] = df['${colName}'].interpolate(method='time')`);
            } else {
              lines.push(`df['${colName}'] = df['${colName}'].interpolate(method='linear')`);
            }
            break;
          case 'ffill':
            if (isDateColumn) {
              lines.push(`# 日期列按时间顺序排序后前向填充`);
              lines.push(`df = df.sort_values('${colName}')`);
            }
            lines.push(`df['${colName}'] = df['${colName}'].ffill()`);
            break;
          case 'bfill':
            if (isDateColumn) {
              lines.push(`# 日期列按时间顺序排序后后向填充`);
              lines.push(`df = df.sort_values('${colName}')`);
            }
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
    lines.push('# ==================== 5. 异常值处理 ====================');
    lines.push('# 按列并行处理异常值检测');

    const numericColumns = columns.filter((col, idx) => {
      const colStat = columnStats[idx];
      return colStat && colStat.type === 'numeric';
    });

    if (numericColumns.length > 0) {
      lines.push(`numeric_cols = [${numericColumns.map(c => `'${c}'`).join(', ')}]`);
      lines.push('');
    }

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
          lines.push(`outlier_mask_${i} = z_scores > ${threshold}`);
        } else {
          lines.push(`Q1 = df['${colName}'].quantile(0.25)`);
          lines.push(`Q3 = df['${colName}'].quantile(0.75)`);
          lines.push(`IQR = Q3 - Q1`);
          lines.push(`lower_bound = Q1 - ${threshold} * IQR`);
          lines.push(`upper_bound = Q3 + ${threshold} * IQR`);
          lines.push(`outlier_mask_${i} = (df['${colName}'] < lower_bound) | (df['${colName}'] > upper_bound)`);
        }

        if (action === 'remove') {
          lines.push(`outlier_count = outlier_mask_${i}.sum()`);
          lines.push(`df = df[~outlier_mask_${i}]`);
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
          lines.push(`print(f"盖帽处理 ${colName} 异常值: {outlier_mask_${i}.sum()} 个")`);
        } else {
          lines.push(`df['${colName}_is_outlier'] = outlier_mask_${i}`);
          lines.push(`print(f"标记 ${colName} 异常值: {outlier_mask_${i}.sum()} 个")`);
        }
        lines.push('');
      }
    }
  }

  if (rules.normalize.enabled) {
    const stepNumber = rules.detectOutliers.enabled ? '6' : '5';
    lines.push(`# ==================== ${stepNumber}. 数据标准化 ====================`);

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

  const saveStepNumber = [
    rules.removeDuplicates.enabled,
    rules.handleMissing.enabled,
    rules.detectOutliers.enabled,
    rules.normalize.enabled,
  ].filter(Boolean).length + 2;

  lines.push(`# ==================== ${saveStepNumber}. 保存结果 ====================`);
  lines.push(`print(f"清洗后数据形状: {df.shape}")`);
  lines.push(`df.to_csv('cleaned_data.csv', index=False)`);
  lines.push(`print("清洗完成，结果已保存到 cleaned_data.csv")`);
  lines.push('');
  lines.push('if __name__ == "__main__":');
  lines.push('    print("数据清洗脚本执行完成")');

  return lines.join('\n');
}

export function downloadScript(script: string, filename: string = 'cleaning_script.py'): void {
  const blob = new Blob([script], { type: 'text/plain;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

export function downloadRequirements(): void {
  const content = generateRequirements();
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = 'requirements.txt';
  link.click();
  URL.revokeObjectURL(link.href);
}

export function copyToClipboard(text: string): Promise<void> {
  return navigator.clipboard.writeText(text);
}

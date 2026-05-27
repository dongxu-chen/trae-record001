import * as ss from 'simple-statistics';
import type { ColumnStats, ColumnType, DatasetStats } from '../types';

export function isNumeric(value: any): boolean {
  if (value === null || value === undefined || value === '') return false;
  const num = Number(value);
  return !isNaN(num) && isFinite(num);
}

export function isBoolean(value: any): boolean {
  return typeof value === 'boolean' || value === 'true' || value === 'false';
}

export function isDate(value: any): boolean {
  if (value === null || value === undefined || value === '') return false;
  const d = new Date(value);
  return d instanceof Date && !isNaN(d.getTime());
}

export function detectColumnType(values: any[]): ColumnType {
  const nonEmpty = values.filter((v) => v !== null && v !== undefined && v !== '');
  if (nonEmpty.length === 0) return 'string';

  const numericCount = nonEmpty.filter(isNumeric).length;
  const booleanCount = nonEmpty.filter(isBoolean).length;
  const dateCount = nonEmpty.filter(isDate).length;

  const threshold = 0.8;
  if (numericCount / nonEmpty.length >= threshold) return 'numeric';
  if (booleanCount / nonEmpty.length >= threshold) return 'boolean';
  if (dateCount / nonEmpty.length >= threshold) return 'date';
  if (numericCount > 0 || booleanCount > 0 || dateCount > 0) return 'mixed';
  return 'string';
}

export function getNumericValues(values: any[]): number[] {
  return values
    .filter((v) => v !== null && v !== undefined && v !== '')
    .map(Number)
    .filter((n) => !isNaN(n) && isFinite(n));
}

export function calculateMean(values: number[]): number | undefined {
  if (values.length === 0) return undefined;
  return ss.mean(values);
}

export function calculateMedian(values: number[]): number | undefined {
  if (values.length === 0) return undefined;
  return ss.median(values);
}

export function calculateMode(values: any[]): any | undefined {
  const nonEmpty = values.filter((v) => v !== null && v !== undefined && v !== '');
  if (nonEmpty.length === 0) return undefined;

  const frequency: Record<string, number> = {};
  let maxFreq = 0;
  let mode: any = nonEmpty[0];

  for (const v of nonEmpty) {
    const key = String(v);
    frequency[key] = (frequency[key] || 0) + 1;
    if (frequency[key] > maxFreq) {
      maxFreq = frequency[key];
      mode = v;
    }
  }
  return mode;
}

export function calculateStd(values: number[]): number | undefined {
  if (values.length < 2) return undefined;
  return ss.standardDeviation(values);
}

export function calculateHistogram(values: number[], bins: number = 20): { bins: number[]; counts: number[] } | undefined {
  if (values.length === 0) return undefined;

  const min = ss.min(values);
  const max = ss.max(values);
  const binWidth = (max - min) / bins;

  const binEdges: number[] = [];
  const counts: number[] = new Array(bins).fill(0);

  for (let i = 0; i <= bins; i++) {
    binEdges.push(min + i * binWidth);
  }

  for (const v of values) {
    let binIndex = Math.floor((v - min) / binWidth);
    if (binIndex >= bins) binIndex = bins - 1;
    if (binIndex < 0) binIndex = 0;
    counts[binIndex]++;
  }

  return { bins: binEdges, counts };
}

export function detectOutliersZScore(values: number[], threshold: number = 3): number[] {
  if (values.length < 3) return [];

  const mean = ss.mean(values);
  const std = ss.standardDeviation(values);
  if (std === 0) return [];

  const outliers: number[] = [];
  values.forEach((v, i) => {
    const zScore = Math.abs((v - mean) / std);
    if (zScore > threshold) {
      outliers.push(i);
    }
  });
  return outliers;
}

export function detectOutliersIQR(values: number[], threshold: number = 1.5): number[] {
  if (values.length < 4) return [];

  const sorted = [...values].sort((a, b) => a - b);
  const q1 = ss.quantileSorted(sorted, 0.25);
  const q3 = ss.quantileSorted(sorted, 0.75);
  const iqr = q3 - q1;

  const lowerBound = q1 - threshold * iqr;
  const upperBound = q3 + threshold * iqr;

  const outliers: number[] = [];
  values.forEach((v, i) => {
    if (v < lowerBound || v > upperBound) {
      outliers.push(i);
    }
  });
  return outliers;
}

export function calculateColumnStats(columnName: string, values: any[]): ColumnStats {
  const type = detectColumnType(values);
  const count = values.length;
  const missingCount = values.filter((v) => v === null || v === undefined || v === '').length;
  const missingPercent = (missingCount / count) * 100;

  const uniqueSet = new Set(values.map((v) => String(v)));
  const uniqueCount = uniqueSet.size;
  const duplicateCount = count - uniqueCount;

  const stats: ColumnStats = {
    name: columnName,
    type,
    count,
    missingCount,
    missingPercent,
    uniqueCount,
    duplicateCount,
  };

  if (type === 'numeric') {
    const numericValues = getNumericValues(values);
    if (numericValues.length > 0) {
      stats.min = ss.min(numericValues);
      stats.max = ss.max(numericValues);
      stats.mean = calculateMean(numericValues);
      stats.median = calculateMedian(numericValues);
      stats.mode = calculateMode(values);
      stats.std = calculateStd(numericValues);
      stats.histogram = calculateHistogram(numericValues);
    }
  } else {
    stats.mode = calculateMode(values);
  }

  return stats;
}

export function calculateDatasetStats(data: any[][], columns: string[]): DatasetStats {
  const columnStats: ColumnStats[] = columns.map((col, idx) => {
    const columnValues = data.map((row) => row[idx]);
    return calculateColumnStats(col, columnValues);
  });

  const totalMissing = columnStats.reduce((sum, col) => sum + col.missingCount, 0);
  const totalDuplicates = columnStats.reduce((sum, col) => sum + col.duplicateCount, 0);

  let memorySize = '0 B';
  try {
    const bytes = new Blob([JSON.stringify(data)]).size;
    if (bytes < 1024) memorySize = `${bytes} B`;
    else if (bytes < 1024 * 1024) memorySize = `${(bytes / 1024).toFixed(2)} KB`;
    else memorySize = `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  } catch (e) {
    memorySize = '未知';
  }

  return {
    rowCount: data.length,
    columnCount: columns.length,
    columns: columnStats,
    totalMissing,
    totalDuplicates,
    memorySize,
  };
}

export function formatNumber(num: number | undefined, decimals: number = 2): string {
  if (num === undefined) return '-';
  return num.toLocaleString('zh-CN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function formatPercent(percent: number | undefined): string {
  if (percent === undefined) return '-';
  return `${percent.toFixed(2)}%`;
}

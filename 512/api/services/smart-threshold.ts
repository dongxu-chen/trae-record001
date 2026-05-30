import { getRecentMetrics } from './redis.js';
import type { ThresholdRecommendation, MetricData } from '../types.js';

interface Stats {
  mean: number;
  stdDev: number;
  min: number;
  max: number;
  p50: number;
  p90: number;
  p95: number;
  p99: number;
}

export function calculateStats(values: number[]): Stats {
  if (values.length === 0) {
    return { mean: 0, stdDev: 0, min: 0, max: 0, p50: 0, p90: 0, p95: 0, p99: 0 };
  }

  const sorted = [...values].sort((a, b) => a - b);
  const n = sorted.length;

  const sum = values.reduce((a, b) => a + b, 0);
  const mean = sum / n;

  const variance = values.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / n;
  const stdDev = Math.sqrt(variance);

  const min = sorted[0];
  const max = sorted[n - 1];

  const p50 = percentile(sorted, 50);
  const p90 = percentile(sorted, 90);
  const p95 = percentile(sorted, 95);
  const p99 = percentile(sorted, 99);

  return { mean, stdDev, min, max, p50, p90, p95, p99 };
}

function percentile(sorted: number[], p: number): number {
  const n = sorted.length;
  const index = Math.ceil((p / 100) * n) - 1;
  return sorted[Math.max(0, Math.min(n - 1, index))];
}

export async function getMetricHistory(metric: string, hours: number = 24): Promise<number[]> {
  const dataPoints = await getRecentMetrics(metric, 500);

  if (dataPoints.length >= 50) {
    return dataPoints.map((d) => d.value);
  }

  return generateSimulatedData(metric, hours);
}

function generateSimulatedData(metric: string, hours: number): number[] {
  const count = Math.min(hours * 30, 500);
  const data: number[] = [];

  const baseValues: Record<string, { mean: number; stdDev: number }> = {
    CPU: { mean: 45, stdDev: 15 },
    Memory: { mean: 60, stdDev: 10 },
    Latency: { mean: 150, stdDev: 50 },
    ErrorRate: { mean: 2, stdDev: 3 },
    Throughput: { mean: 500, stdDev: 150 },
    DiskIO: { mean: 30, stdDev: 20 },
  };

  const base = baseValues[metric] || { mean: 50, stdDev: 15 };

  for (let i = 0; i < count; i++) {
    const u1 = Math.random();
    const u2 = Math.random();
    const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
    const value = base.mean + z * base.stdDev;
    data.push(Math.max(0, value));
  }

  return data;
}

export async function recommendThreshold(
  metric: string,
  method: 'zscore' | 'percentile' | 'iqr' = 'zscore',
  sensitivity: 'low' | 'medium' | 'high' = 'medium'
): Promise<ThresholdRecommendation> {
  const values = await getMetricHistory(metric);
  const stats = calculateStats(values);

  const sensitivityConfig = {
    low: { warning: 3, danger: 4, critical: 5 },
    medium: { warning: 2, danger: 3, critical: 4 },
    high: { warning: 1.5, danger: 2, critical: 3 },
  };

  const config = sensitivityConfig[sensitivity];
  let warning: number, danger: number, critical: number;

  if (method === 'zscore') {
    warning = stats.mean + config.warning * stats.stdDev;
    danger = stats.mean + config.danger * stats.stdDev;
    critical = stats.mean + config.critical * stats.stdDev;
  } else if (method === 'percentile') {
    const percentiles = { low: 95, medium: 90, high: 85 };
    const p = percentiles[sensitivity];
    const sorted = [...values].sort((a, b) => a - b);
    warning = percentile(sorted, p);
    danger = percentile(sorted, Math.min(100, p + 5));
    critical = percentile(sorted, Math.min(100, p + 8));
  } else {
    const q1 = percentile([...values].sort((a, b) => a - b), 25);
    const q3 = percentile([...values].sort((a, b) => a - b), 75);
    const iqr = q3 - q1;
    const iqrMultiplier = { low: 2.5, medium: 1.5, high: 1.0 };
    const mult = iqrMultiplier[sensitivity];
    warning = q3 + mult * iqr;
    danger = q3 + (mult + 0.5) * iqr;
    critical = q3 + (mult + 1) * iqr;
  }

  const confidence = Math.min(1, values.length / 200);

  return {
    metric,
    method,
    warning: Math.round(warning * 100) / 100,
    danger: Math.round(danger * 100) / 100,
    critical: Math.round(critical * 100) / 100,
    confidence: Math.round(confidence * 100) / 100,
    sampleSize: values.length,
    stats: {
      mean: Math.round(stats.mean * 100) / 100,
      stdDev: Math.round(stats.stdDev * 100) / 100,
      p95: Math.round(stats.p95 * 100) / 100,
    },
  };
}

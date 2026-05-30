import type { MetricData } from '../types.js';

interface MetricConfig {
  name: string;
  unit: string;
  baseValue: number;
  min: number;
  max: number;
  volatility: number;
  spikeChance: number;
  spikeMagnitude: number;
}

const METRIC_CONFIGS: MetricConfig[] = [
  { name: 'CPU', unit: '%', baseValue: 55, min: 5, max: 100, volatility: 5, spikeChance: 0.05, spikeMagnitude: 35 },
  { name: 'Memory', unit: '%', baseValue: 60, min: 10, max: 100, volatility: 3, spikeChance: 0.03, spikeMagnitude: 25 },
  { name: 'Network', unit: 'Mbps', baseValue: 300, min: 0, max: 1000, volatility: 50, spikeChance: 0.04, spikeMagnitude: 300 },
  { name: 'DiskIO', unit: 'MB/s', baseValue: 80, min: 0, max: 500, volatility: 20, spikeChance: 0.04, spikeMagnitude: 150 },
  { name: 'Latency', unit: 'ms', baseValue: 50, min: 5, max: 500, volatility: 15, spikeChance: 0.06, spikeMagnitude: 200 },
  { name: 'ErrorRate', unit: '%', baseValue: 1.5, min: 0, max: 20, volatility: 0.5, spikeChance: 0.05, spikeMagnitude: 8 },
];

const currentValues = new Map<string, number>();

for (const config of METRIC_CONFIGS) {
  currentValues.set(config.name, config.baseValue);
}

function randomWalk(current: number, config: MetricConfig): number {
  const change = (Math.random() - 0.5) * 2 * config.volatility;
  let newValue = current + change;

  if (Math.random() < config.spikeChance) {
    const spikeDirection = Math.random() > 0.3 ? 1 : -1;
    newValue += spikeDirection * config.spikeMagnitude * (0.5 + Math.random() * 0.5);
  }

  const meanReversion = (config.baseValue - newValue) * 0.02;
  newValue += meanReversion;

  return Math.max(config.min, Math.min(config.max, newValue));
}

export function generateMetricData(): MetricData[] {
  const timestamp = new Date().toISOString();
  const results: MetricData[] = [];

  for (const config of METRIC_CONFIGS) {
    const current = currentValues.get(config.name) ?? config.baseValue;
    const newValue = randomWalk(current, config);
    currentValues.set(config.name, newValue);

    results.push({
      metric: config.name,
      value: Number(newValue.toFixed(2)),
      timestamp,
      labels: { unit: config.unit },
    });
  }

  return results;
}

export function getMetricConfigs(): { name: string; unit: string; baseValue: number }[] {
  return METRIC_CONFIGS.map((c) => ({
    name: c.name,
    unit: c.unit,
    baseValue: c.baseValue,
  }));
}

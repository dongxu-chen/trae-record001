import type { EChartsOption } from 'echarts';
import type { ThresholdRule, ChartSnapshot, MetricData } from '@/types';

export interface MetricDisplayConfig {
  label: string;
  unit: string;
  min: number;
  max: number;
  decimals: number;
  color: string;
}

export const METRIC_DISPLAY_CONFIG: Record<string, MetricDisplayConfig> = {
  CPU: { label: 'CPU 使用率', unit: '%', min: 0, max: 100, decimals: 1, color: '#00d4ff' },
  Memory: { label: '内存使用率', unit: '%', min: 0, max: 100, decimals: 1, color: '#8b5cf6' },
  Network: { label: '网络流量', unit: 'MB/s', min: 0, max: 1000, decimals: 2, color: '#06b6d4' },
  DiskIO: { label: '磁盘 IO', unit: 'MB/s', min: 0, max: 500, decimals: 2, color: '#f59e0b' },
  Latency: { label: '响应延迟', unit: 'ms', min: 0, max: 5000, decimals: 0, color: '#10b981' },
  ErrorRate: { label: '错误率', unit: '%', min: 0, max: 100, decimals: 2, color: '#ef4444' },
};

const LEVEL_COLORS: Record<string, string> = {
  warning: '#f59e0b',
  danger: '#ef4444',
  critical: '#dc2626',
};

const LEVEL_LABELS: Record<string, string> = {
  warning: '警告',
  danger: '危险',
  critical: '严重',
};

export function buildLineChartOption(
  metric: string,
  data: MetricData[],
  rules: ThresholdRule[]
): EChartsOption {
  const config = METRIC_DISPLAY_CONFIG[metric];
  const color = config?.color || '#00d4ff';
  const timestamps = data.map(d => {
    const date = new Date(d.timestamp);
    return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}:${String(date.getSeconds()).padStart(2, '0')}`;
  });
  const values = data.map(d => d.value);

  const markLines = rules
    .filter(r => r.enabled && r.metric === metric)
    .flatMap(r =>
      r.conditions.map(c => ({
        yAxis: c.value,
        lineStyle: { color: LEVEL_COLORS[r.level], type: 'dashed' as const, width: 2 },
        label: {
          formatter: `${LEVEL_LABELS[r.level]} ${c.operator} ${c.value}`,
          position: 'insideEndTop' as const,
          color: LEVEL_COLORS[r.level],
          fontSize: 11,
          fontFamily: 'JetBrains Mono',
        },
      }))
    );

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1a1f2e',
      borderColor: '#2a3040',
      textStyle: { color: '#e2e8f0', fontFamily: 'JetBrains Mono', fontSize: 12 },
    },
    grid: { left: 60, right: 20, top: 30, bottom: 50 },
    xAxis: {
      type: 'category',
      data: timestamps,
      axisLine: { lineStyle: { color: '#2a3040' } },
      axisLabel: { color: '#94a3b8', fontSize: 10, fontFamily: 'JetBrains Mono' },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      min: config?.min,
      max: config?.max,
      axisLine: { show: false },
      axisLabel: { color: '#94a3b8', fontSize: 10, fontFamily: 'JetBrains Mono' },
      splitLine: { lineStyle: { color: '#1a1f2e' } },
    },
    series: [
      {
        type: 'line',
        data: values,
        smooth: true,
        symbol: 'none',
        lineStyle: { color, width: 2 },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: `${color}40` },
              { offset: 1, color: `${color}05` },
            ],
          },
        },
        markLine: markLines.length ? { data: markLines, silent: true, animation: false } : undefined,
      },
    ],
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 20, bottom: 5, borderColor: '#2a3040', fillerColor: '#00d4ff20', handleStyle: { color: '#00d4ff' } }],
    animation: true,
  };
}

export function buildAlertChartOption(
  metric: string,
  snapshot: ChartSnapshot,
  triggerIndex: number
): EChartsOption {
  const config = METRIC_DISPLAY_CONFIG[metric];
  const color = config?.color || '#00d4ff';

  const triggerLabel = snapshot.xAxisLabels[triggerIndex] ?? '';

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1a1f2e',
      borderColor: '#2a3040',
      textStyle: { color: '#e2e8f0', fontFamily: 'JetBrains Mono', fontSize: 12 },
    },
    grid: { left: 60, right: 20, top: 30, bottom: 30 },
    xAxis: {
      type: 'category',
      data: snapshot.xAxisLabels,
      axisLine: { lineStyle: { color: '#2a3040' } },
      axisLabel: { color: '#94a3b8', fontSize: 10, fontFamily: 'JetBrains Mono' },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      min: config?.min,
      max: config?.max,
      axisLine: { show: false },
      axisLabel: { color: '#94a3b8', fontSize: 10, fontFamily: 'JetBrains Mono' },
      splitLine: { lineStyle: { color: '#1a1f2e' } },
    },
    series: [
      {
        type: 'line',
        data: snapshot.seriesData,
        smooth: true,
        symbol: 'none',
        lineStyle: { color, width: 2 },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: `${color}40` },
              { offset: 1, color: `${color}05` },
            ],
          },
        },
        markPoint: triggerIndex >= 0
          ? {
              data: [
                {
                  name: '触发点',
                  xAxis: triggerLabel,
                  yAxis: snapshot.seriesData[triggerIndex],
                  symbol: 'circle',
                  symbolSize: 14,
                  itemStyle: { color: '#ef4444', borderColor: '#ef4444', borderWidth: 3 },
                  label: { show: false },
                },
              ],
              animation: true,
            }
          : undefined,
      },
    ],
    animation: true,
  };
}

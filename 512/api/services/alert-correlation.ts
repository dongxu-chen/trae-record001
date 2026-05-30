import type { MetricCorrelation, AlertRecord } from '../types.js';

interface CorrelationMap {
  metric: string;
  relatedMetrics: Array<{
    metric: string;
    strength: number;
    description: string;
  }>;
}

const correlationMap: CorrelationMap[] = [
  {
    metric: 'CPU',
    relatedMetrics: [
      { metric: 'Memory', strength: 0.85, description: '高CPU使用率通常伴随内存压力' },
      { metric: 'Latency', strength: 0.75, description: 'CPU瓶颈会增加请求延迟' },
      { metric: 'Throughput', strength: 0.65, description: '高CPU可能影响系统吞吐量' },
    ],
  },
  {
    metric: 'Memory',
    relatedMetrics: [
      { metric: 'CPU', strength: 0.8, description: '内存压力可能导致CPU垃圾回收增加' },
      { metric: 'DiskIO', strength: 0.75, description: '内存不足会增加磁盘交换' },
      { metric: 'Latency', strength: 0.7, description: '内存压力增加处理延迟' },
    ],
  },
  {
    metric: 'Latency',
    relatedMetrics: [
      { metric: 'CPU', strength: 0.75, description: '延迟增加可能由CPU瓶颈' },
      { metric: 'ErrorRate', strength: 0.7, description: '高延迟可能导致错误增加' },
      { metric: 'Memory', strength: 0.65, description: '内存问题可能增加处理时间' },
    ],
  },
  {
    metric: 'ErrorRate',
    relatedMetrics: [
      { metric: 'Latency', strength: 0.75, description: '错误率上升可能伴随延迟增加' },
      { metric: 'CPU', strength: 0.55, description: '错误可能由系统资源问题' },
      { metric: 'Throughput', strength: 0.6, description: '错误率影响系统处理能力' },
    ],
  },
  {
    metric: 'Throughput',
    relatedMetrics: [
      { metric: 'CPU', strength: 0.7, description: '高吞吐量需要更多CPU资源' },
      { metric: 'Memory', strength: 0.65, description: '吞吐量增加消耗更多内存' },
      { metric: 'Latency', strength: 0.6, description: '高吞吐量可能影响延迟' },
    ],
  },
  {
    metric: 'DiskIO',
    relatedMetrics: [
      { metric: 'Memory', strength: 0.8, description: '磁盘IO与内存使用高度相关' },
      { metric: 'CPU', strength: 0.6, description: '磁盘操作需要CPU处理' },
    ],
  },
];

export function getRelatedMetrics(metric: string): MetricCorrelation[] {
  const found = correlationMap.find((c) => c.metric === metric);
  if (!found) {
    return [];
  }
  return found.relatedMetrics.map((r) => ({
    metric,
    relatedMetric: r.metric,
    strength: r.strength,
    description: r.description,
  }));
}

export function getCorrelationStrength(a: string, b: string): number {
  const found = correlationMap.find((c) => c.metric === a);
  if (found) {
    const rel = found.relatedMetrics.find((r) => r.metric === b);
    if (rel) return rel.strength;
  }
  const reverse = correlationMap.find((c) => c.metric === b);
  if (reverse) {
    const rel = reverse.relatedMetrics.find((r) => r.metric === a);
    if (rel) return rel.strength;
  }
  return 0;
}

export function createCorrelatedAlert(
  primaryAlert: AlertRecord,
  relatedMetric: string
): Partial<AlertRecord> {
  const strength = getCorrelationStrength(primaryAlert.metric, relatedMetric);
  const relatedMetrics = getRelatedMetrics(primaryAlert.metric);
  const correlationInfo = relatedMetrics.find((r) => r.relatedMetric === relatedMetric);

  return {
    ruleName: `Correlation Alert: ${relatedMetric}`,
    metric: relatedMetric,
    message: `${primaryAlert.ruleName} 触发了 ${relatedMetric} 的关联告警 (相关性: ${Math.round(strength * 100)}%)`,
    snapshot: primaryAlert.snapshot,
    level: primaryAlert.level,
    triggerValue: primaryAlert.triggerValue,
    thresholdValue: primaryAlert.thresholdValue,
  };
}

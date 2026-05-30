import ReactECharts from 'echarts-for-react';
import { cn } from '@/utils/helpers';
import { METRIC_DISPLAY_CONFIG, buildLineChartOption } from '@/utils/chart-config';
import type { MetricData, ThresholdRule, AlertCondition, MetricCorrelation } from '@/types';
import CorrelationBadge from '@/components/CorrelationBadge';

interface RealtimeChartProps {
  metric: string;
  data: MetricData[];
  rules: ThresholdRule[];
  correlatedMetrics?: MetricCorrelation[];
  activeAlert?: string | null;
}

function evaluateCondition(value: number, c: AlertCondition): boolean {
  switch (c.operator) {
    case '>': return value > c.value;
    case '<': return value < c.value;
    case '>=': return value >= c.value;
    case '<=': return value <= c.value;
    case '==': return value === c.value;
    case '!=': return value !== c.value;
    default: return false;
  }
}

function getHighestAlertLevel(
  value: number | null,
  rules: ThresholdRule[]
): 'normal' | 'warning' | 'danger' | 'critical' {
  if (value === null) return 'normal';
  const levels: Array<'warning' | 'danger' | 'critical'> = [];
  for (const rule of rules) {
    if (!rule.enabled) continue;
    if (rule.conditions.every(c => evaluateCondition(value, c))) {
      levels.push(rule.level);
    }
  }
  if (levels.includes('critical')) return 'critical';
  if (levels.includes('danger')) return 'danger';
  if (levels.includes('warning')) return 'warning';
  return 'normal';
}

const BORDER_COLORS: Record<string, string> = {
  normal: 'border-brand-border',
  warning: 'border-t-brand-amber',
  danger: 'border-t-brand-red',
  critical: 'border-t-brand-red',
};

const GLOW_CLASSES: Record<string, string> = {
  normal: '',
  warning: 'animate-pulse-glow-amber',
  danger: 'animate-pulse-glow-red',
  critical: 'animate-pulse-glow-red',
};

export default function RealtimeChart({ metric, data, rules, correlatedMetrics, activeAlert }: RealtimeChartProps) {
  const config = METRIC_DISPLAY_CONFIG[metric];
  const relatedRules = rules.filter(r => r.metric === metric);
  const latestValue = data.length > 0 ? data[data.length - 1].value : null;
  const alertLevel = getHighestAlertLevel(latestValue, relatedRules);

  const isCorrelated = activeAlert && correlatedMetrics?.some(c => c.relatedMetric === metric || c.metric === metric);
  const correlation = correlatedMetrics?.find(c => c.relatedMetric === metric || c.metric === metric);

  const borderColorClass = BORDER_COLORS[alertLevel];
  const glowClass = GLOW_CLASSES[alertLevel];

  const option = data.length > 0
    ? buildLineChartOption(metric, data, relatedRules)
    : null;

  return (
    <div
      className={cn(
        'flex flex-col rounded-lg border bg-brand-card border-t-2 border-brand-border transition-all duration-300',
        borderColorClass,
        glowClass,
        isCorrelated && 'ring-2 ring-brand-cyan/50 shadow-lg shadow-brand-cyan/20 scale-[1.02] z-10'
      )}
    >
      <div className="flex items-center justify-between border-b border-brand-border px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-brand-text-primary">
            {config?.label ?? metric}
          </span>
          {isCorrelated && correlation && (
            <div className="animate-fade-in">
              <CorrelationBadge strength={correlation.strength} showIcon />
            </div>
          )}
        </div>
        {latestValue !== null && (
          <span className="font-mono-num text-sm text-brand-text-secondary">
            {latestValue.toFixed(config?.decimals ?? 1)}{config?.unit ?? ''}
          </span>
        )}
      </div>

      <div className="flex-1 p-2" style={{ height: 280 }}>
        {option ? (
          <ReactECharts
            option={option}
            style={{ height: '100%', width: '100%' }}
            notMerge
            lazyUpdate
          />
        ) : (
          <div className="flex h-full items-center justify-center">
            <div className="space-y-3 w-3/4">
              <div className="h-4 w-1/3 rounded bg-brand-border/40 animate-pulse" />
              <div className="h-40 w-full rounded bg-brand-border/20 animate-pulse" />
              <div className="h-3 w-2/3 rounded bg-brand-border/30 animate-pulse" />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

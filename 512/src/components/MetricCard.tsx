import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '@/utils/helpers';
import { METRIC_DISPLAY_CONFIG } from '@/utils/chart-config';
import type { MetricData, ThresholdRule, AlertCondition } from '@/types';

interface MetricCardProps {
  metric: string;
  data: MetricData[];
  rules: ThresholdRule[];
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

function getAlertLevel(
  value: number,
  rules: ThresholdRule[]
): 'normal' | 'warning' | 'danger' | 'critical' {
  const levels: Array<'warning' | 'danger' | 'critical'> = [];
  for (const rule of rules) {
    if (!rule.enabled) continue;
    const triggered = rule.conditions.every(c => evaluateCondition(value, c));
    if (triggered) levels.push(rule.level);
  }
  if (levels.includes('critical')) return 'critical';
  if (levels.includes('danger')) return 'danger';
  if (levels.includes('warning')) return 'warning';
  return 'normal';
}

const BAR_COLORS: Record<string, string> = {
  normal: '#00d4ff',
  warning: '#f59e0b',
  danger: '#ef4444',
  critical: '#dc2626',
};

const GLOW_CLASSES: Record<string, string> = {
  normal: '',
  warning: 'animate-pulse-glow-amber',
  danger: 'animate-pulse-glow-red',
  critical: 'animate-pulse-glow-red',
};

export default function MetricCard({ metric, data, rules }: MetricCardProps) {
  const config = METRIC_DISPLAY_CONFIG[metric];
  const relatedRules = rules.filter(r => r.metric === metric);

  const latest = data.length > 0 ? data[data.length - 1] : null;
  const previous = data.length > 1 ? data[data.length - 2] : null;
  const value = latest?.value ?? null;

  const alertLevel = value !== null ? getAlertLevel(value, relatedRules) : 'normal';
  const barColor = BAR_COLORS[alertLevel];
  const glowClass = GLOW_CLASSES[alertLevel];

  const trend = value !== null && previous !== null
    ? value > previous.value ? 'up' : value < previous.value ? 'down' : 'flat'
    : null;

  const sparkData = data.slice(-10).map(d => d.value);
  const sparkMin = sparkData.length > 0 ? Math.min(...sparkData) : 0;
  const sparkMax = sparkData.length > 0 ? Math.max(...sparkData) : 1;
  const sparkRange = sparkMax - sparkMin || 1;

  return (
    <div
      className={cn(
        'relative flex overflow-hidden rounded-lg border bg-brand-card border-brand-border transition-shadow',
        glowClass
      )}
    >
      <div className="w-1 shrink-0" style={{ backgroundColor: barColor }} />

      <div className="flex flex-1 flex-col p-4">
        <div className="flex items-center justify-between">
          <span className="text-sm text-brand-text-secondary">{config?.label ?? metric}</span>
          {trend === 'up' && <TrendingUp className="h-4 w-4 text-brand-red" />}
          {trend === 'down' && <TrendingDown className="h-4 w-4 text-brand-green" />}
          {trend === 'flat' && <Minus className="h-4 w-4 text-brand-text-secondary" />}
        </div>

        <div className="mt-1 flex items-baseline gap-1.5">
          <span className="font-mono-num text-2xl font-bold text-brand-text-primary">
            {value !== null ? value.toFixed(config?.decimals ?? 1) : '--'}
          </span>
          {config?.unit && (
            <span className="text-sm text-brand-text-secondary">{config.unit}</span>
          )}
        </div>

        <div className="mt-auto pt-3">
          {sparkData.length >= 2 ? (
            <svg viewBox="0 0 100 24" className="h-6 w-full" preserveAspectRatio="none">
              <polyline
                fill="none"
                stroke={barColor}
                strokeWidth="1.5"
                strokeLinejoin="round"
                points={sparkData
                  .map((v, i) => {
                    const x = (i / (sparkData.length - 1)) * 100;
                    const y = 24 - ((v - sparkMin) / sparkRange) * 20 - 2;
                    return `${x},${y}`;
                  })
                  .join(' ')}
              />
            </svg>
          ) : (
            <div className="h-6" />
          )}
        </div>
      </div>
    </div>
  );
}

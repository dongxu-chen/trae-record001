import { cn } from '@/utils/helpers';
import { getAlertLevelColor, getAlertLevelLabel } from '@/utils/helpers';

interface AlertStatusBadgeProps {
  level: 'warning' | 'danger' | 'critical';
  count: number;
  active: boolean;
}

export default function AlertStatusBadge({ level, count, active }: AlertStatusBadgeProps) {
  const color = getAlertLevelColor(level);
  const label = getAlertLevelLabel(level);

  const levelTextClass = {
    warning: 'text-brand-amber',
    danger: 'text-brand-red',
    critical: 'text-brand-red',
  }[level];

  return (
    <div className="flex items-center gap-2 rounded-lg bg-brand-card border border-brand-border px-4 py-2.5">
      <span className="relative flex h-3 w-3">
        {active && (
          <span
            className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
            style={{ backgroundColor: color }}
          />
        )}
        <span
          className={cn('relative inline-flex h-3 w-3 rounded-full', !active && 'opacity-50')}
          style={{ backgroundColor: color }}
        />
      </span>
      <span className={cn('text-sm font-medium', levelTextClass)}>{label}</span>
      <span className="font-mono-num text-lg font-bold text-brand-text-primary">{count}</span>
    </div>
  );
}

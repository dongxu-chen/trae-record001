import { cn } from '@/utils/helpers';
import { getAlertLevelLabel } from '@/utils/helpers';

interface LevelBadgeProps {
  level: 'warning' | 'danger' | 'critical';
  size?: 'sm' | 'md';
  active?: boolean;
}

const LEVEL_STYLES: Record<string, { dot: string; text: string; pulse: string }> = {
  warning: {
    dot: 'bg-brand-amber',
    text: 'text-brand-amber',
    pulse: 'animate-pulse-amber',
  },
  danger: {
    dot: 'bg-brand-red',
    text: 'text-brand-red',
    pulse: 'animate-pulse-red',
  },
  critical: {
    dot: 'bg-red-700',
    text: 'text-red-400',
    pulse: 'animate-pulse-critical',
  },
};

export default function LevelBadge({ level, size = 'md', active = false }: LevelBadgeProps) {
  const style = LEVEL_STYLES[level];

  return (
    <span className={cn('inline-flex items-center gap-1.5', style.text)}>
      <span
        className={cn(
          'rounded-full',
          style.dot,
          active ? style.pulse : '',
          size === 'sm' ? 'h-1.5 w-1.5' : 'h-2 w-2'
        )}
      />
      <span className={size === 'sm' ? 'text-xs' : 'text-sm'}>
        {getAlertLevelLabel(level)}
      </span>
    </span>
  );
}

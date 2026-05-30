import { ThumbsUp, ThumbsDown, AlertTriangle } from 'lucide-react';
import { cn } from '@/utils/helpers';

interface FeedbackBadgeProps {
  type?: 'false_positive' | 'true_positive' | 'needs_adjustment';
  showLabel?: boolean;
  size?: 'sm' | 'md';
}

const FEEDBACK_CONFIG = {
  true_positive: {
    icon: ThumbsUp,
    color: 'text-brand-green',
    bgColor: 'bg-brand-green/15',
    label: '准确预警',
  },
  false_positive: {
    icon: ThumbsDown,
    color: 'text-brand-red',
    bgColor: 'bg-brand-red/15',
    label: '误报',
  },
  needs_adjustment: {
    icon: AlertTriangle,
    color: 'text-brand-amber',
    bgColor: 'bg-brand-amber/15',
    label: '需要调整',
  },
};

export default function FeedbackBadge({ type, showLabel = false, size = 'sm' }: FeedbackBadgeProps) {
  if (!type) {
    return (
      <div className={cn(
        'rounded-full bg-brand-border/50',
        size === 'sm' ? 'w-2 h-2' : 'w-3 h-3'
      )} />
    );
  }

  const config = FEEDBACK_CONFIG[type];
  const Icon = config.icon;

  return (
    <div className={cn(
      'inline-flex items-center gap-1 rounded-full px-2 py-0.5',
      config.bgColor
    )}>
      <Icon className={cn(
        config.color,
        size === 'sm' ? 'h-3 w-3' : 'h-4 w-4'
      )} />
      {showLabel && (
        <span className={cn(config.color, size === 'sm' ? 'text-xs' : 'text-sm')}>
          {config.label}
        </span>
      )}
    </div>
  );
}

import { Link2 } from 'lucide-react';
import { cn } from '@/utils/helpers';

interface CorrelationBadgeProps {
  strength: number;
  showIcon?: boolean;
  size?: 'sm' | 'md';
}

export default function CorrelationBadge({ strength, showIcon = false, size = 'sm' }: CorrelationBadgeProps) {
  const percentage = Math.round(strength * 100);
  
  const getColor = () => {
    if (strength >= 0.8) return 'bg-brand-cyan';
    if (strength >= 0.5) return 'bg-brand-green';
    if (strength >= 0.3) return 'bg-brand-amber';
    return 'bg-brand-text-secondary';
  };

  const getBarWidth = () => {
    return Math.max(percentage, 10);
  };

  return (
    <div className={cn(
      'inline-flex items-center gap-1.5',
      size === 'sm' ? 'text-xs' : 'text-sm'
    )}>
      {showIcon && <Link2 className={cn(size === 'sm' ? 'h-3 w-3' : 'h-4 w-4', 'text-brand-cyan')} />}
      <div className="flex items-center gap-1.5">
        <div className={cn(
          'rounded-full bg-brand-border overflow-hidden',
          size === 'sm' ? 'w-12 h-1.5' : 'w-16 h-2'
        )}>
          <div
            className={cn('h-full transition-all duration-300', getColor())}
            style={{ width: `${getBarWidth()}%` }}
          />
        </div>
        <span className="font-mono text-brand-text-secondary">{percentage}%</span>
      </div>
    </div>
  );
}

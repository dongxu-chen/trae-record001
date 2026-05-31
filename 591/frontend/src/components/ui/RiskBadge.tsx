import { cn } from '@/utils/helpers';
import type { RiskLevel } from '@/types';

interface RiskBadgeProps {
  risk: RiskLevel;
}

export function RiskBadge({ risk }: RiskBadgeProps) {
  const styles: Record<RiskLevel, { bg: string; text: string; label: string }> = {
    SAFE: { bg: 'bg-dep-safe/15 border-dep-safe/30', text: 'text-dep-safe', label: '安全' },
    LOW_RISK: { bg: 'bg-dep-low/15 border-dep-low/30', text: 'text-dep-low', label: '低风险' },
    MEDIUM_RISK: { bg: 'bg-dep-medium/15 border-dep-medium/30', text: 'text-dep-medium', label: '中风险' },
    HIGH_RISK: { bg: 'bg-dep-critical/15 border-dep-critical/30', text: 'text-dep-critical', label: '高风险' },
  };

  const { bg, text, label } = styles[risk] || styles.LOW_RISK;

  return (
    <span className={cn('inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium', bg, text)}>
      {label}
    </span>
  );
}

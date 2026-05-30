import { Check, X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface WcagBadgeProps {
  level: 'AA' | 'AAA';
  size: 'normal' | 'large';
  pass: boolean;
}

export function WcagBadge({ level, size, pass }: WcagBadgeProps) {
  const sizeLabel = size === 'normal' ? '普通文本' : '大文本';
  const threshold = level === 'AA'
    ? size === 'normal' ? '4.5:1' : '3:1'
    : size === 'normal' ? '7:1' : '4.5:1';

  return (
    <div
      className={cn(
        'flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium',
        pass
          ? 'bg-[#00d4aa]/10 text-[#00d4aa] border border-[#00d4aa]/20'
          : 'bg-[#ff6b35]/10 text-[#ff6b35] border border-[#ff6b35]/20'
      )}
    >
      {pass ? <Check className="w-3.5 h-3.5" /> : <X className="w-3.5 h-3.5" />}
      <span className="font-mono">{level}</span>
      <span className="text-zinc-500">{sizeLabel}</span>
      <span className="ml-auto font-mono text-zinc-500">{threshold}</span>
    </div>
  );
}

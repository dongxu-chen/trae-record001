import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface EmptyProps {
  icon?: ReactNode;
  title?: string;
  description?: string;
  className?: string;
}

export default function Empty({ icon, title, description, className }: EmptyProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-16 px-4', className)}>
      {icon && <div className="mb-4 text-brand-text-secondary">{icon}</div>}
      {title && (
        <h3 className="text-base font-medium text-brand-text-primary mb-1">{title}</h3>
      )}
      {description && (
        <p className="text-sm text-brand-text-secondary text-center max-w-xs">{description}</p>
      )}
    </div>
  );
}

import { cn } from '@/utils/helpers'

interface CardProps {
  children: React.ReactNode
  className?: string
  glowing?: boolean
  pulseRed?: boolean
}

export function Card({ children, className, glowing, pulseRed }: CardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border border-dep-border bg-dep-card p-5',
        glowing && 'animate-pulse-glow',
        pulseRed && 'animate-pulse-red',
        className,
      )}
    >
      {children}
    </div>
  )
}

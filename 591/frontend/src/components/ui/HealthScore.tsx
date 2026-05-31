import { healthScoreColor } from '@/utils/helpers'

interface HealthScoreProps {
  score: number
  size?: number
  strokeWidth?: number
  className?: string
}

export function HealthScore({ score, size = 140, strokeWidth = 10, className }: HealthScoreProps) {
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (score / 100) * circumference

  const colorMap: Record<string, string> = {
    'text-dep-safe': '#00D4AA',
    'text-dep-medium': '#FFA502',
    'text-dep-high': '#FF6B35',
    'text-dep-critical': '#FF4757',
  }

  const colorClass = healthScoreColor(score)
  const strokeColor = colorMap[colorClass] || '#7B8FA3'

  return (
    <div className={className}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#1A3A5C"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={strokeColor}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-1000 ease-out"
          style={{ filter: `drop-shadow(0 0 6px ${strokeColor}66)` }}
        />
      </svg>
      <div
        className="absolute inset-0 flex flex-col items-center justify-center"
        style={{ width: size, height: size }}
      >
        <span className={`font-mono text-3xl font-bold ${colorClass}`}>{score}</span>
        <span className="text-xs text-dep-muted">健康评分</span>
      </div>
    </div>
  )
}

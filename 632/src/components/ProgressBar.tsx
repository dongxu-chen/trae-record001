import { motion } from 'framer-motion';

interface ProgressBarProps {
  progress: number;
  showLabel?: boolean;
  height?: string;
  color?: string;
}

export function ProgressBar({
  progress,
  showLabel = true,
  height = 'h-2',
  color = 'bg-neon-blue-500'
}: ProgressBarProps) {
  const clampedProgress = Math.max(0, Math.min(100, progress));

  return (
    <div className="w-full">
      <div className={`w-full ${height} bg-deep-space-700 rounded-full overflow-hidden`}>
        <motion.div
          className={`h-full ${color} rounded-full relative overflow-hidden`}
          initial={{ width: 0 }}
          animate={{ width: `${clampedProgress}%` }}
          transition={{ duration: 0.3, ease: 'easeOut' }}
        >
          <div className="absolute inset-0 shimmer-progress" />
        </motion.div>
      </div>
      {showLabel && (
        <div className="text-xs text-deep-space-400 mt-1 font-mono">
          {clampedProgress.toFixed(0)}%
        </div>
      )}
    </div>
  );
}

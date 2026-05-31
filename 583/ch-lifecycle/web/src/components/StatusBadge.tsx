interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md';
}

const colorMap: Record<string, string> = {
  success: 'text-green-400',
  running: 'text-green-400',
  error: 'text-red-400',
  scheduled: 'text-slate-400',
  idle: 'text-slate-400',
};

const dotColorMap: Record<string, string> = {
  success: 'bg-green-400',
  running: 'bg-green-400',
  error: 'bg-red-400',
  scheduled: 'bg-slate-400',
  idle: 'bg-slate-400',
};

function getColor(status: string) {
  return colorMap[status] ?? 'text-yellow-400';
}

function getDotColor(status: string) {
  return dotColorMap[status] ?? 'bg-yellow-400';
}

export default function StatusBadge({ status, size = 'md' }: StatusBadgeProps) {
  const isRunning = status === 'running';
  const sizeClasses = size === 'sm' ? 'text-xs gap-1.5' : 'text-sm gap-2';
  const dotSize = size === 'sm' ? 'h-1.5 w-1.5' : 'h-2 w-2';

  return (
    <span className={`inline-flex items-center font-medium ${sizeClasses} ${getColor(status)}`}>
      <span className="relative flex">
        <span
          className={`${dotSize} rounded-full ${getDotColor(status)}`}
        />
        {isRunning && (
          <span
            className={`absolute inline-flex h-full w-full animate-ping rounded-full ${getDotColor(status)} opacity-75`}
          />
        )}
      </span>
      {status}
    </span>
  );
}

import React from 'react';

interface MetricsCardProps {
  title: string;
  value: string | number;
  unit?: string;
  trend?: 'up' | 'down' | 'stable';
  trendValue?: string;
  icon: string;
  color: string;
}

const MetricsCard: React.FC<MetricsCardProps> = ({
  title,
  value,
  unit,
  trend,
  trendValue,
  icon,
  color,
}) => {
  const trendColors = {
    up: 'text-green-500',
    down: 'text-red-500',
    stable: 'text-gray-500',
  };

  const trendIcons = {
    up: '↑',
    down: '↓',
    stable: '→',
  };

  return (
    <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100 hover:shadow-md transition-shadow duration-300">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-500 mb-1">{title}</p>
          <div className="flex items-baseline space-x-2">
            <span className={`text-3xl font-bold font-mono ${color}`}>{value}</span>
            {unit && <span className="text-sm text-gray-400">{unit}</span>}
          </div>
          {trend && trendValue && (
            <div className="mt-2 flex items-center space-x-1">
              <span className={`text-sm font-medium ${trendColors[trend]}`}>
                {trendIcons[trend]} {trendValue}
              </span>
              <span className="text-xs text-gray-400">vs 上次</span>
            </div>
          )}
        </div>
        <div className="w-12 h-12 rounded-lg bg-gray-50 flex items-center justify-center text-2xl">
          {icon}
        </div>
      </div>
    </div>
  );
};

export default MetricsCard;

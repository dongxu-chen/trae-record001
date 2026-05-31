import { Card, Progress, Tooltip } from 'antd';
import { TrendUp, TrendDown, Minus } from '@phosphor-icons/react';
import { getTrendColor, formatNumber, formatPercent } from '@/utils/format';

interface StatCardProps {
  title: string;
  value: number | string;
  icon: React.ReactNode;
  trend?: number;
  trendLabel?: string;
  progress?: number;
  color?: string;
  suffix?: string;
  tooltip?: string;
  loading?: boolean;
}

const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  icon,
  trend,
  trendLabel,
  progress,
  color = '#3B82F6',
  suffix,
  tooltip,
  loading,
}) => {
  const TrendIcon = trend && trend > 0 ? TrendUp : trend && trend < 0 ? TrendDown : Minus;
  const trendColor = trend ? getTrendColor(trend, false) : '#6B7280';

  return (
    <Tooltip title={tooltip}>
      <Card
        className="glass-card hover-lift border-0 h-full"
        styles={{ body: { padding: '20px' } }}
        loading={loading}
      >
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="text-sm text-gray-400 mb-1">{title}</div>
            <div className="flex items-baseline gap-1">
              <span
                className="font-display text-3xl font-bold"
                style={{ color }}
              >
                {typeof value === 'number' ? formatNumber(value) : value}
              </span>
              {suffix && (
                <span className="text-sm text-gray-400">{suffix}</span>
              )}
            </div>

            {trend !== undefined && (
              <div className="flex items-center gap-1 mt-2">
                <TrendIcon size={16} style={{ color: trendColor }} />
                <span className="text-sm" style={{ color: trendColor }}>
                  {Math.abs(trend).toFixed(1)}%
                </span>
                {trendLabel && (
                  <span className="text-xs text-gray-500 ml-1">{trendLabel}</span>
                )}
              </div>
            )}

            {progress !== undefined && (
              <div className="mt-3">
                <Progress
                  percent={Math.round(progress)}
                  showInfo={false}
                  strokeColor={color}
                  trailColor="#334155"
                  size="small"
                />
              </div>
            )}
          </div>

          <div
            className="w-12 h-12 rounded-xl flex items-center justify-center"
            style={{ backgroundColor: `${color}20` }}
          >
            <div style={{ color }}>{icon}</div>
          </div>
        </div>
      </Card>
    </Tooltip>
  );
};

export default StatCard;

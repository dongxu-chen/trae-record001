import { TrendingUp, TrendingDown, AlertTriangle, Minus } from 'lucide-react';

const colorClasses = {
  blue: 'bg-blue-500/20 text-blue-400',
  green: 'bg-green-500/20 text-green-400',
  amber: 'bg-amber-500/20 text-amber-400',
  red: 'bg-red-500/20 text-red-400',
  slate: 'bg-slate-500/20 text-slate-400'
};

function StatsCard({ title, value, max, unit = '', icon, trend, color = 'blue' }) {
  const percentage = max ? (value / max) * 100 : 0;
  
  const TrendIcon = {
    up: TrendingUp,
    down: TrendingDown,
    warning: AlertTriangle,
    danger: AlertTriangle,
    neutral: Minus
  }[trend] || Minus;

  const trendColor = {
    up: 'text-green-400',
    down: 'text-red-400',
    warning: 'text-amber-400',
    danger: 'text-red-400',
    neutral: 'text-slate-400'
  }[trend] || 'text-slate-400';

  return (
    <div className="card-glass rounded-xl p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-slate-400 mb-1">{title}</p>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white">{value}</span>
            {unit && <span className="text-sm text-slate-500">{unit}</span>}
          </div>
          {max && (
            <div className="mt-2 w-full bg-slate-700 rounded-full h-1.5">
              <div
                className={`h-1.5 rounded-full transition-all duration-500 ${
                  percentage > 80 ? 'bg-red-500' : percentage > 50 ? 'bg-amber-500' : 'bg-blue-500'
                }`}
                style={{ width: `${Math.min(percentage, 100)}%` }}
              ></div>
            </div>
          )}
        </div>
        <div className="flex flex-col items-end gap-2">
          <div className={`p-2 rounded-lg ${colorClasses[color]}`}>
            {icon}
          </div>
          <div className={`flex items-center gap-1 text-xs ${trendColor}`}>
            <TrendIcon className="w-3 h-3" />
            <span>
              {trend === 'danger' ? '异常' : trend === 'warning' ? '警告' : trend === 'up' ? '正常' : '稳定'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default StatsCard;

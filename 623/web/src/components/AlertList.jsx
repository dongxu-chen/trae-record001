import { AlertTriangle, AlertCircle, Info, Clock } from 'lucide-react';

const severityConfig = {
  warning: {
    icon: AlertTriangle,
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    text: 'text-amber-400',
    iconColor: 'text-amber-400'
  },
  error: {
    icon: AlertCircle,
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
    text: 'text-red-400',
    iconColor: 'text-red-400'
  },
  info: {
    icon: Info,
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/30',
    text: 'text-blue-400',
    iconColor: 'text-blue-400'
  }
};

function AlertList({ alerts, fullWidth = false }) {
  const displayAlerts = alerts.slice(0, fullWidth ? 50 : 10);

  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  return (
    <div className={`card-glass rounded-xl p-6 ${fullWidth ? '' : 'h-full'}`}>
      <h3 className="text-lg font-semibold mb-4 text-white">告警日志</h3>
      <div className={`space-y-2 ${fullWidth ? '' : 'max-h-64 overflow-y-auto'}`}>
        {displayAlerts.length === 0 ? (
          <div className="text-center py-8 text-slate-500">
            <Info className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p className="text-sm">暂无告警</p>
          </div>
        ) : (
          displayAlerts.map((alert, index) => {
            const config = severityConfig[alert.severity] || severityConfig.info;
            const Icon = config.icon;
            
            return (
              <div
                key={index}
                className={`p-3 rounded-lg ${config.bg} ${config.border} border`}
              >
                <div className="flex items-start gap-3">
                  <Icon className={`w-4 h-4 mt-0.5 ${config.iconColor} flex-shrink-0`} />
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm ${config.text}`}>{alert.description}</p>
                    <div className="flex items-center gap-1 mt-1 text-xs text-slate-500">
                      <Clock className="w-3 h-3" />
                      <span>{formatTime(alert.timestamp)}</span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
      {alerts.length > 10 && !fullWidth && (
        <p className="text-xs text-slate-500 mt-3 text-center">
          还有 {alerts.length - 10} 条告警...
        </p>
      )}
    </div>
  );
}

export default AlertList;

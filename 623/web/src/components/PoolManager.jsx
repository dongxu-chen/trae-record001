import { useEffect, useState } from 'react';
import { Layers, ThermometerSun, TrendingUp, TrendingDown, Activity, History, Zap, Gauge } from 'lucide-react';

export default function PoolManager({ stats }) {
  const [scalingHistory, setScalingHistory] = useState([]);
  const [usageHistory, setUsageHistory] = useState([]);
  const [preWarmStats, setPreWarmStats] = useState({});
  const [scaleFactor, setScaleFactor] = useState(1.5);
  const [warmCount, setWarmCount] = useState(20);

  useEffect(() => {
    fetchPoolData();
    const interval = setInterval(fetchPoolData, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchPoolData = async () => {
    try {
      const [scalingRes, usageRes, prewarmRes] = await Promise.all([
        fetch('/api/pool/scaling-history'),
        fetch('/api/pool/usage-history'),
        fetch('/api/prewarm')
      ]);
      const scalingData = await scalingRes.json();
      const usageData = await usageRes.json();
      const prewarmData = await prewarmRes.json();
      
      setScalingHistory(scalingData.events || []);
      setUsageHistory(usageData.snapshots || []);
      setPreWarmStats(prewarmData);
    } catch (err) {
      console.error('Failed to fetch pool data:', err);
    }
  };

  const handleScaleUp = async () => {
    try {
      await fetch('/api/pool/scale-up', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ factor: scaleFactor, reason: 'Manual scale up' })
      });
      fetchPoolData();
    } catch (err) {
      console.error('Scale up failed:', err);
    }
  };

  const handleScaleDown = async () => {
    try {
      await fetch('/api/pool/scale-down', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ factor: 0.7, reason: 'Manual scale down' })
      });
      fetchPoolData();
    } catch (err) {
      console.error('Scale down failed:', err);
    }
  };

  const handlePreWarm = async () => {
    try {
      await fetch('/api/prewarm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ count: warmCount })
      });
      fetchPoolData();
    } catch (err) {
      console.error('Pre-warm failed:', err);
    }
  };

  const pool = stats.pool || {};
  const prewarm = stats.prewarm || {};
  const usageRatio = pool.usage_ratio || 0;
  const currentMax = pool.current_max_connections || 0;
  const baseMax = pool.base_max_connections || 0;
  const isExpanded = currentMax > baseMax;

  const usageBarColor = usageRatio > 0.85 ? 'bg-red-500' : usageRatio > 0.6 ? 'bg-amber-500' : 'bg-emerald-500';
  const usageBarBg = usageRatio > 0.85 ? 'bg-red-500/10' : usageRatio > 0.6 ? 'bg-amber-500/10' : 'bg-emerald-500/10';

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card-glass rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Layers className="w-4 h-4 text-blue-400" />
            <span className="text-sm text-slate-400">当前容量</span>
          </div>
          <div className="flex items-baseline gap-2">
            <p className="text-3xl font-bold text-white">{currentMax}</p>
            <span className="text-sm text-slate-500">/ {baseMax} 基准</span>
          </div>
          {isExpanded && (
            <div className="mt-2 flex items-center gap-1 text-xs text-amber-400">
              <TrendingUp className="w-3 h-3" />
              已扩容 {(((currentMax / baseMax) - 1) * 100).toFixed(0)}%
            </div>
          )}
        </div>

        <div className="card-glass rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Gauge className="w-4 h-4 text-emerald-400" />
            <span className="text-sm text-slate-400">使用率</span>
          </div>
          <p className="text-3xl font-bold text-white">{(usageRatio * 100).toFixed(1)}%</p>
          <div className={`mt-2 h-2 ${usageBarBg} rounded-full overflow-hidden`}>
            <div className={`h-full ${usageBarColor} rounded-full transition-all`} style={{ width: `${Math.min(usageRatio * 100, 100)}%` }} />
          </div>
        </div>

        <div className="card-glass rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <ThermometerSun className="w-4 h-4 text-orange-400" />
            <span className="text-sm text-slate-400">预热池</span>
          </div>
          <div className="flex items-baseline gap-2">
            <p className="text-3xl font-bold text-white">{pool.warm_pool_total || 0}</p>
            <span className="text-sm text-slate-500">可用 {pool.warm_pool_available || 0}</span>
          </div>
          <div className="mt-1 text-xs text-slate-500">
            命中率: {(prewarm.hit_rate || 0).toFixed(1)}%
          </div>
        </div>

        <div className="card-glass rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="w-4 h-4 text-violet-400" />
            <span className="text-sm text-slate-400">预热预测</span>
          </div>
          <div className="text-sm space-y-1">
            <div className="flex justify-between">
              <span className="text-slate-500">预测速率</span>
              <span className="text-white">{(prewarmStats.prediction?.predicted_rate || 0).toFixed(2)} conn/s</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">置信度</span>
              <span className="text-white">{((prewarmStats.prediction?.confidence || 0) * 100).toFixed(0)}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">建议预热</span>
              <span className={prewarmStats.prediction?.should_warm ? 'text-amber-400' : 'text-slate-400'}>
                {prewarmStats.prediction?.should_warm ? '是' : '否'}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card-glass rounded-xl p-4">
          <h3 className="text-lg font-semibold text-white mb-4">容量操作</h3>
          <div className="space-y-4">
            <div>
              <label className="text-sm text-slate-400 mb-2 block">手动扩容</label>
              <div className="flex items-center gap-3">
                <input
                  type="number"
                  value={scaleFactor}
                  onChange={e => setScaleFactor(parseFloat(e.target.value) || 1.5)}
                  step="0.1"
                  min="1.1"
                  max="3.0"
                  className="w-24 bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                />
                <span className="text-sm text-slate-500">倍</span>
                <button
                  onClick={handleScaleUp}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm rounded transition-colors flex items-center gap-1"
                >
                  <TrendingUp className="w-4 h-4" />
                  扩容
                </button>
                <button
                  onClick={handleScaleDown}
                  className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white text-sm rounded transition-colors flex items-center gap-1"
                >
                  <TrendingDown className="w-4 h-4" />
                  缩容
                </button>
              </div>
              <p className="text-xs text-slate-600 mt-1">
                最大允许 {baseMax * 3} 连接（基准的3倍）
              </p>
            </div>
            
            <div>
              <label className="text-sm text-slate-400 mb-2 block">手动预热</label>
              <div className="flex items-center gap-3">
                <input
                  type="number"
                  value={warmCount}
                  onChange={e => setWarmCount(parseInt(e.target.value) || 20)}
                  min="1"
                  max="100"
                  className="w-24 bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                />
                <span className="text-sm text-slate-500">个连接</span>
                <button
                  onClick={handlePreWarm}
                  className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-sm rounded transition-colors flex items-center gap-1"
                >
                  <ThermometerSun className="w-4 h-4" />
                  预热
                </button>
              </div>
            </div>
          </div>
        </div>

        <div className="card-glass rounded-xl p-4">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <History className="w-5 h-5 text-slate-400" />
            扩缩容历史
          </h3>
          <div className="space-y-2 max-h-[300px] overflow-y-auto">
            {scalingHistory.length === 0 ? (
              <p className="text-sm text-slate-500 text-center py-4">暂无扩缩容记录</p>
            ) : (
              scalingHistory.slice().reverse().map((event, i) => {
                const isScaleUp = event.new_capacity > event.old_capacity;
                return (
                  <div key={i} className="flex items-center gap-3 py-2 border-b border-slate-800 last:border-0">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center ${isScaleUp ? 'bg-emerald-500/20' : 'bg-red-500/20'}`}>
                      {isScaleUp ? <TrendingUp className="w-4 h-4 text-emerald-400" /> : <TrendingDown className="w-4 h-4 text-red-400" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-white">{event.old_capacity} → {event.new_capacity}</span>
                        <span className={`text-xs px-1.5 py-0.5 rounded ${isScaleUp ? 'bg-emerald-500/20 text-emerald-300' : 'bg-red-500/20 text-red-300'}`}>
                          {event.event_type}
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 truncate">{event.reason}</p>
                    </div>
                    <span className="text-xs text-slate-600">
                      {new Date(event.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      <div className="card-glass rounded-xl p-4">
        <h3 className="text-lg font-semibold text-white mb-4">使用率趋势</h3>
        <div className="h-48 flex items-end gap-px">
          {usageHistory.slice(-60).map((snapshot, i) => {
            const height = Math.max((snapshot.usage_ratio || 0) * 100, 2);
            const color = snapshot.usage_ratio > 0.85 ? 'bg-red-500' : snapshot.usage_ratio > 0.6 ? 'bg-amber-500' : 'bg-emerald-500';
            return (
              <div
                key={i}
                className={`flex-1 ${color} rounded-t opacity-70 hover:opacity-100 transition-opacity`}
                style={{ height: `${height}%` }}
                title={`使用率: ${(snapshot.usage_ratio * 100).toFixed(1)}% | 活跃: ${snapshot.active_conns} | 最大: ${snapshot.max_conns}`}
              />
            );
          })}
        </div>
        <div className="flex justify-between mt-2 text-xs text-slate-600">
          <span>5分钟前</span>
          <span>现在</span>
        </div>
      </div>
    </div>
  );
}

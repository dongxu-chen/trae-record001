import { useEffect, useState, useCallback } from 'react';
import { Shield, Activity, Database, AlertTriangle, Clock, Users, Zap, Settings, RefreshCw, GitBranch, ThermometerSun, Layers } from 'lucide-react';
import StatsCard from './components/StatsCard';
import ConnectionChart from './components/ConnectionChart';
import ConnectionTable from './components/ConnectionTable';
import AlertList from './components/AlertList';
import ControlPanel from './components/ControlPanel';
import ConnectionLifecycle from './components/ConnectionLifecycle';
import PoolManager from './components/PoolManager';
import { useWebSocket } from './hooks/useWebSocket';

function App() {
  const [stats, setStats] = useState({
    proxy: { active_connections: 0, total_connections: 0, connection_rate: 0 },
    analyzer: { slow_connection_count: 0, leak_candidate_count: 0, storm_alert_count: 0 },
    limiter: { total_connections: 0, max_connections: 500, storm_detected: false },
    pool: { active_connections: 0, base_max_connections: 500, current_max_connections: 500, usage_ratio: 0, is_storm: false, warm_pool_total: 0, warm_pool_available: 0 },
    prewarm: { is_pre_warming: false, total_pre_warmed: 0, cache_hits: 0, cache_misses: 0, hit_rate: 0 },
    lifecycle: { tracked_connections: 0, total_events: 0, phase_distribution: {} }
  });
  const [connections, setConnections] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [activeTab, setActiveTab] = useState('overview');

  const { connected } = useWebSocket((data) => {
    if (data.type === 'stats') {
      setStats(data.data);
    }
  });

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = useCallback(async () => {
    try {
      const [statsRes, connRes, alertsRes] = await Promise.all([
        fetch('/api/stats'),
        fetch('/api/connections'),
        fetch('/api/alerts')
      ]);
      
      const statsData = await statsRes.json();
      const connData = await connRes.json();
      const alertsData = await alertsRes.json();

      setStats(statsData);
      setConnections(connData.connections || []);
      setAlerts(alertsData.alerts || []);
    } catch (err) {
      console.error('Failed to fetch data:', err);
    }
  }, []);

  return (
    <div className="min-h-screen bg-slate-900">
      <header className="bg-slate-800 border-b border-slate-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-600 rounded-lg">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">DB Guardian</h1>
              <p className="text-sm text-slate-400">数据库连接风暴防护系统</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500 pulse-dot' : 'bg-red-500'}`}></span>
              <span className="text-sm text-slate-400">{connected ? '实时连接' : '未连接'}</span>
            </div>
            {stats.pool?.is_storm && (
              <div className="flex items-center gap-2 px-3 py-1 bg-red-900/50 border border-red-700 rounded-full">
                <AlertTriangle className="w-4 h-4 text-red-400" />
                <span className="text-xs font-medium text-red-300">风暴模式</span>
              </div>
            )}
            {stats.prewarm?.is_pre_warming && (
              <div className="flex items-center gap-2 px-3 py-1 bg-amber-900/50 border border-amber-700 rounded-full">
                <ThermometerSun className="w-4 h-4 text-amber-400" />
                <span className="text-xs font-medium text-amber-300">预热中</span>
              </div>
            )}
            <button
              onClick={fetchData}
              className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
            >
              <RefreshCw className="w-5 h-5 text-slate-400" />
            </button>
          </div>
        </div>
      </header>

      <nav className="bg-slate-800/50 border-b border-slate-700 px-6">
        <div className="flex gap-1">
          {[
            { id: 'overview', label: '总览', icon: Activity },
            { id: 'connections', label: '连接管理', icon: Database },
            { id: 'lifecycle', label: '生命周期', icon: GitBranch },
            { id: 'pool', label: '连接池', icon: Layers },
            { id: 'alerts', label: '告警中心', icon: AlertTriangle },
            { id: 'control', label: '控制中心', icon: Settings }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors border-b-2 ${
                activeTab === tab.id
                  ? 'text-blue-400 border-blue-400'
                  : 'text-slate-400 border-transparent hover:text-slate-200'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>
      </nav>

      <main className="p-6">
        {activeTab === 'overview' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4">
              <StatsCard
                title="活跃连接"
                value={stats.proxy.active_connections}
                max={stats.pool?.current_max_connections || stats.limiter.max_connections}
                icon={<Database className="w-5 h-5" />}
                trend="up"
                color="blue"
              />
              <StatsCard
                title="连接速率"
                value={stats.proxy.connection_rate?.toFixed(2) || '0'}
                unit="conn/s"
                icon={<Zap className="w-5 h-5" />}
                trend={stats.limiter.storm_detected ? 'danger' : 'up'}
                color={stats.limiter.storm_detected ? 'red' : 'green'}
              />
              <StatsCard
                title="慢建连"
                value={stats.analyzer.slow_connection_count}
                icon={<Clock className="w-5 h-5" />}
                trend="warning"
                color="amber"
              />
              <StatsCard
                title="泄漏风险"
                value={stats.analyzer.leak_candidate_count}
                icon={<Users className="w-5 h-5" />}
                trend={stats.analyzer.leak_candidate_count > 0 ? 'danger' : 'neutral'}
                color={stats.analyzer.leak_candidate_count > 0 ? 'red' : 'slate'}
              />
              <StatsCard
                title="预热池"
                value={stats.pool?.warm_pool_total || 0}
                subtitle={`可用 ${stats.pool?.warm_pool_available || 0}`}
                icon={<ThermometerSun className="w-5 h-5" />}
                trend={stats.prewarm?.is_pre_warming ? 'up' : 'neutral'}
                color={stats.prewarm?.is_pre_warming ? 'amber' : 'slate'}
              />
              <StatsCard
                title="容量使用率"
                value={`${((stats.pool?.usage_ratio || 0) * 100).toFixed(1)}%`}
                icon={<Layers className="w-5 h-5" />}
                trend={(stats.pool?.usage_ratio || 0) > 0.85 ? 'danger' : 'neutral'}
                color={(stats.pool?.usage_ratio || 0) > 0.85 ? 'red' : (stats.pool?.usage_ratio || 0) > 0.6 ? 'amber' : 'green'}
              />
            </div>

            {stats.pool?.is_storm && (
              <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 flex items-center gap-3">
                <AlertTriangle className="w-6 h-6 text-red-400" />
                <div>
                  <p className="font-semibold text-red-300">检测到连接风暴！</p>
                  <p className="text-sm text-red-400">
                    系统已自动扩容至 {stats.pool?.current_max_connections} 连接（基准 {stats.pool?.base_max_connections}），预热池已激活
                  </p>
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <ConnectionChart />
              </div>
              <AlertList alerts={alerts} />
            </div>

            <div className="card-glass rounded-xl p-6">
              <h3 className="text-lg font-semibold mb-4 text-white">最近连接</h3>
              <ConnectionTable connections={connections.slice(0, 10)} compact />
            </div>
          </div>
        )}

        {activeTab === 'connections' && (
          <div className="space-y-6">
            <div className="card-glass rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white">连接列表</h3>
                <span className="text-sm text-slate-400">共 {connections.length} 个连接</span>
              </div>
              <ConnectionTable connections={connections} />
            </div>
          </div>
        )}

        {activeTab === 'lifecycle' && (
          <ConnectionLifecycle stats={stats} />
        )}

        {activeTab === 'pool' && (
          <PoolManager stats={stats} />
        )}

        {activeTab === 'alerts' && (
          <div className="card-glass rounded-xl p-6">
            <h3 className="text-lg font-semibold mb-4 text-white">告警中心</h3>
            <AlertList alerts={alerts} fullWidth />
          </div>
        )}

        {activeTab === 'control' && (
          <ControlPanel stats={stats} />
        )}
      </main>
    </div>
  );
}

export default App;

import { useEffect, useState } from 'react';
import { GitBranch, Clock, Activity, Eye, Search, Filter } from 'lucide-react';

const PHASE_CONFIG = {
  created: { label: '创建', color: '#3b82f6', bg: 'bg-blue-500/20', border: 'border-blue-500', text: 'text-blue-300' },
  authenticating: { label: '认证', color: '#8b5cf6', bg: 'bg-violet-500/20', border: 'border-violet-500', text: 'text-violet-300' },
  active: { label: '活跃', color: '#10b981', bg: 'bg-emerald-500/20', border: 'border-emerald-500', text: 'text-emerald-300' },
  querying: { label: '查询', color: '#06b6d4', bg: 'bg-cyan-500/20', border: 'border-cyan-500', text: 'text-cyan-300' },
  idle: { label: '空闲', color: '#f59e0b', bg: 'bg-amber-500/20', border: 'border-amber-500', text: 'text-amber-300' },
  pre_warmed: { label: '预热', color: '#f97316', bg: 'bg-orange-500/20', border: 'border-orange-500', text: 'text-orange-300' },
  leased: { label: '租用', color: '#6366f1', bg: 'bg-indigo-500/20', border: 'border-indigo-500', text: 'text-indigo-300' },
  releasing: { label: '释放', color: '#ec4899', bg: 'bg-pink-500/20', border: 'border-pink-500', text: 'text-pink-300' },
  closed: { label: '关闭', color: '#64748b', bg: 'bg-slate-500/20', border: 'border-slate-500', text: 'text-slate-300' },
  rate_limited: { label: '限流', color: '#ef4444', bg: 'bg-red-500/20', border: 'border-red-500', text: 'text-red-300' },
  storm_blocked: { label: '风暴阻断', color: '#ef4444', bg: 'bg-red-500/20', border: 'border-red-500', text: 'text-red-300' },
  leak_detected: { label: '泄漏', color: '#ef4444', bg: 'bg-red-500/20', border: 'border-red-500', text: 'text-red-300' },
  force_closed: { label: '强制关闭', color: '#dc2626', bg: 'bg-red-600/20', border: 'border-red-600', text: 'text-red-400' },
  expired: { label: '过期', color: '#78716c', bg: 'bg-stone-500/20', border: 'border-stone-500', text: 'text-stone-300' },
  returned: { label: '归还', color: '#22d3ee', bg: 'bg-cyan-400/20', border: 'border-cyan-400', text: 'text-cyan-300' },
};

const PHASE_ORDER = ['created', 'authenticating', 'pre_warmed', 'leased', 'active', 'querying', 'idle', 'releasing', 'returned', 'closed', 'expired', 'rate_limited', 'storm_blocked', 'leak_detected', 'force_closed'];

function PhaseBar({ events }) {
  const phaseSequence = events.map(e => e.event_type);
  const uniquePhases = [...new Set(phaseSequence)];
  
  return (
    <div className="flex items-center gap-1">
      {PHASE_ORDER.filter(p => uniquePhases.includes(p)).map((phase, i) => {
        const cfg = PHASE_CONFIG[phase] || PHASE_CONFIG.created;
        const eventCount = phaseSequence.filter(p => p === phase).length;
        return (
          <div key={i} className="flex items-center">
            <div 
              className={`${cfg.bg} ${cfg.border} border rounded px-2 py-0.5 text-xs ${cfg.text} font-medium`}
              title={`${cfg.label} (${eventCount}次)`}
            >
              {cfg.label}
              {eventCount > 1 && <span className="ml-1 opacity-60">×{eventCount}</span>}
            </div>
            {i < uniquePhases.filter(p => PHASE_ORDER.includes(p)).length - 1 && (
              <div className="w-2 h-px bg-slate-600 mx-0.5" />
            )}
          </div>
        );
      })}
    </div>
  );
}

function TimelineView({ timeline }) {
  const [expanded, setExpanded] = useState(false);
  const cfg = PHASE_CONFIG[timeline.current_phase] || PHASE_CONFIG.created;
  const duration = timeline.duration;
  const durationStr = duration < 60 ? `${duration.toFixed(1)}s` : `${(duration / 60).toFixed(1)}m`;

  return (
    <div className="border border-slate-700 rounded-lg overflow-hidden">
      <div 
        className="px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-slate-800/50"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-sm font-mono text-slate-400">#{timeline.connection_id}</span>
            <span className={`${cfg.bg} ${cfg.border} border rounded-full px-2 py-0.5 text-xs ${cfg.text} font-medium`}>
              {cfg.label}
            </span>
          </div>
          <span className="text-xs text-slate-500">{timeline.client_id}</span>
          <span className="text-xs text-slate-600">{timeline.client_ip}</span>
        </div>
        <div className="flex items-center gap-4">
          <PhaseBar events={timeline.events} />
          <span className="text-xs text-slate-400 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {durationStr}
          </span>
          <span className="text-xs text-slate-500">{timeline.events.length} 事件</span>
        </div>
      </div>
      
      {expanded && (
        <div className="border-t border-slate-700 bg-slate-800/30 p-4">
          <div className="relative ml-4">
            {timeline.events.map((event, i) => {
              const eCfg = PHASE_CONFIG[event.event_type] || PHASE_CONFIG.created;
              return (
                <div key={i} className="flex items-start gap-3 mb-3 last:mb-0">
                  <div className="flex flex-col items-center">
                    <div 
                      className="w-3 h-3 rounded-full border-2"
                      style={{ borderColor: eCfg.color, backgroundColor: `${eCfg.color}40` }}
                    />
                    {i < timeline.events.length - 1 && (
                      <div className="w-px h-6 bg-slate-700" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={`text-sm font-medium ${eCfg.text}`}>{eCfg.label}</span>
                      <span className="text-xs text-slate-500">
                        {new Date(event.timestamp).toLocaleTimeString()}
                      </span>
                      {event.duration > 0 && (
                        <span className="text-xs text-slate-600">
                          耗时 {event.duration.toFixed(2)}s
                        </span>
                      )}
                    </div>
                    {event.detail && (
                      <p className="text-xs text-slate-500 mt-0.5">{event.detail}</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default function ConnectionLifecycle({ stats }) {
  const [timelines, setTimelines] = useState([]);
  const [activeConns, setActiveConns] = useState([]);
  const [phaseStats, setPhaseStats] = useState({});
  const [filter, setFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchLifecycleData();
    const interval = setInterval(fetchLifecycleData, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchLifecycleData = async () => {
    try {
      const [recentRes, activeRes, phasesRes] = await Promise.all([
        fetch('/api/lifecycle/recent'),
        fetch('/api/lifecycle/active'),
        fetch('/api/lifecycle/phases')
      ]);
      const recentData = await recentRes.json();
      const activeData = await activeRes.json();
      const phasesData = await phasesRes.json();
      
      setTimelines(recentData.timelines || []);
      setActiveConns(activeData.connections || []);
      setPhaseStats(phasesData.phases || {});
    } catch (err) {
      console.error('Failed to fetch lifecycle data:', err);
    }
  };

  const filteredTimelines = timelines.filter(t => {
    if (filter !== 'all' && t.current_phase !== filter) return false;
    if (searchTerm && !t.client_id?.includes(searchTerm) && !t.client_ip?.includes(searchTerm) && !String(t.connection_id).includes(searchTerm)) return false;
    return true;
  });

  const totalTracked = stats.lifecycle?.tracked_connections || 0;
  const totalEvents = stats.lifecycle?.total_events || 0;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card-glass rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <GitBranch className="w-4 h-4 text-blue-400" />
            <span className="text-sm text-slate-400">追踪连接</span>
          </div>
          <p className="text-2xl font-bold text-white">{totalTracked}</p>
        </div>
        <div className="card-glass rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-4 h-4 text-emerald-400" />
            <span className="text-sm text-slate-400">活跃连接</span>
          </div>
          <p className="text-2xl font-bold text-white">{activeConns.length}</p>
        </div>
        <div className="card-glass rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Eye className="w-4 h-4 text-violet-400" />
            <span className="text-sm text-slate-400">生命周期事件</span>
          </div>
          <p className="text-2xl font-bold text-white">{totalEvents}</p>
        </div>
        <div className="card-glass rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-amber-400" />
            <span className="text-sm text-slate-400">当前阶段分布</span>
          </div>
          <div className="flex flex-wrap gap-1 mt-1">
            {Object.entries(phaseStats).map(([phase, count]) => {
              const cfg = PHASE_CONFIG[phase] || PHASE_CONFIG.created;
              return (
                <span key={phase} className={`${cfg.bg} ${cfg.border} border rounded px-1.5 py-0.5 text-xs ${cfg.text}`}>
                  {cfg.label}: {count}
                </span>
              );
            })}
          </div>
        </div>
      </div>

      <div className="card-glass rounded-xl p-4">
        <div className="flex items-center gap-4 mb-4">
          <h3 className="text-lg font-semibold text-white">阶段分布</h3>
        </div>
        <div className="flex gap-2 flex-wrap">
          {Object.entries(phaseStats).sort((a, b) => b[1] - a[1]).map(([phase, count]) => {
            const cfg = PHASE_CONFIG[phase] || PHASE_CONFIG.created;
            const pct = totalTracked > 0 ? ((count / totalTracked) * 100).toFixed(1) : 0;
            return (
              <div key={phase} className="flex-1 min-w-[100px] max-w-[200px]">
                <div className={`${cfg.bg} border ${cfg.border} rounded-lg p-3 text-center`}>
                  <div className={`text-lg font-bold ${cfg.text}`}>{count}</div>
                  <div className="text-xs text-slate-400">{cfg.label}</div>
                  <div className="text-xs text-slate-500">{pct}%</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="card-glass rounded-xl p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">连接时间线</h3>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="w-4 h-4 text-slate-500 absolute left-2 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="搜索连接ID/客户端..."
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="pl-8 pr-3 py-1.5 bg-slate-800 border border-slate-700 rounded text-sm text-slate-300 focus:outline-none focus:border-blue-500"
              />
            </div>
            <div className="flex items-center gap-1">
              <Filter className="w-4 h-4 text-slate-500" />
              <select
                value={filter}
                onChange={e => setFilter(e.target.value)}
                className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-sm text-slate-300 focus:outline-none focus:border-blue-500"
              >
                <option value="all">全部阶段</option>
                {PHASE_ORDER.map(phase => {
                  const cfg = PHASE_CONFIG[phase];
                  return <option key={phase} value={phase}>{cfg?.label || phase}</option>;
                })}
              </select>
            </div>
          </div>
        </div>
        
        <div className="space-y-2 max-h-[600px] overflow-y-auto">
          {filteredTimelines.length === 0 ? (
            <div className="text-center py-8 text-slate-500">
              <GitBranch className="w-12 h-12 mx-auto mb-2 opacity-30" />
              <p>暂无生命周期数据</p>
            </div>
          ) : (
            filteredTimelines.map(tl => (
              <TimelineView key={tl.connection_id} timeline={tl} />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

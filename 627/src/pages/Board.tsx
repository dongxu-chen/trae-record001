import { useEffect, useState } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { Database, Shield, AlertTriangle, Activity, Clock, FullScreen } from 'lucide-react';
import { statsApi } from '@/lib/api';
import type { BoardMetrics } from '../../shared/types.js';

const PIE_COLORS = ['#0d9488', '#f59e0b', '#ef4444', '#6366f1'];

const gradeColors: Record<string, { text: string; glow: string }> = {
  A: { text: 'text-green-400', glow: 'shadow-green-500/50' },
  B: { text: 'text-blue-400', glow: 'shadow-blue-500/50' },
  C: { text: 'text-yellow-400', glow: 'shadow-yellow-500/50' },
  D: { text: 'text-orange-400', glow: 'shadow-orange-500/50' },
  F: { text: 'text-red-400', glow: 'shadow-red-500/50' },
};

export default function Board() {
  const [metrics, setMetrics] = useState<BoardMetrics | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const refreshBoard = async () => {
    try {
      const data = await statsApi.getBoard();
      setMetrics(data);
    } catch {}
  };

  useEffect(() => {
    void refreshBoard();
    const interval = setInterval(() => void refreshBoard(), 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsFullscreen(false);
      if (e.key === 'f' || e.key === 'F') setIsFullscreen(prev => !prev);
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, []);

  if (!metrics) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <p className="text-gray-400 text-lg">加载数据看板...</p>
      </div>
    );
  }

  const hs = metrics.healthScore;
  const gc = gradeColors[hs.grade] ?? gradeColors.F;

  return (
    <div className={`${isFullscreen ? 'fixed inset-0 z-50' : 'min-h-[calc(100vh-8rem)]'} bg-gray-950 text-white p-6 rounded-xl overflow-auto`}>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Database className="w-8 h-8 text-primary-400" />
          <h1 className="text-2xl font-bold font-display">数据质量看板</h1>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-gray-400 text-sm">
            <Clock className="w-4 h-4" />
            <span>{new Date(metrics.lastUpdated).toLocaleTimeString()}</span>
            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          </div>
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
          >
            <FullScreen className="w-5 h-5 text-gray-400" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[
          { label: '健康评分', value: `${hs.overall}`, suffix: '分', icon: Activity, color: 'text-primary-400' },
          { label: '活跃规则', value: `${metrics.activeRules}`, suffix: `/${metrics.totalRules}`, icon: Shield, color: 'text-blue-400' },
          { label: '待处理问题', value: `${metrics.openIssues}`, suffix: '个', icon: AlertTriangle, color: 'text-orange-400' },
          { label: '失败记录', value: `${metrics.failedRecords}`, suffix: `/${metrics.totalRecords}`, icon: Database, color: 'text-red-400' },
        ].map((item, i) => {
          const Icon = item.icon;
          return (
            <div key={i} className="bg-gray-900 rounded-xl p-5 border border-gray-800">
              <div className="flex items-center gap-2 mb-2">
                <Icon className={`w-5 h-5 ${item.color}`} />
                <span className="text-gray-400 text-sm">{item.label}</span>
              </div>
              <div className="flex items-end gap-1">
                <span className="text-3xl font-bold">{item.value}</span>
                <span className="text-gray-500 text-sm mb-1">{item.suffix}</span>
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        <div className="bg-gray-900 rounded-xl p-6 border border-gray-800 flex flex-col items-center justify-center">
          <p className="text-gray-400 text-sm mb-4">健康等级</p>
          <div className={`w-36 h-36 rounded-full border-4 flex items-center justify-center shadow-lg ${gc.glow}`}
            style={{ borderColor: hs.grade === 'A' ? '#22c55e' : hs.grade === 'B' ? '#3b82f6' : hs.grade === 'C' ? '#eab308' : hs.grade === 'D' ? '#f97316' : '#ef4444' }}
          >
            <span className={`text-6xl font-bold ${gc.text}`}>{hs.grade}</span>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
            <span className="text-gray-500">完整性</span>
            <span className="text-gray-200">{hs.dimensionScores.completeness}%</span>
            <span className="text-gray-500">唯一性</span>
            <span className="text-gray-200">{hs.dimensionScores.uniqueness}%</span>
            <span className="text-gray-500">有效性</span>
            <span className="text-gray-200">{hs.dimensionScores.validity}%</span>
            <span className="text-gray-500">一致性</span>
            <span className="text-gray-200">{hs.dimensionScores.consistency}%</span>
          </div>
        </div>

        <div className="lg:col-span-2 bg-gray-900 rounded-xl p-6 border border-gray-800">
          <p className="text-gray-400 text-sm mb-4">近期质量评分趋势</p>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={metrics.recentScores}>
                <defs>
                  <linearGradient id="boardGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0d9488" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#0d9488" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="date" stroke="#6b7280" fontSize={11} />
                <YAxis domain={[0, 100]} stroke="#6b7280" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1f2937',
                    border: '1px solid #374151',
                    borderRadius: '8px',
                    color: '#e5e7eb',
                  }}
                />
                <Area type="monotone" dataKey="value" stroke="#0d9488" strokeWidth={2} fill="url(#boardGrad)" name="质量分" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
          <p className="text-gray-400 text-sm mb-4">问题类型分布</p>
          <div className="h-52 flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={metrics.issueDistribution}
                  dataKey="count"
                  nameKey="label"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={({ label, count }) => `${label}: ${count}`}
                >
                  {metrics.issueDistribution.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1f2937',
                    border: '1px solid #374151',
                    borderRadius: '8px',
                    color: '#e5e7eb',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
          <p className="text-gray-400 text-sm mb-4">规则评分明细</p>
          <div className="space-y-3 max-h-52 overflow-auto">
            {hs.ruleScores.map((rs) => (
              <div key={rs.ruleId} className="flex items-center gap-3">
                <span className="text-sm text-gray-300 w-32 truncate">{rs.ruleName}</span>
                <div className="flex-1 bg-gray-800 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${rs.score >= 90 ? 'bg-green-500' : rs.score >= 70 ? 'bg-yellow-500' : 'bg-red-500'}`}
                    style={{ width: `${Math.min(rs.score, 100)}%` }}
                  />
                </div>
                <span className={`text-sm font-mono w-12 text-right ${rs.score >= 90 ? 'text-green-400' : rs.score >= 70 ? 'text-yellow-400' : 'text-red-400'}`}>
                  {rs.score}%
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

import { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  Legend,
  ReferenceLine,
} from 'recharts';
import { TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react';
import { useAppStore } from '@/store/appStore';

export default function Trends() {
  const {
    qualityTrendWithThreshold,
    issuesTrendWithThreshold,
    fetchQualityTrendWithThreshold,
    fetchIssuesTrendWithThreshold,
  } = useAppStore();
  const [days, setDays] = useState(7);

  useEffect(() => {
    void fetchQualityTrendWithThreshold(days);
    void fetchIssuesTrendWithThreshold(days);
  }, [fetchQualityTrendWithThreshold, fetchIssuesTrendWithThreshold, days]);

  const qualityAnomalyCount = qualityTrendWithThreshold.filter(d => d.isAnomaly).length;
  const issuesAnomalyCount = issuesTrendWithThreshold.filter(d => d.isAnomaly).length;

  const avgScore =
    qualityTrendWithThreshold.length > 0
      ? Math.round(qualityTrendWithThreshold.reduce((sum, d) => sum + d.value, 0) / qualityTrendWithThreshold.length)
      : 0;
  const totalIssues = issuesTrendWithThreshold.reduce((sum, d) => sum + d.value, 0);

  const combinedData = qualityTrendWithThreshold.map((q, index) => ({
    date: q.date,
    qualityScore: q.value,
    qualityUpper: q.upper,
    qualityLower: q.lower,
    qualityBaseline: q.baseline,
    qualityAnomaly: q.isAnomaly,
    issues: issuesTrendWithThreshold[index]?.value || 0,
    issuesUpper: issuesTrendWithThreshold[index]?.upper || 0,
    issuesLower: issuesTrendWithThreshold[index]?.lower || 0,
    issuesBaseline: issuesTrendWithThreshold[index]?.baseline || 0,
    issuesAnomaly: issuesTrendWithThreshold[index]?.isAnomaly || false,
  }));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {[7, 14, 30].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-4 py-2 rounded-lg transition-colors ${
                days === d
                  ? 'bg-primary-600 text-white'
                  : 'bg-white text-gray-600 hover:bg-gray-100'
              }`}
            >
              近{d}天
            </button>
          ))}
        </div>
        {(qualityAnomalyCount > 0 || issuesAnomalyCount > 0) && (
          <div className="flex items-center gap-2 px-4 py-2 bg-amber-50 border border-amber-200 rounded-lg">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            <span className="text-sm text-amber-700">
              检测到 {qualityAnomalyCount + issuesAnomalyCount} 个异常点（动态阈值）
            </span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-800">质量评分趋势</h3>
            <div className="flex items-center gap-2">
              {avgScore >= 80 ? (
                <TrendingUp className="w-5 h-5 text-green-500" />
              ) : (
                <TrendingDown className="w-5 h-5 text-red-500" />
              )}
              <span
                className={`font-bold ${
                  avgScore >= 80 ? 'text-green-600' : 'text-red-600'
                }`}
              >
                {avgScore}%
              </span>
            </div>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={combinedData}>
                <defs>
                  <linearGradient id="colorQuality" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0d9488" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#0d9488" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorThresholdBand" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.1} />
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="date" stroke="#9ca3af" fontSize={12} />
                <YAxis domain={[0, 100]} stroke="#9ca3af" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#fff',
                    border: 'none',
                    borderRadius: '8px',
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                  }}
                  formatter={(value: number, name: string) => {
                    if (name === '质量分') return [`${value}%`, name];
                    if (name === '上阈值' || name === '下阈值' || name === '基线') return [`${value}%`, name];
                    return [value, name];
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="qualityUpper"
                  stroke="none"
                  fill="url(#colorThresholdBand)"
                  name="上阈值"
                />
                <Area
                  type="monotone"
                  dataKey="qualityScore"
                  stroke="#0d9488"
                  strokeWidth={2}
                  fill="url(#colorQuality)"
                  name="质量分"
                  dot={(props: Record<string, unknown>) => {
                    const { cx, cy, payload } = props as { cx: number; cy: number; payload: { qualityAnomaly: boolean } };
                    return (
                      <circle
                        key={`dot-${cx}-${cy}`}
                        cx={cx}
                        cy={cy}
                        r={payload.qualityAnomaly ? 6 : 3}
                        fill={payload.qualityAnomaly ? '#ef4444' : '#0d9488'}
                        stroke={payload.qualityAnomaly ? '#ef4444' : '#0d9488'}
                        strokeWidth={payload.qualityAnomaly ? 2 : 0}
                      />
                    );
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="qualityUpper"
                  stroke="#f59e0b"
                  strokeWidth={1}
                  strokeDasharray="4 4"
                  dot={false}
                  name="上阈值"
                />
                <Line
                  type="monotone"
                  dataKey="qualityLower"
                  stroke="#f59e0b"
                  strokeWidth={1}
                  strokeDasharray="4 4"
                  dot={false}
                  name="下阈值"
                />
                <ReferenceLine
                  y={qualityTrendWithThreshold.length > 0 ? qualityTrendWithThreshold[0].baseline : 80}
                  stroke="#94a3b8"
                  strokeDasharray="2 2"
                  strokeWidth={1}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <span className="w-3 h-0.5 bg-amber-400 inline-block border-dashed" style={{ borderTop: '1px dashed #f59e0b' }} />
              动态阈值带
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />
              异常点
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-0.5 bg-gray-400 inline-block" style={{ borderTop: '1px dashed #94a3b8' }} />
              历史基线
            </span>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-800">问题数量趋势</h3>
            <span className="font-bold text-orange-600">共 {totalIssues} 个</span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={combinedData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="date" stroke="#9ca3af" fontSize={12} />
                <YAxis stroke="#9ca3af" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#fff',
                    border: 'none',
                    borderRadius: '8px',
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                  }}
                />
                <Bar
                  dataKey="issues"
                  name="问题数"
                  radius={[4, 4, 0, 0]}
                  fill={(data: Record<string, unknown>) => {
                    const payload = data as { issuesAnomaly: boolean };
                    return payload.issuesAnomaly ? '#ef4444' : '#f59e0b';
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="issuesUpper"
                  stroke="#ef4444"
                  strokeWidth={1}
                  strokeDasharray="4 4"
                  dot={false}
                  name="上阈值"
                />
                <Line
                  type="monotone"
                  dataKey="issuesLower"
                  stroke="#22c55e"
                  strokeWidth={1}
                  strokeDasharray="4 4"
                  dot={false}
                  name="下阈值"
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded bg-amber-400 inline-block" />
              正常
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded bg-red-500 inline-block" />
              超出阈值
            </span>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-800">综合趋势对比（动态阈值）</h3>
          <div className="flex items-center gap-3 text-xs">
            <span className="flex items-center gap-1 px-2 py-1 bg-amber-50 text-amber-700 rounded">
              <AlertTriangle className="w-3 h-3" />
              异常点: {qualityAnomalyCount + issuesAnomalyCount}
            </span>
          </div>
        </div>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={combinedData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="date" stroke="#9ca3af" fontSize={12} />
              <YAxis yAxisId="left" domain={[0, 100]} stroke="#0d9488" fontSize={12} />
              <YAxis yAxisId="right" orientation="right" stroke="#f59e0b" fontSize={12} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#fff',
                  border: 'none',
                  borderRadius: '8px',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                }}
                formatter={(value: number, name: string) => {
                  if (name.includes('质量') || name.includes('阈值') || name.includes('基线')) return [`${value}%`, name];
                  return [value, name];
                }}
              />
              <Legend />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="qualityScore"
                stroke="#0d9488"
                strokeWidth={2}
                dot={(props: Record<string, unknown>) => {
                  const { cx, cy, payload } = props as { cx: number; cy: number; payload: { qualityAnomaly: boolean } };
                  return (
                    <circle
                      key={`qdot-${cx}-${cy}`}
                      cx={cx}
                      cy={cy}
                      r={payload.qualityAnomaly ? 6 : 3}
                      fill={payload.qualityAnomaly ? '#ef4444' : '#0d9488'}
                      stroke={payload.qualityAnomaly ? '#ef4444' : '#0d9488'}
                      strokeWidth={payload.qualityAnomaly ? 2 : 0}
                    />
                  );
                }}
                name="质量分 (%)"
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="qualityUpper"
                stroke="#f59e0b"
                strokeWidth={1}
                strokeDasharray="4 4"
                dot={false}
                name="质量上阈值"
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="qualityLower"
                stroke="#f59e0b"
                strokeWidth={1}
                strokeDasharray="4 4"
                dot={false}
                name="质量下阈值"
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="issues"
                stroke="#f59e0b"
                strokeWidth={2}
                dot={(props: Record<string, unknown>) => {
                  const { cx, cy, payload } = props as { cx: number; cy: number; payload: { issuesAnomaly: boolean } };
                  return (
                    <circle
                      key={`idot-${cx}-${cy}`}
                      cx={cx}
                      cy={cy}
                      r={payload.issuesAnomaly ? 6 : 3}
                      fill={payload.issuesAnomaly ? '#ef4444' : '#f59e0b'}
                      stroke={payload.issuesAnomaly ? '#ef4444' : '#f59e0b'}
                      strokeWidth={payload.issuesAnomaly ? 2 : 0}
                    />
                  );
                }}
                name="问题数"
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="issuesUpper"
                stroke="#ef4444"
                strokeWidth={1}
                strokeDasharray="4 4"
                dot={false}
                name="问题上阈值"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

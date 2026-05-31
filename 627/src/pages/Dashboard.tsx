import { useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { FileCheck, Clock, AlertTriangle, TrendingUp, Play, CheckCircle, XCircle } from 'lucide-react';
import { useAppStore } from '@/store/appStore';

export default function Dashboard() {
  const { overviewStats, qualityTrend, executions, fetchAll } = useAppStore();

  useEffect(() => {
    void fetchAll();
  }, [fetchAll]);

  const stats = [
    { label: '总规则数', value: overviewStats?.totalRules || 0, icon: FileCheck, color: 'from-blue-500 to-blue-600' },
    { label: '总任务数', value: overviewStats?.totalTasks || 0, icon: Clock, color: 'from-purple-500 to-purple-600' },
    { label: '待处理问题', value: overviewStats?.openIssues || 0, icon: AlertTriangle, color: 'from-orange-500 to-orange-600' },
    { label: '平均质量分', value: `${overviewStats?.avgQualityScore || 0}%`, icon: TrendingUp, color: 'from-green-500 to-green-600' },
  ];

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Play className="w-5 h-5 text-blue-500" />;
    }
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <div
              key={index}
              className="bg-white rounded-xl shadow-sm p-6 hover:shadow-md transition-shadow duration-300"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-500 text-sm">{stat.label}</p>
                  <p className="text-3xl font-bold text-gray-800 mt-1">{stat.value}</p>
                </div>
                <div className={`bg-gradient-to-br ${stat.color} p-3 rounded-xl`}>
                  <Icon className="w-6 h-6 text-white" />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">质量评分趋势</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={qualityTrend}>
                <defs>
                  <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0d9488" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#0d9488" stopOpacity={0} />
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
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="#0d9488"
                  strokeWidth={2}
                  fill="url(#colorScore)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">最近执行</h3>
          <div className="space-y-3">
            {executions.slice(0, 5).map((execution) => (
              <div
                key={execution.id}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <div className="flex items-center gap-3">
                  {getStatusIcon(execution.status)}
                  <div>
                    <p className="font-medium text-gray-800 text-sm">{execution.taskName}</p>
                    <p className="text-xs text-gray-500">
                      {new Date(execution.startTime).toLocaleString()}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-semibold text-gray-800">{execution.qualityScore}%</p>
                  <p className="text-xs text-gray-500">
                    {execution.failedRecords > 0 ? `${execution.failedRecords} 个问题` : '无问题'}
                  </p>
                </div>
              </div>
            ))}
            {executions.length === 0 && (
              <p className="text-gray-500 text-center py-4">暂无执行记录</p>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">执行成功率</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={qualityTrend}>
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
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={{ fill: '#10b981' }}
                  name="质量分"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">快速统计</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-green-50 rounded-lg">
              <p className="text-green-600 text-sm font-medium">成功执行</p>
              <p className="text-2xl font-bold text-green-700 mt-1">
                {executions.filter((e) => e.status === 'success').length}
              </p>
            </div>
            <div className="p-4 bg-red-50 rounded-lg">
              <p className="text-red-600 text-sm font-medium">失败执行</p>
              <p className="text-2xl font-bold text-red-700 mt-1">
                {executions.filter((e) => e.status === 'failed').length}
              </p>
            </div>
            <div className="p-4 bg-blue-50 rounded-lg">
              <p className="text-blue-600 text-sm font-medium">活跃规则</p>
              <p className="text-2xl font-bold text-blue-700 mt-1">
                {overviewStats?.activeRules || 0}
              </p>
            </div>
            <div className="p-4 bg-purple-50 rounded-lg">
              <p className="text-purple-600 text-sm font-medium">总执行次数</p>
              <p className="text-2xl font-bold text-purple-700 mt-1">
                {overviewStats?.totalExecutions || 0}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

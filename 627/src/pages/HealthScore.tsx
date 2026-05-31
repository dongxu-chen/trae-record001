import { useEffect } from 'react';
import { useAppStore } from '@/store/appStore';
import { Activity, Award, TrendingUp, Shield } from 'lucide-react';

const gradeColors: Record<string, string> = {
  A: 'text-green-500',
  B: 'text-blue-500',
  C: 'text-yellow-500',
  D: 'text-orange-500',
  F: 'text-red-500',
};

const gradeBgColors: Record<string, string> = {
  A: 'from-green-400 to-green-600',
  B: 'from-blue-400 to-blue-600',
  C: 'from-yellow-400 to-yellow-600',
  D: 'from-orange-400 to-orange-600',
  F: 'from-red-400 to-red-600',
};

const dimensionLabels: Record<string, string> = {
  completeness: '完整性',
  uniqueness: '唯一性',
  validity: '有效性',
  consistency: '一致性',
};

const dimensionIcons: Record<string, typeof Activity> = {
  completeness: Activity,
  uniqueness: Shield,
  validity: TrendingUp,
  consistency: Award,
};

export default function HealthScorePage() {
  const { healthScore, fetchHealthScore } = useAppStore();

  useEffect(() => {
    void fetchHealthScore();
    const interval = setInterval(() => void fetchHealthScore(), 30000);
    return () => clearInterval(interval);
  }, [fetchHealthScore]);

  if (!healthScore) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">加载健康评分中...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl shadow-sm p-8 flex flex-col items-center justify-center">
          <p className="text-gray-500 text-sm mb-4">综合健康评分</p>
          <div className={`relative w-40 h-40 rounded-full bg-gradient-to-br ${gradeBgColors[healthScore.grade]} flex items-center justify-center shadow-lg`}>
            <div className="w-32 h-32 rounded-full bg-white flex flex-col items-center justify-center">
              <span className={`text-5xl font-bold ${gradeColors[healthScore.grade]}`}>
                {healthScore.grade}
              </span>
              <span className="text-gray-500 text-sm mt-1">{healthScore.overall}分</span>
            </div>
          </div>
          <p className="mt-4 text-gray-600 text-sm">
            基于 {healthScore.ruleScores.length} 条规则的综合评估
          </p>
          <p className="text-xs text-gray-400 mt-1">
            更新于 {new Date(healthScore.timestamp).toLocaleString()}
          </p>
        </div>

        <div className="lg:col-span-2 grid grid-cols-2 gap-4">
          {(Object.entries(healthScore.dimensionScores) as [string, number][]).map(([key, value]) => {
            const Icon = dimensionIcons[key] ?? Activity;
            const percentage = Math.round(value);
            const color = percentage >= 90 ? 'text-green-500' : percentage >= 70 ? 'text-yellow-500' : 'text-red-500';
            const bgColor = percentage >= 90 ? 'bg-green-50' : percentage >= 70 ? 'bg-yellow-50' : 'bg-red-50';
            return (
              <div key={key} className={`bg-white rounded-xl shadow-sm p-6 ${bgColor} border border-gray-100`}>
                <div className="flex items-center gap-3 mb-3">
                  <Icon className={`w-5 h-5 ${color}`} />
                  <span className="font-semibold text-gray-800">{dimensionLabels[key]}</span>
                </div>
                <div className="flex items-end gap-2">
                  <span className={`text-3xl font-bold ${color}`}>{percentage}</span>
                  <span className="text-gray-400 text-sm mb-1">%</span>
                </div>
                <div className="mt-3 w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all duration-500 ${
                      percentage >= 90 ? 'bg-green-500' : percentage >= 70 ? 'bg-yellow-500' : 'bg-red-500'
                    }`}
                    style={{ width: `${percentage}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">各规则评分详情</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">规则名称</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">类型</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">表.列</th>
                <th className="text-center py-3 px-4 text-sm font-medium text-gray-500">总记录</th>
                <th className="text-center py-3 px-4 text-sm font-medium text-gray-500">失败记录</th>
                <th className="text-center py-3 px-4 text-sm font-medium text-gray-500">评分</th>
                <th className="text-center py-3 px-4 text-sm font-medium text-gray-500">权重</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">状态</th>
              </tr>
            </thead>
            <tbody>
              {healthScore.ruleScores.map((rs) => {
                const scoreColor = rs.score >= 90 ? 'text-green-600' : rs.score >= 70 ? 'text-yellow-600' : 'text-red-600';
                return (
                  <tr key={rs.ruleId} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-3 px-4 text-sm font-medium text-gray-800">{rs.ruleName}</td>
                    <td className="py-3 px-4 text-sm text-gray-600">{rs.ruleType}</td>
                    <td className="py-3 px-4 text-sm text-gray-600">{rs.tableName}.{rs.columnName}</td>
                    <td className="py-3 px-4 text-sm text-center text-gray-600">{rs.totalRecords}</td>
                    <td className="py-3 px-4 text-sm text-center text-gray-600">{rs.failedRecords}</td>
                    <td className={`py-3 px-4 text-sm text-center font-bold ${scoreColor}`}>{rs.score}%</td>
                    <td className="py-3 px-4 text-sm text-center text-gray-600">x{rs.weight}</td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-gray-200 rounded-full h-1.5">
                          <div
                            className={`h-1.5 rounded-full ${rs.score >= 90 ? 'bg-green-500' : rs.score >= 70 ? 'bg-yellow-500' : 'bg-red-500'}`}
                            style={{ width: `${Math.min(rs.score, 100)}%` }}
                          />
                        </div>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

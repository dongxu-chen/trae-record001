import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const CommitQuality = ({ data }) => {
  const metadata = data?.metadata || {};
  const items = data?.items || [];
  const issuesByType = metadata.issues_by_type || {};

  const getStatusColor = (status) => {
    switch (status) {
      case 'pass': return 'text-green-600';
      case 'fail': return 'text-red-600';
      case 'warning': return 'text-yellow-600';
      default: return 'text-gray-600';
    }
  };

  const getStatusBg = (status) => {
    switch (status) {
      case 'pass': return 'bg-green-100 border-green-200';
      case 'fail': return 'bg-red-100 border-red-200';
      case 'warning': return 'bg-yellow-100 border-yellow-200';
      default: return 'bg-gray-100 border-gray-200';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'pass': return '✓';
      case 'fail': return '✗';
      case 'warning': return '⚠';
      default: return 'ℹ';
    }
  };

  const issueTypeNames = {
    too_short: '信息过短',
    too_long: '信息过长',
    missing_prefix: '缺少前缀',
    forbidden_word: '禁用词汇',
    not_imperative: '非祈使语气'
  };

  const COLORS = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6', '#8b5cf6'];

  const chartData = Object.entries(issuesByType).map(([type, examples]) => ({
    name: issueTypeNames[type] || type,
    count: examples.length,
    examples: examples.slice(0, 3)
  }));

  const pieData = [
    { name: '规范提交', value: metadata.good_commits_count || 0, color: '#22c55e' },
    { name: '存在问题', value: Object.keys(issuesByType).length, color: '#ef4444' }
  ];

  const getComplianceColor = (rate) => {
    if (rate >= 90) return 'text-green-600';
    if (rate >= 70) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-800">
        📝 提交质量分析
      </h2>

      <div className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-xl p-6 border border-indigo-100">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-3xl font-bold text-indigo-600">
              {metadata.total_commits || 0}
            </div>
            <div className="text-sm text-gray-600 mt-1">总提交数</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-green-600">
              {metadata.good_commits_count || 0}
            </div>
            <div className="text-sm text-gray-600 mt-1">规范提交</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-red-600">
              {metadata.total_issues || 0}
            </div>
            <div className="text-sm text-gray-600 mt-1">问题数量</div>
          </div>
          <div className="text-center">
            <div className={`text-3xl font-bold ${getComplianceColor(metadata.compliance_rate)}`}>
              {metadata.compliance_rate || 0}%
            </div>
            <div className="text-sm text-gray-600 mt-1">规范遵守率</div>
          </div>
        </div>
      </div>

      {chartData.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">问题类型分布</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">质量概览</h3>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      <div className="space-y-3">
        {items.map((item, index) => (
          <div
            key={index}
            className={`p-4 rounded-lg border ${getStatusBg(item.status)}`}
          >
            <div className="flex items-start gap-3">
              <span className={`text-xl ${getStatusColor(item.status)}`}>
                {getStatusIcon(item.status)}
              </span>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className={`font-semibold ${getStatusColor(item.status)}`}>
                    [{item.severity?.toUpperCase()}]
                  </span>
                  <h3 className="font-medium text-gray-800">{item.name}</h3>
                </div>
                <p className="text-gray-600 mt-1">{item.message}</p>
                
                {item.details?.examples && (
                  <div className="mt-3 space-y-2">
                    <div className="text-sm font-medium text-gray-700">示例：</div>
                    {item.details.examples.map((ex, i) => (
                      <div key={i} className="bg-white bg-opacity-70 rounded p-2 text-sm">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-gray-500">{ex.hash}</span>
                          <span className="text-gray-600">-</span>
                          <span className="text-gray-700 truncate">{ex.message}</span>
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          {ex.author} · {ex.date} · {ex.detail}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {item.suggestion && (
                  <div className="mt-2 p-2 bg-white bg-opacity-50 rounded text-sm text-gray-700">
                    💡 <span className="font-medium">建议：</span>{item.suggestion}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {metadata.good_commits && metadata.good_commits.length > 0 && (
        <div className="p-6 bg-green-50 rounded-xl border border-green-200">
          <h3 className="text-lg font-semibold text-green-800 mb-4">🌟 优秀提交示例</h3>
          <div className="space-y-2">
            {metadata.good_commits.slice(0, 5).map((commit, index) => (
              <div key={index} className="flex items-center gap-3 p-3 bg-white rounded-lg">
                <span className="text-green-500">✓</span>
                <span className="font-mono text-sm text-gray-500">{commit.hash}</span>
                <span className="text-gray-700 flex-1">{commit.message}</span>
                <span className="text-sm text-gray-500">{commit.author}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default CommitQuality;

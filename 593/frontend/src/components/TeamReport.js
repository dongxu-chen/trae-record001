import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts';

const TeamReport = ({ days = 30 }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedDays, setSelectedDays] = useState(days);

  useEffect(() => {
    fetchTeamReport();
  }, [selectedDays]);

  const fetchTeamReport = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/team-report?days=${selectedDays}`);
      const result = await response.json();
      setData(result);
    } catch (error) {
      console.error('Failed to fetch team report:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-600">加载团队数据中...</div>
      </div>
    );
  }

  const metadata = data?.metadata || {};
  const items = data?.items || [];
  const overall = metadata.overall || {};
  const authorStats = metadata.author_stats || {};

  const COLORS = ['#6366f1', '#22c55e', '#f97316', '#eab308', '#8b5cf6', '#ec4899'];

  const authorChartData = Object.entries(authorStats).map(([name, stats], index) => ({
    name: name.split(' ')[0],
    commits: stats.total_commits || 0,
    compliance: stats.compliance_rate || 0,
    additions: stats.additions || 0,
    color: COLORS[index % COLORS.length]
  }));

  const issueDistribution = Object.entries(overall.issue_distribution || {}).map(([type, count]) => ({
    name: {
      too_short: '信息过短',
      too_long: '信息过长',
      missing_prefix: '缺少前缀',
      forbidden_word: '禁用词汇',
      not_imperative: '非祈使语气'
    }[type] || type,
    count
  }));

  const getComplianceColor = (rate) => {
    if (rate >= 90) return 'text-green-600 bg-green-100';
    if (rate >= 70) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-800">
          👥 团队简报
        </h2>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600">统计周期：</span>
          <select
            value={selectedDays}
            onChange={(e) => setSelectedDays(Number(e.target.value))}
            className="px-3 py-1 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value={7}>最近7天</option>
            <option value={14}>最近14天</option>
            <option value={30}>最近30天</option>
            <option value={90}>最近90天</option>
          </select>
        </div>
      </div>

      <div className="bg-gradient-to-r from-blue-50 to-cyan-50 rounded-xl p-6 border border-blue-100">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div className="text-center">
            <div className="text-3xl font-bold text-blue-600">
              {metadata.total_commits || 0}
            </div>
            <div className="text-sm text-gray-600 mt-1">总提交数</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-purple-600">
              {metadata.total_authors || 0}
            </div>
            <div className="text-sm text-gray-600 mt-1">活跃成员</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-green-600">
              {overall.avg_compliance_rate || 0}%
            </div>
            <div className="text-sm text-gray-600 mt-1">平均规范遵守率</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-orange-600">
              {overall.avg_commits_per_member || 0}
            </div>
            <div className="text-sm text-gray-600 mt-1">人均提交</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-cyan-600">
              +{overall.total_additions || 0}
            </div>
            <div className="text-sm text-gray-600 mt-1">新增代码行</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">成员提交排行</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={authorChartData.sort((a, b) => b.commits - a.commits)} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" />
              <YAxis dataKey="name" type="category" width={80} />
              <Tooltip />
              <Bar dataKey="commits" fill="#6366f1" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">规范遵守率对比</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={authorChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis domain={[0, 100]} />
              <Tooltip />
              <Bar dataKey="compliance" fill="#22c55e" radius={[4, 4, 0, 0]} name="规范遵守率(%)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {issueDistribution.length > 0 && (
        <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">团队问题分布</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={issueDistribution}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#f97316" radius={[4, 4, 0, 0]} name="问题数" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="space-y-4">
        {items.map((item, index) => (
          <div
            key={index}
            className="p-4 rounded-lg border border-gray-200 bg-white"
          >
            <h3 className="font-semibold text-gray-800 mb-3">{item.name}</h3>
            <p className="text-gray-600 mb-3">{item.message}</p>
            
            {item.details?.members && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {item.details.members.map((member, i) => (
                  <div key={i} className="p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-gray-800">{member.name}</span>
                      {member.compliance_rate !== undefined && (
                        <span className={`px-2 py-1 rounded-full text-sm font-medium ${getComplianceColor(member.compliance_rate)}`}>
                          {member.compliance_rate}%
                        </span>
                      )}
                    </div>
                    <div className="mt-2 text-sm text-gray-600">
                      提交: {member.commits} 次
                      {member.inactive_days && ` · 不活跃: ${member.inactive_days} 天`}
                    </div>
                    {member.top_issues && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {member.top_issues.map((issue, j) => (
                          <span key={j} className="px-2 py-0.5 bg-red-100 text-red-600 rounded text-xs">
                            {{
                              too_short: '信息过短',
                              missing_prefix: '缺少前缀',
                              forbidden_word: '禁用词汇',
                              not_imperative: '语气问题'
                            }[issue.type] || issue.type}: {issue.count}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {item.suggestion && (
              <div className="mt-3 p-2 bg-blue-50 rounded text-sm text-blue-700">
                💡 {item.suggestion}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">📋 成员详细统计</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-2 px-3 font-medium text-gray-600">成员</th>
                <th className="text-center py-2 px-3 font-medium text-gray-600">提交数</th>
                <th className="text-center py-2 px-3 font-medium text-gray-600">规范遵守率</th>
                <th className="text-center py-2 px-3 font-medium text-gray-600">新增代码</th>
                <th className="text-center py-2 px-3 font-medium text-gray-600">删除代码</th>
                <th className="text-center py-2 px-3 font-medium text-gray-600">最后提交</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(authorStats).map(([name, stats], index) => (
                <tr key={index} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-2 px-3 font-medium text-gray-800">{name}</td>
                  <td className="text-center py-2 px-3 text-gray-600">{stats.total_commits}</td>
                  <td className="text-center py-2 px-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getComplianceColor(stats.compliance_rate)}`}>
                      {stats.compliance_rate}%
                    </span>
                  </td>
                  <td className="text-center py-2 px-3 text-green-600">+{stats.additions}</td>
                  <td className="text-center py-2 px-3 text-red-600">-{stats.deletions}</td>
                  <td className="text-center py-2 px-3 text-gray-500">{stats.last_commit}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default TeamReport;

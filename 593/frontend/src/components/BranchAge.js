import React, { useState, useEffect } from 'react';

const BranchAge = ({ data, sourceBranch, targetBranch, onCheck }) => {
  const [loading, setLoading] = useState(false);
  const [allBranchesData, setAllBranchesData] = useState(null);
  const [showAllBranches, setShowAllBranches] = useState(false);

  const metadata = data?.metadata || {};
  const items = data?.items || [];

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

  const handleCheckAllBranches = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/check/branch-age/all?target=${targetBranch}`);
      const result = await response.json();
      setAllBranchesData(result);
      setShowAllBranches(true);
    } catch (error) {
      console.error('Failed to check all branches:', error);
    } finally {
      setLoading(false);
    }
  };

  const getAgeLevel = (days) => {
    if (days >= 90) return { text: '严重过期', color: 'text-red-600', icon: '🔴' };
    if (days >= 60) return { text: '过期', color: 'text-orange-600', icon: '🟠' };
    if (days >= 30) return { text: '预警', color: 'text-yellow-600', icon: '🟡' };
    return { text: '正常', color: 'text-green-600', icon: '🟢' };
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-800">
          ⏰ 分支年龄检查
        </h2>
        <button
          onClick={handleCheckAllBranches}
          disabled={loading}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 transition-colors"
        >
          {loading ? '检查中...' : '检查全部分支'}
        </button>
      </div>

      {metadata.age_days !== undefined && (
        <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl p-6 border border-blue-100">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className={`text-3xl font-bold ${getAgeLevel(metadata.age_days).color}`}>
                {metadata.age_days} 天
              </div>
              <div className="text-sm text-gray-600 mt-1">分支年龄</div>
            </div>
            <div className="text-center">
              <div className={`text-3xl font-bold ${getAgeLevel(metadata.inactive_days).color}`}>
                {metadata.inactive_days} 天
              </div>
              <div className="text-sm text-gray-600 mt-1">无活动天数</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-purple-600">
                {metadata.commit_count || 0}
              </div>
              <div className="text-sm text-gray-600 mt-1">提交次数</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold mt-2">
                {getAgeLevel(metadata.age_days).icon}
              </div>
              <div className={`text-sm font-medium ${getAgeLevel(metadata.age_days).color}`}>
                {getAgeLevel(metadata.age_days).text}
              </div>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 pt-4 border-t border-blue-200">
            <div className="text-sm text-gray-600">
              <span className="font-medium">创建时间：</span>
              {metadata.creation_date ? new Date(metadata.creation_date).toLocaleDateString('zh-CN') : '-'}
            </div>
            <div className="text-sm text-gray-600">
              <span className="font-medium">最后活动：</span>
              {metadata.last_activity_date ? new Date(metadata.last_activity_date).toLocaleDateString('zh-CN') : '-'}
            </div>
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
                {item.suggestion && (
                  <div className="mt-2 p-2 bg-white bg-opacity-50 rounded text-sm text-gray-700">
                    💡 <span className="font-medium">建议：</span>{item.suggestion}
                  </div>
                )}
                {item.documentation_url && (
                  <a
                    href={item.documentation_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-block mt-2 text-sm text-blue-600 hover:underline"
                  >
                    📚 查看文档
                  </a>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {showAllBranches && allBranchesData && (
        <div className="mt-8 p-6 bg-gray-50 rounded-xl border border-gray-200">
          <h3 className="text-lg font-bold text-gray-800 mb-4">📊 全部分支状态</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-green-100 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-green-600">
                {allBranchesData.metadata?.healthy_count || 0}
              </div>
              <div className="text-sm text-green-700">状态良好</div>
            </div>
            <div className="bg-yellow-100 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-yellow-600">
                {allBranchesData.metadata?.warning_count || 0}
              </div>
              <div className="text-sm text-yellow-700">需要关注</div>
            </div>
            <div className="bg-red-100 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-red-600">
                {allBranchesData.metadata?.stale_count || 0}
              </div>
              <div className="text-sm text-red-700">已过期</div>
            </div>
          </div>

          {allBranchesData.items?.map((item, index) => (
            <div key={index} className={`p-4 rounded-lg border mb-3 ${getStatusBg(item.status)}`}>
              <div className="flex items-center justify-between">
                <div>
                  <span className={`mr-2 ${getStatusColor(item.status)}`}>
                    {getStatusIcon(item.status)}
                  </span>
                  <span className="font-medium">{item.name}</span>
                </div>
              </div>
              <p className="text-gray-600 mt-1 ml-6">{item.message}</p>
              {item.details?.branches && (
                <div className="mt-2 ml-6 flex flex-wrap gap-2">
                  {item.details.branches.map((branch, i) => (
                    <span key={i} className="px-2 py-1 bg-white rounded text-sm text-gray-600">
                      🌿 {branch}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}

          <button
            onClick={() => setShowAllBranches(false)}
            className="mt-4 text-gray-600 hover:text-gray-800"
          >
            收起
          </button>
        </div>
      )}
    </div>
  );
};

export default BranchAge;

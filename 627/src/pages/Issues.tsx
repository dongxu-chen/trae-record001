import { useState, useEffect } from 'react';
import { AlertTriangle, User, Clock, CheckCircle, ArrowRight, ShieldAlert } from 'lucide-react';
import { useAppStore } from '@/store/appStore';
import { issuesApi, getCurrentUser } from '@/lib/api';
import type { QualityIssue } from '../../shared/types.js';

const statusConfig = {
  open: { label: '待处理', color: 'bg-red-100 text-red-700 border-red-200' },
  in_progress: { label: '处理中', color: 'bg-yellow-100 text-yellow-700 border-yellow-200' },
  resolved: { label: '已解决', color: 'bg-green-100 text-green-700 border-green-200' },
};

const priorityConfig = {
  low: { label: '低', color: 'bg-gray-100 text-gray-600' },
  medium: { label: '中', color: 'bg-orange-100 text-orange-600' },
  high: { label: '高', color: 'bg-red-100 text-red-600' },
};

export default function Issues() {
  const { issues, fetchIssues } = useAppStore();
  const [activeTab, setActiveTab] = useState<'all' | 'open' | 'in_progress' | 'resolved'>('all');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetchIssues(activeTab === 'all' ? undefined : activeTab);
  }, [fetchIssues, activeTab]);

  const currentUser = getCurrentUser();
  const isAdmin = currentUser.role === 'admin';

  const canTakeIssue = (issue: QualityIssue) => {
    if (isAdmin) return true;
    if (issue.status === 'open') return !issue.assignee || issue.assignee === currentUser.name;
    return false;
  };

  const canResolveIssue = (issue: QualityIssue) => {
    if (isAdmin) return true;
    return issue.assignee === currentUser.name;
  };

  const canAssignIssue = (issue: QualityIssue) => {
    if (isAdmin) return true;
    if (issue.status === 'open') return !issue.assignee || issue.assignee === currentUser.name;
    return issue.assignee === currentUser.name;
  };

  const handleStatusChange = async (issue: QualityIssue, newStatus: QualityIssue['status']) => {
    setError(null);
    try {
      await issuesApi.update(issue.id, { status: newStatus });
      await fetchIssues(activeTab === 'all' ? undefined : activeTab);
    } catch (err) {
      setError(err instanceof Error ? err.message : '操作失败');
      setTimeout(() => setError(null), 3000);
    }
  };

  const handleAssign = async (issue: QualityIssue, assigneeName: string) => {
    setError(null);
    try {
      await issuesApi.update(issue.id, { assignee: assigneeName, status: 'in_progress' });
      await fetchIssues(activeTab === 'all' ? undefined : activeTab);
    } catch (err) {
      setError(err instanceof Error ? err.message : '操作失败');
      setTimeout(() => setError(null), 3000);
    }
  };

  const filteredIssues =
    activeTab === 'all'
      ? issues
      : issues.filter((issue) => issue.status === activeTab);

  const tabs = [
    { key: 'all', label: '全部', count: issues.length },
    { key: 'open', label: '待处理', count: issues.filter((i) => i.status === 'open').length },
    {
      key: 'in_progress',
      label: '处理中',
      count: issues.filter((i) => i.status === 'in_progress').length,
    },
    {
      key: 'resolved',
      label: '已解决',
      count: issues.filter((i) => i.status === 'resolved').length,
    },
  ];

  return (
    <div className="space-y-6">
      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg flex items-center gap-2">
          <ShieldAlert className="w-5 h-5" />
          {error}
        </div>
      )}

      <div className="flex items-center gap-4 bg-white rounded-xl shadow-sm p-2">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as typeof activeTab)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
              activeTab === tab.key
                ? 'bg-primary-600 text-white'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            {tab.label}
            <span
              className={`px-2 py-0.5 text-xs rounded-full ${
                activeTab === tab.key ? 'bg-white/20' : 'bg-gray-200'
              }`}
            >
              {tab.count}
            </span>
          </button>
        ))}
      </div>

      <div className="grid gap-4">
        {filteredIssues.map((issue) => (
          <div
            key={issue.id}
            className="bg-white rounded-xl shadow-sm p-6 hover:shadow-md transition-shadow"
          >
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-4">
                <div
                  className={`p-2 rounded-lg ${
                    issue.priority === 'high'
                      ? 'bg-red-100'
                      : issue.priority === 'medium'
                      ? 'bg-orange-100'
                      : 'bg-gray-100'
                  }`}
                >
                  <AlertTriangle
                    className={`w-5 h-5 ${
                      issue.priority === 'high'
                        ? 'text-red-600'
                        : issue.priority === 'medium'
                        ? 'text-orange-600'
                        : 'text-gray-600'
                    }`}
                  />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h4 className="font-semibold text-gray-900">{issue.ruleName}</h4>
                    <span className={`px-2 py-0.5 text-xs rounded-full ${statusConfig[issue.status].color}`}>
                      {statusConfig[issue.status].label}
                    </span>
                    <span className={`px-2 py-0.5 text-xs rounded-full ${priorityConfig[issue.priority].color}`}>
                      {priorityConfig[issue.priority].label}优先级
                    </span>
                  </div>
                  <p className="text-gray-600 mt-2">{issue.description}</p>
                  <div className="flex items-center gap-4 mt-3 text-sm text-gray-500">
                    <span>
                      {issue.tableName}.{issue.columnName}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-4 h-4" />
                      {new Date(issue.createdAt).toLocaleString()}
                    </span>
                    {issue.assignee && (
                      <span className="flex items-center gap-1">
                        <User className="w-4 h-4" />
                        {issue.assignee}
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {issue.status === 'open' && canAssignIssue(issue) && (
                  <button
                    onClick={() => handleAssign(issue, currentUser.name)}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm bg-yellow-100 text-yellow-700 rounded-lg hover:bg-yellow-200 transition-colors"
                  >
                    认领处理
                    <ArrowRight className="w-4 h-4" />
                  </button>
                )}
                {issue.status === 'in_progress' && canResolveIssue(issue) && (
                  <button
                    onClick={() => handleStatusChange(issue, 'resolved')}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors"
                  >
                    <CheckCircle className="w-4 h-4" />
                    标记解决
                  </button>
                )}
                {!isAdmin && issue.status === 'in_progress' && !canResolveIssue(issue) && (
                  <span className="text-xs text-gray-400 flex items-center gap-1">
                    <ShieldAlert className="w-3 h-3" />
                    仅{issue.assignee}可关闭
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
        {filteredIssues.length === 0 && (
          <div className="bg-white rounded-xl shadow-sm p-12 text-center text-gray-500">
            <CheckCircle className="w-12 h-12 mx-auto mb-4 text-green-300" />
            <p>暂无问题数据</p>
          </div>
        )}
      </div>
    </div>
  );
}

import { useState, useEffect } from 'react';
import { Plus, Play, Clock, CheckCircle, XCircle, Calendar } from 'lucide-react';
import { useAppStore } from '@/store/appStore';
import { tasksApi, rulesApi } from '@/lib/api';
import type { ScheduledTask } from '../../shared/types.js';

export default function Tasks() {
  const { tasks, executions, rules, fetchTasks, fetchExecutions, fetchRules } = useAppStore();
  const [showModal, setShowModal] = useState(false);
  const [running, setRunning] = useState<string | null>(null);

  const [formData, setFormData] = useState<{
    name: string;
    cronExpression: string;
    ruleIds: string[];
  }>({
    name: '',
    cronExpression: '0 0 * * *',
    ruleIds: [],
  });

  useEffect(() => {
    void fetchTasks();
    void fetchExecutions();
    void fetchRules();
  }, [fetchTasks, fetchExecutions, fetchRules]);

  const handleSubmit = async () => {
    try {
      await tasksApi.create({ ...formData, enabled: true });
      await fetchTasks();
      setShowModal(false);
      setFormData({ name: '', cronExpression: '0 0 * * *', ruleIds: [] });
    } catch (error) {
      console.error('Failed to create task:', error);
    }
  };

  const handleRun = async (task: ScheduledTask) => {
    setRunning(task.id);
    try {
      await tasksApi.run(task.id);
      await fetchExecutions();
    } catch (error) {
      console.error('Failed to run task:', error);
    } finally {
      setRunning(null);
    }
  };

  const toggleRule = (ruleId: string) => {
    setFormData((prev) => ({
      ...prev,
      ruleIds: prev.ruleIds.includes(ruleId)
        ? prev.ruleIds.filter((id) => id !== ruleId)
        : [...prev.ruleIds, ruleId],
    }));
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-800">定时任务列表</h2>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          <Plus className="w-5 h-5" />
          新建任务
        </button>
      </div>

      <div className="grid gap-6">
        {tasks.map((task) => (
          <div
            key={task.id}
            className="bg-white rounded-xl shadow-sm p-6 hover:shadow-md transition-shadow"
          >
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-semibold text-gray-900 text-lg">{task.name}</h3>
                <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                  <span className="flex items-center gap-1">
                    <Clock className="w-4 h-4" />
                    {task.cronExpression}
                  </span>
                  <span className="flex items-center gap-1">
                    <Calendar className="w-4 h-4" />
                    {task.lastRunAt
                      ? `上次执行: ${new Date(task.lastRunAt).toLocaleString()}`
                      : '尚未执行'}
                  </span>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {task.ruleIds.map((ruleId) => {
                    const rule = rules.find((r) => r.id === ruleId);
                    return (
                      <span
                        key={ruleId}
                        className="px-2 py-1 bg-primary-50 text-primary-700 text-xs rounded-full"
                      >
                        {rule?.name || ruleId}
                      </span>
                    );
                  })}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`px-3 py-1 text-sm rounded-full ${
                    task.enabled
                      ? 'bg-green-100 text-green-700'
                      : 'bg-gray-100 text-gray-500'
                  }`}
                >
                  {task.enabled ? '已启用' : '已禁用'}
                </span>
                <button
                  onClick={() => handleRun(task)}
                  disabled={running === task.id}
                  className="p-2 text-primary-600 hover:bg-primary-50 rounded-lg transition-colors disabled:opacity-50"
                  title="立即执行"
                >
                  <Play className={`w-5 h-5 ${running === task.id ? 'animate-pulse' : ''}`} />
                </button>
              </div>
            </div>
          </div>
        ))}

        {tasks.length === 0 && (
          <div className="bg-white rounded-xl shadow-sm p-12 text-center text-gray-500">
            <Clock className="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <p>暂无定时任务</p>
          </div>
        )}
      </div>

      <div className="bg-white rounded-xl shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">执行记录</h3>
        <div className="space-y-3">
          {executions.slice(0, 10).map((execution) => (
            <div
              key={execution.id}
              className="flex items-center justify-between p-4 bg-gray-50 rounded-lg"
            >
              <div className="flex items-center gap-3">
                {execution.status === 'success' ? (
                  <CheckCircle className="w-5 h-5 text-green-500" />
                ) : execution.status === 'failed' ? (
                  <XCircle className="w-5 h-5 text-red-500" />
                ) : (
                  <Clock className="w-5 h-5 text-blue-500 animate-spin" />
                )}
                <div>
                  <p className="font-medium text-gray-800">{execution.taskName}</p>
                  <p className="text-sm text-gray-500">
                    {new Date(execution.startTime).toLocaleString()}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="font-semibold text-gray-800">{execution.qualityScore}%</p>
                <p className="text-sm text-gray-500">
                  {execution.totalRecords} 条记录 · {execution.failedRecords} 个问题
                </p>
              </div>
            </div>
          ))}
          {executions.length === 0 && (
            <p className="text-center text-gray-500 py-8">暂无执行记录</p>
          )}
        </div>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4">
            <div className="p-6 border-b">
              <h3 className="text-lg font-semibold text-gray-900">新建定时任务</h3>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">任务名称</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="输入任务名称"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Cron 表达式
                </label>
                <input
                  type="text"
                  value={formData.cronExpression}
                  onChange={(e) => setFormData({ ...formData, cronExpression: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="0 0 * * *"
                />
                <p className="text-xs text-gray-500 mt-1">例如: 0 0 * * * (每天凌晨执行)</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">选择规则</label>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {rules.map((rule) => (
                    <label
                      key={rule.id}
                      className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100"
                    >
                      <input
                        type="checkbox"
                        checked={formData.ruleIds.includes(rule.id)}
                        onChange={() => toggleRule(rule.id)}
                        className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
                      />
                      <div>
                        <p className="font-medium text-gray-800">{rule.name}</p>
                        <p className="text-xs text-gray-500">{rule.tableName}.{rule.columnName}</p>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 p-6 border-t">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleSubmit}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
              >
                创建
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

import { useEffect } from 'react';
import { BarChart3, CheckCircle, XCircle, Clock } from 'lucide-react';
import { useAppStore } from '@/store/appStore';

export default function Reports() {
  const { executions, fetchExecutions } = useAppStore();

  useEffect(() => {
    void fetchExecutions();
  }, [fetchExecutions]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Clock className="w-5 h-5 text-blue-500" />;
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600 bg-green-100';
    if (score >= 70) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl shadow-sm p-6">
          <p className="text-gray-500 text-sm">总报告数</p>
          <p className="text-3xl font-bold text-gray-800 mt-1">{executions.length}</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-6">
          <p className="text-gray-500 text-sm">成功执行</p>
          <p className="text-3xl font-bold text-green-600 mt-1">
            {executions.filter((e) => e.status === 'success').length}
          </p>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-6">
          <p className="text-gray-500 text-sm">平均质量分</p>
          <p className="text-3xl font-bold text-primary-600 mt-1">
            {executions.length > 0
              ? Math.round(executions.reduce((sum, e) => sum + e.qualityScore, 0) / executions.length)
              : 0}
            %
          </p>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <div className="p-6 border-b">
          <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
            <BarChart3 className="w-5 h-5" />
            质量报告列表
          </h3>
        </div>
        <div className="divide-y">
          {executions.map((execution) => (
            <div key={execution.id} className="p-6 hover:bg-gray-50 transition-colors">
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4">
                  {getStatusIcon(execution.status)}
                  <div>
                    <h4 className="font-semibold text-gray-900">{execution.taskName}</h4>
                    <p className="text-sm text-gray-500 mt-1">
                      执行时间: {new Date(execution.startTime).toLocaleString()}
                    </p>
                    {execution.endTime && (
                      <p className="text-sm text-gray-500">
                        耗时:{' '}
                        {Math.round(
                          (new Date(execution.endTime).getTime() -
                            new Date(execution.startTime).getTime()) /
                            1000
                        )}{' '}
                        秒
                      </p>
                    )}
                  </div>
                </div>
                <div className="text-right">
                  <span
                    className={`inline-block px-4 py-2 rounded-full text-lg font-bold ${getScoreColor(
                      execution.qualityScore
                    )}`}
                  >
                    {execution.qualityScore}%
                  </span>
                  <div className="mt-2 text-sm text-gray-500">
                    <p>共 {execution.totalRecords} 条记录</p>
                    <p className={execution.failedRecords > 0 ? 'text-red-500' : ''}>
                      {execution.failedRecords} 条问题
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ))}
          {executions.length === 0 && (
            <div className="p-12 text-center text-gray-500">
              <BarChart3 className="w-12 h-12 mx-auto mb-4 text-gray-300" />
              <p>暂无报告数据</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

import { useState } from 'react'
import {
  ArrowPathIcon,
  PlayIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline'
import { useMigrationPlan, useMigrationTasks, useExecuteMigrations } from '../hooks/useBalancer'
import { format } from 'date-fns'

export function Migrations() {
  const { data: plan, isLoading: planLoading, refetch: refetchPlan } = useMigrationPlan()
  const { data: tasks, isLoading: tasksLoading } = useMigrationTasks()
  const { mutate: executeMigrations, isPending: isExecuting } = useExecuteMigrations()
  const [showConfirmModal, setShowConfirmModal] = useState(false)

  const handleExecute = () => {
    executeMigrations(undefined, {
      onSuccess: () => {
        setShowConfirmModal(false)
        refetchPlan()
      },
    })
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">迁移任务</h2>
        {plan && plan.length > 0 && (
          <button
            className="btn-primary flex items-center space-x-2"
            onClick={() => setShowConfirmModal(true)}
            disabled={isExecuting}
          >
            <PlayIcon className="w-4 h-4" />
            <span>{isExecuting ? '执行中...' : '执行迁移计划'}</span>
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-white">待执行迁移计划</h3>
            <span className={`badge ${plan && plan.length > 0 ? 'bg-es-yellow/20 text-es-yellow' : 'bg-es-green/20 text-es-green'}`}>
              {plan?.length || 0} 个待执行
            </span>
          </div>

          {!planLoading && plan && plan.length > 0 ? (
            <div className="space-y-4 max-h-96 overflow-y-auto">
              {plan.map((item, index) => (
                <div
                  key={index}
                  className="p-4 bg-es-dark-900 rounded-lg border border-es-dark-700 hover:border-es-yellow/50 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="p-2 bg-es-yellow/20 rounded-lg">
                        <ArrowPathIcon className="w-4 h-4 text-es-yellow" />
                      </div>
                      <div>
                        <p className="font-mono text-sm text-es-blue">{item.index}</p>
                        <p className="text-xs text-es-dark-400">分片 {item.shard}</p>
                      </div>
                    </div>
                  </div>
                  <div className="mt-4 flex items-center text-sm">
                    <div className="flex items-center space-x-2 text-es-dark-300">
                      <span className="px-2 py-1 bg-es-dark-800 rounded">{item.from_node}</span>
                      <ArrowPathIcon className="w-4 h-4 text-es-dark-400" />
                      <span className="px-2 py-1 bg-es-dark-800 rounded">{item.to_node}</span>
                    </div>
                  </div>
                  <p className="text-xs text-es-dark-400 mt-3">{item.reason}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="h-48 flex flex-col items-center justify-center text-es-dark-400">
              <CheckCircleIcon className="w-12 h-12 mb-3 text-es-green" />
              <p>暂无待执行的迁移计划</p>
              <p className="text-sm mt-1">集群分片分布均衡</p>
            </div>
          )}
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-white">执行中的任务</h3>
            <span className={`badge ${tasks && tasks.length > 0 ? 'bg-es-blue/20 text-es-blue' : 'bg-es-dark-600 text-es-dark-300'}`}>
              {tasks?.length || 0} 个进行中
            </span>
          </div>

          {!tasksLoading && tasks && tasks.length > 0 ? (
            <div className="space-y-4 max-h-96 overflow-y-auto">
              {tasks.map((task, index) => (
                <div
                  key={index}
                  className="p-4 bg-es-dark-900 rounded-lg border border-es-dark-700"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="p-2 bg-es-blue/20 rounded-lg">
                        <ArrowPathIcon className="w-4 h-4 text-es-blue animate-spin" />
                      </div>
                      <div>
                        <p className="font-mono text-sm text-es-blue">{task.index}</p>
                        <p className="text-xs text-es-dark-400">分片 {task.shard}</p>
                      </div>
                    </div>
                    <span className="badge bg-es-blue/20 text-es-blue">{task.status}</span>
                  </div>
                  <div className="mt-4">
                    <div className="flex justify-between text-sm mb-2">
                      <span className="text-es-dark-400">进度</span>
                      <span className="text-es-dark-200">{task.progress.toFixed(1)}%</span>
                    </div>
                    <div className="h-2 bg-es-dark-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-es-blue transition-all duration-500 rounded-full"
                        style={{ width: `${task.progress}%` }}
                      ></div>
                    </div>
                  </div>
                  <div className="mt-3 flex items-center text-xs text-es-dark-400">
                    <ClockIcon className="w-3 h-3 mr-1" />
                    开始于 {format(new Date(task.started_at), 'HH:mm:ss')}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="h-48 flex flex-col items-center justify-center text-es-dark-400">
              <ExclamationTriangleIcon className="w-12 h-12 mb-3 text-es-dark-600" />
              <p>暂无正在执行的任务</p>
            </div>
          )}
        </div>
      </div>

      <div className="card p-6">
        <h3 className="text-lg font-semibold text-white mb-6">迁移历史</h3>
        <div className="text-center py-12 text-es-dark-400">
          <ClockIcon className="w-12 h-12 mx-auto mb-3 text-es-dark-600" />
          <p>暂无迁移历史记录</p>
          <p className="text-sm mt-1">执行迁移后，记录将显示在这里</p>
        </div>
      </div>

      {showConfirmModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="card p-6 w-full max-w-md mx-4">
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-es-yellow/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <ExclamationTriangleIcon className="w-8 h-8 text-es-yellow" />
              </div>
              <h3 className="text-xl font-semibold text-white">确认执行迁移</h3>
              <p className="text-es-dark-300 mt-2">
                即将执行 {plan?.length} 个分片迁移操作
              </p>
            </div>

            <div className="bg-es-dark-900 rounded-lg p-4 mb-6">
              <p className="text-sm text-es-dark-400 mb-2">注意事项：</p>
              <ul className="text-sm text-es-dark-300 space-y-1">
                <li>• 迁移过程可能影响集群性能</li>
                <li>• 建议在业务低峰期执行</li>
                <li>• 可以在设置中调整迁移速度限制</li>
              </ul>
            </div>

            <div className="flex space-x-3">
              <button
                className="btn-secondary flex-1"
                onClick={() => setShowConfirmModal(false)}
              >
                取消
              </button>
              <button
                className="btn-primary flex-1"
                onClick={handleExecute}
                disabled={isExecuting}
              >
                {isExecuting ? '执行中...' : '确认执行'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

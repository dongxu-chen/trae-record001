import { useState } from 'react'
import {
  PlayIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  TrendingUpIcon,
  TrendingDownIcon,
  ClockIcon,
  BeakerIcon,
} from '@heroicons/react/24/outline'
import { useSimulateMigration } from '../hooks/useBalancer'
import type { MigrationSimulationResult } from '../types'

export function Simulation() {
  const { data: simulationResult, isLoading, refetch, isError, error } = useSimulateMigration()
  const [showResult, setShowResult] = useState(false)

  const handleSimulate = () => {
    refetch()
    setShowResult(true)
  }

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const formatTime = (seconds: number) => {
    if (seconds < 60) return `${seconds.toFixed(0)} 秒`
    if (seconds < 3600) return `${(seconds / 60).toFixed(1)} 分钟`
    return `${(seconds / 3600).toFixed(1)} 小时`
  }

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-es-green'
    if (score >= 60) return 'text-es-yellow'
    return 'text-es-red'
  }

  const getScoreBg = (score: number) => {
    if (score >= 80) return 'bg-es-green/20'
    if (score >= 60) return 'bg-es-yellow/20'
    return 'bg-es-red/20'
  }

  const MetricCard = ({
    title,
    before,
    after,
    improvement,
    suffix = '',
    format,
  }: {
    title: string
    before: number
    after: number
    improvement: number
    suffix?: string
    format?: (v: number) => string
  }) => {
    const displayValue = (v: number) => (format ? format(v) : v.toFixed(2))
    const isImproved = improvement > 0
    const isDegraded = improvement < 0

    return (
      <div className="p-4 bg-es-dark-900 rounded-lg">
        <p className="text-sm text-es-dark-300 mb-2">{title}</p>
        <div className="flex items-end justify-between">
          <div className="flex items-center space-x-2">
            <span className="text-sm text-es-dark-400 line-through">{displayValue(before)}{suffix}</span>
            <ArrowPathIcon className="w-4 h-4 text-es-dark-500" />
            <span className="text-lg font-semibold text-white">{displayValue(after)}{suffix}</span>
          </div>
          {improvement !== 0 && (
            <div className={`flex items-center space-x-1 text-sm ${isImproved ? 'text-es-green' : isDegraded ? 'text-es-red' : 'text-es-dark-400'}`}>
              {isImproved ? (
                <TrendingDownIcon className="w-4 h-4" />
              ) : isDegraded ? (
                <TrendingUpIcon className="w-4 h-4" />
              ) : null}
              <span>{Math.abs(improvement).toFixed(1)}%</span>
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-es-purple/20 rounded-lg">
            <BeakerIcon className="w-6 h-6 text-es-purple" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white">迁移演练</h2>
            <p className="text-sm text-es-dark-400">模拟迁移效果评估，预览迁移后的集群状态</p>
          </div>
        </div>
        <button
          className="btn-primary flex items-center space-x-2"
          onClick={handleSimulate}
          disabled={isLoading}
        >
            <PlayIcon className="w-4 h-4" />
            <span>{isLoading ? '模拟中...' : '开始演练'}</span>
          </button>
        </div>
      </div>

      {isError && (
        <div className="card p-6 bg-es-red/10 border border-es-red/30">
          <div className="flex items-center space-x-3">
            <ExclamationTriangleIcon className="w-5 h-5 text-es-red" />
            <p className="text-es-red">{error instanceof Error ? error.message : '演练失败'}</p>
          </div>
        </div>
      )}

      {showResult && simulationResult && !isLoading && (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <div className="card p-6">
                <h3 className="text-lg font-semibold text-white mb-6">效果评估</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <MetricCard
                    title="分片不均衡度"
                    before={simulationResult.improvement_metrics.before_imbalance}
                    after={simulationResult.improvement_metrics.after_imbalance}
                    improvement={simulationResult.improvement_metrics.imbalance_improvement_percent}
                  />
                  <MetricCard
                    title="最大磁盘使用率"
                    before={simulationResult.improvement_metrics.before_max_disk_usage}
                    after={simulationResult.improvement_metrics.after_max_disk_usage}
                    improvement={simulationResult.improvement_metrics.disk_usage_improvement_percent}
                    suffix="%"
                  />
                  <MetricCard
                    title="高水位节点数"
                    before={simulationResult.improvement_metrics.nodes_over_high_watermark_before}
                    after={simulationResult.improvement_metrics.nodes_over_high_watermark_after}
                    improvement={
                      simulationResult.improvement_metrics.nodes_over_high_watermark_before > 0
                        ? ((simulationResult.improvement_metrics.nodes_over_high_watermark_before -
                            simulationResult.improvement_metrics.nodes_over_high_watermark_after) /
                          simulationResult.improvement_metrics.nodes_over_high_watermark_before *
                          100
                        : 0
                    }
                    format={(v) => v.toFixed(0)}
                  />
                  <MetricCard
                    title="高负载节点热分片数"
                    before={simulationResult.improvement_metrics.before_hot_shards_on_high_load}
                    after={simulationResult.improvement_metrics.after_hot_shards_on_high_load}
                    improvement={simulationResult.improvement_metrics.hot_shard_improvement_percent}
                    format={(v) => v.toFixed(0)}
                  />
                </div>
              </div>
            </div>

            <div className="space-y-6">
              <div className="card p-6">
                <h3 className="text-lg font-semibold text-white mb-4">综合评分</h3>
                <div className="flex flex-col items-center justify-center py-4">
                  <div
                    className={`w-32 h-32 rounded-full ${getScoreBg(simulationResult.improvement_metrics.overall_score)} flex items-center justify-center`}
                  >
                    <span className={`text-4xl font-bold ${getScoreColor(simulationResult.improvement_metrics.overall_score)}`}>
                      {simulationResult.improvement_metrics.overall_score.toFixed(0)}
                    </span>
                  </div>
                  <p className="text-sm text-es-dark-300 mt-4">
                    {simulationResult.improvement_metrics.overall_score >= 80
                      ? '优秀，建议执行'
                      : simulationResult.improvement_metrics.overall_score >= 60
                        ? '良好，可以执行'
                        : '一般，建议谨慎执行'}
                  </p>
                </div>
              </div>

              <div className="card p-6">
                <h3 className="text-lg font-semibold text-white mb-4">预估信息</h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-es-dark-300">迁移计划数</span>
                    <span className="text-white font-medium">{simulationResult.plans.length} 个</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-es-dark-300">预估数据量</span>
                    <span className="text-white font-medium">{formatBytes(simulationResult.estimated_total_bytes)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <ClockIcon className="w-4 h-4 text-es-dark-400" />
                      <span className="text-es-dark-300">预估时间</span>
                    </div>
                    <span className="text-white font-medium">{formatTime(simulationResult.estimated_time_seconds)}</span>
                  </div>
                </div>
              </div>

              {simulationResult.warnings.length > 0 && (
                <div className="card p-6 bg-es-yellow/10 border border-es-yellow/30">
                  <div className="flex items-start space-x-3">
                    <ExclamationTriangleIcon className="w-5 h-5 text-es-yellow flex-shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-es-yellow font-medium mb-2">注意事项</h4>
                      <ul className="space-y-1">
                        {simulationResult.warnings.map((warning, idx) => (
                          <li key={idx} className="text-sm text-es-dark-300">
                            • {warning}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="card p-6">
            <h3 className="text-lg font-semibold text-white mb-4">模拟迁移计划</h3>
            {simulationResult.plans.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-es-dark-700">
                      <th className="text-left py-3 px-4 text-sm font-medium text-es-dark-300">
                        索引
                      </th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-es-dark-300">
                        分片
                      </th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-es-dark-300">
                        源节点
                      </th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-es-dark-300">
                        目标节点
                      </th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-es-dark-300">
                        热度
                      </th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-es-dark-300">
                        原因
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {simulationResult.plans.map((plan, index) => (
                      <tr key={index} className="border-b border-es-dark-800 hover:bg-es-dark-900/50">
                        <td className="py-3 px-4 font-mono text-sm text-es-blue">
                          {plan.index}
                        </td>
                        <td className="py-3 px-4 text-sm text-white">{plan.shard}
                        </td>
                        <td className="py-3 px-4 text-sm text-es-dark-200">
                          {plan.from_node}
                        </td>
                        <td className="py-3 px-4 text-sm text-es-dark-200">
                          {plan.to_node}
                        </td>
                        <td className="py-3 px-4">
                          {plan.is_hot_shard ? (
                            <span className="px-2 py-1 bg-red-500/20 text-red-500 text-xs rounded">
                              热分片
                            </span>
                          ) : (
                            <span className="px-2 py-1 bg-es-dark-700 text-es-dark-400 text-xs rounded">
                              普通
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-sm text-es-dark-300">{plan.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
                <div className="py-12 text-center text-es-dark-400">
                  <CheckCircleIcon className="w-12 h-12 mx-auto mb-3 text-es-green" />
                  <p>无需迁移计划为空</p>
                  <p className="text-sm mt-1">当前集群状态良好，无需迁移</p>
                </div>
              )}
            </div>
          </>
        )}

      {!showResult && !isLoading && (
        <div className="card p-12 text-center">
          <BeakerIcon className="w-16 h-16 mx-auto mb-4 text-es-dark-500 opacity-50" />
          <h3 className="text-xl font-semibold text-white mb-2">开始迁移演练</h3>
          <p className="text-es-dark-400 max-w-md mx-auto">
            点击"开始演练"按钮，系统将模拟生成迁移计划并计算迁移后的效果，
            评估迁移对集群的影响，包括分片分布、磁盘使用率、热分片分布等指标的变化情况。
          </p>
        </div>
      )}
    </div>
  )
}

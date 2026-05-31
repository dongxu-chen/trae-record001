import {
  ServerIcon,
  CircleStackIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline'
import { useClusterHealth, useShardDistribution } from '../hooks/useCluster'
import { useMigrationPlan, useMigrationTasks } from '../hooks/useBalancer'
import { formatNumber, formatPercent, getStatusColor, getDiskUsageColor } from '../utils/format'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'

export function Dashboard() {
  const { data: health, isLoading: healthLoading } = useClusterHealth()
  const { data: distribution, isLoading: distLoading } = useShardDistribution()
  const { data: plan, isLoading: planLoading } = useMigrationPlan()
  const { data: tasks, isLoading: tasksLoading } = useMigrationTasks()

  const nodeChartData = distribution
    ? Object.values(distribution.nodes).map((node) => ({
        name: node.node_name,
        shards: node.shard_count,
        disk_usage: node.disk_usage.used_percent,
      }))
    : []

  const stats = [
    {
      name: '节点数量',
      value: health?.number_of_data_nodes || 0,
      icon: ServerIcon,
      color: 'text-es-blue',
      bgColor: 'bg-es-blue/10',
    },
    {
      name: '总分片数',
      value: health?.active_shards || 0,
      icon: CircleStackIcon,
      color: 'text-es-green',
      bgColor: 'bg-es-green/10',
    },
    {
      name: '迁移中',
      value: health?.relocating_shards || 0,
      icon: ArrowPathIcon,
      color: 'text-es-yellow',
      bgColor: 'bg-es-yellow/10',
    },
    {
      name: '待分配',
      value: health?.unassigned_shards || 0,
      icon: ExclamationTriangleIcon,
      color: 'text-es-red',
      bgColor: 'bg-es-red/10',
    },
  ]

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">集群总览</h2>
        <div className="flex items-center space-x-2">
          <span className="text-sm text-es-dark-300">集群状态:</span>
          {health && (
            <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(health.status)} text-white`}>
              <span className="w-2 h-2 bg-white rounded-full mr-2 animate-pulse"></span>
              {health.status.toUpperCase()}
            </span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => (
          <div key={stat.name} className="card p-6 card-hover">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-es-dark-300">{stat.name}</p>
                <p className="text-3xl font-bold text-white mt-1">{formatNumber(stat.value)}</p>
              </div>
              <div className={`p-3 rounded-lg ${stat.bgColor}`}>
                <stat.icon className={`w-6 h-6 ${stat.color}`} />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-white mb-4">节点分片分布</h3>
          {!distLoading && nodeChartData.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={nodeChartData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#334e68" />
                  <XAxis type="number" stroke="#9fb3c8" />
                  <YAxis type="category" dataKey="name" stroke="#9fb3c8" width={120} tick={{ fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#243b53',
                      border: '1px solid #334e68',
                      borderRadius: '8px',
                      color: '#e2e8f0',
                    }}
                  />
                  <Bar dataKey="shards" fill="#3b82f6" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center text-es-dark-400">
              加载中...
            </div>
          )}
        </div>

        <div className="card p-6">
          <h3 className="text-lg font-semibold text-white mb-4">节点磁盘使用率</h3>
          {!distLoading && distribution ? (
            <div className="space-y-4">
              {Object.values(distribution.nodes).map((node) => (
                <div key={node.node_name} className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-es-dark-200">{node.node_name}</span>
                    <span className={`text-sm font-medium ${getDiskUsageColor(node.disk_usage.used_percent)}`}>
                      {formatPercent(node.disk_usage.used_percent)}
                    </span>
                  </div>
                  <div className="h-2 bg-es-dark-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-500 rounded-full ${
                        node.disk_usage.used_percent >= 90
                          ? 'bg-es-red'
                          : node.disk_usage.used_percent >= 80
                          ? 'bg-es-yellow'
                          : 'bg-es-green'
                      }`}
                      style={{ width: `${Math.min(node.disk_usage.used_percent, 100)}%` }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="h-48 flex items-center justify-center text-es-dark-400">
              加载中...
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">迁移计划</h3>
            <span className="text-sm text-es-dark-300">
              {plan?.length || 0} 个待执行
            </span>
          </div>
          {!planLoading && plan && plan.length > 0 ? (
            <div className="space-y-3 max-h-64 overflow-y-auto">
              {plan.slice(0, 5).map((item, index) => (
                <div key={index} className="p-3 bg-es-dark-900 rounded-lg border border-es-dark-700">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-sm text-es-blue">{item.index}</span>
                    <span className="text-xs text-es-dark-400">分片 {item.shard}</span>
                  </div>
                  <div className="flex items-center mt-2 text-xs text-es-dark-300">
                    <span>{item.from_node}</span>
                    <ArrowPathIcon className="w-3 h-3 mx-2" />
                    <span>{item.to_node}</span>
                  </div>
                  <p className="text-xs text-es-dark-400 mt-1">{item.reason}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="h-32 flex flex-col items-center justify-center text-es-dark-400">
              <CheckCircleIcon className="w-8 h-8 mb-2 text-es-green" />
              <p>暂无迁移计划</p>
            </div>
          )}
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">集群指标</h3>
          </div>
          {!healthLoading && health ? (
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-es-dark-900 rounded-lg">
                <p className="text-xs text-es-dark-400">主分片数</p>
                <p className="text-xl font-bold text-white mt-1">{health.active_primary_shards}</p>
              </div>
              <div className="p-4 bg-es-dark-900 rounded-lg">
                <p className="text-xs text-es-dark-400">活跃分片率</p>
                <p className="text-xl font-bold text-es-green mt-1">
                  {health.active_shards_percent_as_number.toFixed(1)}%
                </p>
              </div>
              <div className="p-4 bg-es-dark-900 rounded-lg">
                <p className="text-xs text-es-dark-400">初始化中</p>
                <p className="text-xl font-bold text-es-yellow mt-1">{health.initializing_shards}</p>
              </div>
              <div className="p-4 bg-es-dark-900 rounded-lg">
                <p className="text-xs text-es-dark-400">待处理任务</p>
                <p className="text-xl font-bold text-white mt-1">{health.number_of_pending_tasks}</p>
              </div>
            </div>
          ) : (
            <div className="h-32 flex items-center justify-center text-es-dark-400">
              加载中...
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

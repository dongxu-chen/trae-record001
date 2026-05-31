import { useState } from 'react'
import {
  ServerIcon,
  CircleStackIcon,
  DeviceTabletIcon,
  CpuChipIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  FireIcon,
  SnowflakeIcon,
  BoltIcon,
  SignalSlashIcon,
  SignalIcon,
} from '@heroicons/react/24/outline'
import { useShardDistribution } from '../hooks/useCluster'
import { useAllNodeLoads } from '../hooks/useMonitor'
import { formatBytes, formatPercent, getDiskUsageColor, getNodeTypeColor } from '../utils/format'
import type { NodeShardInfo } from '../types'

export function Nodes() {
  const { data: distribution, isLoading } = useShardDistribution()
  const { data: nodeLoads } = useAllNodeLoads()
  const [expandedNode, setExpandedNode] = useState<string | null>(null)

  const toggleNode = (nodeName: string) => {
    setExpandedNode(expandedNode === nodeName ? null : nodeName)
  }

  const getLoadColor = (score: number) => {
    if (score >= 0.8) return 'text-es-red'
    if (score >= 0.5) return 'text-es-yellow'
    return 'text-es-green'
  }

  const getLoadIcon = (isHighLoad: boolean, score: number) => {
    if (isHighLoad) return <SignalSlashIcon className="w-4 h-4" />
    if (score >= 0.5) return <BoltIcon className="w-4 h-4" />
    return <SignalIcon className="w-4 h-4" />
  }

  const getNodeTypeIcon = (type: string) => {
    switch (type) {
      case 'hot':
        return <FireIcon className="w-4 h-4" />
      case 'cold':
        return <SnowflakeIcon className="w-4 h-4" />
      default:
        return <ServerIcon className="w-4 h-4" />
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">节点管理</h2>
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <span className="flex items-center text-sm text-es-dark-300">
              <span className="w-3 h-3 bg-orange-500 rounded-full mr-1"></span>
              热节点
            </span>
            <span className="flex items-center text-sm text-es-dark-300">
              <span className="w-3 h-3 bg-blue-500 rounded-full mr-1"></span>
              冷节点
            </span>
            <span className="flex items-center text-sm text-es-dark-300">
              <span className="w-3 h-3 bg-gray-500 rounded-full mr-1"></span>
              普通节点
            </span>
          </div>
        </div>
      </div>

      {!isLoading && distribution ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {Object.values(distribution.nodes).map((node: NodeShardInfo) => (
            <div key={node.node_name} className="card overflow-hidden">
              <div
                className="p-6 cursor-pointer hover:bg-es-dark-700/50 transition-colors"
                onClick={() => toggleNode(node.node_name)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-4">
                    <div className="p-3 bg-es-dark-700 rounded-lg">
                      <ServerIcon className="w-6 h-6 text-es-blue" />
                    </div>
                    <div>
                      <div className="flex items-center space-x-2 flex-wrap">
                        <h3 className="text-lg font-semibold text-white">{node.node_name}</h3>
                        <span className={`badge flex items-center space-x-1 ${getNodeTypeColor(node.node_type)}`}>
                          {getNodeTypeIcon(node.node_type)}
                          <span className="capitalize">{node.node_type}</span>
                        </span>
                        {nodeLoads && nodeLoads[node.node_name] && (
                          <span className={`badge flex items-center space-x-1 ${
                            nodeLoads[node.node_name].is_high_load
                              ? 'bg-es-red/20 text-es-red'
                              : nodeLoads[node.node_name].load_score >= 0.5
                              ? 'bg-es-yellow/20 text-es-yellow'
                              : 'bg-es-green/20 text-es-green'
                          }`}>
                            {getLoadIcon(nodeLoads[node.node_name].is_high_load, nodeLoads[node.node_name].load_score)}
                            <span>负载 {nodeLoads[node.node_name].load_score.toFixed(2)}</span>
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-es-dark-400 mt-1">
                        {node.indices.length} 个索引 | {node.shard_count} 个分片
                      </p>
                    </div>
                  </div>
                  <button className="p-2 text-es-dark-400 hover:text-white transition-colors">
                    {expandedNode === node.node_name ? (
                      <ChevronUpIcon className="w-5 h-5" />
                    ) : (
                      <ChevronDownIcon className="w-5 h-5" />
                    )}
                  </button>
                </div>

                <div className="mt-6 grid grid-cols-4 gap-3">
                  <div className="bg-es-dark-900 rounded-lg p-3">
                    <div className="flex items-center space-x-1 text-es-dark-400">
                      <CircleStackIcon className="w-3.5 h-3.5" />
                      <span className="text-xs">分片</span>
                    </div>
                    <p className="text-lg font-bold text-white mt-1">{node.shard_count}</p>
                  </div>
                  <div className="bg-es-dark-900 rounded-lg p-3">
                    <div className="flex items-center space-x-1 text-es-dark-400">
                      <CpuChipIcon className="w-3.5 h-3.5" />
                      <span className="text-xs">索引</span>
                    </div>
                    <p className="text-lg font-bold text-white mt-1">{node.indices.length}</p>
                  </div>
                  <div className="bg-es-dark-900 rounded-lg p-3">
                    <div className="flex items-center space-x-1 text-es-dark-400">
                      <DeviceTabletIcon className="w-3.5 h-3.5" />
                      <span className="text-xs">磁盘</span>
                    </div>
                    <p className={`text-lg font-bold mt-1 ${getDiskUsageColor(node.disk_usage.used_percent)}`}>
                      {formatPercent(node.disk_usage.used_percent)}
                    </p>
                  </div>
                  <div className="bg-es-dark-900 rounded-lg p-3">
                    <div className="flex items-center space-x-1 text-es-dark-400">
                      <BoltIcon className="w-3.5 h-3.5" />
                      <span className="text-xs">负载</span>
                    </div>
                    <p className={`text-lg font-bold mt-1 ${
                      nodeLoads && nodeLoads[node.node_name]
                        ? getLoadColor(nodeLoads[node.node_name].load_score)
                        : 'text-es-dark-400'
                    }`}>
                      {nodeLoads && nodeLoads[node.node_name]
                        ? nodeLoads[node.node_name].load_score.toFixed(2)
                        : '-'}
                    </p>
                  </div>
                </div>

                <div className="mt-4">
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-es-dark-400">
                      磁盘空间
                      {node.disk_usage.dynamic_high !== undefined && (
                        <span className="ml-2 text-xs text-es-blue">
                          (动态水位: {node.disk_usage.dynamic_high.toFixed(1)}%)
                        </span>
                      )}
                    </span>
                    <span className="text-es-dark-200">
                      {formatBytes(node.disk_usage.used_bytes)} / {formatBytes(node.disk_usage.total_bytes)}
                    </span>
                  </div>
                  <div className="h-3 bg-es-dark-700 rounded-full overflow-hidden relative">
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
                    {node.disk_usage.dynamic_high !== undefined && (
                      <div
                        className="absolute top-0 bottom-0 w-0.5 bg-es-blue z-10"
                        style={{ left: `${Math.min(node.disk_usage.dynamic_high, 100)}%` }}
                        title={`动态高水位: ${node.disk_usage.dynamic_high.toFixed(1)}%`}
                      ></div>
                    )}
                  </div>
                  {node.disk_usage.dynamic_high !== undefined && (
                    <div className="flex justify-between text-xs mt-1">
                      <span className="text-es-green">低: {node.disk_usage.dynamic_low?.toFixed(1)}%</span>
                      <span className="text-es-yellow">高: {node.disk_usage.dynamic_high?.toFixed(1)}%</span>
                      <span className="text-es-red">洪水: {node.disk_usage.dynamic_flood?.toFixed(1)}%</span>
                    </div>
                  )}
                </div>

                {nodeLoads && nodeLoads[node.node_name] && nodeLoads[node.node_name].history.length > 0 && (
                  <div className="mt-4 p-3 bg-es-dark-900 rounded-lg">
                    <h4 className="text-xs text-es-dark-400 mb-2">实时负载</h4>
                    <div className="grid grid-cols-3 gap-3 text-center">
                      <div>
                        <p className="text-xs text-es-dark-400">CPU 使用率</p>
                        <p className={`text-sm font-semibold ${getLoadColor(nodeLoads[node.node_name].avg_cpu / 100)}`}>
                          {nodeLoads[node.node_name].avg_cpu.toFixed(1)}%
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-es-dark-400">负载均值</p>
                        <p className={`text-sm font-semibold ${getLoadColor(nodeLoads[node.node_name].avg_load / 10)}`}>
                          {nodeLoads[node.node_name].avg_load.toFixed(2)}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-es-dark-400">IO 等待</p>
                        <p className={`text-sm font-semibold ${getLoadColor(nodeLoads[node.node_name].avg_io_wait / 100)}`}>
                          {nodeLoads[node.node_name].avg_io_wait.toFixed(1)}%
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {expandedNode === node.node_name && (
                <div className="border-t border-es-dark-700 p-6">
                  <h4 className="text-sm font-semibold text-es-dark-200 mb-4">索引列表</h4>
                  <div className="flex flex-wrap gap-2">
                    {node.indices.map((index) => (
                      <span
                        key={index}
                        className="px-3 py-1 bg-es-dark-900 text-es-dark-200 text-sm rounded-md font-mono"
                      >
                        {index}
                      </span>
                    ))}
                  </div>

                  <h4 className="text-sm font-semibold text-es-dark-200 mt-6 mb-4">分片详情</h4>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-es-dark-400">
                          <th className="text-left py-2 px-3">索引</th>
                          <th className="text-left py-2 px-3">分片</th>
                          <th className="text-left py-2 px-3">类型</th>
                          <th className="text-left py-2 px-3">状态</th>
                        </tr>
                      </thead>
                      <tbody>
                        {node.shards.slice(0, 10).map((shard, idx) => (
                          <tr key={idx} className="border-t border-es-dark-700">
                            <td className="py-2 px-3 font-mono text-es-blue">{shard.index}</td>
                            <td className="py-2 px-3 text-es-dark-200">{shard.shard}</td>
                            <td className="py-2 px-3">
                              <span className={`badge ${shard.prirep === 'p' ? 'bg-es-blue/20 text-es-blue' : 'bg-es-green/20 text-es-green'}`}>
                                {shard.prirep === 'p' ? '主分片' : '副本'}
                              </span>
                            </td>
                            <td className="py-2 px-3">
                              <span className={`badge ${shard.state === 'STARTED' ? 'bg-es-green/20 text-es-green' : 'bg-es-yellow/20 text-es-yellow'}`}>
                                {shard.state}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {node.shards.length > 10 && (
                      <p className="text-sm text-es-dark-400 mt-2 text-center">
                        还有 {node.shards.length - 10} 个分片...
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="card p-12 flex items-center justify-center">
          <div className="text-es-dark-400">加载中...</div>
        </div>
      )}
    </div>
  )
}

import { useState, useMemo } from 'react'
import { CircleStackIcon, MagnifyingGlassIcon, ArrowRightIcon } from '@heroicons/react/24/outline'
import { useShardDistribution, useShards } from '../hooks/useCluster'
import { useMoveShard } from '../hooks/useBalancer'

export function Shards() {
  const { data: distribution, isLoading: distLoading } = useShardDistribution()
  const { data: shards, isLoading: shardsLoading } = useShards()
  const { mutate: moveShard } = useMoveShard()
  const [selectedShard, setSelectedShard] = useState<any>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [targetNode, setTargetNode] = useState('')
  const [showMoveModal, setShowMoveModal] = useState(false)

  const filteredShards = useMemo(() => {
    if (!shards) return []
    return shards.filter((shard) =>
      shard.index.toLowerCase().includes(searchTerm.toLowerCase()) ||
      shard.node.toLowerCase().includes(searchTerm.toLowerCase())
    )
  }, [shards, searchTerm])

  const handleMoveShard = () => {
    if (selectedShard && targetNode) {
      moveShard({
        index: selectedShard.index,
        shard: selectedShard.shard,
        from_node: selectedShard.node,
        to_node: targetNode,
      })
      setShowMoveModal(false)
      setSelectedShard(null)
      setTargetNode('')
    }
  }

  const getShardColor = (shard: any) => {
    if (shard.state !== 'STARTED') return 'bg-es-yellow'
    if (shard.prirep === 'p') return 'bg-es-blue'
    return 'bg-es-green'
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">分片分布</h2>
        <div className="flex items-center space-x-4">
          <div className="relative">
            <MagnifyingGlassIcon className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-es-dark-400" />
            <input
              type="text"
              placeholder="搜索索引或节点..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="input-field pl-10 w-64"
            />
          </div>
        </div>
      </div>

      <div className="flex items-center space-x-6">
        <div className="flex items-center space-x-2">
          <span className="w-4 h-4 rounded bg-es-blue"></span>
          <span className="text-sm text-es-dark-300">主分片</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="w-4 h-4 rounded bg-es-green"></span>
          <span className="text-sm text-es-dark-300">副本分片</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="w-4 h-4 rounded bg-es-yellow"></span>
          <span className="text-sm text-es-dark-300">未就绪</span>
        </div>
      </div>

      {!distLoading && distribution ? (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          {Object.values(distribution.nodes).map((node) => (
            <div key={node.node_name} className="card p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-es-dark-700 rounded-lg">
                    <CircleStackIcon className="w-5 h-5 text-es-blue" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white">{node.node_name}</h3>
                    <p className="text-sm text-es-dark-400">{node.shard_count} 个分片</p>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-10 gap-1">
                {node.shards.slice(0, 50).map((shard, idx) => (
                  <div
                    key={idx}
                    className={`aspect-square rounded cursor-pointer transition-all hover:scale-110 ${getShardColor(shard)}`}
                    title={`${shard.index} - 分片 ${shard.shard} (${shard.prirep === 'p' ? '主' : '副'})`}
                    onClick={() => {
                      setSelectedShard(shard)
                      setTargetNode('')
                      setShowMoveModal(true)
                    }}
                  ></div>
                ))}
                {node.shard_count > 50 && (
                  <div className="aspect-square rounded bg-es-dark-700 flex items-center justify-center text-xs text-es-dark-300">
                    +{node.shard_count - 50}
                  </div>
                )}
              </div>

              <div className="mt-4 pt-4 border-t border-es-dark-700">
                <div className="flex flex-wrap gap-1">
                  {[...new Set(node.indices)].slice(0, 8).map((index) => (
                    <span
                      key={index}
                      className="px-2 py-0.5 bg-es-dark-900 text-es-dark-300 text-xs rounded font-mono"
                    >
                      {index.length > 15 ? index.slice(0, 15) + '...' : index}
                    </span>
                  ))}
                  {node.indices.length > 8 && (
                    <span className="px-2 py-0.5 text-es-dark-400 text-xs">
                      +{node.indices.length - 8} 更多
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="card p-12 flex items-center justify-center">
          <div className="text-es-dark-400">加载中...</div>
        </div>
      )}

      <div className="card overflow-hidden">
        <div className="p-6 border-b border-es-dark-700">
          <h3 className="text-lg font-semibold text-white">分片列表</h3>
        </div>
        <div className="overflow-x-auto max-h-96 overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-es-dark-800">
              <tr className="text-es-dark-400">
                <th className="text-left py-3 px-6">索引</th>
                <th className="text-left py-3 px-6">分片</th>
                <th className="text-left py-3 px-6">类型</th>
                <th className="text-left py-3 px-6">状态</th>
                <th className="text-left py-3 px-6">节点</th>
                <th className="text-left py-3 px-6">操作</th>
              </tr>
            </thead>
            <tbody>
              {!shardsLoading &&
                filteredShards.slice(0, 100).map((shard, idx) => (
                  <tr key={idx} className="border-t border-es-dark-700 hover:bg-es-dark-700/30">
                    <td className="py-3 px-6 font-mono text-es-blue">{shard.index}</td>
                    <td className="py-3 px-6 text-es-dark-200">{shard.shard}</td>
                    <td className="py-3 px-6">
                      <span
                        className={`badge ${
                          shard.prirep === 'p' ? 'bg-es-blue/20 text-es-blue' : 'bg-es-green/20 text-es-green'
                        }`}
                      >
                        {shard.prirep === 'p' ? '主分片' : '副本'}
                      </span>
                    </td>
                    <td className="py-3 px-6">
                      <span
                        className={`badge ${
                          shard.state === 'STARTED'
                            ? 'bg-es-green/20 text-es-green'
                            : shard.state === 'INITIALIZING'
                            ? 'bg-es-yellow/20 text-es-yellow'
                            : 'bg-es-red/20 text-es-red'
                        }`}
                      >
                        {shard.state}
                      </span>
                    </td>
                    <td className="py-3 px-6 text-es-dark-200">{shard.node || '-'}</td>
                    <td className="py-3 px-6">
                      {shard.state === 'STARTED' && (
                        <button
                          className="text-es-blue hover:text-blue-400 text-sm font-medium"
                          onClick={() => {
                            setSelectedShard(shard)
                            setTargetNode('')
                            setShowMoveModal(true)
                          }}
                        >
                          迁移
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>

      {showMoveModal && selectedShard && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="card p-6 w-full max-w-md mx-4">
            <h3 className="text-lg font-semibold text-white mb-4">迁移分片</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-es-dark-300 mb-2">分片信息</label>
                <div className="p-3 bg-es-dark-900 rounded-lg">
                  <p className="font-mono text-es-blue">{selectedShard.index}</p>
                  <p className="text-sm text-es-dark-400 mt-1">
                    分片 {selectedShard.shard} | {selectedShard.prirep === 'p' ? '主分片' : '副本'}
                  </p>
                </div>
              </div>
              <div className="flex items-center justify-center">
                <ArrowRightIcon className="w-6 h-6 text-es-dark-400" />
              </div>
              <div>
                <label className="block text-sm text-es-dark-300 mb-2">源节点</label>
                <div className="p-3 bg-es-dark-900 rounded-lg text-es-dark-200">
                  {selectedShard.node}
                </div>
              </div>
              <div>
                <label className="block text-sm text-es-dark-300 mb-2">目标节点</label>
                <select
                  value={targetNode}
                  onChange={(e) => setTargetNode(e.target.value)}
                  className="input-field"
                >
                  <option value="">请选择目标节点</option>
                  {distribution &&
                    Object.values(distribution.nodes)
                      .filter((n) => n.node_name !== selectedShard.node)
                      .map((node) => (
                        <option key={node.node_name} value={node.node_name}>
                          {node.node_name} ({node.shard_count} 分片)
                        </option>
                      ))}
                </select>
              </div>
              <div className="flex space-x-3 pt-4">
                <button
                  className="btn-secondary flex-1"
                  onClick={() => {
                    setShowMoveModal(false)
                    setSelectedShard(null)
                  }}
                >
                  取消
                </button>
                <button
                  className="btn-primary flex-1"
                  onClick={handleMoveShard}
                  disabled={!targetNode}
                >
                  确认迁移
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

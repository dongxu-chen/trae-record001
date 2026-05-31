import React, { useState, useEffect } from 'react'
import { api } from '../services/api'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis } from 'recharts'

export default function Simulation({ nodes, onRefresh }) {
  const [simType, setSimType] = useState('scaleup')
  const [nodeCount, setNodeCount] = useState(1)
  const [selectedNode, setSelectedNode] = useState('')
  const [message, setMessage] = useState(null)
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState([])
  const [currentResult, setCurrentResult] = useState(null)

  const loadResults = async () => {
    try {
      const r = await api.getSimulateResults()
      setResults(Array.isArray(r) ? r : [])
    } catch {}
  }

  useEffect(() => {
    loadResults()
  }, [])

  const handleSimulate = async () => {
    setLoading(true)
    setMessage(null)
    setCurrentResult(null)
    try {
      let result
      switch (simType) {
        case 'scaleup':
          result = await api.simulateScaleUp(nodeCount)
          break
        case 'scaledown':
          result = await api.simulateScaleDown(nodeCount)
          break
        case 'rebalance':
          result = await api.simulateRebalance()
          break
        case 'failover':
          if (!selectedNode) {
            setMessage({ type: 'error', text: '请选择要模拟故障的节点' })
            setLoading(false)
            return
          }
          result = await api.simulateFailover(selectedNode)
          break
      }
      setCurrentResult(result)
      loadResults()
    } catch (e) {
      setMessage({ type: 'error', text: e.message })
    } finally {
      setLoading(false)
    }
  }

  const getRiskColor = (risk) => {
    switch (risk) {
      case 'low': return 'bg-green-100 text-green-800 border-green-300'
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-300'
      case 'high': return 'bg-red-100 text-red-800 border-red-300'
      default: return 'bg-gray-100 text-gray-800 border-gray-300'
    }
  }

  const getRiskText = (risk) => {
    switch (risk) {
      case 'low': return '低风险'
      case 'medium': return '中风险'
      case 'high': return '高风险'
      default: return '未知'
    }
  }

  const getImpactChartData = () => {
    if (!currentResult?.impacts) return []
    return currentResult.impacts.map((imp) => ({
      category: imp.category || 'unknown',
      before: imp.before_value || 0,
      after: imp.after_value || 0,
    }))
  }

  const getRadarData = () => {
    if (!currentResult?.impacts) return []
    return currentResult.impacts.map((imp) => ({
      category: imp.category || 'unknown',
      score: imp.score || 0,
      fullMark: 100,
    }))
  }

  const masters = Array.isArray(nodes) ? nodes.filter((n) => n.role === 'master') : []

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-6">扩缩容演练</h2>

      {message && (
        <div className={`mb-4 p-3 rounded ${message.type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
          {message.text}
        </div>
      )}

      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <h3 className="text-lg font-semibold mb-3">模拟设置</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">模拟类型</label>
            <select
              value={simType}
              onChange={(e) => setSimType(e.target.value)}
              className="w-full border rounded px-3 py-2"
            >
              <option value="scaleup">模拟扩容</option>
              <option value="scaledown">模拟缩容</option>
              <option value="rebalance">模拟重新平衡</option>
              <option value="failover">模拟故障转移</option>
            </select>
          </div>

          {(simType === 'scaleup' || simType === 'scaledown') && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">节点数量</label>
              <input
                type="number"
                min="1"
                max="10"
                value={nodeCount}
                onChange={(e) => setNodeCount(Math.max(1, parseInt(e.target.value) || 1))}
                className="w-full border rounded px-3 py-2"
              />
            </div>
          )}

          {simType === 'failover' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">模拟故障节点</label>
              <select
                value={selectedNode}
                onChange={(e) => setSelectedNode(e.target.value)}
                className="w-full border rounded px-3 py-2"
              >
                <option value="">选择节点...</option>
                {masters.map((n) => (
                  <option key={n.id} value={n.id}>
                    {n.id?.slice(0, 8)} - {n.address}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="flex items-end">
            <button
              onClick={handleSimulate}
              disabled={loading}
              className="w-full bg-purple-500 text-white px-4 py-2 rounded hover:bg-purple-600 disabled:bg-gray-300"
            >
              {loading ? '模拟中...' : '开始模拟'}
            </button>
          </div>
        </div>

        <div className="bg-blue-50 p-3 rounded text-sm text-blue-700">
          <strong>提示：</strong>演练模式不会对实际集群造成任何影响。系统会捕获当前集群状态，
          在内存中模拟操作，并生成详细的影响评估报告。
        </div>
      </div>

      {currentResult && (
        <div className="space-y-6 mb-6">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">模拟结果 - {currentResult.type}</h3>
              <span className={`px-3 py-1 rounded-full text-sm font-medium border ${getRiskColor(currentResult.risk_level)}`}>
                {getRiskText(currentResult.risk_level)}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
              <div className="bg-gray-50 p-3 rounded">
                <div className="text-sm text-gray-500">模拟ID</div>
                <div className="text-sm font-mono">{currentResult.id?.slice(0, 12) || '-'}</div>
              </div>
              <div className="bg-gray-50 p-3 rounded">
                <div className="text-sm text-gray-500">原始节点数</div>
                <div className="text-xl font-bold">{currentResult.original_state?.total_nodes || 0}</div>
              </div>
              <div className="bg-gray-50 p-3 rounded">
                <div className="text-sm text-gray-500">模拟后节点数</div>
                <div className="text-xl font-bold">{currentResult.simulated_state?.total_nodes || 0}</div>
              </div>
              <div className="bg-gray-50 p-3 rounded">
                <div className="text-sm text-gray-500">综合评分</div>
                <div className={`text-xl font-bold ${
                  (currentResult.overall_score || 0) > 70 ? 'text-green-600' :
                  (currentResult.overall_score || 0) > 40 ? 'text-yellow-600' : 'text-red-600'
                }`}>
                  {(currentResult.overall_score || 0).toFixed(1)}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-4">
              <div>
                <h4 className="font-semibold mb-2">影响对比</h4>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={getImpactChartData()}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="category" fontSize={12} />
                    <YAxis fontSize={12} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="before" fill="#94a3b8" name="操作前" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="after" fill="#3b82f6" name="操作后" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div>
                <h4 className="font-semibold mb-2">影响评分雷达图</h4>
                <ResponsiveContainer width="100%" height={250}>
                  <RadarChart data={getRadarData()}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="category" fontSize={12} />
                    <PolarRadiusAxis angle={30} domain={[0, 100]} fontSize={10} />
                    <Radar name="评分" dataKey="score" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.5} />
                    <Tooltip />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {currentResult.impacts && currentResult.impacts.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold mb-2">详细影响评估</h4>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left py-2">评估类别</th>
                        <th className="text-right py-2">操作前</th>
                        <th className="text-right py-2">操作后</th>
                        <th className="text-right py-2">变化</th>
                        <th className="text-right py-2">评分</th>
                        <th className="text-left py-2">说明</th>
                      </tr>
                    </thead>
                    <tbody>
                      {currentResult.impacts.map((imp, idx) => (
                        <tr key={idx} className="border-b hover:bg-gray-50">
                          <td className="py-2 font-medium">{imp.category}</td>
                          <td className="py-2 text-right">{imp.before_value_formatted || imp.before_value || '-'}</td>
                          <td className="py-2 text-right">{imp.after_value_formatted || imp.after_value || '-'}</td>
                          <td className={`py-2 text-right font-medium ${
                            (imp.change_pct || 0) > 0 ? 'text-red-600' : 'text-green-600'
                          }`}>
                            {imp.change_pct !== undefined ? `${imp.change_pct > 0 ? '+' : ''}${imp.change_pct.toFixed(1)}%` : '-'}
                          </td>
                          <td className="py-2 text-right">
                            <span className={`px-2 py-1 rounded text-xs font-medium ${
                              (imp.score || 0) >= 70 ? 'bg-green-100 text-green-800' :
                              (imp.score || 0) >= 40 ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'
                            }`}>
                              {(imp.score || 0).toFixed(0)}
                            </span>
                          </td>
                          <td className="py-2 text-gray-600 max-w-xs truncate" title={imp.description}>
                            {imp.description || '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {currentResult.cost_prediction && (
              <div className="mb-4">
                <h4 className="font-semibold mb-2">成本预测</h4>
                <div className="bg-gray-50 p-4 rounded">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <span className="text-sm text-gray-500">小时成本变化：</span>
                      <span className={`font-bold ml-2 ${
                        currentResult.cost_prediction.hourly_cost_diff > 0 ? 'text-red-600' : 'text-green-600'
                      }`}>
                        {currentResult.cost_prediction.hourly_cost_diff > 0 ? '+' : ''}
                        ¥{currentResult.cost_prediction.hourly_cost_diff.toFixed(2)}
                      </span>
                    </div>
                    <div>
                      <span className="text-sm text-gray-500">月成本变化：</span>
                      <span className={`font-bold ml-2 ${
                        currentResult.cost_prediction.monthly_cost_diff > 0 ? 'text-red-600' : 'text-green-600'
                      }`}>
                        {currentResult.cost_prediction.monthly_cost_diff > 0 ? '+' : ''}
                        ¥{currentResult.cost_prediction.monthly_cost_diff.toFixed(2)}
                      </span>
                    </div>
                    <div>
                      <span className="text-sm text-gray-500">预期内存使用率：</span>
                      <span className="font-bold ml-2 text-blue-600">
                        {(currentResult.cost_prediction.expected_memory_pct * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {currentResult.migration_plan && currentResult.migration_plan.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold mb-2">模拟迁移计划</h4>
                <div className="bg-gray-50 p-4 rounded">
                  <div className="text-sm text-gray-600 mb-2">
                    预计需要迁移 <strong>{currentResult.migration_plan.length}</strong> 个槽位，
                    约 <strong>{currentResult.estimated_migration_ms ? (currentResult.estimated_migration_ms / 1000).toFixed(1) : '未知'}</strong> 秒
                  </div>
                  <div className="overflow-x-auto max-h-40 overflow-y-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="border-b">
                          <th className="text-left py-1">槽位</th>
                          <th className="text-left py-1">源节点</th>
                          <th className="text-left py-1">目标节点</th>
                          <th className="text-right py-1">Key 数量</th>
                        </tr>
                      </thead>
                      <tbody>
                        {currentResult.migration_plan.slice(0, 20).map((task, idx) => (
                          <tr key={idx} className="border-b">
                            <td className="py-1 font-mono">{task.slot}</td>
                            <td className="py-1 font-mono text-xs">{task.from_node?.slice(0, 8)}</td>
                            <td className="py-1 font-mono text-xs">{task.to_node?.slice(0, 8)}</td>
                            <td className="py-1 text-right">{task.key_count || 0}</td>
                          </tr>
                        ))}
                        {currentResult.migration_plan.length > 20 && (
                          <tr>
                            <td colSpan="4" className="py-2 text-center text-gray-400">
                              ... 还有 {currentResult.migration_plan.length - 20} 个迁移任务
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {currentResult.recommendations && currentResult.recommendations.length > 0 && (
              <div>
                <h4 className="font-semibold mb-2">建议</h4>
                <ul className="space-y-2">
                  {currentResult.recommendations.map((rec, idx) => (
                    <li key={idx} className="flex items-start">
                      <span className="text-blue-500 mr-2">•</span>
                      <span className="text-gray-700">{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-lg font-semibold mb-3">模拟历史</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2">时间</th>
                <th className="text-left py-2">类型</th>
                <th className="text-left py-2">风险等级</th>
                <th className="text-right py-2">综合评分</th>
                <th className="text-left py-2">节点变化</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r, idx) => (
                <tr key={idx} className="border-b hover:bg-gray-50 cursor-pointer" onClick={() => setCurrentResult(r)}>
                  <td className="py-2">{r.created_at || '-'}</td>
                  <td className="py-2">{r.type || '-'}</td>
                  <td className="py-2">
                    <span className={`px-2 py-1 rounded text-xs font-medium border ${getRiskColor(r.risk_level)}`}>
                      {getRiskText(r.risk_level)}
                    </span>
                  </td>
                  <td className={`py-2 text-right font-medium ${
                    (r.overall_score || 0) > 70 ? 'text-green-600' :
                    (r.overall_score || 0) > 40 ? 'text-yellow-600' : 'text-red-600'
                  }`}>
                    {(r.overall_score || 0).toFixed(1)}
                  </td>
                  <td className="py-2">
                    {r.simulated_state?.total_nodes - (r.original_state?.total_nodes || 0) > 0 ? '+' : ''}
                    {r.simulated_state?.total_nodes - (r.original_state?.total_nodes || 0)} 节点
                  </td>
                </tr>
              ))}
              {results.length === 0 && (
                <tr>
                  <td colSpan="5" className="py-8 text-center text-gray-400">暂无模拟记录</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

import React, { useState, useEffect } from 'react'
import { api } from '../services/api'
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4']

export default function CostAnalysis({ nodes, onRefresh }) {
  const [currentCost, setCurrentCost] = useState(null)
  const [prediction, setPrediction] = useState(null)
  const [predType, setPredType] = useState('scaleup')
  const [nodeCount, setNodeCount] = useState(1)
  const [message, setMessage] = useState(null)
  const [loading, setLoading] = useState(false)

  const loadCurrentCost = async () => {
    try {
      const c = await api.getCurrentCost()
      setCurrentCost(c)
    } catch {}
  }

  useEffect(() => {
    loadCurrentCost()
  }, [])

  const handlePredict = async () => {
    setLoading(true)
    setMessage(null)
    setPrediction(null)
    try {
      let result
      switch (predType) {
        case 'scaleup':
          result = await api.predictScaleUp(nodeCount)
          break
        case 'scaledown':
          result = await api.predictScaleDown(nodeCount)
          break
        case 'rebalance':
          result = await api.predictRebalance()
          break
        case 'replica':
          result = await api.predictAddReplica(nodeCount)
          break
      }
      setPrediction(result)
    } catch (e) {
      setMessage({ type: 'error', text: e.message })
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (value) => {
    if (value === null || value === undefined) return '-'
    const currency = currentCost?.currency || 'CNY'
    const symbol = currency === 'CNY' ? '¥' : currency === 'USD' ? '$' : '€'
    return `${symbol}${value.toFixed(2)}`
  }

  const getNodeCostData = () => {
    if (!currentCost?.node_costs) return []
    return currentCost.node_costs.map((nc) => ({
      name: nc.node_id?.slice(0, 8) || 'unknown',
      cost: nc.hourly_cost || 0,
      memory: nc.memory_gb || 0,
      role: nc.role || 'unknown',
    }))
  }

  const getCostBreakdownData = () => {
    if (!currentCost) return []
    return [
      { name: '主节点', value: currentCost.total_master_hourly || 0 },
      { name: '从节点', value: currentCost.total_replica_hourly || 0 },
    ]
  }

  const masters = Array.isArray(nodes) ? nodes.filter((n) => n.role === 'master') : []
  const replicas = Array.isArray(nodes) ? nodes.filter((n) => n.role === 'slave') : []

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-6">成本分析与预测</h2>

      {message && (
        <div className={`mb-4 p-3 rounded ${message.type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
          {message.text}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">当前节点数</div>
          <div className="text-2xl font-bold text-blue-600">{masters.length + replicas.length}</div>
          <div className="text-xs text-gray-400">{masters.length} 主 / {replicas.length} 从</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">小时成本</div>
          <div className="text-2xl font-bold text-green-600">{formatCurrency(currentCost?.total_hourly)}</div>
          <div className="text-xs text-gray-400">{currentCost?.currency || 'CNY'}/小时</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">日成本</div>
          <div className="text-2xl font-bold text-yellow-600">{formatCurrency(currentCost?.total_daily)}</div>
          <div className="text-xs text-gray-400">24小时计算</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">月成本</div>
          <div className="text-2xl font-bold text-red-600">{formatCurrency(currentCost?.total_monthly)}</div>
          <div className="text-xs text-gray-400">30天计算</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-lg font-semibold mb-3">节点成本分布</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={getNodeCostData()}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" fontSize={12} />
              <YAxis fontSize={12} />
              <Tooltip formatter={(value) => formatCurrency(value)} />
              <Legend />
              <Bar dataKey="cost" fill="#3b82f6" name="小时成本" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-lg font-semibold mb-3">主从成本占比</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={getCostBreakdownData()}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {getCostBreakdownData().map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(value) => formatCurrency(value)} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <h3 className="text-lg font-semibold mb-3">成本预测</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">预测类型</label>
            <select
              value={predType}
              onChange={(e) => setPredType(e.target.value)}
              className="w-full border rounded px-3 py-2"
            >
              <option value="scaleup">扩容 (增加主节点)</option>
              <option value="scaledown">缩容 (减少主节点)</option>
              <option value="rebalance">重新平衡</option>
              <option value="replica">增加从节点</option>
            </select>
          </div>
          {predType !== 'rebalance' && (
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
          <div className="flex items-end">
            <button
              onClick={handlePredict}
              disabled={loading}
              className="w-full bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 disabled:bg-gray-300"
            >
              {loading ? '计算中...' : '预测成本'}
            </button>
          </div>
        </div>

        {prediction && (
          <div className="border-t pt-4">
            <h4 className="font-semibold mb-3">预测结果</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
              <div className="bg-gray-50 p-3 rounded">
                <div className="text-sm text-gray-500">操作类型</div>
                <div className="text-lg font-bold">{prediction.action}</div>
              </div>
              <div className="bg-gray-50 p-3 rounded">
                <div className="text-sm text-gray-500">节点变化</div>
                <div className={`text-lg font-bold ${prediction.node_diff > 0 ? 'text-red-600' : 'text-green-600'}`}>
                  {prediction.node_diff > 0 ? '+' : ''}{prediction.node_diff}
                </div>
              </div>
              <div className="bg-gray-50 p-3 rounded">
                <div className="text-sm text-gray-500">小时成本变化</div>
                <div className={`text-lg font-bold ${prediction.hourly_cost_diff > 0 ? 'text-red-600' : 'text-green-600'}`}>
                  {prediction.hourly_cost_diff > 0 ? '+' : ''}{formatCurrency(prediction.hourly_cost_diff)}
                </div>
              </div>
              <div className="bg-gray-50 p-3 rounded">
                <div className="text-sm text-gray-500">月成本变化</div>
                <div className={`text-lg font-bold ${prediction.monthly_cost_diff > 0 ? 'text-red-600' : 'text-green-600'}`}>
                  {prediction.monthly_cost_diff > 0 ? '+' : ''}{formatCurrency(prediction.monthly_cost_diff)}
                </div>
              </div>
            </div>

            {prediction.expected_memory_pct !== undefined && (
              <div className="bg-blue-50 p-3 rounded mb-3">
                <span className="font-medium">预期内存使用率：</span>
                <span className="text-blue-700 font-bold">{(prediction.expected_memory_pct * 100).toFixed(1)}%</span>
              </div>
            )}

            {prediction.roi !== undefined && (
              <div className="bg-green-50 p-3 rounded mb-3">
                <span className="font-medium">预期 ROI：</span>
                <span className="text-green-700 font-bold">{prediction.roi.toFixed(2)}</span>
              </div>
            )}

            {prediction.expected_impact && (
              <div className="bg-yellow-50 p-3 rounded">
                <span className="font-medium">预期性能影响：</span>
                <span className="text-yellow-700">{prediction.expected_impact}</span>
              </div>
            )}
          </div>
        )}
      </div>

      {currentCost?.node_costs && (
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-lg font-semibold mb-3">节点成本明细</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2">节点ID</th>
                  <th className="text-left py-2">地址</th>
                  <th className="text-left py-2">角色</th>
                  <th className="text-right py-2">内存 (GB)</th>
                  <th className="text-right py-2">每GB单价</th>
                  <th className="text-right py-2">角色系数</th>
                  <th className="text-right py-2">小时成本</th>
                  <th className="text-right py-2">月成本</th>
                </tr>
              </thead>
              <tbody>
                {currentCost.node_costs.map((nc, idx) => (
                  <tr key={idx} className="border-b hover:bg-gray-50">
                    <td className="py-2 font-mono text-xs">{nc.node_id?.slice(0, 8) || '-'}</td>
                    <td className="py-2">{nc.address || '-'}</td>
                    <td className="py-2">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        nc.role === 'master' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'
                      }`}>
                        {nc.role === 'master' ? '主节点' : '从节点'}
                      </span>
                    </td>
                    <td className="py-2 text-right">{(nc.memory_gb || 0).toFixed(2)}</td>
                    <td className="py-2 text-right">{formatCurrency(nc.price_per_gb_hour || 0)}</td>
                    <td className="py-2 text-right">{nc.role_multiplier?.toFixed(1) || '-'}</td>
                    <td className="py-2 text-right font-medium">{formatCurrency(nc.hourly_cost || 0)}</td>
                    <td className="py-2 text-right font-medium">{formatCurrency((nc.hourly_cost || 0) * 24 * 30)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

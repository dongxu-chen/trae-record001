import React, { useState, useEffect } from 'react'
import { api } from '../services/api'

export default function FailoverStatus({ nodes, onRefresh }) {
  const [health, setHealth] = useState([])
  const [events, setEvents] = useState([])
  const [selectedNode, setSelectedNode] = useState('')
  const [message, setMessage] = useState(null)
  const [busy, setBusy] = useState(false)

  const loadHealth = async () => {
    try {
      const h = await api.getFailoverHealth()
      setHealth(Array.isArray(h) ? h : [])
    } catch {}
  }

  const loadEvents = async () => {
    try {
      const e = await api.getFailoverEvents()
      setEvents(Array.isArray(e) ? e : [])
    } catch {}
  }

  useEffect(() => {
    loadHealth()
    loadEvents()
    const interval = setInterval(loadHealth, 5000)
    return () => clearInterval(interval)
  }, [])

  const handleTriggerFailover = async () => {
    if (!selectedNode) return
    setBusy(true)
    setMessage(null)
    try {
      await api.triggerFailover(selectedNode)
      setMessage({ type: 'success', text: 'Manual failover triggered' })
      loadEvents()
      setTimeout(onRefresh, 2000)
    } catch (e) {
      setMessage({ type: 'error', text: e.message })
    } finally {
      setBusy(false)
    }
  }

  const getHealthColor = (status) => {
    switch (status) {
      case 'healthy': return 'bg-green-100 text-green-800'
      case 'unhealthy': return 'bg-red-100 text-red-800'
      case 'failed': return 'bg-red-600 text-white'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getHealthText = (status) => {
    switch (status) {
      case 'healthy': return '健康'
      case 'unhealthy': return '不健康'
      case 'failed': return '故障'
      default: return '未知'
    }
  }

  const masters = Array.isArray(nodes) ? nodes.filter((n) => n.role === 'master') : []

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-6">自动故障转移</h2>

      {message && (
        <div className={`mb-4 p-3 rounded ${message.type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
          {message.text}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-lg font-semibold mb-3">节点健康状态</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2">节点ID</th>
                  <th className="text-left py-2">地址</th>
                  <th className="text-left py-2">角色</th>
                  <th className="text-left py-2">状态</th>
                  <th className="text-left py-2">延迟(ms)</th>
                  <th className="text-left py-2">连续失败</th>
                </tr>
              </thead>
              <tbody>
                {health.map((h, idx) => (
                  <tr key={idx} className="border-b hover:bg-gray-50">
                    <td className="py-2 font-mono text-xs">{h.node_id?.slice(0, 8) || '-'}</td>
                    <td className="py-2">{h.address || '-'}</td>
                    <td className="py-2">{h.role || '-'}</td>
                    <td className="py-2">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${getHealthColor(h.status)}`}>
                        {getHealthText(h.status)}
                      </span>
                    </td>
                    <td className="py-2">{h.latency_ms ?? '-'}</td>
                    <td className="py-2">{h.consecutive_failures ?? 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-lg font-semibold mb-3">手动故障转移</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                选择要故障转移的主节点
              </label>
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
            <button
              onClick={handleTriggerFailover}
              disabled={!selectedNode || busy}
              className="w-full bg-orange-500 text-white px-4 py-2 rounded hover:bg-orange-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              {busy ? '执行中...' : '触发手动故障转移'}
            </button>
            <div className="text-sm text-gray-500 bg-yellow-50 p-3 rounded">
              <strong>注意：</strong>手动故障转移会将所选主节点的从节点晋升为新的主节点，
              原主节点将变为从节点。此操作会导致短暂的连接中断。
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-lg font-semibold mb-3">故障转移事件</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2">时间</th>
                <th className="text-left py-2">类型</th>
                <th className="text-left py-2">原主节点</th>
                <th className="text-left py-2">新主节点</th>
                <th className="text-left py-2">状态</th>
                <th className="text-left py-2">详情</th>
              </tr>
            </thead>
            <tbody>
              {events.map((e, idx) => (
                <tr key={idx} className="border-b hover:bg-gray-50">
                  <td className="py-2">{e.timestamp || '-'}</td>
                  <td className="py-2">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      e.type === 'auto' ? 'bg-blue-100 text-blue-800' : 'bg-purple-100 text-purple-800'
                    }`}>
                      {e.type === 'auto' ? '自动' : '手动'}
                    </span>
                  </td>
                  <td className="py-2 font-mono text-xs">{e.old_master_id?.slice(0, 8) || '-'}</td>
                  <td className="py-2 font-mono text-xs">{e.new_master_id?.slice(0, 8) || '-'}</td>
                  <td className="py-2">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      e.status === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {e.status === 'success' ? '成功' : '失败'}
                    </span>
                  </td>
                  <td className="py-2 max-w-xs truncate">{e.details || '-'}</td>
                </tr>
              ))}
              {events.length === 0 && (
                <tr>
                  <td colSpan="6" className="py-8 text-center text-gray-400">暂无故障转移事件</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

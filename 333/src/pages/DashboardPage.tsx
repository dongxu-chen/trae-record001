import React, { useState, useEffect } from 'react'
import { useApp } from '../context/AppContext'
import { formatSpeed, formatLatency, formatFileSize } from '@shared/utils'

const DashboardPage: React.FC = () => {
  const { getDashboardData, getFormattedStats, dashboardData, connectionStatus, devices } = useApp()
  const [stats, setStats] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    loadStats()
    const interval = setInterval(loadStats, 1000)
    return () => clearInterval(interval)
  }, [dashboardData])

  const loadStats = async () => {
    try {
      const [formattedStats] = await Promise.all([
        getFormattedStats()
      ])
      setStats(formattedStats)
    } catch (e) {
      console.error('加载统计数据失败:', e)
    } finally {
      setIsLoading(false)
    }
  }

  const currentTransfers = dashboardData?.currentTransfers || []
  const networkStats = dashboardData?.networkStats
  const transferHistory = dashboardData?.transferHistory || []

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">同步速度仪表盘</h2>
          <p className="text-sm text-gray-500 mt-1">
            实时监控传输速度、延迟和连接状态
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full ${connectionStatus.isConnected ? 'bg-green-500' : 'bg-gray-400'}`}></div>
          <span className="text-sm text-gray-600">
            {connectionStatus.isConnected ? '已连接' : '未连接'}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <div className="card p-4 bg-gradient-to-br from-blue-500 to-blue-600 text-white">
          <div className="text-3xl font-bold">
            {stats?.currentSpeed || '0 B/s'}
          </div>
          <div className="text-xs opacity-80 mt-1">当前上传速度</div>
        </div>

        <div className="card p-4 bg-gradient-to-br from-green-500 to-green-600 text-white">
          <div className="text-3xl font-bold">
            {stats?.peakSpeed || '0 B/s'}
          </div>
          <div className="text-xs opacity-80 mt-1">峰值速度</div>
        </div>

        <div className="card p-4 bg-gradient-to-br from-purple-500 to-purple-600 text-white">
          <div className="text-3xl font-bold">
            {stats?.averageSpeed || '0 B/s'}
          </div>
          <div className="text-xs opacity-80 mt-1">平均速度</div>
        </div>

        <div className="card p-4 bg-gradient-to-br from-orange-500 to-orange-600 text-white">
          <div className="text-3xl font-bold">
            {stats?.activeTransfers || 0}
          </div>
          <div className="text-xs opacity-80 mt-1">活动传输</div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="card p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">📊 网络统计</h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-500">上传速度</span>
              <span className="font-medium">{formatSpeed(networkStats?.uploadSpeed || 0)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">下载速度</span>
              <span className="font-medium">{formatSpeed(networkStats?.downloadSpeed || 0)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">总上传</span>
              <span className="font-medium">{formatFileSize(networkStats?.totalUploaded || 0)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">总下载</span>
              <span className="font-medium">{formatFileSize(networkStats?.totalDownloaded || 0)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">平均延迟</span>
              <span className="font-medium">{formatLatency(networkStats?.averageLatency || 0)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">已连接设备</span>
              <span className="font-medium">{networkStats?.connectedPeers || 0}</span>
            </div>
          </div>
        </div>

        <div className="card p-4 col-span-2">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">🔄 当前传输</h3>
          {currentTransfers.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              暂无活动传输
            </div>
          ) : (
            <div className="space-y-3">
              {currentTransfers.map(transfer => (
                <div key={transfer.transferId} className="p-3 bg-gray-50 rounded-lg">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-medium text-sm">
                      {transfer.peerName}
                    </span>
                    <span className={`text-xs px-2 py-1 rounded ${
                      transfer.status === 'transferring' ? 'bg-blue-100 text-blue-700' :
                      transfer.status === 'completed' ? 'bg-green-100 text-green-700' :
                      'bg-red-100 text-red-700'
                    }`}>
                      {transfer.status}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                    <div 
                      className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${Math.min(100, (transfer.transferredBytes / transfer.totalBytes) * 100)}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>{formatFileSize(transfer.transferredBytes)} / {formatFileSize(transfer.totalBytes)}</span>
                    <span>{formatSpeed(transfer.currentSpeed)}</span>
                  </div>
                  <div className="flex gap-4 mt-1 text-xs text-gray-400">
                    <span>延迟: {formatLatency(transfer.latency)}</span>
                    <span>分片: {transfer.transferredChunks}/{transfer.totalChunks}</span>
                    <span>失败: {transfer.failedChunks}</span>
                    <span>重试: {transfer.retriedChunks}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="card p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">📱 已连接设备</h3>
        <div className="grid grid-cols-2 gap-3">
          {devices.map(device => (
            <div 
              key={device.id} 
              className={`p-3 rounded-lg border ${
                device.isOnline 
                  ? 'border-green-200 bg-green-50' 
                  : 'border-gray-200 bg-gray-50'
              }`}
            >
              <div className="flex justify-between items-center">
                <span className="font-medium">{device.name}</span>
                <div className="flex items-center gap-1">
                  <div className={`w-2 h-2 rounded-full ${device.isOnline ? 'bg-green-500' : 'bg-gray-400'}`}></div>
                  <span className="text-xs text-gray-500">
                    {device.isOnline ? '在线' : '离线'}
                  </span>
                </div>
              </div>
              <div className="text-xs text-gray-500 mt-1">
                {device.isLocal ? '局域网' : '远程'} | {device.connectionMode || '未知'}
              </div>
            </div>
          ))}
          {devices.length === 0 && (
            <div className="col-span-2 text-center py-4 text-gray-400">
              暂无已连接设备
            </div>
          )}
        </div>
      </div>

      <div className="card p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">📜 传输历史</h3>
        {transferHistory.length === 0 ? (
          <div className="text-center py-4 text-gray-400">
            暂无传输记录
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 px-2">设备</th>
                  <th className="text-left py-2 px-2">大小</th>
                  <th className="text-left py-2 px-2">平均速度</th>
                  <th className="text-left py-2 px-2">峰值速度</th>
                  <th className="text-left py-2 px-2">状态</th>
                  <th className="text-left py-2 px-2">耗时</th>
                </tr>
              </thead>
              <tbody>
                {transferHistory.slice(-10).reverse().map(transfer => (
                  <tr key={transfer.transferId} className="border-b hover:bg-gray-50">
                    <td className="py-2 px-2">{transfer.peerName}</td>
                    <td className="py-2 px-2">{formatFileSize(transfer.totalBytes)}</td>
                    <td className="py-2 px-2">{formatSpeed(transfer.averageSpeed)}</td>
                    <td className="py-2 px-2">{formatSpeed(transfer.peakSpeed)}</td>
                    <td className="py-2 px-2">
                      <span className={`px-2 py-0.5 rounded text-xs ${
                        transfer.status === 'completed' ? 'bg-green-100 text-green-700' :
                        'bg-red-100 text-red-700'
                      }`}>
                        {transfer.status === 'completed' ? '成功' : '失败'}
                      </span>
                    </td>
                    <td className="py-2 px-2">
                      {transfer.endTime && transfer.startTime 
                        ? `${Math.round((transfer.endTime - transfer.startTime) / 1000)}s`
                        : '-'
                      }
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

export default DashboardPage

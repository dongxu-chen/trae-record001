import React from 'react'
import { useApp } from '../context/AppContext'
import { formatTimestamp } from '@shared/utils'

const DevicesPage: React.FC = () => {
  const { devices, connectionStatus, connect, disconnect, settings } = useApp()

  const handleConnect = async () => {
    await connect()
  }

  const handleDisconnect = async () => {
    await disconnect()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">设备管理</h2>
          <p className="text-sm text-gray-500 mt-1">
            管理您的同步设备，当前共 {devices.length} 台设备
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          {connectionStatus.isConnected ? (
            <button onClick={handleDisconnect} className="btn-danger">
              🔌 断开连接
            </button>
          ) : (
            <button onClick={handleConnect} className="btn-primary">
              🔗 连接同步网络
            </button>
          )}
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <div className="card p-6">
          <div className="flex items-center gap-4 mb-4">
            <div className="w-16 h-16 bg-blue-100 rounded-xl flex items-center justify-center text-3xl">
              💻
            </div>
            <div>
              <h3 className="font-semibold text-gray-800">当前设备</h3>
              <p className="text-sm text-gray-500">本机</p>
            </div>
          </div>
          
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">设备名称</span>
              <span className="font-medium text-gray-800">{settings.deviceName || '未命名'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">设备类型</span>
              <span className="font-medium text-gray-800">桌面端</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">状态</span>
              <span className={`font-medium ${
                connectionStatus.isConnected ? 'text-green-600' : 'text-gray-400'
              }`}>
                {connectionStatus.isConnected ? '已连接' : '未连接'}
              </span>
            </div>
          </div>
          
          <div className="mt-4 pt-4 border-t border-gray-100">
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full bg-green-500 animate-pulse-dot`} />
              <span className="text-sm text-gray-600">
                已连接 {connectionStatus.connectedDevices} 台设备
              </span>
            </div>
          </div>
        </div>

        <div className="md:col-span-2 card p-6">
          <h3 className="font-semibold text-gray-800 mb-4">信令服务器</h3>
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <div className={`w-3 h-3 rounded-full ${
                connectionStatus.isConnected ? 'bg-green-500' : 'bg-red-500'
              }`} />
              <div className="flex-1">
                <div className="font-medium text-gray-800">{settings.signalingServer}</div>
                <div className="text-sm text-gray-500">
                  {connectionStatus.isConnected ? '连接成功' : '无法连接'}
                </div>
              </div>
            </div>
            
            <div className="p-4 bg-blue-50 rounded-lg">
              <div className="text-sm text-blue-800">
                💡 <strong>提示：</strong>确保所有设备使用相同的加密密钥和信令服务器地址才能正常同步。
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="p-6 border-b border-gray-100">
          <h3 className="font-semibold text-gray-800">在线设备</h3>
          <p className="text-sm text-gray-500 mt-1">与您在同一同步网络中的设备</p>
        </div>
        
        {devices.length === 0 ? (
          <div className="p-12 text-center">
            <div className="text-6xl mb-4">🔍</div>
            <h3 className="text-xl font-semibold text-gray-700 mb-2">暂无发现其他设备</h3>
            <p className="text-gray-500">
              请确保其他设备也已连接到同一信令服务器并使用相同的加密密钥
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {devices.map(device => (
              <div key={device.id} className="p-6 flex items-center gap-4 hover:bg-gray-50 transition-colors">
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-2xl ${
                  device.isOnline ? 'bg-green-100' : 'bg-gray-100'
                }`}>
                  {device.type === 'mobile' ? '📱' : '💻'}
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h4 className="font-medium text-gray-800 truncate">{device.name}</h4>
                    {device.isLocal && (
                      <span className="badge bg-blue-100 text-blue-600">局域网</span>
                    )}
                  </div>
                  <div className="text-sm text-gray-500 mt-0.5">
                    {device.type === 'mobile' ? '移动设备' : '桌面设备'} · 
                    最后在线: {formatTimestamp(device.lastSeen)}
                  </div>
                </div>
                
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${
                      device.isOnline ? 'bg-green-500 animate-pulse-dot' : 'bg-gray-300'
                    }`} />
                    <span className={`text-sm ${
                      device.isOnline ? 'text-green-600' : 'text-gray-400'
                    }`}>
                      {device.isOnline ? '在线' : '离线'}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card p-6">
        <h3 className="font-semibold text-gray-800 mb-4">连接说明</h3>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-3">
            <h4 className="font-medium text-gray-700">局域网传输优先</h4>
            <p className="text-sm text-gray-500">
              当检测到设备在同一局域网时，系统会自动优先使用局域网进行数据传输，
              以获得更快的传输速度和更好的隐私保护。
            </p>
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <span className="text-green-500">✓</span>
              <span>自动检测局域网设备</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <span className="text-green-500">✓</span>
              <span>优先局域网直连传输</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <span className="text-green-500">✓</span>
              <span>支持仅局域网模式</span>
            </div>
          </div>
          
          <div className="space-y-3">
            <h4 className="font-medium text-gray-700">端到端加密</h4>
            <p className="text-sm text-gray-500">
              所有数据在传输前都会使用 AES-256-GCM 算法进行加密，
              只有拥有正确密钥的设备才能解密和读取内容。
            </p>
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <span className="text-green-500">✓</span>
              <span>AES-256-GCM 加密</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <span className="text-green-500">✓</span>
              <span>密钥由用户自主管理</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <span className="text-green-500">✓</span>
              <span>服务器无法解密数据</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default DevicesPage

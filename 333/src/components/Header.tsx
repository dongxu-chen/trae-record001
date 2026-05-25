import React from 'react'
import { useApp } from '../context/AppContext'
import { ClipboardDataType } from '@shared/types'

const Header: React.FC = () => {
  const { connectionStatus, isSyncing, history, settings } = useApp()

  const stats = {
    total: history.length,
    text: history.filter(h => h.content.type === ClipboardDataType.TEXT).length,
    images: history.filter(h => h.content.type === ClipboardDataType.IMAGE).length,
    files: history.filter(h => 
      h.content.type === ClipboardDataType.FILE || 
      h.content.type === ClipboardDataType.FILES
    ).length,
    favorites: history.filter(h => h.favorite).length
  }

  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center px-6 justify-between">
      <div className="flex items-center gap-6">
        <h1 className="text-lg font-semibold text-gray-800">剪贴板同步</h1>
        
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${
              connectionStatus.isConnected ? 'bg-green-500' : 'bg-gray-400'
            } ${connectionStatus.isConnected ? 'animate-pulse-dot' : ''}`} />
            <span className="text-gray-600">
              {connectionStatus.isConnected 
                ? `已连接 (${connectionStatus.connectedDevices} 台设备)` 
                : '未连接'}
            </span>
          </div>
          
          {isSyncing && (
            <div className="flex items-center gap-2 text-primary-600">
              <span className="animate-spin">⟳</span>
              <span>同步中...</span>
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-4 text-sm text-gray-500">
        <div className="hidden md:flex items-center gap-4">
          <span>📝 {stats.text} 文本</span>
          <span>🖼️ {stats.images} 图片</span>
          <span>📁 {stats.files} 文件</span>
          <span>⭐ {stats.favorites} 收藏</span>
        </div>
        
        <div className="text-gray-400">|</div>
        
        <div>
          当前设备: <span className="text-gray-700 font-medium">{settings.deviceName || '未命名'}</span>
        </div>
      </div>
    </header>
  )
}

export default Header

import React, { useState } from 'react'
import type { HistoryItem, ClipboardContent, FileData } from '@shared/types'
import { ClipboardDataType } from '@shared/types'
import { formatTimestamp, formatFileSize } from '@shared/utils'
import { useApp } from '../context/AppContext'

interface HistoryItemCardProps {
  item: HistoryItem
  onSelect?: (content: ClipboardContent) => void
}

const HistoryItemCard: React.FC<HistoryItemCardProps> = ({ item, onSelect }) => {
  const { copyToClipboard, deleteHistoryItem, toggleFavorite, sendToDevice, devices } = useApp()
  const [showMenu, setShowMenu] = useState(false)
  const [showSendMenu, setShowSendMenu] = useState(false)

  const getTypeIcon = (type: ClipboardDataType) => {
    switch (type) {
      case ClipboardDataType.TEXT:
        return '📝'
      case ClipboardDataType.IMAGE:
        return '🖼️'
      case ClipboardDataType.FILE:
      case ClipboardDataType.FILES:
        return '📁'
      default:
        return '📋'
    }
  }

  const getTypeLabel = (type: ClipboardDataType) => {
    switch (type) {
      case ClipboardDataType.TEXT:
        return '文本'
      case ClipboardDataType.IMAGE:
        return '图片'
      case ClipboardDataType.FILE:
        return '文件'
      case ClipboardDataType.FILES:
        return '多文件'
      default:
        return '未知'
    }
  }

  const getPreviewContent = () => {
    const { content } = item
    
    switch (content.type) {
      case ClipboardDataType.TEXT: {
        const text = content.data as string
        return (
          <div className="text-sm text-gray-700 line-clamp-3 font-mono bg-gray-50 p-3 rounded-lg">
            {text.length > 500 ? text.substring(0, 500) + '...' : text}
          </div>
        )
      }
      
      case ClipboardDataType.IMAGE: {
        const imageData = content.data as FileData
        return (
          <div className="relative">
            <img 
              src={`data:${imageData.type};base64,${imageData.data}`}
              alt="剪贴板图片"
              className="max-h-48 rounded-lg object-contain bg-gray-100 w-full"
            />
          </div>
        )
      }
      
      case ClipboardDataType.FILE:
      case ClipboardDataType.FILES: {
        const files = Array.isArray(content.data) ? content.data as FileData[] : [content.data as FileData]
        return (
          <div className="space-y-2">
            {files.map((file, index) => (
              <div key={index} className="flex items-center gap-3 bg-gray-50 p-3 rounded-lg">
                <span className="text-2xl">📄</span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-gray-800 truncate">{file.name}</div>
                  <div className="text-xs text-gray-500">{formatFileSize(file.size)} · {file.type}</div>
                </div>
              </div>
            ))}
          </div>
        )
      }
      
      default:
        return <div className="text-gray-400">不支持的内容类型</div>
    }
  }

  const handleCopy = async () => {
    await copyToClipboard(item.content)
    setShowMenu(false)
  }

  const handleDelete = async () => {
    await deleteHistoryItem(item.id)
    setShowMenu(false)
  }

  const handleToggleFavorite = async () => {
    await toggleFavorite(item.id)
  }

  const handleSend = async (deviceId: string) => {
    await sendToDevice(deviceId, item.content)
    setShowSendMenu(false)
    setShowMenu(false)
  }

  const handleClick = () => {
    if (onSelect) {
      onSelect(item.content)
    } else {
      handleCopy()
    }
  }

  const onlineDevices = devices.filter(d => d.isOnline)

  return (
    <div className="card p-4 hover:shadow-md transition-shadow duration-200 animate-fade-in">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{getTypeIcon(item.content.type)}</span>
          <div>
            <div className="flex items-center gap-2">
              <span className="badge bg-gray-100 text-gray-600">
                {getTypeLabel(item.content.type)}
              </span>
              {item.favorite && (
                <span className="text-yellow-500">⭐</span>
              )}
            </div>
            <div className="text-xs text-gray-400 mt-1">
              {formatTimestamp(item.createdAt)} · 来自 {item.content.deviceName}
            </div>
          </div>
        </div>
        
        <div className="relative">
          <button
            onClick={(e) => {
              e.stopPropagation()
              setShowMenu(!showMenu)
            }}
            className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-400 hover:text-gray-600"
          >
            ⋮
          </button>
          
          {showMenu && (
            <>
              <div 
                className="fixed inset-0 z-10" 
                onClick={() => {
                  setShowMenu(false)
                  setShowSendMenu(false)
                }}
              />
              <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-100 py-1 z-20 animate-fade-in">
                <button
                  onClick={handleCopy}
                  className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                >
                  📋 复制到剪贴板
                </button>
                
                <button
                  onClick={handleToggleFavorite}
                  className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                >
                  {item.favorite ? '💔 取消收藏' : '⭐ 添加收藏'}
                </button>
                
                {onlineDevices.length > 0 && (
                  <div className="relative">
                    <button
                      onClick={() => setShowSendMenu(!showSendMenu)}
                      className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center justify-between"
                    >
                      <span className="flex items-center gap-2">📤 发送到设备</span>
                      <span className="text-gray-400">→</span>
                    </button>
                    
                    {showSendMenu && (
                      <>
                        <div 
                          className="fixed inset-0 z-10" 
                          style={{ top: 0, left: 0 }}
                          onClick={() => setShowSendMenu(false)}
                        />
                        <div className="absolute left-full top-0 ml-1 w-48 bg-white rounded-lg shadow-lg border border-gray-100 py-1 z-30 animate-fade-in">
                          {onlineDevices.map(device => (
                            <button
                              key={device.id}
                              onClick={() => handleSend(device.id)}
                              className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                            >
                              <span className={`w-2 h-2 rounded-full ${device.isOnline ? 'bg-green-500' : 'bg-gray-300'}`} />
                              {device.name}
                              {device.isLocal && (
                                <span className="badge bg-blue-100 text-blue-600 ml-auto">LAN</span>
                              )}
                            </button>
                          ))}
                        </div>
                      </>
                    )}
                  </div>
                )}
                
                <div className="border-t border-gray-100 my-1" />
                
                <button
                  onClick={handleDelete}
                  className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
                >
                  🗑️ 删除
                </button>
              </div>
            </>
          )}
        </div>
      </div>
      
      <div onClick={handleClick} className="cursor-pointer">
        {getPreviewContent()}
      </div>
    </div>
  )
}

export default HistoryItemCard

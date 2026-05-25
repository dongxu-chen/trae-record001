import React, { useState, useEffect, useRef } from 'react'
import type { ClipboardContent } from '@shared/types'
import { ClipboardDataType } from '@shared/types'
import { useApp } from '../context/AppContext'
import HistoryItemCard from './HistoryItemCard'

interface QuickPasteModalProps {
  onClose: () => void
}

const QuickPasteModal: React.FC<QuickPasteModalProps> = ({ onClose }) => {
  const { history, copyToClipboard, searchQuery, setSearchQuery, selectedFilter, setSelectedFilter } = useApp()
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      } else if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedIndex(prev => Math.min(prev + 1, filteredHistory.length - 1))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIndex(prev => Math.max(prev - 1, 0))
      } else if (e.key === 'Enter') {
        e.preventDefault()
        if (filteredHistory[selectedIndex]) {
          handleSelect(filteredHistory[selectedIndex].content)
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedIndex, onClose])

  useEffect(() => {
    setSelectedIndex(0)
  }, [searchQuery, selectedFilter])

  const filteredHistory = history.filter(item => {
    if (selectedFilter === 'favorites') {
      return item.favorite
    }
    
    if (selectedFilter === 'all') {
      return true
    }
    
    if (selectedFilter === 'file') {
      return item.content.type === ClipboardDataType.FILE || item.content.type === ClipboardDataType.FILES
    }
    
    return item.content.type === ClipboardDataType[selectedFilter.toUpperCase() as keyof typeof ClipboardDataType]
  }).filter(item => {
    if (!searchQuery) return true
    
    const query = searchQuery.toLowerCase()
    
    if (item.content.deviceName.toLowerCase().includes(query)) return true
    
    switch (item.content.type) {
      case ClipboardDataType.TEXT:
        return (item.content.data as string).toLowerCase().includes(query)
      case ClipboardDataType.IMAGE:
      case ClipboardDataType.FILE:
      case ClipboardDataType.FILES:
        const files = Array.isArray(item.content.data) 
          ? item.content.data as any[] 
          : [item.content.data]
        return files.some(f => f.name.toLowerCase().includes(query))
      default:
        return false
    }
  })

  const handleSelect = async (content: ClipboardContent) => {
    await copyToClipboard(content)
    onClose()
  }

  const filters = [
    { key: 'all', label: '全部' },
    { key: 'text', label: '📝 文本' },
    { key: 'image', label: '🖼️ 图片' },
    { key: 'file', label: '📁 文件' },
    { key: 'favorites', label: '⭐ 收藏' }
  ]

  return (
    <div className="fixed inset-0 bg-black/50 flex items-start justify-center pt-24 z-50" onClick={onClose}>
      <div 
        ref={containerRef}
        className="w-full max-w-2xl bg-white rounded-2xl shadow-2xl overflow-hidden animate-fade-in"
        onClick={e => e.stopPropagation()}
      >
        <div className="p-4 border-b border-gray-100">
          <div className="flex items-center gap-3 mb-4">
          <span className="text-2xl">⌨️</span>
          <h2 className="text-lg font-semibold text-gray-800">快速粘贴</h2>
          <span className="ml-auto text-xs text-gray-400">
            按 <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-gray-600">Esc</kbd> 关闭 · 
            <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-gray-600 ml-1">↑↓</kbd> 选择 · 
            <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-gray-600 ml-1">Enter</kbd> 粘贴
          </span>
        </div>

        <div className="relative">
          <input
            ref={inputRef}
            type="text"
            placeholder="搜索剪贴板历史..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
          <span className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400">🔍</span>
        </div>

        <div className="flex gap-2 mt-3 overflow-x-auto pb-1">
          {filters.map(filter => (
            <button
              key={filter.key}
              onClick={() => setSelectedFilter(filter.key as typeof selectedFilter)}
              className={`px-3 py-1.5 rounded-lg text-sm whitespace-nowrap transition-colors ${
                selectedFilter === filter.key
                  ? 'bg-primary-500 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {filter.label}
            </button>
          ))}
        </div>
      </div>

      <div className="max-h-96 overflow-y-auto p-4 space-y-3 scrollbar-thin">
        {filteredHistory.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <div className="text-4xl mb-3">📭</div>
            <div>暂无剪贴板历史</div>
          </div>
        ) : (
            filteredHistory.map((item, index) => (
              <div
                key={item.id}
                className={`${
                  index === selectedIndex ? 'ring-2 ring-primary-500 rounded-xl' : ''} transition-all`}
                onClick={() => handleSelect(item.content)}
              >
                <HistoryItemCard 
                  item={item} 
                  onSelect={handleSelect}
                />
              </div>
            )
        )}
      </div>
      </div>
    </div>
  )
}

export default QuickPasteModal

import React, { useMemo } from 'react'
import { useApp } from '../context/AppContext'
import HistoryItemCard from '../components/HistoryItemCard'
import { ClipboardDataType } from '@shared/types'

const HistoryPage: React.FC = () => {
  const { 
    history, 
    searchQuery, 
    setSearchQuery, 
    selectedFilter, 
    setSelectedFilter,
    clearHistory
  } = useApp()

  const filteredHistory = useMemo(() => {
    return history.filter(item => {
      if (selectedFilter === 'favorites') {
        return item.favorite
      }
      
      if (selectedFilter === 'all') {
        return true
      }
      
      if (selectedFilter === 'file') {
        return item.content.type === ClipboardDataType.FILE || 
               item.content.type === ClipboardDataType.FILES
      }
      
      return item.content.type === ClipboardDataType[
        selectedFilter.toUpperCase() as keyof typeof ClipboardDataType
      ]
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
  }, [history, searchQuery, selectedFilter])

  const filters = [
    { key: 'all', label: '全部', count: history.length },
    { key: 'text', label: '📝 文本', count: history.filter(h => h.content.type === ClipboardDataType.TEXT).length },
    { key: 'image', label: '🖼️ 图片', count: history.filter(h => h.content.type === ClipboardDataType.IMAGE).length },
    { key: 'file', label: '📁 文件', count: history.filter(h => 
      h.content.type === ClipboardDataType.FILE || h.content.type === ClipboardDataType.FILES
    ).length },
    { key: 'favorites', label: '⭐ 收藏', count: history.filter(h => h.favorite).length }
  ]

  const handleClearHistory = async () => {
    const confirmed = window.confirm('确定要清空所有剪贴板历史吗？此操作不可恢复。')
    if (confirmed) {
      await clearHistory()
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">剪贴板历史</h2>
          <p className="text-sm text-gray-500 mt-1">
            共 {history.length} 条记录，{filteredHistory.length} 条匹配
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="relative">
            <input
              type="text"
              placeholder="搜索..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-64 px-4 py-2 pr-10 bg-white border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">🔍</span>
          </div>
          
          <button
            onClick={handleClearHistory}
            className="btn-danger"
            disabled={history.length === 0}
          >
            🗑️ 清空历史
          </button>
        </div>
      </div>

      <div className="flex gap-2 overflow-x-auto pb-2">
        {filters.map(filter => (
          <button
            key={filter.key}
            onClick={() => setSelectedFilter(filter.key as typeof selectedFilter)}
            className={`px-4 py-2 rounded-lg text-sm whitespace-nowrap transition-all flex items-center gap-2 ${
              selectedFilter === filter.key
                ? 'bg-primary-500 text-white shadow-md'
                : 'bg-white text-gray-600 hover:bg-gray-50 border border-gray-200'
            }`}
          >
            {filter.label}
            <span className={`px-1.5 py-0.5 rounded text-xs ${
              selectedFilter === filter.key
                ? 'bg-white/20'
                : 'bg-gray-100'
            }`}>
              {filter.count}
            </span>
          </button>
        ))}
      </div>

      {filteredHistory.length === 0 ? (
        <div className="card p-12 text-center">
          <div className="text-6xl mb-4">📭</div>
          <h3 className="text-xl font-semibold text-gray-700 mb-2">
            {searchQuery ? '没有找到匹配的记录' : '暂无剪贴板历史'}
          </h3>
          <p className="text-gray-500">
            {searchQuery 
              ? '尝试使用其他关键词搜索' 
              : '复制一些内容，它们会显示在这里'}
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filteredHistory.map(item => (
            <HistoryItemCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  )
}

export default HistoryPage

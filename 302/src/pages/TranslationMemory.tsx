import React, { useState, useEffect } from 'react'
import { useApp } from '../contexts/AppContext'
import { LanguageSelector } from '../components/LanguageSelector'
import { TranslationMemory, LanguageCode } from '../types'
import { translationMemoryDB } from '../services/database'
import { LANGUAGE_MAP } from '../constants'

export const TranslationMemoryPage: React.FC = () => {
  const { dbReady } = useApp()
  
  const [memories, setMemories] = useState<TranslationMemory[]>([])
  const [searchText, setSearchText] = useState('')
  const [filterSourceLang, setFilterSourceLang] = useState<LanguageCode | ''>('')
  const [filterTargetLang, setFilterTargetLang] = useState<LanguageCode | ''>('')
  const [sortBy, setSortBy] = useState<'usage' | 'recent'>('usage')

  useEffect(() => {
    if (dbReady) {
      loadMemories()
    }
  }, [dbReady])

  const loadMemories = async () => {
    try {
      let allMemories = await translationMemoryDB.getAll()
      
      if (searchText) {
        allMemories = allMemories.filter(
          m => m.sourceText.toLowerCase().includes(searchText.toLowerCase()) ||
               m.translatedText.toLowerCase().includes(searchText.toLowerCase())
        )
      }
      if (filterSourceLang) {
        allMemories = allMemories.filter(m => m.sourceLang === filterSourceLang)
      }
      if (filterTargetLang) {
        allMemories = allMemories.filter(m => m.targetLang === filterTargetLang)
      }
      
      if (sortBy === 'usage') {
        allMemories.sort((a, b) => b.usageCount - a.usageCount || b.lastUsedAt - a.lastUsedAt)
      } else {
        allMemories.sort((a, b) => b.lastUsedAt - a.lastUsedAt)
      }
      
      setMemories(allMemories)
    } catch (err) {
      console.error('Failed to load memories:', err)
    }
  }

  useEffect(() => {
    loadMemories()
  }, [searchText, filterSourceLang, filterTargetLang, sortBy])

  const handleDeleteMemory = async (id: number) => {
    if (!confirm('确定要删除这条翻译记忆吗？')) return
    
    try {
      await translationMemoryDB.delete(id)
      await loadMemories()
    } catch (err) {
      alert('删除失败')
    }
  }

  const handleClearAll = async () => {
    if (!confirm('确定要清空所有翻译记忆吗？此操作不可恢复！')) return
    
    try {
      await translationMemoryDB.clear()
      await loadMemories()
    } catch (err) {
      alert('清空失败')
    }
  }

  const stats = {
    total: memories.length,
    totalUsage: memories.reduce((sum, m) => sum + m.usageCount, 0),
    langPairs: new Set(memories.map(m => `${m.sourceLang}-${m.targetLang}`)).size,
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="grid md:grid-cols-3 gap-6 mb-6">
        <div className="bg-white rounded-2xl shadow-xl p-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
              <span className="text-2xl">💾</span>
            </div>
            <div>
              <p className="text-sm text-gray-500">记忆条目</p>
              <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-2xl shadow-xl p-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center">
              <span className="text-2xl">🔄</span>
            </div>
            <div>
              <p className="text-sm text-gray-500">总使用次数</p>
              <p className="text-2xl font-bold text-gray-900">{stats.totalUsage}</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-2xl shadow-xl p-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center">
              <span className="text-2xl">🌐</span>
            </div>
            <div>
              <p className="text-sm text-gray-500">语言对</p>
              <p className="text-2xl font-bold text-gray-900">{stats.langPairs}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-xl p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <span>💾</span> 翻译记忆库
          </h2>
          <button
            onClick={handleClearAll}
            disabled={memories.length === 0}
            className="text-sm text-red-500 hover:text-red-700 disabled:opacity-50"
          >
            清空所有
          </button>
        </div>

        <div className="bg-gray-50 rounded-xl p-4 mb-6">
          <div className="grid md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">搜索</label>
              <input
                type="text"
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                placeholder="搜索记忆..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <LanguageSelector
              value={(filterSourceLang || 'en') as LanguageCode}
              onChange={(l) => setFilterSourceLang(l)}
              label="源语言"
            />
            <LanguageSelector
              value={(filterTargetLang || 'zh') as LanguageCode}
              onChange={(l) => setFilterTargetLang(l)}
              label="目标语言"
            />
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">排序</label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as 'usage' | 'recent')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="usage">使用频率</option>
                <option value="recent">最近使用</option>
              </select>
            </div>
          </div>
          <div className="flex justify-between items-center mt-4">
            <span className="text-sm text-gray-500">共 {memories.length} 条记忆</span>
          </div>
        </div>

        {memories.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <div className="text-5xl mb-4">💾</div>
            <p>暂无翻译记忆</p>
            <p className="text-sm mt-2">翻译内容会自动保存到记忆库</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50">
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">源语言</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">源文本</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">目标语言</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">译文</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-gray-700">使用次数</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">最近使用</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-700">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {memories.map((memory) => (
                  <tr key={memory.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm">
                      <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded-full text-xs">
                        {LANGUAGE_MAP[memory.sourceLang].nativeName}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-medium max-w-xs truncate" title={memory.sourceText}>
                      {memory.sourceText}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span className="px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs">
                        {LANGUAGE_MAP[memory.targetLang].nativeName}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600 max-w-xs truncate" title={memory.translatedText}>
                      {memory.translatedText}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded-full text-sm font-medium">
                        {memory.usageCount}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {new Date(memory.lastUsedAt).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => handleDeleteMemory(memory.id!)}
                        className="text-red-500 hover:text-red-700"
                      >
                        🗑️
                      </button>
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

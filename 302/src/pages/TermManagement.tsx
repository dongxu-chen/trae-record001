import React, { useState, useEffect } from 'react'
import { useApp } from '../contexts/AppContext'
import { LanguageSelector } from '../components/LanguageSelector'
import { TermEntry, LanguageCode } from '../types'
import { termDB } from '../services/database'
import { exportTerms, importTerms } from '../services/documentService'
import { LANGUAGE_MAP } from '../constants'

export const TermManagement: React.FC = () => {
  const { dbReady } = useApp()
  
  const [terms, setTerms] = useState<TermEntry[]>([])
  const [searchText, setSearchText] = useState('')
  const [filterSourceLang, setFilterSourceLang] = useState<LanguageCode | ''>('')
  const [filterTargetLang, setFilterTargetLang] = useState<LanguageCode | ''>('')
  const [filterDomain, setFilterDomain] = useState('')
  const [isAdding, setIsAdding] = useState(false)
  const [editingTerm, setEditingTerm] = useState<TermEntry | null>(null)
  const [newTerm, setNewTerm] = useState({
    sourceText: '',
    translatedText: '',
    sourceLang: 'en' as LanguageCode,
    targetLang: 'zh' as LanguageCode,
    domain: '',
  })
  const [isImporting, setIsImporting] = useState(false)
  const fileInputRef = React.useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (dbReady) {
      loadTerms()
    }
  }, [dbReady])

  const loadTerms = async () => {
    try {
      let allTerms = await termDB.getAll()
      
      if (searchText) {
        allTerms = allTerms.filter(
          t => t.sourceText.toLowerCase().includes(searchText.toLowerCase()) ||
               t.translatedText.toLowerCase().includes(searchText.toLowerCase())
        )
      }
      if (filterSourceLang) {
        allTerms = allTerms.filter(t => t.sourceLang === filterSourceLang)
      }
      if (filterTargetLang) {
        allTerms = allTerms.filter(t => t.targetLang === filterTargetLang)
      }
      if (filterDomain) {
        allTerms = allTerms.filter(t => t.domain?.toLowerCase().includes(filterDomain.toLowerCase()))
      }
      
      setTerms(allTerms.sort((a, b) => b.updatedAt - a.updatedAt))
    } catch (err) {
      console.error('Failed to load terms:', err)
    }
  }

  useEffect(() => {
    loadTerms()
  }, [searchText, filterSourceLang, filterTargetLang, filterDomain])

  const handleAddTerm = async () => {
    if (!newTerm.sourceText.trim() || !newTerm.translatedText.trim()) {
      alert('请填写源文本和译文本')
      return
    }

    try {
      await termDB.add({
        ...newTerm,
        createdAt: Date.now(),
        updatedAt: Date.now(),
      })
      setNewTerm({
        sourceText: '',
        translatedText: '',
        sourceLang: 'en',
        targetLang: 'zh',
        domain: '',
      })
      setIsAdding(false)
      await loadTerms()
    } catch (err) {
      alert('添加失败')
    }
  }

  const handleUpdateTerm = async () => {
    if (!editingTerm) return
    
    try {
      await termDB.update({
        ...editingTerm,
        updatedAt: Date.now(),
      })
      setEditingTerm(null)
      await loadTerms()
    } catch (err) {
      alert('更新失败')
    }
  }

  const handleDeleteTerm = async (id: number) => {
    if (!confirm('确定要删除这个术语吗？')) return
    
    try {
      await termDB.delete(id)
      await loadTerms()
    } catch (err) {
      alert('删除失败')
    }
  }

  const handleExport = () => {
    exportTerms(terms)
  }

  const handleImportClick = () => {
    fileInputRef.current?.click()
  }

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setIsImporting(true)
    try {
      const importedTerms = await importTerms(file)
      for (const term of importedTerms) {
        const existing = await termDB.findExact(term.sourceText, term.sourceLang, term.targetLang)
        if (!existing) {
          await termDB.add(term)
        }
      }
      await loadTerms()
      alert(`成功导入 ${importedTerms.length} 条术语`)
    } catch (err) {
      alert('导入失败')
    } finally {
      setIsImporting(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleClearAll = async () => {
    if (!confirm('确定要清空所有术语吗？此操作不可恢复！')) return
    
    try {
      await termDB.clear()
      await loadTerms()
    } catch (err) {
      alert('清空失败')
    }
  }

  const domains = [...new Set(terms.map(t => t.domain).filter(Boolean))]

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="bg-white rounded-2xl shadow-xl p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <span>📚</span> 术语库管理
          </h2>
          <div className="flex gap-2">
            <button
              onClick={handleImportClick}
              disabled={isImporting}
              className="px-4 py-2 bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors flex items-center gap-2"
            >
              📥 导入 CSV
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              onChange={handleImport}
              className="hidden"
            />
            <button
              onClick={handleExport}
              disabled={terms.length === 0}
              className="px-4 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors flex items-center gap-2 disabled:opacity-50"
            >
              📤 导出 CSV
            </button>
            <button
              onClick={() => setIsAdding(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
            >
              ➕ 添加术语
            </button>
          </div>
        </div>

        <div className="bg-gray-50 rounded-xl p-4 mb-6">
          <div className="grid md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">搜索</label>
              <input
                type="text"
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                placeholder="搜索术语..."
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
              <label className="block text-sm font-medium text-gray-700 mb-1">领域</label>
              <select
                value={filterDomain}
                onChange={(e) => setFilterDomain(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="">全部领域</option>
                {domains.map(d => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex justify-between items-center mt-4">
            <span className="text-sm text-gray-500">共 {terms.length} 条术语</span>
            <button
              onClick={handleClearAll}
              disabled={terms.length === 0}
              className="text-sm text-red-500 hover:text-red-700 disabled:opacity-50"
            >
              清空所有
            </button>
          </div>
        </div>

        {isAdding && (
          <div className="bg-blue-50 rounded-xl p-4 mb-6">
            <h3 className="font-medium mb-4 text-blue-800">添加新术语</h3>
            <div className="grid md:grid-cols-5 gap-4">
              <LanguageSelector
                value={newTerm.sourceLang}
                onChange={(l) => setNewTerm({ ...newTerm, sourceLang: l })}
                label="源语言"
              />
              <div className="md:col-span-1">
                <label className="block text-sm font-medium text-gray-700 mb-1">源文本</label>
                <input
                  type="text"
                  value={newTerm.sourceText}
                  onChange={(e) => setNewTerm({ ...newTerm, sourceText: e.target.value })}
                  placeholder="源文本"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <LanguageSelector
                value={newTerm.targetLang}
                onChange={(l) => setNewTerm({ ...newTerm, targetLang: l })}
                label="目标语言"
              />
              <div className="md:col-span-1">
                <label className="block text-sm font-medium text-gray-700 mb-1">译文本</label>
                <input
                  type="text"
                  value={newTerm.translatedText}
                  onChange={(e) => setNewTerm({ ...newTerm, translatedText: e.target.value })}
                  placeholder="译文本"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">领域（可选）</label>
                <input
                  type="text"
                  value={newTerm.domain}
                  onChange={(e) => setNewTerm({ ...newTerm, domain: e.target.value })}
                  placeholder="如：IT、医疗"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => setIsAdding(false)}
                className="px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                取消
              </button>
              <button
                onClick={handleAddTerm}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                保存
              </button>
            </div>
          </div>
        )}

        {terms.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <div className="text-5xl mb-4">📚</div>
            <p>暂无术语数据</p>
            <p className="text-sm mt-2">点击"添加术语"或导入CSV文件开始</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50">
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">源语言</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">源文本</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">目标语言</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">译文本</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">领域</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">更新时间</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-700">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {terms.map((term) => (
                  <tr key={term.id} className="hover:bg-gray-50">
                    {editingTerm?.id === term.id && editingTerm ? (
                      <>
                        <td className="px-4 py-3">
                          <select
                            value={editingTerm.sourceLang}
                            onChange={(e) => setEditingTerm({ ...editingTerm, sourceLang: e.target.value as LanguageCode } as TermEntry)}
                            className="w-full px-2 py-1 border rounded"
                          >
                            {Object.entries(LANGUAGE_MAP).map(([code, lang]) => (
                              <option key={code} value={code}>{lang.nativeName}</option>
                            ))}
                          </select>
                        </td>
                        <td className="px-4 py-3">
                          <input
                            type="text"
                            value={editingTerm.sourceText}
                            onChange={(e) => setEditingTerm({ ...editingTerm, sourceText: e.target.value } as TermEntry)}
                            className="w-full px-2 py-1 border rounded"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <select
                            value={editingTerm.targetLang}
                            onChange={(e) => setEditingTerm({ ...editingTerm, targetLang: e.target.value as LanguageCode } as TermEntry)}
                            className="w-full px-2 py-1 border rounded"
                          >
                            {Object.entries(LANGUAGE_MAP).map(([code, lang]) => (
                              <option key={code} value={code}>{lang.nativeName}</option>
                            ))}
                          </select>
                        </td>
                        <td className="px-4 py-3">
                          <input
                            type="text"
                            value={editingTerm.translatedText}
                            onChange={(e) => setEditingTerm({ ...editingTerm, translatedText: e.target.value } as TermEntry)}
                            className="w-full px-2 py-1 border rounded"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <input
                            type="text"
                            value={editingTerm.domain || ''}
                            onChange={(e) => setEditingTerm({ ...editingTerm, domain: e.target.value } as TermEntry)}
                            className="w-full px-2 py-1 border rounded"
                          />
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500">
                          {new Date(term.updatedAt).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button onClick={handleUpdateTerm} className="text-green-600 hover:text-green-800 mr-2">✓</button>
                          <button onClick={() => setEditingTerm(null)} className="text-gray-600 hover:text-gray-800">✕</button>
                        </td>
                      </>
                    ) : (
                      <>
                        <td className="px-4 py-3 text-sm">
                          <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded-full text-xs">
                            {LANGUAGE_MAP[term.sourceLang].nativeName}
                          </span>
                        </td>
                        <td className="px-4 py-3 font-medium">{term.sourceText}</td>
                        <td className="px-4 py-3 text-sm">
                          <span className="px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs">
                            {LANGUAGE_MAP[term.targetLang].nativeName}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-gray-600">{term.translatedText}</td>
                        <td className="px-4 py-3">
                          {term.domain && (
                            <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded-full text-xs">
                              {term.domain}
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500">
                          {new Date(term.updatedAt).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            onClick={() => setEditingTerm(term)}
                            className="text-blue-600 hover:text-blue-800 mr-3"
                          >
                            ✏️
                          </button>
                          <button
                            onClick={() => handleDeleteTerm(term.id!)}
                            className="text-red-500 hover:text-red-700"
                          >
                            🗑️
                          </button>
                        </td>
                      </>
                    )}
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

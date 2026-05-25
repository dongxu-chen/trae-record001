import React, { useState } from 'react'
import { useApp } from '../contexts/AppContext'
import { API_PROVIDERS } from '../constants'
import { historyDB, termDB, translationMemoryDB, documentDB } from '../services/database'

export const Settings: React.FC = () => {
  const { 
    apiConfig, 
    setApiConfig, 
    useTerms, 
    setUseTerms, 
    useMemory, 
    setUseMemory,
    memoryConfig,
    setMemoryConfig,
    termConfig,
    setTermConfig,
  } = useApp()

  const [showAdvancedMemory, setShowAdvancedMemory] = useState(false)
  const [showAdvancedTerms, setShowAdvancedTerms] = useState(false)

  const handleClearData = async (type: 'history' | 'terms' | 'memory' | 'documents' | 'all') => {
    const messages: Record<string, string> = {
      history: '确定要清空所有翻译历史吗？',
      terms: '确定要清空所有术语库吗？',
      memory: '确定要清空所有翻译记忆吗？',
      documents: '确定要清空所有文档翻译记录吗？',
      all: '确定要清空所有数据吗？此操作不可恢复！',
    }

    if (!confirm(messages[type])) return

    try {
      switch (type) {
        case 'history':
          await historyDB.clear()
          break
        case 'terms':
          await termDB.clear()
          break
        case 'memory':
          await translationMemoryDB.clear()
          break
        case 'documents':
          await documentDB.clear()
          break
        case 'all':
          await historyDB.clear()
          await termDB.clear()
          await translationMemoryDB.clear()
          await documentDB.clear()
          break
      }
      alert('操作成功')
    } catch (err) {
      alert('操作失败')
    }
  }

  const handleExportData = async () => {
    try {
      const data = {
        terms: await termDB.getAll(),
        memory: await translationMemoryDB.getAll(),
        exportDate: new Date().toISOString(),
        version: '1.0',
      }

      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `translator_backup_${Date.now()}.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      alert('导出失败')
    }
  }

  const handleImportData = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = async (event) => {
      try {
        const data = JSON.parse(event.target?.result as string)
        
        if (data.terms && Array.isArray(data.terms)) {
          for (const term of data.terms) {
          const existing = await termDB.findExact(term.sourceText, term.sourceLang, term.targetLang)
          if (!existing) {
            await termDB.add(term)
          }
        }
        }
        
        if (data.memory && Array.isArray(data.memory)) {
          for (const mem of data.memory) {
            const existing = await translationMemoryDB.findExact(mem.sourceText, mem.sourceLang, mem.targetLang)
            if (!existing) {
              await translationMemoryDB.add(mem)
            }
          }
        }
        
        alert('导入成功')
      } catch (err) {
        alert('导入失败，请确保文件格式正确')
      }
    }
    reader.readAsText(file)
    e.target.value = ''
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-4">
          <h2 className="text-xl font-semibold text-white flex items-center gap-2">
            <span>⚙️</span> 设置
          </h2>
        </div>

        <div className="p-6 space-y-8">
          <section>
            <h3 className="text-lg font-medium text-gray-900 mb-4">翻译API设置</h3>
            <div className="bg-gray-50 rounded-xl p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">API提供商</label>
                <div className="grid grid-cols-3 gap-3">
                  {API_PROVIDERS.map((provider) => (
                    <button
                      key={provider.id}
                      onClick={() => setApiConfig({ ...apiConfig, provider: provider.id as any })}
                      className={`p-4 rounded-xl border-2 transition-all ${
                        apiConfig.provider === provider.id
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 bg-white hover:border-blue-300'
                      }`}
                    >
                      <p className={`font-medium ${
                        apiConfig.provider === provider.id ? 'text-blue-700' : 'text-gray-900'
                      }`}>
                        {provider.name}
                      </p>
                      {provider.needKey && (
                        <p className="text-xs text-gray-500 mt-1">需要API Key</p>
                      )}
                    </button>
                  ))}
                </div>
              </div>

              {(apiConfig.provider === 'google' || apiConfig.provider === 'deepl') && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      API Key
                    </label>
                    <input
                      type="password"
                      value={apiConfig.apiKey || ''}
                      onChange={(e) => setApiConfig({ ...apiConfig, apiKey: e.target.value })}
                      placeholder="请输入API Key"
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      {apiConfig.provider === 'google'
                        ? '获取 Google Cloud Translation API Key: https://cloud.google.com/translate'
                        : '获取 DeepL API Key: https://www.deepl.com/pro-api'}
                    </p>
                  </div>
                  {apiConfig.provider === 'deepl' && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        API端点（可选）
                      </label>
                      <input
                        type="url"
                        value={apiConfig.endpoint || ''}
                        onChange={(e) => setApiConfig({ ...apiConfig, endpoint: e.target.value })}
                        placeholder="https://api.deepl.com/v2/translate 或 https://api-free.deepl.com/v2/translate"
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  )}
                </>
              )}

              {apiConfig.provider === 'mock' && (
                <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <p className="text-sm text-yellow-800">
                    ⚠️ 当前使用模拟模式，翻译结果仅供演示。请选择真实API提供商并配置API Key以获得准确翻译。
                  </p>
                </div>
              )}
            </div>
          </section>

          <section>
            <h3 className="text-lg font-medium text-gray-900 mb-4">翻译选项</h3>
            <div className="bg-gray-50 rounded-xl p-4 space-y-4">
              <label className="flex items-center justify-between p-3 bg-white rounded-lg">
                <div>
                  <p className="font-medium text-gray-900">启用术语库</p>
                  <p className="text-sm text-gray-500">翻译时自动应用自定义术语</p>
                </div>
                <input
                  type="checkbox"
                  checked={useTerms}
                  onChange={(e) => setUseTerms(e.target.checked)}
                  className="w-5 h-5 text-blue-600 rounded"
                />
              </label>

              <div className="p-3 bg-white rounded-lg">
                <div className="flex items-center justify-between">
                  <button
                    onClick={() => setShowAdvancedTerms(!showAdvancedTerms)}
                    className="flex items-center gap-2 text-blue-600 hover:text-blue-800 text-sm font-medium"
                  >
                    <span>{showAdvancedTerms ? '▼' : '▶'}</span>
                    术语库高级设置
                  </button>
                </div>
                {showAdvancedTerms && (
                  <div className="mt-4 pt-4 border-t border-gray-200 space-y-4">
                    <label className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900">分词匹配</p>
                        <p className="text-xs text-gray-500">对文本进行分词后识别术语，支持模糊匹配</p>
                      </div>
                      <input
                        type="checkbox"
                        checked={termConfig.useSegmentation}
                        onChange={(e) => setTermConfig({ ...termConfig, useSegmentation: e.target.checked })}
                        className="w-4 h-4 text-blue-600 rounded"
                      />
                    </label>
                    <label className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900">长术语优先</p>
                        <p className="text-xs text-gray-500">优先匹配较长的术语，避免短术语替换错误</p>
                      </div>
                      <input
                        type="checkbox"
                        checked={termConfig.longTermFirst}
                        onChange={(e) => setTermConfig({ ...termConfig, longTermFirst: e.target.checked })}
                        className="w-4 h-4 text-blue-600 rounded"
                      />
                    </label>
                  </div>
                )}
              </div>

              <label className="flex items-center justify-between p-3 bg-white rounded-lg">
                <div>
                  <p className="font-medium text-gray-900">启用翻译记忆</p>
                  <p className="text-sm text-gray-500">复用历史翻译结果，提高一致性</p>
                </div>
                <input
                  type="checkbox"
                  checked={useMemory}
                  onChange={(e) => setUseMemory(e.target.checked)}
                  className="w-5 h-5 text-blue-600 rounded"
                />
              </label>

              <div className="p-3 bg-white rounded-lg">
                <div className="flex items-center justify-between">
                  <button
                    onClick={() => setShowAdvancedMemory(!showAdvancedMemory)}
                    className="flex items-center gap-2 text-blue-600 hover:text-blue-800 text-sm font-medium"
                  >
                    <span>{showAdvancedMemory ? '▼' : '▶'}</span>
                    翻译记忆高级设置
                  </button>
                </div>
                {showAdvancedMemory && (
                  <div className="mt-4 pt-4 border-t border-gray-200 space-y-6">
                    <label className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900">启用模糊匹配</p>
                        <p className="text-xs text-gray-500">使用编辑距离算法进行模糊匹配</p>
                      </div>
                      <input
                        type="checkbox"
                        checked={memoryConfig.useFuzzyMatch}
                        onChange={(e) => setMemoryConfig({ ...memoryConfig, useFuzzyMatch: e.target.checked })}
                        className="w-4 h-4 text-blue-600 rounded"
                      />
                    </label>

                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <div>
                        <p className="text-sm font-medium text-gray-900">匹配阈值</p>
                          <p className="text-xs text-gray-500">达到此相似度的记忆条目将被复用</p>
                        </div>
                        <span className="text-sm font-mono bg-blue-100 text-blue-700 px-2 py-1 rounded">
                          {Math.round(memoryConfig.threshold * 100)}%
                        </span>
                      </div>
                      <input
                        type="range"
                        min="0.5"
                        max="1"
                        step="0.05"
                        value={memoryConfig.threshold}
                        onChange={(e) => setMemoryConfig({ ...memoryConfig, threshold: parseFloat(e.target.value) })}
                        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                      />
                      <div className="flex justify-between text-xs text-gray-400 mt-1">
                        <span>50% (宽松)</span>
                        <span>100% (严格)</span>
                      </div>
                    </div>

                    {memoryConfig.useFuzzyMatch && (
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <div>
                          <p className="text-sm font-medium text-gray-900">模糊匹配阈值</p>
                          <p className="text-xs text-gray-500">模糊匹配所需的最低相似度</p>
                          </div>
                          <span className="text-sm font-mono bg-purple-100 text-purple-700 px-2 py-1 rounded">
                            {Math.round(memoryConfig.fuzzyMatchThreshold * 100)}%
                          </span>
                        </div>
                        <input
                          type="range"
                          min="0.6"
                          max="0.95"
                          step="0.05"
                          value={memoryConfig.fuzzyMatchThreshold}
                          onChange={(e) => setMemoryConfig({ ...memoryConfig, fuzzyMatchThreshold: parseFloat(e.target.value) })}
                          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                        />
                        <div className="flex justify-between text-xs text-gray-400 mt-1">
                          <span>60%</span>
                          <span>95%</span>
                        </div>
                      </div>
                    )}

                    <div className="p-3 bg-blue-50 rounded-lg">
                      <p className="text-xs text-blue-700">
                        <strong>匹配类型说明：</strong><br/>
                        • <strong>精确匹配</strong>：文本完全相同，相似度 100%<br/>
                        • <strong>包含匹配</strong>：一方文本完全包含另一方<br/>
                        • <strong>模糊匹配</strong>：基于编辑距离的相似度计算
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </section>

          <section>
            <h3 className="text-lg font-medium text-gray-900 mb-4">数据管理</h3>
            <div className="bg-gray-50 rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between p-3 bg-white rounded-lg">
                <div>
                  <p className="font-medium text-gray-900">导出数据</p>
                  <p className="text-sm text-gray-500">导出术语库和翻译记忆为JSON文件</p>
                </div>
                <button
                  onClick={handleExportData}
                  className="px-4 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors"
                >
                  📤 导出
                </button>
              </div>
              <div className="flex items-center justify-between p-3 bg-white rounded-lg">
                <div>
                  <p className="font-medium text-gray-900">导入数据</p>
                  <p className="text-sm text-gray-500">从JSON文件导入术语库和翻译记忆</p>
                </div>
                <label className="px-4 py-2 bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors cursor-pointer">
                  📥 导入
                  <input
                    type="file"
                    accept=".json"
                    onChange={handleImportData}
                    className="hidden"
                  />
                </label>
              </div>
            </div>
          </section>

          <section>
            <h3 className="text-lg font-medium text-gray-900 mb-4">危险操作</h3>
            <div className="bg-red-50 rounded-xl p-4 space-y-3">
              <button
                onClick={() => handleClearData('history')}
                className="w-full flex items-center justify-between p-3 bg-white rounded-lg border border-red-200 hover:bg-red-50 transition-colors"
              >
                <div className="text-left">
                  <p className="font-medium text-gray-900">清空翻译历史</p>
                  <p className="text-sm text-gray-500">删除所有文本翻译历史记录</p>
                </div>
                <span className="text-red-500">🗑️</span>
              </button>
              <button
                onClick={() => handleClearData('documents')}
                className="w-full flex items-center justify-between p-3 bg-white rounded-lg border border-red-200 hover:bg-red-50 transition-colors"
              >
                <div className="text-left">
                  <p className="font-medium text-gray-900">清空文档记录</p>
                  <p className="text-sm text-gray-500">删除所有文档翻译记录</p>
                </div>
                <span className="text-red-500">🗑️</span>
              </button>
              <button
                onClick={() => handleClearData('terms')}
                className="w-full flex items-center justify-between p-3 bg-white rounded-lg border border-red-200 hover:bg-red-50 transition-colors"
              >
                <div className="text-left">
                  <p className="font-medium text-gray-900">清空术语库</p>
                  <p className="text-sm text-gray-500">删除所有自定义术语</p>
                </div>
                <span className="text-red-500">🗑️</span>
              </button>
              <button
                onClick={() => handleClearData('memory')}
                className="w-full flex items-center justify-between p-3 bg-white rounded-lg border border-red-200 hover:bg-red-50 transition-colors"
              >
                <div className="text-left">
                  <p className="font-medium text-gray-900">清空翻译记忆</p>
                  <p className="text-sm text-gray-500">删除所有翻译记忆条目</p>
                </div>
                <span className="text-red-500">🗑️</span>
              </button>
              <button
                onClick={() => handleClearData('all')}
                className="w-full flex items-center justify-between p-3 bg-red-100 rounded-lg border border-red-300 hover:bg-red-200 transition-colors"
              >
                <div className="text-left">
                  <p className="font-medium text-red-700">⚠️ 清空所有数据</p>
                  <p className="text-sm text-red-600">删除所有数据，此操作不可恢复</p>
                </div>
                <span className="text-red-500">💥</span>
              </button>
            </div>
          </section>

          <section>
            <h3 className="text-lg font-medium text-gray-900 mb-4">关于</h3>
            <div className="bg-gray-50 rounded-xl p-4">
              <div className="text-center">
                <div className="text-4xl mb-3">🌍</div>
                <h4 className="text-xl font-bold text-gray-900">多语言翻译工具</h4>
                <p className="text-gray-500 mt-1">v1.0.0</p>
                <p className="text-sm text-gray-600 mt-3">
                  支持中/英/日/韩/法/德 六种语言互译，集成术语库和翻译记忆功能。
                </p>
                <div className="mt-4 p-3 bg-blue-50 rounded-lg text-left">
                  <p className="text-xs text-blue-700 font-medium mb-2">✨ 新功能：</p>
                  <ul className="text-xs text-blue-600 space-y-1">
                    <li>• 文档翻译：分段解析保留格式标签，翻译后还原格式</li>
                    <li>• 翻译记忆：可配置匹配阈值，支持模糊匹配复用</li>
                    <li>• 术语库：分词后识别术语，长术语优先匹配</li>
                  </ul>
                </div>
                <p className="text-xs text-gray-400 mt-4">
                  技术栈：React + TypeScript + Vite + IndexedDB + Electron
                </p>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}

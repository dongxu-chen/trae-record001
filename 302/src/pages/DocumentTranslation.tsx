import React, { useState, useRef, useEffect } from 'react'
import { useApp } from '../contexts/AppContext'
import { LanguageSelector } from '../components/LanguageSelector'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { translateDocument, downloadTranslatedDocument, extractTextFromFile } from '../services/documentService'
import { documentDB } from '../services/database'
import { DocumentTranslation as DocTransType, FileType } from '../types'
import { LANGUAGE_MAP } from '../constants'

export const DocumentTranslation: React.FC = () => {
  const { sourceLang, setSourceLang, targetLang, setTargetLang, apiConfig, useTerms, useMemory } = useApp()
  
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isTranslating, setIsTranslating] = useState(false)
  const [progress, setProgress] = useState(0)
  const [currentChunk, setCurrentChunk] = useState(0)
  const [totalChunks, setTotalChunks] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [currentDoc, setCurrentDoc] = useState<DocTransType | null>(null)
  const [history, setHistory] = useState<DocTransType[]>([])
  const [previewText, setPreviewText] = useState<string>('')
  const [showPreview, setShowPreview] = useState(false)
  
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    loadHistory()
  }, [])

  const loadHistory = async () => {
    try {
      const docs = await documentDB.getAll()
      setHistory(docs)
    } catch (err) {
      console.error('Failed to load history:', err)
    }
  }

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const validTypes = ['.docx', '.pdf', '.txt']
    const ext = file.name.toLowerCase().slice(file.name.lastIndexOf('.'))
    if (!validTypes.includes(ext)) {
      setError('不支持的文件格式。请上传 .docx, .pdf 或 .txt 文件')
      return
    }

    if (file.size > 10 * 1024 * 1024) {
      setError('文件大小不能超过 10MB')
      return
    }

    setSelectedFile(file)
    setError(null)
    setCurrentDoc(null)
    setProgress(0)

    try {
      const text = await extractTextFromFile(file)
      setPreviewText(text.slice(0, 500) + (text.length > 500 ? '...' : ''))
    } catch (err) {
      setError('无法读取文件内容')
    }
  }

  const handleTranslate = async () => {
    if (!selectedFile) return

    setIsTranslating(true)
    setError(null)
    setProgress(0)

    try {
      const doc = await translateDocument(
        selectedFile,
        sourceLang,
        targetLang,
        apiConfig,
        (prog, curr, total) => {
          setProgress(prog)
          setCurrentChunk(curr)
          setTotalChunks(total)
        }
      )

      setCurrentDoc(doc)
      await loadHistory()
    } catch (err) {
      setError(err instanceof Error ? err.message : '文档翻译失败')
    } finally {
      setIsTranslating(false)
    }
  }

  const handleDownload = async (format?: FileType) => {
    if (!currentDoc) return
    try {
      await downloadTranslatedDocument(currentDoc, format)
    } catch (err) {
      setError('下载失败')
    }
  }

  const handleHistoryClick = async (doc: DocTransType) => {
    setCurrentDoc(doc)
    setPreviewText(doc.originalContent.slice(0, 500) + '...')
  }

  const handleDeleteHistory = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await documentDB.delete(id)
      await loadHistory()
      if (currentDoc?.id === id) {
        setCurrentDoc(null)
      }
    } catch (err) {
      console.error('Delete failed:', err)
    }
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const getFileIcon = (fileName: string): string => {
    const ext = fileName.toLowerCase().split('.').pop()
    if (ext === 'pdf') return '📕'
    if (ext === 'docx' || ext === 'doc') return '📘'
    return '📄'
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-2xl shadow-xl p-6">
            <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
              <span>📄</span> 文档翻译
            </h2>

            <div className="flex items-center gap-4 mb-6 flex-wrap">
              <LanguageSelector
                value={sourceLang}
                onChange={setSourceLang}
                label="源语言"
              />
              <span className="text-gray-400 mt-5">→</span>
              <LanguageSelector
                value={targetLang}
                onChange={setTargetLang}
                label="目标语言"
                exclude={[sourceLang]}
              />
              <div className="flex items-center gap-4 mt-5">
                <label className="flex items-center gap-2 text-sm text-gray-600">
                  <input
                    type="checkbox"
                    checked={useTerms}
                    onChange={(e) => useApp().setUseTerms(e.target.checked)}
                    className="rounded text-blue-600"
                  />
                  术语库
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-600">
                  <input
                    type="checkbox"
                    checked={useMemory}
                    onChange={(e) => useApp().setUseMemory(e.target.checked)}
                    className="rounded text-blue-600"
                  />
                  翻译记忆
                </label>
              </div>
            </div>

            <div
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all ${
                selectedFile
                  ? 'border-green-300 bg-green-50'
                  : 'border-gray-300 hover:border-blue-400 hover:bg-blue-50'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".docx,.pdf,.txt"
                onChange={handleFileSelect}
                className="hidden"
              />
              {selectedFile ? (
                <div>
                  <div className="text-5xl mb-3">{getFileIcon(selectedFile.name)}</div>
                  <p className="font-medium text-gray-900">{selectedFile.name}</p>
                  <p className="text-sm text-gray-500">{formatFileSize(selectedFile.size)}</p>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setSelectedFile(null)
                      setPreviewText('')
                      if (fileInputRef.current) fileInputRef.current.value = ''
                    }}
                    className="mt-3 text-sm text-red-500 hover:text-red-700"
                  >
                    移除文件
                  </button>
                </div>
              ) : (
                <div>
                  <div className="text-5xl mb-3">📁</div>
                  <p className="text-lg font-medium text-gray-700">点击或拖拽文件到此处</p>
                  <p className="text-sm text-gray-500 mt-2">支持 .docx, .pdf, .txt 格式，最大 10MB</p>
                </div>
              )}
            </div>

            {previewText && (
              <div className="mt-4">
                <button
                  onClick={() => setShowPreview(!showPreview)}
                  className="text-sm text-blue-600 hover:text-blue-800"
                >
                  {showPreview ? '隐藏预览' : '显示原文预览'}
                </button>
                {showPreview && (
                  <div className="mt-2 p-4 bg-gray-50 rounded-lg text-sm text-gray-600 max-h-40 overflow-y-auto">
                    {previewText}
                  </div>
                )}
              </div>
            )}

            {isTranslating && (
              <div className="mt-6">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600">
                    正在翻译... ({currentChunk}/{totalChunks} 段)
                  </span>
                  <span className="text-sm text-gray-600">{Math.round(progress * 100)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${progress * 100}%` }}
                  />
                </div>
              </div>
            )}

            {error && (
              <div className="mt-4 p-3 bg-red-50 text-red-700 rounded-lg">
                ⚠️ {error}
              </div>
            )}

            <div className="mt-6 flex justify-end">
              <button
                onClick={handleTranslate}
                disabled={isTranslating || !selectedFile}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              >
                {isTranslating ? (
                  <>
                    <LoadingSpinner size="sm" />
                    翻译中...
                  </>
                ) : (
                  '开始翻译'
                )}
              </button>
            </div>
          </div>

          {currentDoc && (
            <div className="bg-white rounded-2xl shadow-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <span>✅</span> 翻译完成
                </h3>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleDownload('txt')}
                    className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                  >
                    下载 TXT
                  </button>
                  <button
                    onClick={() => handleDownload('docx')}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    下载 Word
                  </button>
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium text-gray-500 mb-2">
                    原文 ({LANGUAGE_MAP[currentDoc.sourceLang].nativeName})
                  </p>
                  <div className="p-4 bg-gray-50 rounded-lg h-64 overflow-y-auto text-sm">
                    {currentDoc.originalContent}
                  </div>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500 mb-2">
                    译文 ({LANGUAGE_MAP[currentDoc.targetLang].nativeName})
                  </p>
                  <div className="p-4 bg-blue-50 rounded-lg h-64 overflow-y-auto text-sm">
                    {currentDoc.translatedContent}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="bg-white rounded-2xl shadow-xl p-6 h-fit">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span>📋</span> 翻译历史
          </h3>
          {history.length === 0 ? (
            <p className="text-gray-500 text-center py-8">暂无历史记录</p>
          ) : (
            <div className="space-y-3 max-h-[600px] overflow-y-auto">
              {history.map((doc) => (
                <div
                  key={doc.id}
                  onClick={() => handleHistoryClick(doc)}
                  className={`p-4 border rounded-lg cursor-pointer transition-all ${
                    currentDoc?.id === doc.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-blue-300'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-xl">{getFileIcon(doc.fileName)}</span>
                      <div className="min-w-0">
                        <p className="font-medium text-sm truncate">{doc.fileName}</p>
                        <p className="text-xs text-gray-500">
                          {LANGUAGE_MAP[doc.sourceLang].nativeName} → {LANGUAGE_MAP[doc.targetLang].nativeName}
                        </p>
                        <p className="text-xs text-gray-400">
                          {new Date(doc.createdAt).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={(e) => handleDeleteHistory(doc.id!, e)}
                      className="text-gray-400 hover:text-red-500 transition-colors"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}



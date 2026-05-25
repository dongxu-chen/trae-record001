import React, { useState, useCallback, useRef, useEffect } from 'react'
import { useApp } from '../contexts/AppContext'
import { LanguageSelector } from '../components/LanguageSelector'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { QualityAssessmentPanel } from '../components/QualityAssessmentPanel'
import { CollaborationPanel } from '../components/CollaborationPanel'
import { StyleAnalysisPanel } from '../components/StyleAnalysisPanel'
import { translateWithEnhancements, getTranslationSuggestions } from '../services/translationService'
import { detectLanguage } from '../services/translateApi'
import { TranslationResult, QualityAssessment, TranslationStyle } from '../types'
import { termDB } from '../services/database'
import { evaluateTranslationQuality } from '../services/qualityAssessment'
import { LANGUAGE_MAP } from '../constants'

export const TextTranslation: React.FC = () => {
  const {
    sourceLang,
    setSourceLang,
    targetLang,
    setTargetLang,
    apiConfig,
    useTerms,
    useMemory,
    swapLanguages,
  } = useApp()

  const [inputText, setInputText] = useState('')
  const [outputText, setOutputText] = useState('')
  const [isTranslating, setIsTranslating] = useState(false)
  const [isDetecting, setIsDetecting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [suggestions, setSuggestions] = useState<Array<{ text: string; score: number; source: 'memory' | 'term' }>>([])
  const [matchedTerms, setMatchedTerms] = useState<any[]>([])
  const [history, setHistory] = useState<TranslationResult[]>([])
  const [showHistory, setShowHistory] = useState(false)
  const [autoDetect, setAutoDetect] = useState(false)
  const [activeTab, setActiveTab] = useState<'quality' | 'collaboration' | 'style'>('quality')
  const [qualityAssessment, setQualityAssessment] = useState<QualityAssessment | null>(null)
  const [isEvaluatingQuality, setIsEvaluatingQuality] = useState(false)
  const [expectedStyle, setExpectedStyle] = useState<TranslationStyle>('neutral')
  const [autoQualityCheck, setAutoQualityCheck] = useState(true)
  
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const outputRef = useRef<HTMLTextAreaElement>(null)

  const handleTranslate = useCallback(async () => {
    if (!inputText.trim()) {
      setOutputText('')
      return
    }

    setIsTranslating(true)
    setError(null)

    try {
      let actualSourceLang = sourceLang
      if (autoDetect) {
        setIsDetecting(true)
        actualSourceLang = await detectLanguage(inputText, apiConfig)
        setSourceLang(actualSourceLang)
        setIsDetecting(false)
      }

      const result = await translateWithEnhancements(
        inputText,
        actualSourceLang,
        targetLang,
        apiConfig,
        {
          useTerms,
          useMemory,
          saveToHistory: true,
          saveToMemory: true,
        }
      )

      setOutputText(result.translatedText)

      const sug = await getTranslationSuggestions(inputText, actualSourceLang, targetLang)
      setSuggestions(sug.fromMemory)

      const terms = await termDB.search(inputText, actualSourceLang, targetLang)
      setMatchedTerms(terms)

      setHistory(prev => [result, ...prev.slice(0, 19)])

      if (autoQualityCheck) {
        await handleEvaluateQuality(result.translatedText, result.originalText, actualSourceLang, targetLang)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '翻译失败，请稍后重试')
    } finally {
      setIsTranslating(false)
    }
  }, [inputText, sourceLang, targetLang, apiConfig, useTerms, useMemory, autoDetect, setSourceLang, autoQualityCheck])

  const handleEvaluateQuality = useCallback(async (
    translatedText: string,
    sourceText: string,
    sourceLang: string,
    targetLang: string
  ) => {
    if (!translatedText.trim() || !sourceText.trim()) return

    setIsEvaluatingQuality(true)
    try {
      const assessment = await evaluateTranslationQuality(
        sourceText,
        translatedText,
        sourceLang as any,
        targetLang as any,
        {
          expectedStyle: expectedStyle === 'technical' ? undefined : expectedStyle as any,
          checkTerminology: true,
          autoThreshold: 70,
        }
      )
      setQualityAssessment(assessment)
    } catch (err) {
      console.error('质量评估失败:', err)
    } finally {
      setIsEvaluatingQuality(false)
    }
  }, [expectedStyle])

  const handleReevaluateQuality = useCallback(() => {
    if (outputText && inputText) {
      handleEvaluateQuality(outputText, inputText, sourceLang, targetLang)
    }
  }, [outputText, inputText, sourceLang, targetLang, handleEvaluateQuality])

  const handleMergeComplete = useCallback((mergedText: string) => {
    setOutputText(mergedText)
    if (inputText) {
      handleEvaluateQuality(mergedText, inputText, sourceLang, targetLang)
    }
  }, [inputText, sourceLang, targetLang, handleEvaluateQuality])

  const handleCopy = async () => {
    if (outputText) {
      await navigator.clipboard.writeText(outputText)
    }
  }

  const handleClear = () => {
    setInputText('')
    setOutputText('')
    setError(null)
    setSuggestions([])
    setMatchedTerms([])
    inputRef.current?.focus()
  }

  const handleUseSuggestion = (text: string) => {
    setOutputText(text)
  }

  const handleAddToTerms = async () => {
    if (!inputText.trim() || !outputText.trim()) return

    try {
      await termDB.add({
        sourceText: inputText.trim(),
        translatedText: outputText.trim(),
        sourceLang,
        targetLang,
        createdAt: Date.now(),
        updatedAt: Date.now(),
      })
      alert('已添加到术语库')
    } catch (err) {
      alert('添加失败')
    }
  }

  const handleHistoryItemClick = (item: TranslationResult) => {
    setInputText(item.originalText)
    setOutputText(item.translatedText)
    setSourceLang(item.source)
    setTargetLang(item.target)
    setShowHistory(false)
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-4 flex-wrap">
              <div className="flex items-center gap-3">
                <LanguageSelector
                  value={sourceLang}
                  onChange={setSourceLang}
                  exclude={autoDetect ? [] : [targetLang]}
                />
                <label className="flex items-center gap-2 text-sm text-gray-600">
                  <input
                    type="checkbox"
                    checked={autoDetect}
                    onChange={(e) => setAutoDetect(e.target.checked)}
                    className="rounded text-blue-600"
                  />
                  自动检测
                  {isDetecting && <span className="text-blue-500 text-xs">(检测中...)</span>}
                </label>
              </div>

              <button
                onClick={swapLanguages}
                disabled={autoDetect}
                className="p-2 rounded-full hover:bg-blue-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                title="交换语言"
              >
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                </svg>
              </button>

              <LanguageSelector
                value={targetLang}
                onChange={setTargetLang}
                exclude={[sourceLang]}
              />
            </div>

            <div className="flex items-center gap-2 text-sm">
              <label className="flex items-center gap-2 text-gray-600">
                <input
                  type="checkbox"
                  checked={useTerms}
                  onChange={(e) => useApp().setUseTerms(e.target.checked)}
                  className="rounded text-blue-600"
                />
                术语库
              </label>
              <label className="flex items-center gap-2 text-gray-600">
                <input
                  type="checkbox"
                  checked={useMemory}
                  onChange={(e) => useApp().setUseMemory(e.target.checked)}
                  className="rounded text-blue-600"
                />
                翻译记忆
              </label>
              <button
                onClick={() => setShowHistory(!showHistory)}
                className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors"
              >
                历史记录
              </button>
            </div>
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-0">
          <div className="p-6 border-r border-gray-200">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-gray-500">
                {LANGUAGE_MAP[sourceLang].nativeName}
              </span>
              <span className="text-xs text-gray-400">{inputText.length} 字符</span>
            </div>
            <textarea
              ref={inputRef}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="请输入要翻译的文本..."
              className="w-full h-64 p-4 text-lg border border-gray-200 rounded-xl resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              onKeyDown={(e) => {
                if (e.ctrlKey && e.key === 'Enter') {
                  e.preventDefault()
                  handleTranslate()
                }
              }}
            />
            <div className="flex justify-between mt-4">
              <button
                onClick={handleClear}
                className="px-4 py-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
              >
                清空
              </button>
              <button
                onClick={handleTranslate}
                disabled={isTranslating || !inputText.trim()}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              >
                {isTranslating ? (
                  <>
                    <LoadingSpinner size="sm" />
                    翻译中...
                  </>
                ) : (
                  '翻译 (Ctrl+Enter)'
                )}
              </button>
            </div>

            {matchedTerms.length > 0 && (
              <div className="mt-4 p-3 bg-green-50 rounded-lg">
                <p className="text-sm font-medium text-green-700 mb-2">匹配的术语 ({matchedTerms.length})</p>
                <div className="flex flex-wrap gap-2">
                  {matchedTerms.map((term, idx) => (
                    <span key={idx} className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded-full">
                      {term.sourceText} → {term.translatedText}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="p-6 bg-gray-50">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-gray-500">
                {LANGUAGE_MAP[targetLang].nativeName}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={handleCopy}
                  disabled={!outputText}
                  className="px-3 py-1 text-sm text-gray-600 hover:text-blue-600 disabled:opacity-50 transition-colors"
                  title="复制"
                >
                  📋 复制
                </button>
                <button
                  onClick={handleAddToTerms}
                  disabled={!outputText || !inputText}
                  className="px-3 py-1 text-sm text-gray-600 hover:text-green-600 disabled:opacity-50 transition-colors"
                  title="添加到术语库"
                >
                  ➕ 添加到术语库
                </button>
              </div>
            </div>
            <textarea
              ref={outputRef}
              value={outputText}
              onChange={(e) => setOutputText(e.target.value)}
              placeholder="翻译结果将显示在这里..."
              className="w-full h-64 p-4 text-lg border border-gray-200 rounded-xl resize-none bg-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              readOnly={isTranslating}
            />

            {suggestions.length > 0 && (
              <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                <p className="text-sm font-medium text-blue-700 mb-2">来自翻译记忆的建议</p>
                <div className="flex flex-wrap gap-2">
                  {suggestions.map((sug, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleUseSuggestion(sug.text)}
                      className={`px-3 py-1 text-sm rounded-full transition-colors ${
                        sug.source === 'term'
                          ? 'bg-green-100 text-green-700 hover:bg-green-200'
                          : 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                      }`}
                    >
                      {sug.text}
                      <span className="ml-1 text-xs opacity-70">
                        ({sug.source === 'term' ? '术语' : '记忆'} {Math.round(sug.score * 100)}%)
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {error && (
              <div className="mt-4 p-3 bg-red-50 text-red-700 rounded-lg">
                ⚠️ {error}
              </div>
            )}
          </div>
        </div>
      </div>

      {showHistory && (
        <div className="mt-6 bg-white rounded-2xl shadow-xl p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span>📋</span> 翻译历史
          </h3>
          {history.length === 0 ? (
            <p className="text-gray-500 text-center py-8">暂无历史记录</p>
          ) : (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {history.map((item, idx) => (
                <div
                  key={idx}
                  onClick={() => handleHistoryItemClick(item)}
                  className="p-4 border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 cursor-pointer transition-colors"
                >
                  <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
                    <span>{LANGUAGE_MAP[item.source].nativeName}</span>
                    <span>→</span>
                    <span>{LANGUAGE_MAP[item.target].nativeName}</span>
                    <span className="ml-auto">
                      {new Date(item.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-gray-900 mb-1 line-clamp-1">{item.originalText}</p>
                  <p className="text-blue-600 line-clamp-1">{item.translatedText}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="mt-6">
        <div className="bg-white rounded-t-2xl shadow-lg border-b border-gray-200">
          <div className="flex">
            <button
              onClick={() => setActiveTab('quality')}
              className={`flex-1 px-6 py-4 text-sm font-medium transition-colors flex items-center justify-center gap-2 ${
                activeTab === 'quality'
                  ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
                  : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
              }`}
            >
              <span>📊</span> AI质量评估
              <label className="flex items-center gap-1 ml-2 text-xs">
                <input
                  type="checkbox"
                  checked={autoQualityCheck}
                  onChange={(e) => setAutoQualityCheck(e.target.checked)}
                  className="rounded text-blue-600"
                  onClick={(e) => e.stopPropagation()}
                />
                自动
              </label>
            </button>
            <button
              onClick={() => setActiveTab('collaboration')}
              className={`flex-1 px-6 py-4 text-sm font-medium transition-colors flex items-center justify-center gap-2 ${
                activeTab === 'collaboration'
                  ? 'text-purple-600 border-b-2 border-purple-600 bg-purple-50'
                  : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
              }`}
            >
              <span>👥</span> 实时协作
            </button>
            <button
              onClick={() => setActiveTab('style')}
              className={`flex-1 px-6 py-4 text-sm font-medium transition-colors flex items-center justify-center gap-2 ${
                activeTab === 'style'
                  ? 'text-pink-600 border-b-2 border-pink-600 bg-pink-50'
                  : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
              }`}
            >
              <span>🎨</span> 风格检查
            </button>
          </div>
        </div>

        <div className="bg-white rounded-b-2xl shadow-xl">
          {activeTab === 'quality' && (
            <QualityAssessmentPanel
              assessment={qualityAssessment}
              isLoading={isEvaluatingQuality}
              onReevaluate={handleReevaluateQuality}
              onReview={() => outputRef.current?.focus()}
            />
          )}
          {activeTab === 'collaboration' && (
            <CollaborationPanel
              initialText={inputText}
              sourceLang={sourceLang}
              targetLang={targetLang}
              onMergeComplete={handleMergeComplete}
            />
          )}
          {activeTab === 'style' && (
            <StyleAnalysisPanel
              text={outputText}
              lang={targetLang}
              expectedStyle={expectedStyle}
              onExpectedStyleChange={setExpectedStyle}
            />
          )}
        </div>
      </div>
    </div>
  )
}



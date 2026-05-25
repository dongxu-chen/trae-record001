import React, { useState, useRef } from 'react'
import { useApp } from '../contexts/AppContext'
import { LanguageSelector } from '../components/LanguageSelector'
import { translateWithEnhancements } from '../services/translationService'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { LANGUAGE_MAP } from '../constants'

export const WebTranslation: React.FC = () => {
  const { sourceLang, setSourceLang, targetLang, setTargetLang, apiConfig, useTerms, useMemory } = useApp()
  
  const [url, setUrl] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [extractedText, setExtractedText] = useState('')
  const [translatedText, setTranslatedText] = useState('')
  const [translateProgress, setTranslateProgress] = useState(0)
  const [showCode, setShowCode] = useState(false)
  
  const iframeRef = useRef<HTMLIFrameElement>(null)

  const handleExtractText = async () => {
    if (!url.trim()) {
      setError('请输入网页URL')
      return
    }

    setIsLoading(true)
    setError(null)
    setExtractedText('')
    setTranslatedText('')

    try {
      const proxyUrl = `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`
      const response = await fetch(proxyUrl)
      
      if (!response.ok) {
        throw new Error('无法获取网页内容')
      }

      const html = await response.text()
      const parser = new DOMParser()
      const doc = parser.parseFromString(html, 'text/html')
      
      const scripts = doc.querySelectorAll('script, style, noscript')
      scripts.forEach(s => s.remove())
      
      const text = doc.body.innerText
        .replace(/\s+/g, ' ')
        .replace(/\n\s*\n/g, '\n')
        .trim()
      
      setExtractedText(text)
    } catch (err) {
      setError('获取网页内容失败。请确保URL正确且网站允许跨域访问。')
    } finally {
      setIsLoading(false)
    }
  }

  const handleTranslate = async () => {
    if (!extractedText) return

    setIsLoading(true)
    setError(null)
    setTranslateProgress(0)

    try {
      const paragraphs = extractedText.split(/\n+/).filter(p => p.trim().length > 10)
      const translatedParagraphs: string[] = []
      
      for (let i = 0; i < paragraphs.length; i++) {
        const result = await translateWithEnhancements(
          paragraphs[i],
          sourceLang,
          targetLang,
          apiConfig,
          {
            useTerms,
            useMemory,
            saveToHistory: false,
            saveToMemory: true,
          }
        )
        translatedParagraphs.push(result.translatedText)
        setTranslateProgress((i + 1) / paragraphs.length)
      }
      
      setTranslatedText(translatedParagraphs.join('\n\n'))
    } catch (err) {
      setError(err instanceof Error ? err.message : '翻译失败')
    } finally {
      setIsLoading(false)
    }
  }

  const handleOpenIframe = () => {
    if (!url.trim()) {
      setError('请输入URL')
      return
    }
    if (iframeRef.current) {
      iframeRef.current.src = url
    }
  }

  const bookmarkletCode = `javascript:(function(){
  var url = '${window.location.origin}/#/plugin?url=' + encodeURIComponent(window.location.href);
  window.open(url, '_blank', 'width=800,height=600');
})();`

  const handleCopyBookmarklet = async () => {
    await navigator.clipboard.writeText(bookmarkletCode)
    alert('书签代码已复制，请添加到浏览器书签栏')
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="bg-white rounded-2xl shadow-xl p-6 mb-6">
        <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
          <span>🌐</span> 网页翻译
        </h2>

        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-4 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium text-blue-800 mb-1">📌 浏览器翻译插件（书签）</h3>
              <p className="text-sm text-blue-600">将此书签添加到浏览器，在任何网页点击即可翻译</p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setShowCode(!showCode)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                {showCode ? '隐藏代码' : '获取书签代码'}
              </button>
            </div>
          </div>
          
          {showCode && (
            <div className="mt-4 p-4 bg-white rounded-lg">
              <p className="text-sm text-gray-600 mb-2">
                1. 复制下方代码 → 2. 在浏览器添加新书签 → 3. 将代码粘贴到网址位置
              </p>
              <div className="flex gap-2">
                <code className="flex-1 p-3 bg-gray-100 rounded text-xs overflow-x-auto">
                  {bookmarkletCode}
                </code>
                <button
                  onClick={handleCopyBookmarklet}
                  className="px-3 py-2 bg-gray-200 rounded hover:bg-gray-300 transition-colors"
                >
                  📋 复制
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="flex gap-4 mb-6 items-end flex-wrap">
          <div className="flex-1 min-w-[300px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">网页URL</label>
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <button
            onClick={handleExtractText}
            disabled={isLoading || !url.trim()}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 transition-colors flex items-center gap-2"
          >
            {isLoading ? <LoadingSpinner size="sm" /> : '🔍'}
            获取内容
          </button>
          <button
            onClick={handleOpenIframe}
            disabled={!url.trim()}
            className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 disabled:opacity-50 transition-colors"
          >
            🖼️ 预览网页
          </button>
        </div>

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

        {error && (
          <div className="mb-6 p-3 bg-red-50 text-red-700 rounded-lg">
            ⚠️ {error}
          </div>
        )}

        {extractedText && (
          <div className="mb-6">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-medium text-gray-500">
                提取的文本 ({extractedText.length} 字符)
              </span>
              <button
                onClick={handleTranslate}
                disabled={isLoading}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-300 transition-colors flex items-center gap-2"
              >
                {isLoading ? <LoadingSpinner size="sm" /> : '🌐'}
                翻译全文
              </button>
            </div>
            
            {isLoading && translateProgress > 0 && (
              <div className="mb-4">
                <div className="flex justify-between text-xs text-gray-500 mb-1">
                  <span>翻译进度</span>
                  <span>{Math.round(translateProgress * 100)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-green-500 h-2 rounded-full transition-all"
                    style={{ width: `${translateProgress * 100}%` }}
                  />
                </div>
              </div>
            )}

            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-gray-500 mb-1">
                  原文 ({LANGUAGE_MAP[sourceLang].nativeName})
                </p>
                <div className="p-4 bg-gray-50 rounded-lg h-80 overflow-y-auto text-sm">
                  {extractedText}
                </div>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">
                  译文 ({LANGUAGE_MAP[targetLang].nativeName})
                </p>
                <div className="p-4 bg-blue-50 rounded-lg h-80 overflow-y-auto text-sm">
                  {translatedText || (
                    <span className="text-gray-400">点击"翻译全文"开始翻译...</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {iframeRef?.current?.src && (
        <div className="bg-white rounded-2xl shadow-xl p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span>🖼️</span> 网页预览
          </h3>
          <iframe
            ref={iframeRef}
            className="w-full h-[600px] border border-gray-200 rounded-lg"
            sandbox="allow-same-origin allow-scripts"
          />
        </div>
      )}
    </div>
  )
}



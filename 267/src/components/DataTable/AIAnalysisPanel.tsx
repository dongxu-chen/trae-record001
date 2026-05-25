import { useState, useCallback, useEffect, useRef } from 'react'
import { Send, Sparkles, Loader2, Bot, User, History, Trash2 } from 'lucide-react'
import type { DataRow, AIAnalysisResult } from '@/types/table'
import { analyzeQuery, getSuggestedQueries } from '@/utils/aiAnalysis'

interface AIAnalysisPanelProps {
  data: DataRow[]
}

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  result?: AIAnalysisResult
  timestamp: Date
}

export function AIAnalysisPanel({ data }: AIAnalysisPanelProps) {
  const [query, setQuery] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const suggestedQueries = getSuggestedQueries()

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleQuery = useCallback(async (userQuery: string) => {
    if (!userQuery.trim() || isLoading) return

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: userQuery,
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setQuery('')
    setIsLoading(true)

    setTimeout(() => {
      const result = analyzeQuery(userQuery, data)

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: result.result,
        result,
        timestamp: new Date(),
      }

      setMessages(prev => [...prev, assistantMessage])
      setIsLoading(false)
    }, 500)
  }, [data, isLoading])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleQuery(query)
    }
  }

  const clearHistory = () => {
    setMessages([])
  }

  return (
    <div className="bg-white border rounded-lg p-4 flex flex-col h-[500px]">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <Sparkles className="text-yellow-500" size={20} />
          AI 数据分析
        </h3>
        {messages.length > 0 && (
          <button
            onClick={clearHistory}
            className="flex items-center gap-1 text-sm text-gray-500 hover:text-red-500 transition-colors"
          >
            <Trash2 size={14} />
            清空记录
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 mb-4 min-h-0">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-gray-500">
            <Bot size={48} className="mb-3 text-gray-300" />
            <p className="text-center mb-4">
              输入自然语言问题，我来帮你分析数据
              <br />
              <span className="text-sm">例如："各部门薪资总和是多少？"</span>
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 w-full max-w-lg">
              {suggestedQueries.map((q, i) => (
                <button
                  key={i}
                  onClick={() => handleQuery(q)}
                  className="text-left px-3 py-2 text-sm bg-gray-50 hover:bg-blue-50 hover:text-blue-600 rounded-lg transition-colors border border-gray-100"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map(msg => (
            <div
              key={msg.id}
              className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.role === 'assistant' && (
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center flex-shrink-0">
                  <Bot size={16} className="text-white" />
                </div>
              )}
              <div
                className={`max-w-[80%] px-4 py-2 rounded-lg whitespace-pre-wrap ${
                  msg.role === 'user'
                    ? 'bg-blue-500 text-white rounded-br-none'
                    : 'bg-gray-100 text-gray-800 rounded-bl-none'
                }`}
              >
                {msg.content}
                {msg.result && (
                  <div className="mt-2 pt-2 border-t border-gray-200/50">
                    <span className="text-xs text-gray-500">
                      置信度: {(msg.result.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                )}
              </div>
              {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0">
                  <User size={16} className="text-gray-600" />
                </div>
              )}
            </div>
          ))
        )}
        {isLoading && (
          <div className="flex gap-2">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center">
              <Bot size={16} className="text-white" />
            </div>
            <div className="bg-gray-100 px-4 py-3 rounded-lg rounded-bl-none">
              <Loader2 size={20} className="animate-spin text-gray-500" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="border-t pt-3">
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入问题，例如：各部门薪资总和是多少？"
              className="w-full px-4 py-2 pr-12 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={isLoading}
            />
            {query && (
              <button
                onClick={() => setQuery('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <Trash2 size={16} />
              </button>
            )}
          </div>
          <button
            onClick={() => handleQuery(query)}
            disabled={!query.trim() || isLoading}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            {isLoading ? (
              <Loader2 size={18} className="animate-spin" />
            ) : (
              <Send size={18} />
            )}
            发送
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2 flex items-center gap-1">
          <History size={12} />
          支持自然语言查询，自动识别分析意图
        </p>
      </div>
    </div>
  )
}

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Sparkles,
  Wand2,
  Download,
  Plus,
  Palette,
  RefreshCw,
  Check,
  Loader2,
  History,
} from 'lucide-react'
import {
  generateMultipleIcons,
  styleOptions,
  promptSuggestions,
  type GeneratedIcon,
} from '@/utils/aiIconGenerator'
import { useIconStore } from '@/store/iconStore'

export default function AIGenerate() {
  const navigate = useNavigate()
  const { uploadIcon, categories } = useIconStore()
  const [prompt, setPrompt] = useState('')
  const [style, setStyle] = useState<'outline' | 'filled' | 'duotone' | 'sharp'>('outline')
  const [generatedIcons, setGeneratedIcons] = useState<GeneratedIcon[]>([])
  const [isGenerating, setIsGenerating] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [savingIds, setSavingIds] = useState<Set<string>>(new Set())

  const handleGenerate = async () => {
    if (!prompt.trim()) return

    setIsGenerating(true)
    await new Promise((resolve) => setTimeout(resolve, 1500))

    const icons = generateMultipleIcons(
      { prompt: prompt.trim(), style },
      4
    )
    setGeneratedIcons(icons)
    setIsGenerating(false)
  }

  const handleRegenerate = () => {
    handleGenerate()
  }

  const handleSaveToLibrary = async (icon: GeneratedIcon) => {
    setSavingIds((prev) => new Set(prev).add(icon.id))

    try {
      const formData = new FormData()
      formData.append('name', icon.name)
      formData.append('svgContent', icon.svgContent)
      formData.append('tags', JSON.stringify([icon.style, 'ai-generated']))
      if (selectedCategory) {
        formData.append('categoryId', selectedCategory)
      }

      await uploadIcon(formData)
    } finally {
      setSavingIds((prev) => {
        const next = new Set(prev)
        next.delete(icon.id)
        return next
      })
    }
  }

  const handleDownload = (icon: GeneratedIcon) => {
    const blob = new Blob([icon.svgContent], { type: 'image/svg+xml' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${icon.name}.svg`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-4">
        <div>
          <h1 className="font-display text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Sparkles className="text-primary-500" size={28} />
            AI 图标生成
          </h1>
          <p className="text-gray-500 mt-1">输入描述词，AI 自动生成 SVG 图标</p>
        </div>
      </div>

      <div className="card p-6">
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              描述词
            </label>
            <div className="flex gap-3">
              <input
                type="text"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleGenerate()}
                placeholder="例如：用户头像、首页图标、搜索图标..."
                className="input flex-1 text-lg py-3"
              />
              <button
                onClick={handleGenerate}
                disabled={!prompt.trim() || isGenerating}
                className="btn btn-primary px-8 gap-2"
              >
                {isGenerating ? (
                  <Loader2 size={20} className="animate-spin" />
                ) : (
                  <Wand2 size={20} />
                )}
                {isGenerating ? '生成中...' : '生成'}
              </button>
            </div>
            <div className="flex flex-wrap gap-2 mt-3">
              <span className="text-sm text-gray-500">推荐：</span>
              {promptSuggestions.slice(0, 6).map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => setPrompt(suggestion)}
                  className="px-3 py-1 bg-gray-100 text-gray-600 rounded-full text-sm hover:bg-gray-200 transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">
                <Palette size={16} className="inline mr-1" />
                风格选择
              </label>
              <div className="grid grid-cols-2 gap-3">
                {styleOptions.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => setStyle(option.value as typeof style)}
                    className={`p-4 rounded-xl border-2 text-left transition-all ${
                      style === option.value
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <p className="font-medium text-gray-900">{option.label}</p>
                    <p className="text-xs text-gray-500 mt-1">{option.description}</p>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">
                <History size={16} className="inline mr-1" />
                保存分类（可选）
              </label>
              <select
                value={selectedCategory || ''}
                onChange={(e) => setSelectedCategory(e.target.value || null)}
                className="input"
              >
                <option value="">未分类</option>
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.name}
                  </option>
                ))}
              </select>
              <p className="text-xs text-gray-500 mt-2">
                生成的图标可以直接保存到指定分类
              </p>
            </div>
          </div>
        </div>
      </div>

      {generatedIcons.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">生成结果</h2>
            <button
              onClick={handleRegenerate}
              disabled={isGenerating}
              className="flex items-center gap-2 text-sm text-primary-600 hover:text-primary-700"
            >
              <RefreshCw size={16} className={isGenerating ? 'animate-spin' : ''} />
              重新生成
            </button>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {generatedIcons.map((icon) => (
              <div
                key={icon.id}
                className="card p-4 group hover:shadow-lg transition-shadow"
              >
                <div className="aspect-square bg-gray-50 rounded-xl p-6 flex items-center justify-center mb-4">
                  <div
                    className="w-full h-full"
                    dangerouslySetInnerHTML={{ __html: icon.svgContent }}
                  />
                </div>
                <p className="font-medium text-gray-900 truncate text-sm mb-1">
                  {icon.name}
                </p>
                <p className="text-xs text-gray-500 mb-3">
                  {styleOptions.find((s) => s.value === icon.style)?.label}
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleSaveToLibrary(icon)}
                    disabled={savingIds.has(icon.id)}
                    className="flex-1 btn btn-primary text-xs py-2 gap-1"
                  >
                    {savingIds.has(icon.id) ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : (
                      <Plus size={14} />
                    )}
                    保存
                  </button>
                  <button
                    onClick={() => handleDownload(icon)}
                    className="btn btn-secondary text-xs py-2 px-3"
                  >
                    <Download size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {generatedIcons.length === 0 && !isGenerating && (
        <div className="card p-12 text-center">
          <div className="w-20 h-20 bg-gradient-to-br from-primary-100 to-primary-200 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Sparkles className="text-primary-500" size={36} />
          </div>
          <h3 className="font-semibold text-gray-900 mb-2">开始 AI 生成</h3>
          <p className="text-gray-500 max-w-sm mx-auto mb-6">
            输入描述词，选择风格，AI 将为您生成多个 SVG 图标供选择
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            {promptSuggestions.slice(0, 4).map((suggestion) => (
              <button
                key={suggestion}
                onClick={() => setPrompt(suggestion)}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-full text-sm hover:bg-gray-200 transition-colors"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

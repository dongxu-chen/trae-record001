import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Download,
  Copy,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Trash2,
  Palette,
  Code,
  Check,
  Settings2,
  Variable,
  History,
  RefreshCw,
  Clock,
  Eye,
} from 'lucide-react'
import Prism from 'prismjs'
import 'prismjs/components/prism-jsx'
import 'prismjs/components/prism-typescript'
import 'prismjs/themes/prism-tomorrow.css'
import { useIconStore, type Icon } from '@/store/iconStore'
import {
  replaceSvgSingleColor,
  extractColorsFromSvg,
  replaceSvgColors,
  convertToCssVariables,
  generateReactComponentWithCssVars,
  generateVueComponentWithCssVars,
} from '@/utils/svgUtils'

export default function IconDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { icons, deleteIcon, updateIcon, fetchIcons, fetchCategories, rollbackVersion } = useIconStore()
  const [icon, setIcon] = useState<Icon | null>(null)
  const [zoom, setZoom] = useState(100)
  const [currentColor, setCurrentColor] = useState('#000000')
  const [activeTab, setActiveTab] = useState<'react' | 'vue'>('react')
  const [exportMode, setExportMode] = useState<'simple' | 'css-vars'>('simple')
  const [copied, setCopied] = useState(false)
  const [editingName, setEditingName] = useState(false)
  const [newName, setNewName] = useState('')
  const [extractedColors, setExtractedColors] = useState<string[]>([])
  const [multiColorMode, setMultiColorMode] = useState(false)
  const [colorMap, setColorMap] = useState<Record<string, string>>({})
  const [showVersionPanel, setShowVersionPanel] = useState(false)
  const [previewVersion, setPreviewVersion] = useState<string | null>(null)
  const svgContainerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchIcons()
    fetchCategories()
  }, [fetchIcons, fetchCategories])

  useEffect(() => {
    const found = icons.find((i) => i.id === id)
    if (found) {
      setIcon(found)
      setCurrentColor(found.originalColor || '#000000')
      setNewName(found.name)
      
      const colors = extractColorsFromSvg(found.svgContent)
      setExtractedColors(colors)
      
      const initialColorMap: Record<string, string> = {}
      colors.forEach((c) => {
        initialColorMap[c] = c
      })
      setColorMap(initialColorMap)
    }
  }, [id, icons])

  useEffect(() => {
    if (icon && svgContainerRef.current) {
      const baseSvg = getPreviewSvg()
      let updatedSvg = baseSvg
      
      if (!previewVersion) {
        if (multiColorMode) {
          updatedSvg = replaceSvgColors(baseSvg, colorMap)
        } else {
          updatedSvg = replaceSvgSingleColor(baseSvg, currentColor)
        }
      }
      
      svgContainerRef.current.innerHTML = updatedSvg
    }
  }, [icon, currentColor, multiColorMode, colorMap, previewVersion])

  const handleSingleColorChange = (color: string) => {
    setCurrentColor(color)
    const newColorMap: Record<string, string> = {}
    extractedColors.forEach((c) => {
      newColorMap[c] = color
    })
    setColorMap(newColorMap)
  }

  const getComponentName = () => {
    if (!icon) return 'Icon'
    return icon.name
      .split(/[-_\s]/)
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join('')
  }

  const generateSimpleSvg = () => {
    if (!icon) return ''
    return icon.svgContent
      .replace(/fill="[^"]*"/g, `fill="currentColor"`)
      .replace(/stroke="[^"]*"/g, `stroke="currentColor"`)
      .replace(/stop-color="[^"]*"/g, `stop-color="currentColor"`)
  }

  const generateReactComponent = () => {
    if (!icon) return ''
    const componentName = getComponentName()

    if (exportMode === 'css-vars') {
      const { svg, variables } = convertToCssVariables(icon.svgContent)
      return generateReactComponentWithCssVars(componentName, svg, variables)
    }

    const svgWithColor = generateSimpleSvg()

    return `import { SVGProps } from 'react'

interface ${componentName}Props extends SVGProps<SVGSVGElement> {
  size?: number
  color?: string
}

export function ${componentName}({ 
  size = 24, 
  color = 'currentColor',
  ...props 
}: ${componentName}Props) {
  return (
    ${svgWithColor
      .replace('<svg', `<svg width={size} height={size} color={color}`)
      .replace(/\n/g, '\n    ')}
  )
}

export default ${componentName}`
  }

  const generateVueComponent = () => {
    if (!icon) return ''
    const componentName = getComponentName()

    if (exportMode === 'css-vars') {
      const { svg, variables } = convertToCssVariables(icon.svgContent)
      return generateVueComponentWithCssVars(componentName, svg, variables)
    }

    const svgWithColor = generateSimpleSvg()

    return `<script setup lang="ts">
interface Props {
  size?: number
  color?: string
}

withDefaults(defineProps<Props>(), {
  size: 24,
  color: 'currentColor'
})
</script>

<template>
  ${svgWithColor
    .replace('<svg', `<svg :width="size" :height="size" :color="color"`)
    .replace(/\n/g, '\n  ')}
</template>

<script lang="ts">
export default {
  name: '${componentName}'
}
</script>`
  }

  const copyCode = async () => {
    const code = activeTab === 'react' ? generateReactComponent() : generateVueComponent()
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const downloadSvg = () => {
    if (!icon || !svgContainerRef.current) return
    const svgElement = svgContainerRef.current.querySelector('svg')
    if (!svgElement) return

    const svgData = new XMLSerializer().serializeToString(svgElement)
    const blob = new Blob([svgData], { type: 'image/svg+xml' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${icon.name}.svg`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleDelete = async () => {
    if (confirm('确定要删除这个图标吗？')) {
      await deleteIcon(id!)
      navigate('/icons')
    }
  }

  const handleSaveName = async () => {
    if (icon && newName.trim()) {
      await updateIcon(icon.id, { name: newName.trim() })
      setEditingName(false)
    }
  }

  const handleRollback = async (versionId: string) => {
    if (confirm('确定要回滚到此版本吗？当前版本会被保存为历史版本。')) {
      await rollbackVersion(id!, versionId)
      setPreviewVersion(null)
      setShowVersionPanel(false)
    }
  }

  const getPreviewSvg = () => {
    if (!icon) return ''
    if (previewVersion) {
      const version = icon.versions.find((v) => v.id === previewVersion)
      return version?.svgContent || icon.svgContent
    }
    return icon.svgContent
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const presetColors = [
    '#000000', '#374151', '#6B7280',
    '#DC2626', '#EA580C', '#D97706',
    '#16A34A', '#0891B2', '#2563EB',
    '#7C3AED', '#DB2777', '#9333EA',
  ]

  if (!icon) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full" />
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/icons')}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft size={20} />
        </button>
        <div className="flex-1">
          {editingName ? (
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="input max-w-xs"
                autoFocus
              />
              <button onClick={handleSaveName} className="btn btn-primary">
                保存
              </button>
              <button
                onClick={() => {
                  setEditingName(false)
                  setNewName(icon.name)
                }}
                className="btn btn-secondary"
              >
                取消
              </button>
            </div>
          ) : (
            <h1
              className="font-display text-2xl font-bold text-gray-900 cursor-pointer hover:text-primary-600"
              onClick={() => setEditingName(true)}
            >
              {icon.name}
            </h1>
          )}
        </div>
        <button
          onClick={() => setShowVersionPanel(!showVersionPanel)}
          className={`btn gap-2 ${showVersionPanel ? 'btn-primary' : 'btn-secondary'}`}
        >
          <History size={18} />
          版本历史
        </button>
        <button onClick={downloadSvg} className="btn btn-secondary gap-2">
          <Download size={18} />
          下载 SVG
        </button>
        <button onClick={handleDelete} className="btn btn-danger gap-2">
          <Trash2 size={18} />
          删除
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-6">
          <div className="card p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                <Palette size={20} className="text-primary-500" />
                预览
              </h2>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setZoom(Math.max(25, zoom - 25))}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <ZoomOut size={18} />
                </button>
                <span className="text-sm text-gray-600 w-16 text-center">{zoom}%</span>
                <button
                  onClick={() => setZoom(Math.min(200, zoom + 25))}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <ZoomIn size={18} />
                </button>
                <button
                  onClick={() => {
                    setZoom(100)
                    setCurrentColor(icon.originalColor || '#000000')
                  }}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <RotateCcw size={18} />
                </button>
              </div>
            </div>

            <div className="bg-gray-50 rounded-xl p-8 flex items-center justify-center min-h-[300px]">
              <div
                ref={svgContainerRef}
                style={{ transform: `scale(${zoom / 100})`, transition: 'transform 0.2s ease' }}
                className="flex items-center justify-center"
              />
            </div>
          </div>

          <div className="card p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-gray-900">颜色调整</h2>
              <button
                onClick={() => setMultiColorMode(!multiColorMode)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  multiColorMode
                    ? 'bg-primary-100 text-primary-700'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                <Settings2 size={14} />
                {multiColorMode ? '多颜色' : '单色'}
              </button>
            </div>

            {multiColorMode ? (
              <div className="space-y-3">
                <p className="text-sm text-gray-500">检测到 {extractedColors.length} 种颜色</p>
                {extractedColors.map((color, index) => (
                  <div key={color} className="flex items-center gap-3">
                    <span className="text-xs text-gray-500 w-16">颜色 {index + 1}</span>
                    <input
                      type="color"
                      value={colorMap[color] || color}
                      onChange={(e) => {
                        setColorMap((prev) => ({
                          ...prev,
                          [color]: e.target.value,
                        }))
                      }}
                      className="w-10 h-10 rounded-lg cursor-pointer border-0"
                    />
                    <input
                      type="text"
                      value={colorMap[color] || color}
                      onChange={(e) => {
                        setColorMap((prev) => ({
                          ...prev,
                          [color]: e.target.value,
                        }))
                      }}
                      className="input uppercase text-sm py-1 h-9"
                    />
                    <div
                      className="w-10 h-10 rounded-lg border border-gray-200"
                      style={{ backgroundColor: color }}
                      title={`原始: ${color}`}
                    />
                  </div>
                ))}
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center gap-4">
                  <input
                    type="color"
                    value={currentColor}
                    onChange={(e) => handleSingleColorChange(e.target.value)}
                    className="w-12 h-12 rounded-lg cursor-pointer border-0"
                  />
                  <input
                    type="text"
                    value={currentColor}
                    onChange={(e) => handleSingleColorChange(e.target.value)}
                    className="input uppercase flex-1 max-w-xs"
                  />
                </div>
                <div className="grid grid-cols-6 gap-2">
                  {presetColors.map((color) => (
                    <button
                      key={color}
                      onClick={() => handleSingleColorChange(color)}
                      className={`aspect-square rounded-lg border-2 transition-all ${
                        currentColor.toLowerCase() === color.toLowerCase()
                          ? 'border-primary-500 ring-2 ring-primary-200'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                      style={{ backgroundColor: color }}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900 flex items-center gap-2">
              <Code size={20} className="text-emerald-500" />
              导出组件代码
            </h2>
            <button
              onClick={copyCode}
              className="btn btn-secondary gap-2"
            >
              {copied ? <Check size={16} className="text-emerald-500" /> : <Copy size={16} />}
              {copied ? '已复制' : '复制代码'}
            </button>
          </div>

          <div className="space-y-3 mb-4">
            <div className="flex gap-2">
              <button
                onClick={() => setActiveTab('react')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === 'react'
                    ? 'bg-primary-100 text-primary-700'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                React
              </button>
              <button
                onClick={() => setActiveTab('vue')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === 'vue'
                    ? 'bg-emerald-100 text-emerald-700'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                Vue
              </button>
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => setExportMode('simple')}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 ${
                  exportMode === 'simple'
                    ? 'bg-gray-800 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                简单模式
              </button>
              <button
                onClick={() => setExportMode('css-vars')}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 ${
                  exportMode === 'css-vars'
                    ? 'bg-gray-800 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                <Variable size={12} />
                CSS 变量
              </button>
            </div>

            {exportMode === 'css-vars' && (
              <div className="p-3 bg-blue-50 rounded-lg border border-blue-100">
                <p className="text-xs text-blue-700">
                  <strong>主题切换模式：</strong>生成的组件支持通过 CSS 变量动态切换颜色，
                  可用于实现深色/浅色主题切换。
                </p>
              </div>
            )}
          </div>

          <div className="rounded-lg overflow-hidden">
            <pre className="!p-4 !m-0 text-sm overflow-x-auto">
              <code
                className={activeTab === 'react' ? 'language-tsx' : 'language-vue'}
                dangerouslySetInnerHTML={{
                  __html: Prism.highlight(
                    activeTab === 'react' ? generateReactComponent() : generateVueComponent(),
                    Prism.languages[activeTab === 'react' ? 'tsx' : 'javascript'],
                    activeTab === 'react' ? 'tsx' : 'javascript'
                  ),
                }}
              />
            </pre>
          </div>

          <div className="mt-4 pt-4 border-t border-gray-100">
            <h3 className="text-sm font-medium text-gray-700 mb-2">标签</h3>
            <div className="flex flex-wrap gap-2">
              {icon.tags.length > 0 ? (
                icon.tags.map((tag) => (
                  <span
                    key={tag}
                    className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm"
                  >
                    {tag}
                  </span>
                ))
              ) : (
                <span className="text-sm text-gray-500">暂无标签</span>
              )}
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-gray-100">
            <h3 className="text-sm font-medium text-gray-700 mb-3">使用统计</h3>
            <div className="grid grid-cols-3 gap-3">
              <div className="text-center p-3 bg-blue-50 rounded-lg">
                <Eye size={18} className="mx-auto mb-1 text-blue-500" />
                <p className="text-lg font-bold text-blue-700">
                  {icon.analytics?.viewCount || 0}
                </p>
                <p className="text-xs text-blue-600">浏览</p>
              </div>
              <div className="text-center p-3 bg-emerald-50 rounded-lg">
                <Download size={18} className="mx-auto mb-1 text-emerald-500" />
                <p className="text-lg font-bold text-emerald-700">
                  {icon.analytics?.downloadCount || 0}
                </p>
                <p className="text-xs text-emerald-600">下载</p>
              </div>
              <div className="text-center p-3 bg-amber-50 rounded-lg">
                <Code size={18} className="mx-auto mb-1 text-amber-500" />
                <p className="text-lg font-bold text-amber-700">
                  {icon.analytics?.exportCount || 0}
                </p>
                <p className="text-xs text-amber-600">导出</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {showVersionPanel && (
        <div className="card overflow-hidden">
          <div className="p-4 border-b border-gray-100 flex items-center justify-between">
            <h2 className="font-semibold text-gray-900 flex items-center gap-2">
              <History size={20} className="text-primary-500" />
              版本历史
              <span className="text-sm font-normal text-gray-500">
                当前版本: v{icon.version}
              </span>
            </h2>
            {previewVersion && (
              <button
                onClick={() => setPreviewVersion(null)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm text-gray-700 transition-colors"
              >
                <RefreshCw size={14} />
                退出预览
              </button>
            )}
          </div>

          <div className="max-h-80 overflow-y-auto">
            {icon.versions && icon.versions.length > 0 ? (
              <div className="divide-y divide-gray-100">
                {[...icon.versions].reverse().map((version) => (
                  <div
                    key={version.id}
                    className={`p-4 transition-colors ${
                      previewVersion === version.id
                        ? 'bg-primary-50'
                        : 'hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 bg-gray-50 rounded-lg p-2 flex items-center justify-center flex-shrink-0">
                        <div
                          className="w-full h-full"
                          dangerouslySetInnerHTML={{
                            __html: version.svgContent,
                          }}
                        />
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-gray-900">
                            v{version.version}
                          </span>
                          {version.version === icon.version && (
                            <span className="px-2 py-0.5 bg-emerald-100 text-emerald-700 text-xs rounded-full">
                              当前
                            </span>
                          )}
                          {previewVersion === version.id && (
                            <span className="px-2 py-0.5 bg-primary-100 text-primary-700 text-xs rounded-full">
                              预览中
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-gray-600 mt-0.5">
                          {version.name}
                        </p>
                        <p className="text-xs text-gray-500 mt-0.5 flex items-center gap-1">
                          <Clock size={12} />
                          {formatDate(version.createdAt)}
                        </p>
                        {version.note && (
                          <p className="text-xs text-gray-500 mt-1">
                            {version.note}
                          </p>
                        )}
                      </div>

                      <div className="flex gap-2 flex-shrink-0">
                        {version.version !== icon.version && (
                          <>
                            <button
                              onClick={() =>
                                setPreviewVersion(
                                  previewVersion === version.id
                                    ? null
                                    : version.id
                                )
                              }
                              className={`px-3 py-1.5 rounded-lg text-sm transition-colors flex items-center gap-1 ${
                                previewVersion === version.id
                                  ? 'bg-primary-100 text-primary-700'
                                  : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
                              }`}
                            >
                              <Eye size={14} />
                              {previewVersion === version.id ? '取消' : '预览'}
                            </button>
                            <button
                              onClick={() => handleRollback(version.id)}
                              className="px-3 py-1.5 bg-primary-500 hover:bg-primary-600 text-white rounded-lg text-sm transition-colors flex items-center gap-1"
                            >
                              <RefreshCw size={14} />
                              回滚
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center text-gray-500">
                <History size={40} className="mx-auto mb-2 text-gray-300" />
                <p>暂无历史版本</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

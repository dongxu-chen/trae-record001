import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Download, Trash2, Grid, List, Filter, CheckSquare, Square } from 'lucide-react'
import { useIconStore } from '@/store/iconStore'
import JSZip from 'jszip'

export default function IconLibrary() {
  const {
    icons,
    categories,
    selectedIcons,
    loading,
    fetchIcons,
    fetchCategories,
    toggleSelect,
    clearSelection,
    deleteIcon,
    setSelectedCategory,
    selectedCategory,
  } = useIconStore()
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [showFilters, setShowFilters] = useState(false)

  useEffect(() => {
    fetchIcons()
    fetchCategories()
  }, [fetchIcons, fetchCategories])

  useEffect(() => {
    fetchIcons()
  }, [selectedCategory, fetchIcons])

  const handleBatchDownload = async () => {
    const zip = new JSZip()
    const selectedIconData = icons.filter((icon) => selectedIcons.includes(icon.id))
    
    selectedIconData.forEach((icon) => {
      zip.file(`${icon.name}.svg`, icon.svgContent)
    })

    const content = await zip.generateAsync({ type: 'blob' })
    const url = URL.createObjectURL(content)
    const a = document.createElement('a')
    a.href = url
    a.download = 'icons.zip'
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleBatchDelete = async () => {
    if (confirm(`确定要删除选中的 ${selectedIcons.length} 个图标吗？`)) {
      for (const id of selectedIcons) {
        await deleteIcon(id)
      }
      clearSelection()
    }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-gray-900">图标库</h1>
          <p className="text-gray-500 mt-1">共 {icons.length} 个图标</p>
        </div>
        <div className="flex items-center gap-3">
          {selectedIcons.length > 0 && (
            <>
              <button
                onClick={handleBatchDownload}
                className="btn btn-secondary gap-2"
              >
                <Download size={18} />
                下载选中 ({selectedIcons.length})
              </button>
              <button
                onClick={handleBatchDelete}
                className="btn btn-danger gap-2"
              >
                <Trash2 size={18} />
                删除
              </button>
              <button
                onClick={clearSelection}
                className="btn btn-secondary"
              >
                取消选择
              </button>
            </>
          )}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`p-2 rounded-lg transition-colors ${
              showFilters ? 'bg-primary-100 text-primary-600' : 'hover:bg-gray-100 text-gray-600'
            }`}
          >
            <Filter size={20} />
          </button>
          <div className="flex border border-gray-200 rounded-lg overflow-hidden">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 ${viewMode === 'grid' ? 'bg-primary-50 text-primary-600' : 'text-gray-600'}`}
            >
              <Grid size={20} />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 ${viewMode === 'list' ? 'bg-primary-50 text-primary-600' : 'text-gray-600'}`}
            >
              <List size={20} />
            </button>
          </div>
        </div>
      </div>

      {showFilters && (
        <div className="card p-4 animate-slide-up">
          <div className="flex flex-wrap gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">分类筛选</label>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => setSelectedCategory(null)}
                  className={`px-3 py-1.5 rounded-full text-sm transition-colors ${
                    !selectedCategory
                      ? 'bg-primary-500 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  全部
                </button>
                {categories.map((category) => (
                  <button
                    key={category.id}
                    onClick={() => setSelectedCategory(category.id)}
                    className={`px-3 py-1.5 rounded-full text-sm transition-colors ${
                      selectedCategory === category.id
                        ? 'bg-primary-500 text-white'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {category.name} ({category._count?.icons || 0})
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="aspect-square bg-gray-100 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : icons.length === 0 ? (
        <div className="card p-12 text-center">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Download size={32} className="text-gray-400" />
          </div>
          <h3 className="font-semibold text-gray-900 mb-2">暂无图标</h3>
          <p className="text-gray-500 mb-4">开始上传您的第一个SVG图标</p>
          <Link to="/upload" className="btn btn-primary">
            上传图标
          </Link>
        </div>
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {icons.map((icon) => (
            <div
              key={icon.id}
              className={`card p-4 cursor-pointer group transition-all ${
                selectedIcons.includes(icon.id) ? 'ring-2 ring-primary-500' : ''
              }`}
            >
              <div className="relative">
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    toggleSelect(icon.id)
                  }}
                  className="absolute -top-1 -left-1 z-10 opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  {selectedIcons.includes(icon.id) ? (
                    <CheckSquare className="text-primary-500" size={20} fill="currentColor" />
                  ) : (
                    <Square className="text-gray-400" size={20} />
                  )}
                </button>
                <Link to={`/icons/${icon.id}`}>
                  <div className="aspect-square icon-preview bg-gray-50 rounded-lg p-4 flex items-center justify-center">
                    <div
                      className="w-full h-full"
                      dangerouslySetInnerHTML={{ __html: icon.svgContent }}
                    />
                  </div>
                </Link>
              </div>
              <p className="text-sm text-gray-700 mt-3 truncate text-center">{icon.name}</p>
            </div>
          ))}
        </div>
      ) : (
        <div className="card divide-y divide-gray-100">
          {icons.map((icon) => (
            <div
              key={icon.id}
              className={`p-4 flex items-center gap-4 hover:bg-gray-50 transition-colors ${
                selectedIcons.includes(icon.id) ? 'bg-primary-50' : ''
              }`}
            >
              <button onClick={() => toggleSelect(icon.id)}>
                {selectedIcons.includes(icon.id) ? (
                  <CheckSquare className="text-primary-500" size={20} fill="currentColor" />
                ) : (
                  <Square className="text-gray-400" size={20} />
                )}
              </button>
              <Link to={`/icons/${icon.id}`} className="flex items-center gap-4 flex-1">
                <div className="w-12 h-12 bg-gray-50 rounded-lg p-2 flex items-center justify-center">
                  <div
                    className="w-full h-full"
                    dangerouslySetInnerHTML={{ __html: icon.svgContent }}
                  />
                </div>
                <div className="flex-1">
                  <p className="font-medium text-gray-900">{icon.name}</p>
                  <p className="text-sm text-gray-500">
                    {icon.tags.slice(0, 3).join(', ')}
                  </p>
                </div>
                <p className="text-sm text-gray-500">
                  {new Date(icon.createdAt).toLocaleDateString('zh-CN')}
                </p>
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

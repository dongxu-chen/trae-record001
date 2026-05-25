import { useEffect, useState } from 'react'
import { FolderTree, Plus, Pencil, Trash2, ChevronRight, ChevronDown, GripVertical } from 'lucide-react'
import { useIconStore, type Category } from '@/store/iconStore'

export default function Categories() {
  const { categories, fetchCategories } = useIconStore()
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set())
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editName, setEditName] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)
  const [newCategoryName, setNewCategoryName] = useState('')
  const [parentCategoryId, setParentCategoryId] = useState<string | null>(null)

  useEffect(() => {
    fetchCategories()
  }, [fetchCategories])

  const toggleExpand = (id: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const handleAddCategory = async () => {
    if (!newCategoryName.trim()) return

    try {
      await fetch('/api/categories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newCategoryName.trim(),
          parentId: parentCategoryId,
        }),
      })
      setShowAddModal(false)
      setNewCategoryName('')
      setParentCategoryId(null)
      fetchCategories()
    } catch {
      // silent fail
    }
  }

  const handleEditCategory = async (id: string) => {
    if (!editName.trim()) return

    try {
      await fetch(`/api/categories/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: editName.trim() }),
      })
      setEditingId(null)
      setEditName('')
      fetchCategories()
    } catch {
      // silent fail
    }
  }

  const handleDeleteCategory = async (id: string) => {
    if (!confirm('确定要删除此分类吗？分类下的图标将变为未分类。')) return

    try {
      await fetch(`/api/categories/${id}`, { method: 'DELETE' })
      fetchCategories()
    } catch {
      // silent fail
    }
  }

  const renderCategory = (category: Category, level: number = 0) => {
    const children = categories.filter((c) => c.parentId === category.id)
    const isExpanded = expandedCategories.has(category.id)
    const hasChildren = children.length > 0

    return (
      <div key={category.id}>
        <div
          className="flex items-center gap-3 p-3 hover:bg-gray-50 rounded-lg group"
          style={{ paddingLeft: `${level * 24 + 12}px` }}
        >
          <GripVertical size={16} className="text-gray-300 cursor-grab opacity-0 group-hover:opacity-100" />
          
          {hasChildren ? (
            <button
              onClick={() => toggleExpand(category.id)}
              className="p-1 hover:bg-gray-200 rounded transition-colors"
            >
              {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            </button>
          ) : (
            <span className="w-[34px]" />
          )}

          <FolderTree size={20} className="text-primary-500" />

          {editingId === category.id ? (
            <input
              type="text"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              className="input flex-1 max-w-xs py-1"
              autoFocus
              onBlur={() => handleEditCategory(category.id)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleEditCategory(category.id)
                if (e.key === 'Escape') {
                  setEditingId(null)
                  setEditName('')
                }
              }}
            />
          ) : (
            <span className="flex-1 font-medium text-gray-900">{category.name}</span>
          )}

          <span className="text-sm text-gray-500 px-2 py-1 bg-gray-100 rounded-full">
            {category._count?.icons || 0} 个图标
          </span>

          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={() => {
                setEditingId(category.id)
                setEditName(category.name)
              }}
              className="p-2 hover:bg-gray-200 rounded-lg transition-colors"
            >
              <Pencil size={16} />
            </button>
            <button
              onClick={() => handleDeleteCategory(category.id)}
              className="p-2 hover:bg-red-100 text-red-600 rounded-lg transition-colors"
            >
              <Trash2 size={16} />
            </button>
          </div>
        </div>

        {isExpanded && hasChildren && (
          <div>
            {children.map((child) => renderCategory(child, level + 1))}
          </div>
        )}
      </div>
    )
  }

  const rootCategories = categories.filter((c) => !c.parentId)

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-gray-900">分类管理</h1>
          <p className="text-gray-500 mt-1">管理图标分类，支持多级嵌套</p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="btn btn-primary gap-2"
        >
          <Plus size={18} />
          新建分类
        </button>
      </div>

      <div className="card">
        {rootCategories.length === 0 ? (
          <div className="p-12 text-center">
            <FolderTree size={48} className="mx-auto mb-4 text-gray-300" />
            <h3 className="font-semibold text-gray-900 mb-2">暂无分类</h3>
            <p className="text-gray-500 mb-4">创建分类来组织您的图标</p>
            <button
              onClick={() => setShowAddModal(true)}
              className="btn btn-primary"
            >
              创建第一个分类
            </button>
          </div>
        ) : (
          <div className="p-4">
            {rootCategories.map((category) => renderCategory(category))}
          </div>
        )}
      </div>

      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 animate-fade-in">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md animate-scale-in">
            <h2 className="font-display text-xl font-bold text-gray-900 mb-6">新建分类</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">分类名称</label>
                <input
                  type="text"
                  value={newCategoryName}
                  onChange={(e) => setNewCategoryName(e.target.value)}
                  className="input"
                  placeholder="输入分类名称"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">父分类（可选）</label>
                <select
                  value={parentCategoryId || ''}
                  onChange={(e) => setParentCategoryId(e.target.value || null)}
                  className="input"
                >
                  <option value="">无（作为顶级分类）</option>
                  {categories.map((cat) => (
                    <option key={cat.id} value={cat.id}>
                      {cat.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => {
                  setShowAddModal(false)
                  setNewCategoryName('')
                  setParentCategoryId(null)
                }}
                className="btn btn-secondary"
              >
                取消
              </button>
              <button
                onClick={handleAddCategory}
                disabled={!newCategoryName.trim()}
                className="btn btn-primary"
              >
                创建
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

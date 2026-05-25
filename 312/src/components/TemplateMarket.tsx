import { useState, useEffect } from 'react'
import { useEditorStore } from '@/lib/store'
import { templateManager } from '@/lib/templateManager'
import { AnimationTemplate } from '@/types'

export function TemplateMarket() {
  const { project, selectedLayerId, addKeyframe } = useEditorStore()
  const [templates, setTemplates] = useState<AnimationTemplate[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('全部')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showImportModal, setShowImportModal] = useState(false)
  const [newTemplate, setNewTemplate] = useState({
    name: '',
    description: '',
    tags: '',
    category: '基础动画',
  })
  const [importJson, setImportJson] = useState('')

  useEffect(() => {
    loadTemplates()
  }, [searchQuery, selectedCategory])

  const loadTemplates = () => {
    let result = templateManager.getAll()

    if (selectedCategory !== '全部') {
      result = templateManager.getByCategory(selectedCategory)
    }

    if (searchQuery) {
      result = templateManager.search(searchQuery)
    }

    setTemplates(result)
  }

  const applyTemplate = (template: AnimationTemplate) => {
    if (!project || !selectedLayerId) {
      alert('请先选择一个图层')
      return
    }

    template.animation.tracks.forEach((track) => {
      track.keyframes.forEach((kf) => {
        addKeyframe(selectedLayerId, track.property, kf.time, kf.value)
      })
    })

    templateManager.incrementDownload(template.id)
    loadTemplates()
  }

  const handleLike = (templateId: string) => {
    templateManager.likeTemplate(templateId)
    loadTemplates()
  }

  const handleExport = (templateId: string) => {
    const json = templateManager.exportTemplate(templateId)
    if (json) {
      const blob = new Blob([json], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `template-${templateId}.json`
      a.click()
      URL.revokeObjectURL(url)
    }
  }

  const handleImport = () => {
    const imported = templateManager.importTemplate(importJson)
    if (imported) {
      alert('模板导入成功!')
      setImportJson('')
      setShowImportModal(false)
      loadTemplates()
    } else {
      alert('导入失败，请检查JSON格式')
    }
  }

  const handleCreateTemplate = () => {
    if (!project || !newTemplate.name) {
      alert('请填写模板名称')
      return
    }

    const selectedLayers = selectedLayerId
      ? project.layers.filter((l) => l.id === selectedLayerId)
      : project.layers.filter((l) => l.tracks.length > 0)

    if (selectedLayers.length === 0) {
      alert('请选择有动画的图层')
      return
    }

    templateManager.createTemplate(
      newTemplate.name,
      newTemplate.description,
      selectedLayers,
      project.duration,
      project.framerate,
      newTemplate.tags.split(',').map((t) => t.trim()).filter(Boolean),
      newTemplate.category
    )

    setNewTemplate({ name: '', description: '', tags: '', category: '基础动画' })
    setShowCreateModal(false)
    loadTemplates()
  }

  const categories = ['全部', ...templateManager.getCategories()]

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ padding: '16px', borderBottom: '1px solid #0f3460' }}>
        <div style={{ display: 'flex', gap: '10px', marginBottom: '12px' }}>
          <button className="btn btn-secondary" onClick={() => setShowCreateModal(true)}>
            + 保存为模板
          </button>
          <button className="btn btn-secondary" onClick={() => setShowImportModal(true)}>
            📥 导入模板
          </button>
        </div>
        <input
          type="text"
          className="property-input"
          style={{ width: '100%', marginBottom: '10px' }}
          placeholder="搜索模板..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
          {categories.map((cat) => (
            <button
              key={cat}
              className="btn"
              style={{
                padding: '4px 10px',
                fontSize: '12px',
                background: selectedCategory === cat ? '#e94560' : '#0f3460',
                border: 'none',
                borderRadius: '4px',
                color: 'white',
                cursor: 'pointer',
              }}
              onClick={() => setSelectedCategory(cat)}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>
        {templates.map((template) => (
          <div
            key={template.id}
            style={{
              background: '#0f3460',
              borderRadius: '8px',
              padding: '12px',
              marginBottom: '10px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '8px' }}>
              <div>
                <h4 style={{ margin: '0 0 4px 0', fontSize: '14px' }}>{template.name}</h4>
                <span
                  style={{
                    fontSize: '10px',
                    padding: '2px 6px',
                    background: '#1a4a7a',
                    borderRadius: '4px',
                    color: '#888',
                  }}
                >
                  {template.category}
                </span>
              </div>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <span style={{ fontSize: '12px', color: '#facc15' }}>♥ {template.likes}</span>
                <span style={{ fontSize: '12px', color: '#888' }}>⬇ {template.downloads}</span>
              </div>
            </div>

            <p style={{ fontSize: '12px', color: '#aaa', margin: '0 0 8px 0' }}>
              {template.description}
            </p>

            <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', marginBottom: '10px' }}>
              {template.tags.map((tag) => (
                <span
                  key={tag}
                  style={{
                    fontSize: '10px',
                    padding: '2px 6px',
                    background: '#16213e',
                    borderRadius: '4px',
                    color: '#888',
                  }}
                >
                  {tag}
                </span>
              ))}
            </div>

            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                className="btn btn-primary"
                style={{ padding: '6px 12px', fontSize: '12px', flex: 1 }}
                onClick={() => applyTemplate(template)}
              >
                应用
              </button>
              <button
                className="btn btn-secondary"
                style={{ padding: '6px 10px', fontSize: '12px' }}
                onClick={() => handleLike(template.id)}
              >
                ♥
              </button>
              {template.id.startsWith('custom-') || template.id.startsWith('imported-') ? (
                <button
                  className="btn btn-secondary"
                  style={{ padding: '6px 10px', fontSize: '12px' }}
                  onClick={() => handleExport(template.id)}
                >
                  📤
                </button>
              ) : null}
            </div>
          </div>
        ))}
      </div>

      {showCreateModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.7)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
          onClick={() => setShowCreateModal(false)}
        >
          <div
            style={{
              background: '#16213e',
              padding: '24px',
              borderRadius: '12px',
              width: '400px',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ marginBottom: '20px', color: '#e94560' }}>保存为模板</h3>
            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px' }}>名称</label>
              <input
                type="text"
                className="property-input"
                style={{ width: '100%' }}
                value={newTemplate.name}
                onChange={(e) => setNewTemplate({ ...newTemplate, name: e.target.value })}
                placeholder="模板名称"
              />
            </div>
            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px' }}>描述</label>
              <textarea
                className="property-input"
                style={{ width: '100%', minHeight: '60px' }}
                value={newTemplate.description}
                onChange={(e) => setNewTemplate({ ...newTemplate, description: e.target.value })}
                placeholder="模板描述"
              />
            </div>
            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px' }}>分类</label>
              <select
                className="property-input"
                style={{ width: '100%' }}
                value={newTemplate.category}
                onChange={(e) => setNewTemplate({ ...newTemplate, category: e.target.value })}
              >
                <option>基础动画</option>
                <option>加载动画</option>
                <option>情感动画</option>
                <option>反馈动画</option>
                <option>趣味动画</option>
                <option>特效动画</option>
              </select>
            </div>
            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px' }}>标签 (逗号分隔)</label>
              <input
                type="text"
                className="property-input"
                style={{ width: '100%' }}
                value={newTemplate.tags}
                onChange={(e) => setNewTemplate({ ...newTemplate, tags: e.target.value })}
                placeholder="弹跳, 活泼, 通用"
              />
            </div>
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>
                取消
              </button>
              <button className="btn btn-primary" onClick={handleCreateTemplate}>
                保存
              </button>
            </div>
          </div>
        </div>
      )}

      {showImportModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.7)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
          onClick={() => setShowImportModal(false)}
        >
          <div
            style={{
              background: '#16213e',
              padding: '24px',
              borderRadius: '12px',
              width: '500px',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ marginBottom: '20px', color: '#e94560' }}>导入模板</h3>
            <p style={{ fontSize: '13px', color: '#888', marginBottom: '12px' }}>
              粘贴模板 JSON 内容:
            </p>
            <textarea
              className="property-input"
              style={{ width: '100%', minHeight: '200px', fontFamily: 'monospace', fontSize: '12px' }}
              value={importJson}
              onChange={(e) => setImportJson(e.target.value)}
              placeholder='{"id": "...", "name": "...", ...}'
            />
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '16px' }}>
              <button className="btn btn-secondary" onClick={() => setShowImportModal(false)}>
                取消
              </button>
              <button className="btn btn-primary" onClick={handleImport}>
                导入
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

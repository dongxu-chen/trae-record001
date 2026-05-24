import React, { useState } from 'react'
import { useSelector, useDispatch } from 'react-redux'
import { addMarketComponent, uploadComponent } from '../store/dashboardSlice'

export default function ComponentMarket({ onClose }) {
  const dispatch = useDispatch()
  const marketComponents = useSelector((state) => state.dashboard.marketComponents)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedTag, setSelectedTag] = useState('全部')
  const [showUpload, setShowUpload] = useState(false)

  const allTags = ['全部', ...new Set(marketComponents.flatMap(c => c.tags))]
  const filteredComponents = marketComponents.filter(component => {
    const matchesSearch = component.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      component.description.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesTag = selectedTag === '全部' || component.tags.includes(selectedTag)
    return matchesSearch && matchesTag
  })

  const handleAddComponent = (component) => {
    dispatch(addMarketComponent({
      marketComponent: component,
      position: { col: 0, row: 0, width: 6, height: 4 }
    }))
    onClose && onClose()
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content market-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">🏪 组件市场</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        <div className="market-search">
          <input
            type="text"
            placeholder="搜索组件..."
            className="search-input"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <button className="upload-btn" onClick={() => setShowUpload(!showUpload)}>
            ⬆️ 上传组件
          </button>
        </div>

        <div className="tag-filter">
          {allTags.map(tag => (
            <button
              key={tag}
              className={`tag-btn ${selectedTag === tag ? 'active' : ''}`}
              onClick={() => setSelectedTag(tag)}
            >
              {tag}
            </button>
          ))}
        </div>

        {showUpload && (
          <UploadForm onSuccess={() => setShowUpload(false)} />
        )}

        <div className="market-grid">
          {filteredComponents.map(component => (
            <div key={component.id} className="market-card">
              <div className="market-card-preview">
                <span className="preview-icon">{component.preview}</span>
              </div>
              <div className="market-card-info">
                <h3 className="market-card-name">{component.name}</h3>
                <p className="market-card-desc">{component.description}</p>
                <div className="market-card-meta">
                  <span className="author">
                    <span className="author-avatar">{component.authorAvatar}</span>
                    {component.author}
                  </span>
                  <span className="downloads">⬇️ {component.downloads}</span>
                  <span className="rating">⭐ {component.rating}</span>
                </div>
                <div className="market-card-tags">
                  {component.tags.map(tag => (
                    <span key={tag} className="market-tag">{tag}</span>
                  ))}
                </div>
                <button
                  className="add-component-btn"
                  onClick={() => handleAddComponent(component)}
                >
                  添加到仪表板
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function UploadForm({ onSuccess }) {
  const dispatch = useDispatch()
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    tags: '',
    preview: '📊',
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!formData.name || !formData.description) return

    dispatch(uploadComponent({
      ...formData,
      tags: formData.tags.split(',').map(t => t.trim()).filter(Boolean),
      config: { value: 0 },
    }))
    onSuccess()
  }

  return (
    <form className="upload-form" onSubmit={handleSubmit}>
      <h4>上传自定义组件</h4>
      <div className="form-row">
        <label>组件名称</label>
        <input
          type="text"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          placeholder="输入组件名称"
          required
        />
      </div>
      <div className="form-row">
        <label>描述</label>
        <textarea
          value={formData.description}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          placeholder="描述组件功能"
          required
        />
      </div>
      <div className="form-row">
        <label>标签（逗号分隔）</label>
        <input
          type="text"
          value={formData.tags}
          onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
          placeholder="指标, 可视化"
        />
      </div>
      <div className="form-row">
        <label>预览图标</label>
        <select
          value={formData.preview}
          onChange={(e) => setFormData({ ...formData, preview: e.target.value })}
        >
          <option value="📊">📊</option>
          <option value="📈">📈</option>
          <option value="📋">📋</option>
          <option value="🎯">🎯</option>
          <option value="🔥">🔥</option>
          <option value="🔔">🔔</option>
        </select>
      </div>
      <button type="submit" className="submit-btn">
        发布组件
      </button>
    </form>
  )
}

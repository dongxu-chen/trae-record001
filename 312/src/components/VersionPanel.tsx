import { useState } from 'react'
import { useEditorStore } from '@/lib/store'

export function VersionPanel() {
  const { project, createVersion, restoreVersion } = useEditorStore()
  const [showModal, setShowModal] = useState(false)
  const [versionName, setVersionName] = useState('')
  const [versionDesc, setVersionDesc] = useState('')

  if (!project) return null

  const handleCreate = async () => {
    if (!versionName) return
    await createVersion(versionName, versionDesc)
    setVersionName('')
    setVersionDesc('')
    setShowModal(false)
  }

  return (
    <div className="sidebar-panel">
      <h3>版本管理</h3>
      <button
        className="btn btn-secondary"
        style={{ width: '100%', marginBottom: '12px' }}
        onClick={() => setShowModal(true)}
      >
        + 创建版本
      </button>

      <div className="version-panel" style={{ maxHeight: '300px', overflowY: 'auto' }}>
        {project.versions.length === 0 ? (
          <p style={{ color: '#888', fontSize: '12px' }}>暂无版本</p>
        ) : (
          project.versions.map((version) => (
            <div
              key={version.id}
              className="version-item"
              onClick={() => restoreVersion(version.id)}
            >
              <div className="version-name">{version.name}</div>
              <div className="version-date">
                {new Date(version.createdAt).toLocaleString()}
              </div>
              {version.description && (
                <div style={{ fontSize: '11px', color: '#888', marginTop: '4px' }}>
                  {version.description}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {showModal && (
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
          onClick={() => setShowModal(false)}
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
            <h3 style={{ marginBottom: '20px', color: '#e94560' }}>创建版本</h3>
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px' }}>版本名称</label>
              <input
                type="text"
                className="property-input"
                style={{ width: '100%' }}
                value={versionName}
                onChange={(e) => setVersionName(e.target.value)}
                placeholder="如 v1.0"
              />
            </div>
            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px' }}>描述</label>
              <textarea
                className="property-input"
                style={{ width: '100%', minHeight: '80px' }}
                value={versionDesc}
                onChange={(e) => setVersionDesc(e.target.value)}
                placeholder="版本变更说明..."
              />
            </div>
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button className="btn btn-secondary" onClick={() => setShowModal(false)}>
                取消
              </button>
              <button className="btn btn-primary" onClick={handleCreate}>
                创建
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

import { useEffect, useState } from 'react'
import { useEditorStore } from '@/lib/store'
import { Canvas } from '@/components/Canvas'
import { LayerPanel } from '@/components/LayerPanel'
import { PropertiesPanel } from '@/components/PropertiesPanel'
import { Timeline } from '@/components/Timeline'
import { ProjectModal } from '@/components/ProjectModal'
import { VersionPanel } from '@/components/VersionPanel'
import { PreviewModal } from '@/components/PreviewModal'
import { ExportModal } from '@/components/ExportModal'
import { AIPanel } from '@/components/AIPanel'
import { TemplateMarket } from '@/components/TemplateMarket'
import { PerformancePanel } from '@/components/PerformancePanel'

type RightPanelTab = 'properties' | 'ai' | 'templates' | 'performance'

function App() {
  const { init, project, projects, loadProject, saveProject, deleteProject, isLoading } = useEditorStore()
  const [showProjectModal, setShowProjectModal] = useState(false)
  const [showPreview, setShowPreview] = useState(false)
  const [showExport, setShowExport] = useState(false)
  const [showProjectsList, setShowProjectsList] = useState(false)
  const [rightPanelTab, setRightPanelTab] = useState<RightPanelTab>('properties')

  useEffect(() => {
    init()
  }, [])

  if (isLoading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', background: '#1a1a2e' }}>
        <div style={{ color: 'white', fontSize: '18px' }}>加载中...</div>
      </div>
    )
  }

  const renderRightPanel = () => {
    switch (rightPanelTab) {
      case 'ai':
        return <AIPanel />
      case 'templates':
        return <TemplateMarket />
      case 'performance':
        return <PerformancePanel />
      default:
        return <PropertiesPanel />
    }
  }

  return (
    <div className="app-container">
      <header className="header">
        <h1>🎨 Icon Animation Editor</h1>
        <div className="header-actions">
          <button className="btn btn-secondary" onClick={() => setShowProjectsList(!showProjectsList)}>
            📂 项目 ({projects.length})
          </button>
          <button className="btn btn-secondary" onClick={() => setShowProjectModal(true)}>
            + 新建
          </button>
          {project && (
            <>
              <button className="btn btn-secondary" onClick={() => setShowPreview(true)}>
                👁 预览
              </button>
              <button className="btn btn-secondary" onClick={saveProject}>
                💾 保存
              </button>
              <button className="btn btn-primary" onClick={() => setShowExport(true)}>
                ⬇ 导出 Lottie
              </button>
            </>
          )}
        </div>
      </header>

      <div className="main-content">
        {showProjectsList && (
          <div className="sidebar">
            <div className="sidebar-panel">
              <h3>项目列表</h3>
              {projects.length === 0 ? (
                <p style={{ color: '#888', fontSize: '13px' }}>暂无项目</p>
              ) : (
                projects.map((p) => (
                  <div
                    key={p.id}
                    style={{
                      padding: '12px',
                      background: project?.id === p.id ? '#e94560' : '#0f3460',
                      borderRadius: '6px',
                      marginBottom: '8px',
                      cursor: 'pointer',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                    onClick={() => {
                      loadProject(p.id)
                      setShowProjectsList(false)
                    }}
                  >
                    <div>
                      <div style={{ fontSize: '14px' }}>{p.name}</div>
                      <div style={{ fontSize: '11px', color: '#aaa' }}>
                        {new Date(p.updatedAt).toLocaleString()}
                      </div>
                    </div>
                    <button
                      className="btn btn-secondary"
                      style={{ padding: '4px 8px', fontSize: '12px' }}
                      onClick={(e) => {
                        e.stopPropagation()
                        if (confirm('确定删除此项目?')) {
                          deleteProject(p.id)
                        }
                      }}
                    >
                      🗑
                    </button>
                  </div>
                ))
              )}
            </div>
            <VersionPanel />
          </div>
        )}

        <LayerPanel />

        <div className="canvas-area">
          <div className="canvas-toolbar">
            {project ? (
              <>
                <span style={{ fontSize: '14px' }}>{project.name}</span>
                <span style={{ color: '#888', fontSize: '12px' }}>
                  {project.width}x{project.height} • {project.layers.length} 图层
                </span>
              </>
            ) : (
              <span style={{ color: '#888' }}>请创建或选择一个项目开始编辑</span>
            )}
          </div>
          <Canvas />
        </div>

        <div className="properties-panel" style={{ display: 'flex', flexDirection: 'column' }}>
          <div
            style={{
              display: 'flex',
              borderBottom: '1px solid #0f3460',
              background: '#16213e',
            }}
          >
            {[
              { key: 'properties', label: '⚙️ 属性', showAlways: true },
              { key: 'ai', label: '🤖 AI', requiresProject: true },
              { key: 'templates', label: '📦 模板', showAlways: true },
              { key: 'performance', label: '📊 性能', requiresProject: true },
            ].map((tab) => {
              const disabled = tab.requiresProject && !project
              return (
                <button
                  key={tab.key}
                  className="btn"
                  style={{
                    flex: 1,
                    padding: '10px 4px',
                    fontSize: '11px',
                    border: 'none',
                    background: rightPanelTab === tab.key ? '#e94560' : 'transparent',
                    color: rightPanelTab === tab.key ? 'white' : '#888',
                    cursor: disabled ? 'not-allowed' : 'pointer',
                    opacity: disabled ? 0.5 : 1,
                    borderRadius: 0,
                  }}
                  onClick={() => !disabled && setRightPanelTab(tab.key as RightPanelTab)}
                  disabled={disabled}
                >
                  {tab.label}
                </button>
              )
            })}
          </div>
          {renderRightPanel()}
        </div>
      </div>

      <Timeline />

      {showProjectModal && <ProjectModal onClose={() => setShowProjectModal(false)} />}
      {showPreview && <PreviewModal onClose={() => setShowPreview(false)} />}
      {showExport && <ExportModal onClose={() => setShowExport(false)} />}
    </div>
  )
}

export default App

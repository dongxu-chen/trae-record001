import { useEditorStore } from '@/lib/store'

export function LayerPanel() {
  const { project, selectedLayerId, selectLayer } = useEditorStore()

  if (!project) {
    return <div className="sidebar">
      <div className="sidebar-panel">
        <h3>图层</h3>
        <p style={{ color: '#888', fontSize: '13px' }}>无项目</p>
      </div>
    </div>
  }

  return (
    <div className="sidebar">
      <div className="sidebar-panel">
        <h3>图层</h3>
      </div>
      <div className="layer-list">
        {project.layers.map((layer) => (
          <div
            key={layer.id}
            className={`layer-item ${selectedLayerId === layer.id ? 'active' : ''}`}
            onClick={() => selectLayer(layer.id)}
          >
            <span style={{ flex: 1 }}>{layer.name}</span>
            <span
              onClick={(e) => {
                e.stopPropagation()
              }}
              style={{ opacity: layer.visible ? 1 : 0.3 }}
            >
              👁
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

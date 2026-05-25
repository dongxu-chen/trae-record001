import { useState } from 'react'
import { useEditorStore } from '@/lib/store'
import { EasingType } from '@/types'

const easingOptions: EasingType[] = [
  'linear',
  'easeIn',
  'easeOut',
  'easeInOut',
  'easeInQuad',
  'easeOutQuad',
  'easeInOutQuad',
  'easeInCubic',
  'easeOutCubic',
  'easeInOutCubic',
  'easeInSine',
  'easeOutSine',
  'easeInOutSine',
  'easeOutBounce',
  'elastic',
  'bounce',
]

const animatableProperties = [
  { key: 'position.x', label: '位置 X', unit: 'px' },
  { key: 'position.y', label: '位置 Y', unit: 'px' },
  { key: 'rotation', label: '旋转', unit: '°' },
  { key: 'scale.x', label: '缩放 X', unit: 'x' },
  { key: 'scale.y', label: '缩放 Y', unit: 'x' },
  { key: 'opacity', label: '透明度', unit: '' },
]

export function PropertiesPanel() {
  const { project, selectedLayerId, currentTime, addKeyframe, updateElementTransform } = useEditorStore()
  const [selectedEasing, setSelectedEasing] = useState<EasingType>('easeInOutCubic')

  if (!project || !selectedLayerId) {
    return (
      <div className="properties-panel">
        <div className="properties-section">
          <h3>属性</h3>
          <p style={{ color: '#888', fontSize: '13px' }}>选择一个图层以编辑属性</p>
        </div>
      </div>
    )
  }

  const layer = project.layers.find((l) => l.id === selectedLayerId)
  if (!layer) return null

  const element = project.elements[layer.elementId]
  if (!element) return null

  const handleAddKeyframe = (property: string) => {
    let value: any
    if (property === 'position.x') value = element.transform.position.x
    else if (property === 'position.y') value = element.transform.position.y
    else if (property === 'rotation') value = element.transform.rotation
    else if (property === 'scale.x') value = element.transform.scale.x
    else if (property === 'scale.y') value = element.transform.scale.y
    else if (property === 'opacity') value = element.transform.opacity

    addKeyframe(selectedLayerId, property, currentTime, value)
  }

  const handleTransformChange = (path: string, value: number) => {
    if (path === 'position.x') {
      updateElementTransform(layer.elementId, { position: { ...element.transform.position, x: value } })
    } else if (path === 'position.y') {
      updateElementTransform(layer.elementId, { position: { ...element.transform.position, y: value } })
    } else if (path === 'rotation') {
      updateElementTransform(layer.elementId, { rotation: value })
    } else if (path === 'scale.x') {
      updateElementTransform(layer.elementId, { scale: { ...element.transform.scale, x: value } })
    } else if (path === 'scale.y') {
      updateElementTransform(layer.elementId, { scale: { ...element.transform.scale, y: value } })
    } else if (path === 'opacity') {
      updateElementTransform(layer.elementId, { opacity: value })
    }
  }

  const getCurrentValue = (prop: string): number => {
    if (prop === 'position.x') return element.transform.position.x
    if (prop === 'position.y') return element.transform.position.y
    if (prop === 'rotation') return element.transform.rotation
    if (prop === 'scale.x') return element.transform.scale.x
    if (prop === 'scale.y') return element.transform.scale.y
    if (prop === 'opacity') return element.transform.opacity
    return 0
  }

  return (
    <div className="properties-panel">
      <div className="properties-section">
        <h3>变换属性</h3>
        {animatableProperties.map((prop) => (
          <div key={prop.key} className="property-row">
            <label className="property-label">{prop.label}</label>
            <input
              type="number"
              className="property-input"
              value={getCurrentValue(prop.key)}
              onChange={(e) => handleTransformChange(prop.key, parseFloat(e.target.value) || 0)}
              step={prop.key.includes('scale') || prop.key === 'opacity' ? 0.1 : 1}
            />
            <button
              className="btn btn-secondary"
              style={{ padding: '6px 10px' }}
              onClick={() => handleAddKeyframe(prop.key)}
            >
              ⏺
            </button>
          </div>
        ))}
      </div>

      <div className="properties-section">
        <h3>缓动曲线</h3>
        <div className="property-row">
          <label className="property-label">类型</label>
          <select
            className="property-input"
            value={selectedEasing}
            onChange={(e) => setSelectedEasing(e.target.value as EasingType)}
          >
            {easingOptions.map((ease) => (
              <option key={ease} value={ease}>
                {ease}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="properties-section">
        <h3>动画轨道</h3>
        {layer.tracks.length === 0 ? (
          <p style={{ color: '#888', fontSize: '13px' }}>暂无动画轨道</p>
        ) : (
          layer.tracks.map((track) => (
            <div key={track.id} style={{ marginBottom: '12px' }}>
              <div style={{ fontSize: '13px', marginBottom: '6px', color: '#aaa' }}>
                {track.property} ({track.keyframes.length} 个关键帧)
              </div>
              <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                {track.keyframes.map((kf) => (
                  <span
                    key={kf.id}
                    style={{
                      padding: '2px 8px',
                      background: '#0f3460',
                      borderRadius: '4px',
                      fontSize: '11px',
                    }}
                  >
                    {(kf.time / 1000).toFixed(1)}s
                  </span>
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

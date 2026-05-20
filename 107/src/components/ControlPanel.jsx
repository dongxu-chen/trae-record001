import { useState } from 'react'

const modelOptions = [
  { id: 'helmet', name: '头盔模型', icon: '⛑️' },
  { id: 'duck', name: '小黄鸭', icon: '🦆' },
  { id: 'avocado', name: '牛油果', icon: '🥑' },
  { id: 'torus', name: '环形结', icon: '🔗' }
]

const animationPresets = [
  { id: 'rotate360', name: '360°旋转', icon: '🔄' },
  { id: 'zoomIn', name: '放大细节', icon: '🔍' },
  { id: 'orbit', name: '轨道环绕', icon: '🪐' },
  { id: 'flyAround', name: '飞越浏览', icon: '✈️' },
  { id: 'topDown', name: '俯视视角', icon: '📐' },
  { id: 'closeUp', name: '近距离', icon: '👁️' }
]

const materialPresets = [
  { name: '抛光金属', metalness: 1, roughness: 0.1, color: '#c0c0c0' },
  { name: '拉丝金属', metalness: 0.9, roughness: 0.4, color: '#a0a0a0' },
  { name: '哑光塑料', metalness: 0, roughness: 0.9, color: '#ff6b6b' },
  { name: '光泽塑料', metalness: 0.1, roughness: 0.3, color: '#4ecdc4' },
  { name: '玻璃质感', metalness: 0.1, roughness: 0.05, color: '#a8e6cf' },
  { name: '陶瓷质感', metalness: 0.2, roughness: 0.7, color: '#f8f5f0' }
]

const ControlPanel = ({
  materialProps,
  updateMaterial,
  backgroundColor,
  setBackgroundColor,
  backgroundPresets,
  resetCamera,
  animation,
  setAnimation,
  isPlaying,
  setIsPlaying,
  hotspots,
  activeHotspot,
  setActiveHotspot,
  modelType,
  setModelType
}) => {
  const [activePreset, setActivePreset] = useState(null)

  const applyMaterialPreset = (preset, index) => {
    setActivePreset(index)
    updateMaterial('metalness', preset.metalness)
    updateMaterial('roughness', preset.roughness)
    updateMaterial('color', preset.color)
  }

  const resetMaterial = () => {
    setActivePreset(null)
    updateMaterial('color', '#ff6b6b')
    updateMaterial('metalness', 0.5)
    updateMaterial('roughness', 0.5)
    updateMaterial('envMapIntensity', 1)
  }

  const handleModelChange = (newModel) => {
    setModelType(newModel)
    setAnimation(null)
    setIsPlaying(false)
    setActiveHotspot(null)
  }

  return (
    <div className="control-panel">
      <h1>3D产品展示看板</h1>

      <div className="control-section">
        <h2>🎨 选择模型</h2>
        <div className="grid grid-2" style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' }}>
          {modelOptions.map((model) => (
            <button
              key={model.id}
              onClick={() => handleModelChange(model.id)}
              style={{
                padding: '12px 8px',
                borderRadius: '8px',
                border: 'none',
                background:
                  modelType === model.id
                    ? 'linear-gradient(135deg, #00d2ff, #3a7bd5)'
                    : 'rgba(255, 255, 255, 0.1)',
                color: 'white',
                fontSize: '12px',
                cursor: 'pointer',
                transition: 'all 0.3s ease',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '4px'
              }}
              onMouseOver={(e) => {
                if (modelType !== model.id) {
                  e.target.style.background = 'rgba(0, 210, 255, 0.2)'
                }
              }}
              onMouseOut={(e) => {
                if (modelType !== model.id) {
                  e.target.style.background = 'rgba(255, 255, 255, 0.1)'
                }
              }}
            >
              <span style={{ fontSize: '20px' }}>{model.icon}</span>
              <span>{model.name}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="control-section">
        <h2>🎬 动画序列</h2>
        <div className="grid grid-2" style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' }}>
          {animationPresets.map((preset) => (
            <button
              key={preset.id}
              onClick={() => setAnimation(preset.id)}
              style={{
                padding: '10px',
                borderRadius: '8px',
                border: 'none',
                background:
                  animation === preset.id
                    ? 'linear-gradient(135deg, #00d2ff, #3a7bd5)'
                    : 'rgba(255, 255, 255, 0.1)',
                color: 'white',
                fontSize: '12px',
                cursor: 'pointer',
                transition: 'all 0.3s ease',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '4px'
              }}
              onMouseOver={(e) => {
                if (animation !== preset.id) {
                  e.target.style.background = 'rgba(0, 210, 255, 0.2)'
                }
              }}
              onMouseOut={(e) => {
                if (animation !== preset.id) {
                  e.target.style.background = 'rgba(255, 255, 255, 0.1)'
                }
              }}
            >
              <span style={{ fontSize: '20px' }}>{preset.icon}</span>
              <span>{preset.name}</span>
            </button>
          ))}
        </div>
        <div className="button-group" style={{ marginTop: '12px', display: 'flex', gap: '8px' }}>
          <button
            className="btn btn-primary"
            onClick={() => setIsPlaying(!isPlaying)}
            disabled={!animation}
          >
            {isPlaying ? '⏸️ 暂停' : '▶️ 播放'}
          </button>
          <button
            className="btn btn-secondary"
            onClick={() => {
              setIsPlaying(false)
              resetCamera()
            }}
          >
            🔄 重置
          </button>
        </div>
      </div>

      <div className="control-section">
        <h2>📍 热点标注</h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '200px', overflowY: 'auto' }}>
          {hotspots.map((hotspot) => (
            <div
              key={hotspot.id}
              onClick={() => setActiveHotspot(activeHotspot?.id === hotspot.id ? null : hotspot)}
              style={{
                padding: '10px 14px',
                borderRadius: '8px',
                background:
                  activeHotspot?.id === hotspot.id
                    ? 'linear-gradient(135deg, #00d2ff, #3a7bd5)'
                    : 'rgba(255, 255, 255, 0.1)',
                cursor: 'pointer',
                transition: 'all 0.3s ease',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                border: activeHotspot?.id === hotspot.id ? 'none' : '1px solid rgba(255, 255, 255, 0.2)'
              }}
              onMouseOver={(e) => {
                if (activeHotspot?.id !== hotspot.id) {
                  e.target.style.background = 'rgba(0, 210, 255, 0.2)'
                }
              }}
              onMouseOut={(e) => {
                if (activeHotspot?.id !== hotspot.id) {
                  e.target.style.background = 'rgba(255, 255, 255, 0.1)'
                }
              }}
            >
              <span style={{ fontSize: '18px' }}>{hotspot.icon}</span>
              <div style={{ flex: 1 }}>
                <div style={{ color: 'white', fontSize: '13px', fontWeight: 600 }}>{hotspot.label}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="control-section">
        <h2>材质预设</h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {materialPresets.map((preset, index) => (
            <div
              key={index}
              className={`material-preset ${activePreset === index ? 'active' : ''}`}
              onClick={() => applyMaterialPreset(preset, index)}
            >
              {preset.name}
            </div>
          ))}
        </div>
      </div>

      <div className="control-section">
        <h2>材质属性</h2>

        <div className="control-group">
          <label>颜色</label>
          <input
            type="color"
            value={materialProps.color}
            onChange={(e) => updateMaterial('color', e.target.value)}
          />
        </div>

        <div className="control-group">
          <label>金属度: {materialProps.metalness.toFixed(2)}</label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={materialProps.metalness}
            onChange={(e) => updateMaterial('metalness', parseFloat(e.target.value))}
          />
          <div className="value-display">{Math.round(materialProps.metalness * 100)}%</div>
        </div>

        <div className="control-group">
          <label>粗糙度: {materialProps.roughness.toFixed(2)}</label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={materialProps.roughness}
            onChange={(e) => updateMaterial('roughness', parseFloat(e.target.value))}
          />
          <div className="value-display">{Math.round(materialProps.roughness * 100)}%</div>
        </div>

        <div className="control-group">
          <label>环境光强度: {materialProps.envMapIntensity.toFixed(2)}</label>
          <input
            type="range"
            min="0"
            max="3"
            step="0.01"
            value={materialProps.envMapIntensity}
            onChange={(e) => updateMaterial('envMapIntensity', parseFloat(e.target.value))}
          />
          <div className="value-display">{Math.round(materialProps.envMapIntensity * 100)}%</div>
        </div>

        <div className="button-group">
          <button className="btn btn-secondary" onClick={resetMaterial}>
            重置材质
          </button>
        </div>
      </div>

      <div className="control-section">
        <h2>背景设置</h2>
        <div className="control-group">
          <label>自定义颜色</label>
          <input
            type="color"
            value={backgroundColor}
            onChange={(e) => setBackgroundColor(e.target.value)}
          />
        </div>
        <div className="color-presets">
          {backgroundPresets.map((color, index) => (
            <div
              key={index}
              className="color-preset"
              style={{ backgroundColor: color }}
              onClick={() => setBackgroundColor(color)}
            />
          ))}
        </div>
      </div>

      <div className="control-section">
        <h2>相机控制</h2>
        <div className="button-group">
          <button className="btn btn-primary" onClick={resetCamera}>
            重置视角
          </button>
        </div>
        <div style={{ marginTop: '16px', fontSize: '0.85rem', color: '#888' }}>
          <p style={{ marginBottom: '8px' }}>
            <strong style={{ color: '#aaa' }}>桌面端：</strong>
          </p>
          <p>🖱️ 左键拖动：旋转模型</p>
          <p>🖱️ 右键拖动：平移视角</p>
          <p>🖱️ 滚轮：缩放视图</p>
          <p style={{ margin: '12px 0 8px 0' }}>
            <strong style={{ color: '#aaa' }}>移动端：</strong>
          </p>
          <p>👆 单指滑动：旋转模型</p>
          <p>👆👆 双指滑动：平移视角</p>
          <p>🔍 双指捏合：缩放视图</p>
        </div>
      </div>
    </div>
  )
}

export default ControlPanel

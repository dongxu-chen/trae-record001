import useStore, { metalnessMapPresets } from '../store/store'
import './EffectControls.css'

export default function EffectControls() {
  const snowEnabled = useStore((state) => state.snowEnabled)
  const metalnessMapType = useStore((state) => state.metalnessMapType)
  const toggleSnow = useStore((state) => state.toggleSnow)
  const setMetalnessMapType = useStore((state) => state.setMetalnessMapType)

  return (
    <div className="effect-controls">
      <h3 className="control-title">效果控制</h3>
      
      <div className="effect-section">
        <div className="toggle-row">
          <span className="toggle-label">下雪效果</span>
          <button
            className={`toggle-btn ${snowEnabled ? 'active' : ''}`}
            onClick={toggleSnow}
          >
            <span className="toggle-icon">{snowEnabled ? '❄️' : '☀️'}</span>
            <span className="toggle-text">{snowEnabled ? '开启' : '关闭'}</span>
          </button>
        </div>
      </div>
      
      <div className="effect-section">
        <h4 className="sub-title">金属度贴图</h4>
        <div className="texture-grid">
          {metalnessMapPresets.map((preset) => (
            <button
              key={preset.id}
              className={`texture-btn ${metalnessMapType === preset.id ? 'active' : ''}`}
              onClick={() => setMetalnessMapType(preset.id)}
            >
              {preset.id === 'none' ? '🚫' : 
               preset.id === 'brushed' ? '⚡' :
               preset.id === 'scratched' ? '💥' : '🔨'}
              <span className="texture-name">{preset.name}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

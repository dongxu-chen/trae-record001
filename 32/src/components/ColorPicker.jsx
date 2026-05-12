import useStore, { colorPresets } from '../store/store'
import './ColorPicker.css'

export default function ColorPicker() {
  const currentColor = useStore((state) => state.color)
  const setColor = useStore((state) => state.setColor)

  return (
    <div className="color-picker">
      <h3 className="control-title">选择颜色</h3>
      <div className="color-grid">
        {colorPresets.map((preset) => (
          <button
            key={preset.id}
            className={`color-swatch ${currentColor === preset.color ? 'active' : ''}`}
            style={{ backgroundColor: preset.color }}
            onClick={() => setColor(preset.color)}
            title={preset.name}
          />
        ))}
      </div>
      <div className="custom-color">
        <label htmlFor="custom-color">自定义颜色：</label>
        <input
          type="color"
          id="custom-color"
          value={currentColor}
          onChange={(e) => setColor(e.target.value)}
          className="color-input"
        />
      </div>
      <div className="current-color">
        <span>当前颜色：</span>
        <div 
          className="color-preview" 
          style={{ backgroundColor: currentColor }}
        />
        <span className="color-code">{currentColor.toUpperCase()}</span>
      </div>
    </div>
  )
}

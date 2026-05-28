import React, { useState, useMemo } from 'react'
import { generateCustomPalette } from '../utils/colorRecommender.js'

const HARMONY_TYPES = [
  { value: 'analogous', label: '邻近色', description: '色相相近的颜色组合' },
  { value: 'complementary', label: '互补色', description: '色环上相对的颜色组合' },
  { value: 'triadic', label: '三色组', description: '色环上等距的三种颜色' },
  { value: 'monochromatic', label: '单色渐变', description: '同一色相的明暗变化' }
]

function CustomPalette() {
  const [baseColor, setBaseColor] = useState('#4f46e5')
  const [harmonyType, setHarmonyType] = useState('analogous')
  const [colorCount, setColorCount] = useState(6)

  const customPalette = useMemo(() => {
    try {
      return generateCustomPalette(baseColor, colorCount, harmonyType)
    } catch (e) {
      return []
    }
  }, [baseColor, harmonyType, colorCount])

  const copyPalette = () => {
    const text = customPalette.join(', ')
    navigator.clipboard.writeText(text)
  }

  return (
    <div className="custom-palette">
      <h3>🎨 自定义色板</h3>

      <div className="custom-inputs">
        <div className="input-row">
          <label>基准色</label>
          <input
            type="color"
            value={baseColor}
            onChange={(e) => setBaseColor(e.target.value)}
            className="color-picker"
          />
          <input
            type="text"
            value={baseColor}
            onChange={(e) => setBaseColor(e.target.value)}
            className="color-input"
          />
        </div>

        <div className="input-row">
          <label>和谐类型</label>
          <select
            value={harmonyType}
            onChange={(e) => setHarmonyType(e.target.value)}
            className="harmony-select"
          >
            {HARMONY_TYPES.map(t => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>

        <div className="input-row">
          <label>颜色数量：{colorCount}</label>
          <input
            type="range"
            min="3"
            max="12"
            value={colorCount}
            onChange={(e) => setColorCount(parseInt(e.target.value))}
            className="count-slider"
          />
        </div>
      </div>

      <div className="harmony-description">
        {HARMONY_TYPES.find(t => t.value === harmonyType)?.description}
      </div>

      <div className="custom-palette-preview">
        {customPalette.map((color, index) => (
          <div
            key={index}
            className="custom-swatch"
            style={{ backgroundColor: color }}
            title={color}
          >
            <span className="swatch-hex">{color}</span>
          </div>
        ))}
      </div>

      <button className="copy-btn" onClick={copyPalette}>
        📋 复制色板
      </button>
    </div>
  )
}

export default CustomPalette

import { useState } from 'react'
import './ControlPanel.css'

export default function ControlPanel({ config, setConfig, particleCount }) {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [showPhysics, setShowPhysics] = useState(false)

  const handleChange = (key, value) => {
    setConfig(prev => ({ ...prev, [key]: value }))
  }

  const animationTypes = [
    { value: 'gather', label: '聚集' },
    { value: 'disperse', label: '消散' },
    { value: 'trail', label: '拖尾' },
    { value: 'morph', label: '变形' }
  ]

  const backgroundEffects = [
    { value: 'none', label: '无' },
    { value: 'gradient', label: '渐变' },
    { value: 'stars', label: '星空' },
    { value: 'grid', label: '网格' }
  ]

  const presetColors = [
    '#00d4ff',
    '#ff6b6b',
    '#4ecdc4',
    '#ffe66d',
    '#95e1d3',
    '#f38181',
    '#aa96da',
    '#fcbad3'
  ]

  return (
    <div className={`control-panel ${isCollapsed ? 'collapsed' : ''}`}>
      <button
        className="collapse-btn"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        {isCollapsed ? '→' : '←'}
      </button>

      {!isCollapsed && (
        <div className="panel-content">
          <h2>粒子文字特效</h2>

          <div className="control-group">
            <label>输入文字</label>
            <input
              type="text"
              value={config.text}
              onChange={(e) => handleChange('text', e.target.value)}
              placeholder="输入文字..."
              maxLength={20}
            />
          </div>

          <div className="control-group">
            <label>动画类型</label>
            <div className="radio-group">
              {animationTypes.map(type => (
                <label key={type.value} className="radio-label">
                  <input
                    type="radio"
                    name="animationType"
                    value={type.value}
                    checked={config.animationType === type.value}
                    onChange={(e) => handleChange('animationType', e.target.value)}
                  />
                  {type.label}
                </label>
              ))}
            </div>
          </div>

          <div className="control-group">
            <label>动画速度: {config.speed.toFixed(1)}</label>
            <input
              type="range"
              min="0.1"
              max="3"
              step="0.1"
              value={config.speed}
              onChange={(e) => handleChange('speed', parseFloat(e.target.value))}
            />
          </div>

          <div className="control-group">
            <label>粒子大小: {config.particleSize}</label>
            <input
              type="range"
              min="1"
              max="10"
              step="1"
              value={config.particleSize}
              onChange={(e) => handleChange('particleSize', parseInt(e.target.value))}
            />
          </div>

          <div className="control-group">
            <label>粒子密度: {config.particleSpacing}</label>
            <input
              type="range"
              min="2"
              max="10"
              step="1"
              value={config.particleSpacing}
              onChange={(e) => handleChange('particleSpacing', parseInt(e.target.value))}
            />
          </div>

          <div className="control-group">
            <label>粒子颜色</label>
            <div className="color-presets">
              {presetColors.map(color => (
                <button
                  key={color}
                  className={`color-preset ${config.particleColor === color ? 'active' : ''}`}
                  style={{ backgroundColor: color }}
                  onClick={() => handleChange('particleColor', color)}
                />
              ))}
            </div>
            <input
              type="color"
              value={config.particleColor}
              onChange={(e) => handleChange('particleColor', e.target.value)}
            />
          </div>

          <div className="control-group">
            <label>
              <input
                type="checkbox"
                checked={config.showTrail}
                onChange={(e) => handleChange('showTrail', e.target.checked)}
              />
              显示拖尾
            </label>
          </div>

          {config.showTrail && (
            <div className="control-group">
              <label>拖尾长度: {config.trailLength}</label>
              <input
                type="range"
                min="1"
                max="30"
                step="1"
                value={config.trailLength}
                onChange={(e) => handleChange('trailLength', parseInt(e.target.value))}
              />
            </div>
          )}

          <div className="control-group">
            <label>背景颜色</label>
            <input
              type="color"
              value={config.backgroundColor}
              onChange={(e) => handleChange('backgroundColor', e.target.value)}
            />
          </div>

          <div className="control-group">
            <label>背景特效</label>
            <select
              value={config.backgroundEffect}
              onChange={(e) => handleChange('backgroundEffect', e.target.value)}
            >
              {backgroundEffects.map(effect => (
                <option key={effect.value} value={effect.value}>
                  {effect.label}
                </option>
              ))}
            </select>
          </div>

          <div className="control-group section-toggle" onClick={() => setShowPhysics(!showPhysics)}>
            <label>
              <span>⚙️ 物理引擎</span>
              <span className="toggle-arrow">{showPhysics ? '▼' : '▶'}</span>
            </label>
          </div>

          {showPhysics && (
            <div className="physics-section">
              <div className="control-group">
                <label>
                  <input
                    type="checkbox"
                    checked={config.physicsEnabled}
                    onChange={(e) => handleChange('physicsEnabled', e.target.checked)}
                  />
                  启用物理
                </label>
              </div>

              {config.physicsEnabled && (
                <>
                  <div className="control-group">
                    <label>重力: {config.gravity.toFixed(2)}</label>
                    <input
                      type="range"
                      min="0"
                      max="0.5"
                      step="0.01"
                      value={config.gravity}
                      onChange={(e) => handleChange('gravity', parseFloat(e.target.value))}
                    />
                  </div>

                  <div className="control-group">
                    <label>
                      <input
                        type="checkbox"
                        checked={config.bounce}
                        onChange={(e) => handleChange('bounce', e.target.checked)}
                      />
                      边界反弹
                    </label>
                  </div>

                  <div className="control-group">
                    <label>
                      <input
                        type="checkbox"
                        checked={config.collision}
                        onChange={(e) => handleChange('collision', e.target.checked)}
                      />
                      粒子碰撞
                    </label>
                  </div>

                  <div className="control-group">
                    <label>鼠标影响半径: {config.mouseRadius}</label>
                    <input
                      type="range"
                      min="50"
                      max="250"
                      step="10"
                      value={config.mouseRadius}
                      onChange={(e) => handleChange('mouseRadius', parseInt(e.target.value))}
                    />
                  </div>

                  <div className="control-group">
                    <label>鼠标推力: {config.mouseForce.toFixed(1)}</label>
                    <input
                      type="range"
                      min="0.1"
                      max="3"
                      step="0.1"
                      value={config.mouseForce}
                      onChange={(e) => handleChange('mouseForce', parseFloat(e.target.value))}
                    />
                  </div>
                </>
              )}
            </div>
          )}

          <div className="particle-info">
            <span>粒子数量: {particleCount}</span>
          </div>
        </div>
      )}
    </div>
  )
}

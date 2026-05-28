import React, { useMemo } from 'react'
import { getColorInfo } from '../utils/colorRecommender.js'
import { simulateColorBlindness, getColorBlindnessInfo } from '../utils/colorBlindness.js'
import { getColorName, getColorEmotion } from '../utils/brandColors.js'

function ColorInfoPanel({ color, schemeName, onClose }) {
  const colorInfo = useMemo(() => {
    try {
      return getColorInfo(color)
    } catch (e) {
      return null
    }
  }, [color])

  const colorNameInfo = useMemo(() => {
    try {
      return getColorName(color)
    } catch (e) {
      return { name: '未知', family: 'unknown', tags: [] }
    }
  }, [color])

  const emotionInfo = useMemo(() => {
    try {
      return getColorEmotion(color)
    } catch (e) {
      return { emotions: [], scenes: [], intensity: 0 }
    }
  }, [color])

  const colorBlindnessInfo = getColorBlindnessInfo()

  if (!colorInfo) return null

  const copyValue = (text) => {
    navigator.clipboard.writeText(text)
  }

  return (
    <div className="color-info-panel">
      <div className="info-panel-header">
        <h3>颜色详情</h3>
        <button className="close-btn" onClick={onClose}>✕</button>
      </div>

      <div className="color-preview-large" style={{ backgroundColor: color }}>
        <div className="preview-text-group">
          <span className="color-name-label">{colorNameInfo.name}</span>
          <span className="color-preview-text">{color}</span>
        </div>
      </div>

      {schemeName && (
        <p className="scheme-reference">来自色板：{schemeName}</p>
      )}

      <div className="color-tags-section">
        {colorNameInfo.tags.length > 0 && (
          <div className="tag-group">
            <span className="tag-group-label">关键词</span>
            <div className="tag-list">
              {colorNameInfo.tags.map((tag, i) => (
                <span key={i} className="color-tag name-tag">{tag}</span>
              ))}
            </div>
          </div>
        )}
        {emotionInfo.emotions && emotionInfo.emotions.length > 0 && (
          <div className="tag-group">
            <span className="tag-group-label">情感</span>
            <div className="tag-list">
              {emotionInfo.emotions.slice(0, 4).map((emotion, i) => (
                <span key={i} className="color-tag emotion-tag">{emotion}</span>
              ))}
            </div>
          </div>
        )}
        {emotionInfo.scenes && emotionInfo.scenes.length > 0 && (
          <div className="tag-group">
            <span className="tag-group-label">适用场景</span>
            <div className="tag-list">
              {emotionInfo.scenes.slice(0, 3).map((scene, i) => (
                <span key={i} className="color-tag scene-tag">{scene}</span>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="color-values">
        <div className="value-row" onClick={() => copyValue(colorInfo.hex)} title="点击复制">
          <span className="value-label">HEX</span>
          <span className="value-content">{colorInfo.hex}</span>
          <span className="copy-hint">📋</span>
        </div>
        <div className="value-row" onClick={() => copyValue(`rgb(${colorInfo.rgb.join(', ')})`)} title="点击复制">
          <span className="value-label">RGB</span>
          <span className="value-content">{colorInfo.rgb.join(', ')}</span>
          <span className="copy-hint">📋</span>
        </div>
        <div className="value-row" onClick={() => copyValue(`hsl(${colorInfo.hsl[0].toFixed(0)}, ${(colorInfo.hsl[1] * 100).toFixed(0)}%, ${(colorInfo.hsl[2] * 100).toFixed(0)}%)`)} title="点击复制">
          <span className="value-label">HSL</span>
          <span className="value-content">
            {colorInfo.hsl[0].toFixed(0)}°, {(colorInfo.hsl[1] * 100).toFixed(0)}%, {(colorInfo.hsl[2] * 100).toFixed(0)}%
          </span>
          <span className="copy-hint">📋</span>
        </div>
      </div>

      <div className="color-metrics">
        <div className="metric">
          <span className="metric-label">亮度</span>
          <div className="metric-bar">
            <div
              className="metric-fill"
              style={{ width: `${colorInfo.luminance * 100}%` }}
            />
          </div>
          <span className="metric-value">{(colorInfo.luminance * 100).toFixed(1)}%</span>
        </div>
        <div className="metric">
          <span className="metric-label">饱和度</span>
          <div className="metric-bar">
            <div
              className="metric-fill saturation"
              style={{ width: `${colorInfo.saturation * 100}%` }}
            />
          </div>
          <span className="metric-value">{(colorInfo.saturation * 100).toFixed(1)}%</span>
        </div>
        {emotionInfo.intensity !== undefined && (
          <div className="metric">
            <span className="metric-label">情感强度</span>
            <div className="metric-bar">
              <div
                className="metric-fill emotion"
                style={{ width: `${emotionInfo.intensity * 10}%` }}
              />
            </div>
            <span className="metric-value">{emotionInfo.intensity}/10</span>
          </div>
        )}
      </div>

      <div className="colorblindness-simulation">
        <h4>色盲模拟</h4>
        <div className="simulation-grid">
          {colorBlindnessInfo.map(info => (
            <div key={info.type} className="simulation-item">
              <div
                className="simulation-color"
                style={{ backgroundColor: simulateColorBlindness(color, info.type) }}
              />
              <span className="simulation-label">{info.name}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default ColorInfoPanel

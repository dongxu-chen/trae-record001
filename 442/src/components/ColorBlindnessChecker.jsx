import React, { useMemo } from 'react'
import {
  checkPaletteColorBlindFriendly,
  simulateColorBlindness,
  getColorBlindnessInfo,
  getComprehensiveAssessment,
  COLOR_BLINDNESS_TYPES
} from '../utils/colorBlindness.js'

function ColorBlindnessChecker({ colors, schemeName }) {
  const accessibility = useMemo(() => {
    if (colors.length === 0) return null
    return checkPaletteColorBlindFriendly(colors)
  }, [colors])

  const comprehensive = useMemo(() => {
    if (colors.length === 0) return null
    return getComprehensiveAssessment(colors)
  }, [colors])

  const colorBlindnessInfo = getColorBlindnessInfo()

  if (colors.length === 0) {
    return (
      <div className="colorblindness-checker">
        <h3>👁️ 色盲友好检测</h3>
        <p className="empty-hint">请先选择一个颜色方案进行检测</p>
      </div>
    )
  }

  return (
    <div className="colorblindness-checker">
      <h3>👁️ 色盲友好检测</h3>
      <p className="scheme-name-hint">当前检测：{schemeName}</p>

      <div className={`accessibility-status ${accessibility.isFriendly ? 'friendly' : 'unfriendly'}`}>
        <div className="status-main">
          <span className="status-icon">{accessibility.isFriendly ? '✓' : '⚠'}</span>
          <span>{accessibility.isFriendly ? '此方案对色盲用户友好' : '此方案可能不适合色盲用户'}</span>
        </div>
        <div className="status-score">
          <span className="score-label">综合评分</span>
          <span className="score-value">{accessibility.overallScore}%</span>
        </div>
      </div>

      {comprehensive && comprehensive.recommendations.length > 0 && (
        <div className="assessment-recommendations">
          {comprehensive.recommendations.map((rec, i) => (
            <div key={i} className={`assessment-rec assessment-rec-${rec.type}`}>
              {rec.text}
            </div>
          ))}
        </div>
      )}

      {comprehensive && (
        <div className="assessment-metrics">
          <div className="metric-item">
            <span className="metric-name">对比度</span>
            <div className="metric-bar-container">
              <div
                className="metric-bar-fill contrast"
                style={{ width: `${comprehensive.contrastScore}%` }}
              />
            </div>
            <span className="metric-score">{comprehensive.avgContrast}</span>
          </div>
          <div className="metric-item">
            <span className="metric-name">亮度范围</span>
            <div className="metric-bar-container">
              <div
                className="metric-bar-fill luminance"
                style={{ width: `${comprehensive.luminanceScore}%` }}
              />
            </div>
            <span className="metric-score">{comprehensive.luminanceRange}</span>
          </div>
        </div>
      )}

      <div className="colorblindness-types">
        {colorBlindnessInfo.map(info => {
          const result = accessibility[info.type]
          if (!result) return null
          return (
            <div key={info.type} className="colorblindness-type">
              <div className="type-header">
                <div className="type-title">
                  <span className="type-name">{info.name}</span>
                  <span className={`type-severity severity-${info.severity}`}>
                    {info.severity === 'total' ? '严重' : info.severity === 'mixed' ? '混合' : info.severity === 'anopia' ? '完全' : '部分'}
                  </span>
                </div>
                <span className={`type-status ${result.distinguishable ? 'ok' : 'warn'}`}>
                  {result.distinguishable ? '✓ 可区分' : '⚠ 难区分'}
                </span>
              </div>
              <p className="type-description">{info.description}</p>
              <p className="type-prevalence">{info.prevalence}</p>
              <div className="type-metrics">
                <span className="delta-metric" title="最小色差(ΔE)">
                  ΔE<sub>min</sub>: {result.deltaEMin}
                </span>
                <span className="delta-metric" title="平均色差(ΔE)">
                  ΔE<sub>avg</sub>: {result.deltaEAvg}
                </span>
              </div>
              <div className="simulated-palette">
                {result.colors.map((color, index) => (
                  <div
                    key={index}
                    className="simulated-swatch"
                    style={{ backgroundColor: color }}
                    title={`原始: ${colors[index]} → 模拟: ${color}`}
                  >
                    <span className="swatch-label">{colors[index]}</span>
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default ColorBlindnessChecker

import React, { useMemo } from 'react'
import { recommendColorSchemes } from '../utils/colorRecommender.js'
import { getColorName } from '../utils/brandColors.js'

function ColorRecommendations({
  chartType,
  dataFeatures,
  categoryCount,
  sampleData,
  onSelectScheme,
  onAddToComparison,
  comparisonSchemes,
  onColorClick
}) {
  const recommendations = useMemo(() => {
    return recommendColorSchemes(chartType, dataFeatures, categoryCount, sampleData)
  }, [chartType, dataFeatures, categoryCount, sampleData])

  const isInComparison = (scheme) => {
    return comparisonSchemes.some(s => s.name === scheme.name && s.type === scheme.type)
  }

  const groupedByType = useMemo(() => {
    const groups = {
      qualitative: [],
      sequential: [],
      diverging: []
    }
    recommendations.forEach(r => {
      groups[r.type]?.push(r)
    })
    return groups
  }, [recommendations])

  const typeLabels = {
    qualitative: { label: '分类色', description: '适用于离散的类别数据', color: '#4f46e5' },
    sequential: { label: '顺序色', description: '适用于连续的数值数据', color: '#10b981' },
    diverging: { label: '发散色', description: '适用于正负值或双向数据', color: '#f59e0b' }
  }

  return (
    <div className="color-recommendations">
      <div className="recommendations-header">
        <h2>推荐方案</h2>
        <span className="recommendation-count">共 {recommendations.length} 个方案</span>
      </div>

      {Object.entries(groupedByType).map(([type, schemes]) => (
        schemes.length > 0 && (
          <div key={type} className="scheme-group">
            <div className="group-header" style={{ borderLeftColor: typeLabels[type].color }}>
              <h3>
                <span className="group-indicator" style={{ backgroundColor: typeLabels[type].color }}></span>
                {typeLabels[type].label}
              </h3>
              <span className="group-description">{typeLabels[type].description}</span>
            </div>

            <div className="scheme-grid">
              {schemes.slice(0, 4).map(scheme => (
                <div
                  key={`${scheme.name}-${scheme.type}`}
                  className="scheme-card"
                >
                  <div className="scheme-header">
                    <div className="scheme-info">
                      <h4 className="scheme-name">{scheme.name}</h4>
                      <div className="scheme-meta">
                        <span className="scheme-score">推荐度 {scheme.score}%</span>
                        {scheme.reasonTags?.length > 0 && (
                          <div className="scheme-tags">
                            {scheme.reasonTags.map((tag, i) => (
                              <span key={i} className="scheme-tag">{tag}</span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="scheme-actions">
                      <button
                        className={`compare-btn ${isInComparison(scheme) ? 'active' : ''}`}
                        onClick={() => onAddToComparison(scheme)}
                        title={isInComparison(scheme) ? '移出对比' : '加入对比'}
                      >
                        {isInComparison(scheme) ? '✓' : '+'}
                      </button>
                      <button
                        className="preview-btn"
                        onClick={() => onSelectScheme(scheme)}
                      >
                        预览
                      </button>
                    </div>
                  </div>

                  <div className="color-palette">
                    {scheme.colors.map((color, index) => (
                      <div
                        key={index}
                        className="color-swatch"
                        style={{ backgroundColor: color }}
                        title={`${getColorName(color).name} ${color}`}
                        onClick={() => onColorClick(color, scheme)}
                      >
                        <span className="color-hex">{color}</span>
                      </div>
                    ))}
                  </div>
                  <div className="palette-names">
                    {scheme.colors.slice(0, 6).map((color, index) => (
                      <span key={index} className="palette-name">{getColorName(color).name}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )
      ))}
    </div>
  )
}

export default ColorRecommendations

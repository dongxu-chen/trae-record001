import React from 'react'
import { CHART_TYPES, DATA_FEATURES, DATA_DISTRIBUTION, analyzeDataDistribution } from '../utils/colorRecommender.js'

const CHART_TYPE_OPTIONS = [
  { value: CHART_TYPES.BAR, label: '柱状图', icon: '📊' },
  { value: CHART_TYPES.LINE, label: '折线图', icon: '📈' },
  { value: CHART_TYPES.PIE, label: '饼图', icon: '🥧' },
  { value: CHART_TYPES.SCATTER, label: '散点图', icon: '⚬' },
  { value: CHART_TYPES.AREA, label: '面积图', icon: '🔲' },
  { value: CHART_TYPES.HEATMAP, label: '热力图', icon: '🔥' },
  { value: CHART_TYPES.RADAR, label: '雷达图', icon: '🕸️' },
  { value: CHART_TYPES.SANKEY, label: '桑基图', icon: '🔀' },
  { value: CHART_TYPES.TREEMAP, label: '矩形树图', icon: '🗂️' }
]

const DATA_FEATURE_OPTIONS = [
  { value: DATA_FEATURES.CATEGORICAL, label: '分类数据', description: '离散的类别，如城市、产品类型', icon: '🏷️' },
  { value: DATA_FEATURES.SEQUENTIAL, label: '顺序数据', description: '连续的数值，如温度、销售额', icon: '📏' },
  { value: DATA_FEATURES.DIVERGING, label: '发散数据', description: '有正负值或双向变化，如增长率', icon: '↔️' },
  { value: DATA_FEATURES.ORDINAL, label: '有序数据', description: '有顺序的等级，如评分、满意度', icon: '🔢' }
]

const DISTRIBUTION_OPTIONS = [
  { value: DATA_DISTRIBUTION.NORMAL, label: '正态分布', description: '对称分布，无明显偏态', icon: '⟂' },
  { value: DATA_DISTRIBUTION.SKEWED_POSITIVE, label: '右偏分布', description: '长尾向右，有高值离群', icon: '↗️' },
  { value: DATA_DISTRIBUTION.SKEWED_NEGATIVE, label: '左偏分布', description: '长尾向左，有低值离群', icon: '↖️' },
  { value: DATA_DISTRIBUTION.OUTLIERS, label: '含离群值', description: '存在显著异常值', icon: '⚠️' },
  { value: DATA_DISTRIBUTION.UNIFORM, label: '均匀分布', description: '各区间频率相近', icon: '▭' }
]

function ChartInput({
  chartType,
  setChartType,
  dataFeatures,
  setDataFeatures,
  categoryCount,
  setCategoryCount,
  distributionType,
  setDistributionType,
  sampleData,
  setSampleData
}) {
  const toggleDataFeature = (feature) => {
    if (dataFeatures.includes(feature)) {
      setDataFeatures(dataFeatures.filter(f => f !== feature))
    } else {
      setDataFeatures([...dataFeatures, feature])
    }
  }

  const analyzeDistribution = () => {
    if (sampleData && sampleData.length > 0) {
      const analysis = analyzeDataDistribution(sampleData)
      if (analysis) {
        setDistributionType(analysis.distributionType)
      }
    }
  }

  const generateRandomData = () => {
    const newData = Array.from({ length: categoryCount }, () =>
      Math.floor(Math.random() * 80 + 20)
    )
    setSampleData(newData)
  }

  return (
    <div className="chart-input">
      <div className="input-group">
        <label className="input-label">图表类型</label>
        <div className="chart-type-grid">
          {CHART_TYPE_OPTIONS.map(option => (
            <button
              key={option.value}
              className={`chart-type-btn ${chartType === option.value ? 'active' : ''}`}
              onClick={() => setChartType(option.value)}
            >
              <span className="chart-icon">{option.icon}</span>
              <span className="chart-label">{option.label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="input-group">
        <label className="input-label">数据特征（可多选）</label>
        <div className="data-feature-grid">
          {DATA_FEATURE_OPTIONS.map(option => (
            <button
              key={option.value}
              className={`data-feature-btn ${dataFeatures.includes(option.value) ? 'active' : ''}`}
              onClick={() => toggleDataFeature(option.value)}
            >
              <div className="feature-header">
                <span className="feature-icon">{option.icon}</span>
                <span className="feature-label">{option.label}</span>
                {dataFeatures.includes(option.value) && <span className="check-mark">✓</span>}
              </div>
              <p className="feature-description">{option.description}</p>
            </button>
          ))}
        </div>
      </div>

      <div className="input-group">
        <label className="input-label">数据分布类型</label>
        <div className="distribution-grid">
          {DISTRIBUTION_OPTIONS.map(option => (
            <button
              key={option.value}
              className={`distribution-btn ${distributionType === option.value ? 'active' : ''}`}
              onClick={() => setDistributionType(option.value)}
            >
              <span className="distribution-icon">{option.icon}</span>
              <span className="distribution-label">{option.label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="input-group">
        <div className="input-row-between">
          <label className="input-label">颜色数量：{categoryCount}</label>
          <button className="generate-data-btn" onClick={generateRandomData}>
            🎲 生成示例数据
          </button>
        </div>
        <input
          type="range"
          min="3"
          max="12"
          value={categoryCount}
          onChange={(e) => setCategoryCount(parseInt(e.target.value))}
          className="count-slider"
        />
        <div className="count-labels">
          <span>3</span>
          <span>6</span>
          <span>9</span>
          <span>12</span>
        </div>
      </div>

      {sampleData && sampleData.length > 0 && (
        <div className="input-group">
          <div className="input-row-between">
            <label className="input-label">示例数据（{sampleData.length}个值）</label>
            <button className="analyze-btn" onClick={analyzeDistribution}>
              🔍 自动分析
            </button>
          </div>
          <div className="sample-data-display">
            {sampleData.map((value, i) => (
              <span key={i} className="data-chip">{value}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default ChartInput

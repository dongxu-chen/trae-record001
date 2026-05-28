import React, { useState } from 'react'
import ChartInput from './components/ChartInput.jsx'
import ColorRecommendations from './components/ColorRecommendations.jsx'
import ColorBlindnessChecker from './components/ColorBlindnessChecker.jsx'
import CustomPalette from './components/CustomPalette.jsx'
import ColorComparison from './components/ColorComparison.jsx'
import ChartPreview from './components/ChartPreview.jsx'
import ColorInfoPanel from './components/ColorInfoPanel.jsx'
import BrandColorExtractor from './components/BrandColorExtractor.jsx'
import EmotionAnalyzer from './components/EmotionAnalyzer.jsx'
import { DATA_DISTRIBUTION } from './utils/colorRecommender.js'

function App() {
  const [chartType, setChartType] = useState('bar')
  const [dataFeatures, setDataFeatures] = useState(['categorical'])
  const [categoryCount, setCategoryCount] = useState(6)
  const [selectedScheme, setSelectedScheme] = useState(null)
  const [comparisonSchemes, setComparisonSchemes] = useState([])
  const [selectedColor, setSelectedColor] = useState(null)
  const [distributionType, setDistributionType] = useState(DATA_DISTRIBUTION.NORMAL)
  const [sampleData, setSampleData] = useState(null)

  const toggleComparison = (scheme) => {
    setComparisonSchemes(prev => {
      const exists = prev.find(s => s.name === scheme.name && s.type === scheme.type)
      if (exists) {
        return prev.filter(s => !(s.name === scheme.name && s.type === scheme.type))
      }
      if (prev.length >= 4) {
        return [...prev.slice(1), scheme]
      }
      return [...prev, scheme]
    })
  }

  const handleColorClick = (color, scheme) => {
    setSelectedColor({ color, scheme })
  }

  const handleApplyBrandPalette = (scheme) => {
    setSelectedScheme(scheme)
  }

  const handleSceneSelectScheme = (scheme) => {
    setSelectedScheme(scheme)
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>🎨 图表颜色方案推荐工具</h1>
        <p className="subtitle">智能推荐最优颜色方案 · 色盲友好检测 · 品牌色提取 · 情感匹配</p>
      </header>

      <main className="main-content">
        <section className="input-section">
          <ChartInput
            chartType={chartType}
            setChartType={setChartType}
            dataFeatures={dataFeatures}
            setDataFeatures={setDataFeatures}
            categoryCount={categoryCount}
            setCategoryCount={setCategoryCount}
            distributionType={distributionType}
            setDistributionType={setDistributionType}
            sampleData={sampleData}
            setSampleData={setSampleData}
          />
        </section>

        <section className="brand-emotion-section">
          <div className="brand-emotion-grid">
            <div className="tool-card">
              <BrandColorExtractor
                onApplyPalette={handleApplyBrandPalette}
                onSelectScheme={setSelectedScheme}
              />
            </div>
            <div className="tool-card">
              <EmotionAnalyzer
                onSelectScheme={handleSceneSelectScheme}
              />
            </div>
          </div>
        </section>

        <section className="recommendations-section">
          <ColorRecommendations
            chartType={chartType}
            dataFeatures={dataFeatures}
            categoryCount={categoryCount}
            sampleData={sampleData}
            onSelectScheme={setSelectedScheme}
            onAddToComparison={toggleComparison}
            comparisonSchemes={comparisonSchemes}
            onColorClick={handleColorClick}
          />
        </section>

        {selectedScheme && (
          <section className="preview-section">
            <ChartPreview
              chartType={chartType}
              colors={selectedScheme.colors}
              categoryCount={categoryCount}
              sampleData={sampleData}
            />
          </section>
        )}

        <section className="tools-section">
          <div className="tool-card">
            <ColorBlindnessChecker
              colors={selectedScheme?.colors || []}
              schemeName={selectedScheme?.name}
            />
          </div>

          <div className="tool-card">
            <CustomPalette />
          </div>
        </section>

        {comparisonSchemes.length > 0 && (
          <section className="comparison-section">
            <ColorComparison
              schemes={comparisonSchemes}
              chartType={chartType}
              categoryCount={categoryCount}
              sampleData={sampleData}
              onRemove={toggleComparison}
            />
          </section>
        )}

        {selectedColor && (
          <section className="info-section">
            <ColorInfoPanel
              color={selectedColor.color}
              schemeName={selectedColor.scheme?.name}
              onClose={() => setSelectedColor(null)}
            />
          </section>
        )}
      </main>

      <footer className="app-footer">
        <p>Powered by Chroma.js + ColorBrewer + ECharts</p>
      </footer>
    </div>
  )
}

export default App

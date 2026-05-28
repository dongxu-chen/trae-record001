import React, { useState, useRef } from 'react'
import { extractBrandColors, generateBrandPalette, getColorName } from '../utils/brandColors.js'

const PALETTE_TYPES = [
  { value: 'professional', label: '商务专业' },
  { value: 'complementary', label: '互补配色' },
  { value: 'analogous', label: '邻近配色' },
  { value: 'gradient', label: '渐变单色' }
]

function BrandColorExtractor({ onApplyPalette, onSelectScheme }) {
  const [image, setImage] = useState(null)
  const [imageUrl, setImageUrl] = useState(null)
  const [extractedColors, setExtractedColors] = useState(null)
  const [paletteType, setPaletteType] = useState('professional')
  const [generatedPalette, setGeneratedPalette] = useState(null)
  const [isExtracting, setIsExtracting] = useState(false)
  const fileInputRef = useRef(null)
  const imgRef = useRef(null)

  const handleFileUpload = (e) => {
    const file = e.target.files[0]
    if (file) {
      const url = URL.createObjectURL(file)
      setImageUrl(url)
      setExtractedColors(null)
      setGeneratedPalette(null)
    }
  }

  const handleImageLoad = async () => {
    if (!imgRef.current) return
    setIsExtracting(true)
    try {
      const result = await extractBrandColors(imgRef.current, 5)
      setExtractedColors(result)
      const palette = generateBrandPalette(result.primaryColor, 6, paletteType)
      setGeneratedPalette(palette)
    } catch (error) {
      console.error('提取颜色失败:', error)
    }
    setIsExtracting(false)
  }

  const handleRegeneratePalette = () => {
    if (extractedColors?.primaryColor) {
      const palette = generateBrandPalette(extractedColors.primaryColor, 6, paletteType)
      setGeneratedPalette(palette)
    }
  }

  const handleApplyToPreview = () => {
    if (generatedPalette && onApplyPalette) {
      onApplyPalette({
        name: `品牌色 - ${extractedColors?.primaryName || '自定义'}`,
        type: 'brand',
        typeLabel: '品牌色',
        colors: generatedPalette,
        score: 85
      })
    }
  }

  const handleTriggerUpload = () => {
    fileInputRef.current?.click()
  }

  return (
    <div className="brand-color-extractor">
      <h3>🏷️ 品牌色提取</h3>
      <p className="extractor-description">上传品牌Logo，自动提取主色生成配色方案</p>

      <div className="upload-area" onClick={handleTriggerUpload}>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleFileUpload}
          className="file-input"
        />
        {!imageUrl ? (
          <div className="upload-placeholder">
            <span className="upload-icon">📤</span>
            <span className="upload-text">点击上传品牌Logo</span>
            <span className="upload-hint">支持 JPG、PNG、SVG 格式</span>
          </div>
        ) : (
          <div className="image-preview-container">
            <img
              ref={imgRef}
              src={imageUrl}
              alt="Logo预览"
              onLoad={handleImageLoad}
              crossOrigin="anonymous"
            />
            {isExtracting && (
              <div className="extracting-overlay">
                <span>提取中...</span>
              </div>
            )}
          </div>
        )}
      </div>

      {extractedColors && (
        <div className="extraction-results">
          <div className="result-section">
            <h4>提取的品牌色</h4>
            <div className="extracted-colors">
              {extractedColors.colors.map((color, i) => (
                <div
                  key={i}
                  className={`extracted-swatch ${i === 0 ? 'primary' : ''}`}
                  style={{ backgroundColor: color }}
                  title={getColorName(color).name}
                >
                  {i === 0 && <span className="primary-badge">主色</span>}
                  <span className="swatch-name">{getColorName(color).name}</span>
                </div>
              ))}
            </div>
            {extractedColors.primaryName && (
              <div className="primary-info">
                <span className="primary-color-name">主色：{extractedColors.primaryName}</span>
                <div className="primary-tags">
                  {extractedColors.primaryTags.map((tag, i) => (
                    <span key={i} className="tag">{tag}</span>
                  ))}
                </div>
              </div>
            )}
            {extractedColors.emotions && extractedColors.emotions.length > 0 && (
              <div className="emotion-tags">
                <span className="emotion-label">情感倾向：</span>
                {extractedColors.emotions.slice(0, 3).map((e, i) => (
                  <span key={i} className="emotion-tag">{e}</span>
                ))}
              </div>
            )}
          </div>

          <div className="result-section">
            <div className="section-header">
              <h4>生成配色方案</h4>
              <select
                value={paletteType}
                onChange={(e) => setPaletteType(e.target.value)}
                className="palette-type-select"
              >
                {PALETTE_TYPES.map(t => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
            {generatedPalette && (
              <>
                <div className="generated-palette">
                  {generatedPalette.map((color, i) => (
                    <div
                      key={i}
                      className="generated-swatch"
                      style={{ backgroundColor: color }}
                      title={getColorName(color).name}
                    >
                      <span className="swatch-hex">{color}</span>
                    </div>
                  ))}
                </div>
                <div className="palette-actions">
                  <button className="regenerate-btn" onClick={handleRegeneratePalette}>
                    🔄 重新生成
                  </button>
                  <button className="apply-btn" onClick={handleApplyToPreview}>
                    ✓ 应用此方案
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default BrandColorExtractor

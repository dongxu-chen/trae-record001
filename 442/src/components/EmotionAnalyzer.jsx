import React, { useState } from 'react'
import { BUSINESS_SCENES, getSceneRecommendations, getColorEmotion } from '../utils/brandColors.js'
import { recommendColorSchemes } from '../utils/colorRecommender.js'

function EmotionAnalyzer({ onSelectScheme }) {
  const [selectedScene, setSelectedScene] = useState(null)
  const [recommendations, setRecommendations] = useState([])
  const [showAnalysis, setShowAnalysis] = useState(false)

  const handleSceneSelect = (scene) => {
    setSelectedScene(scene)
    const sceneInfo = getSceneRecommendations(scene.id)
    if (sceneInfo) {
      const schemes = recommendColorSchemes('bar', ['categorical'], 6, null)
      const filtered = schemes
        .filter(s => sceneInfo.preferredSchemes.includes(s.name))
        .slice(0, 4)
      setRecommendations(filtered)
      setShowAnalysis(true)
    }
  }

  const getEmotionIcon = (emotion) => {
    const icons = {
      '热情': '🔥',
      '活力': '⚡',
      '信任': '💙',
      '专业': '👔',
      '自然': '🌿',
      '健康': '💚',
      '创意': '💡',
      '高贵': '👑',
      '温暖': '☀️',
      '快乐': '😊',
      '稳重': '🏛️',
      '科技': '🔬',
      '时尚': '✨',
      '浪漫': '💕'
    }
    return icons[emotion] || '🎨'
  }

  return (
    <div className="emotion-analyzer">
      <h3>💼 业务场景推荐</h3>
      <p className="analyzer-description">根据业务场景推荐情感匹配的配色方案</p>

      <div className="scene-grid">
        {BUSINESS_SCENES.map(scene => (
          <button
            key={scene.id}
            className={`scene-card ${selectedScene?.id === scene.id ? 'active' : ''}`}
            onClick={() => handleSceneSelect(scene)}
          >
            <span className="scene-name">{scene.name}</span>
            <span className="scene-desc">{scene.description}</span>
          </button>
        ))}
      </div>

      {showAnalysis && selectedScene && (
        <div className="scene-analysis">
          <div className="analysis-header">
            <h4>{selectedScene.name} - 配色分析</h4>
          </div>

          <div className="emotion-analysis">
            <div className="emotion-section">
              <h5>核心情感关键词</h5>
              <div className="emotion-tags-display">
                {selectedScene.description.split('、').map((emotion, i) => (
                  <span key={i} className="emotion-chip">
                    <span className="emoji">{getEmotionIcon(emotion)}</span>
                    {emotion}
                  </span>
                ))}
              </div>
            </div>

            <div className="emotion-section">
              <h5>推荐色系</h5>
              <div className="color-family-display">
                {getSceneRecommendations(selectedScene.id)?.colorFamilies.map((family, i) => (
                  <div key={i} className={`family-badge family-${family}`}>
                    {family}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {recommendations.length > 0 && (
            <div className="scene-schemes">
              <h5>推荐方案</h5>
              <div className="scheme-list">
                {recommendations.map((scheme, i) => (
                  <div key={i} className="scene-scheme-card" onClick={() => onSelectScheme?.(scheme)}>
                    <div className="scheme-info-row">
                      <span className="scheme-name-label">{scheme.name}</span>
                      <span className="scheme-type-badge">{scheme.typeLabel}</span>
                    </div>
                    <div className="scheme-colors-small">
                      {scheme.colors.slice(0, 6).map((color, j) => (
                        <div
                          key={j}
                          className="small-swatch"
                          style={{ backgroundColor: color }}
                        />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default EmotionAnalyzer

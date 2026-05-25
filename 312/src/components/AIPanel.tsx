import { useState, useEffect } from 'react'
import { useEditorStore } from '@/lib/store'
import { generateAnimationSuggestions, applyAnimationSuggestion } from '@/lib/aiAnimation'
import { AnimationSuggestion } from '@/types'

export function AIPanel() {
  const { project, selectedLayerId, addKeyframe } = useEditorStore()
  const [suggestions, setSuggestions] = useState<AnimationSuggestion[]>([])
  const [isAnalyzing, setIsAnalyzing] = useState(false)

  useEffect(() => {
    if (project) {
      analyzeIcon()
    }
  }, [project?.id])

  const analyzeIcon = () => {
    if (!project) return
    setIsAnalyzing(true)
    setTimeout(() => {
      const results = generateAnimationSuggestions(project.elements)
      setSuggestions(results)
      setIsAnalyzing(false)
    }, 500)
  }

  const applySuggestion = (suggestion: AnimationSuggestion) => {
    if (!project || !selectedLayerId) return

    const layer = project.layers.find((l) => l.id === selectedLayerId)
    if (!layer) return

    const result = applyAnimationSuggestion(
      suggestion,
      selectedLayerId,
      layer.elementId,
      project.elements
    )

    result.tracks.forEach((track: any) => {
      track.keyframes.forEach((kf: any) => {
        addKeyframe(selectedLayerId, track.property, kf.time, kf.value)
      })
    })
  }

  if (!project) return null

  return (
    <div className="sidebar-panel">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <h3 style={{ color: '#e94560', fontSize: '14px', margin: 0 }}>🤖 AI 动画推荐</h3>
        <button
          className="btn btn-secondary"
          style={{ padding: '4px 10px', fontSize: '12px' }}
          onClick={analyzeIcon}
          disabled={isAnalyzing}
        >
          {isAnalyzing ? '分析中...' : '🔄'}
        </button>
      </div>

      {!selectedLayerId && (
        <div style={{ background: '#0f3460', padding: '10px', borderRadius: '6px', marginBottom: '12px' }}>
          <p style={{ fontSize: '12px', color: '#facc15', margin: 0 }}>
            ⚠️ 请先选择一个图层以应用动画
          </p>
        </div>
      )}

      <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
        {suggestions.map((suggestion) => (
          <div
            key={suggestion.id}
            style={{
              background: '#0f3460',
              borderRadius: '8px',
              padding: '12px',
              marginBottom: '10px',
              cursor: selectedLayerId ? 'pointer' : 'default',
              opacity: selectedLayerId ? 1 : 0.6,
              transition: 'all 0.2s',
            }}
            onClick={() => selectedLayerId && applySuggestion(suggestion)}
            onMouseEnter={(e) => {
              if (selectedLayerId) {
                ;(e.currentTarget as HTMLDivElement).style.background = '#1a4a7a'
              }
            }}
            onMouseLeave={(e) => {
              ;(e.currentTarget as HTMLDivElement).style.background = '#0f3460'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '6px' }}>
              <span style={{ fontSize: '14px', fontWeight: 500 }}>{suggestion.name}</span>
              <span
                style={{
                  fontSize: '11px',
                  padding: '2px 6px',
                  borderRadius: '10px',
                  background: suggestion.confidence > 0.7 ? '#4ade80' : suggestion.confidence > 0.5 ? '#facc15' : '#888',
                  color: '#1a1a2e',
                }}
              >
                {(suggestion.confidence * 100).toFixed(0)}%
              </span>
            </div>
            <p style={{ fontSize: '12px', color: '#aaa', margin: '0 0 8px 0' }}>
              {suggestion.description}
            </p>
            <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
              {suggestion.tags.map((tag) => (
                <span
                  key={tag}
                  style={{
                    fontSize: '10px',
                    padding: '2px 6px',
                    background: '#1a4a7a',
                    borderRadius: '4px',
                    color: '#888',
                  }}
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

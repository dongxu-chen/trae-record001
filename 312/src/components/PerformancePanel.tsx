import { useState, useEffect } from 'react'
import { useEditorStore } from '@/lib/store'
import {
  analyzePerformance,
  formatBytes,
  getComplexityColor,
  getGradeColor,
} from '@/lib/performanceAnalyzer'
import { PerformanceReport } from '@/types'

export function PerformancePanel() {
  const { project } = useEditorStore()
  const [report, setReport] = useState<PerformanceReport | null>(null)

  useEffect(() => {
    if (project) {
      const result = analyzePerformance(project)
      setReport(result)
    }
  }, [project])

  if (!project || !report) return null

  const { metrics, suggestions, score, grade } = report

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ padding: '16px', borderBottom: '1px solid #0f3460', textAlign: 'center' }}>
        <div
          style={{
            fontSize: '48px',
            fontWeight: 'bold',
            color: getGradeColor(grade),
            lineHeight: 1,
          }}
        >
          {grade}
        </div>
        <div style={{ fontSize: '14px', color: '#888', marginTop: '4px' }}>
          性能评分: {score}/100
        </div>
      </div>

      <div style={{ padding: '16px', borderBottom: '1px solid #0f3460' }}>
        <h4 style={{ margin: '0 0 12px 0', fontSize: '14px', color: '#e94560' }}>📊 性能指标</h4>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
          <MetricItem label="总图层数" value={metrics.totalLayers.toString()} />
          <MetricItem label="动画图层" value={metrics.animatedLayers.toString()} />
          <MetricItem label="关键帧总数" value={metrics.totalKeyframes.toString()} />
          <MetricItem label="轨道总数" value={metrics.totalTracks.toString()} />
          <MetricItem label="路径数量" value={metrics.pathCount.toString()} />
          <MetricItem label="贝塞尔点" value={metrics.bezierCount.toString()} />
          <MetricItem
            label="渲染复杂度"
            value={metrics.renderComplexity}
            color={getComplexityColor(metrics.renderComplexity)}
          />
          <MetricItem
            label="预估帧率"
            value={`${metrics.estimatedFps} FPS`}
            color={metrics.estimatedFps >= 50 ? '#4ade80' : metrics.estimatedFps >= 30 ? '#facc15' : '#ef4444'}
          />
          <MetricItem label="内存占用" value={formatBytes(metrics.memoryEstimate)} />
          <MetricItem label="文件大小" value={formatBytes(metrics.fileSizeEstimate)} />
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
        <h4 style={{ margin: '0 0 12px 0', fontSize: '14px', color: '#e94560' }}>
          💡 优化建议 ({suggestions.length})
        </h4>
        {suggestions.length === 0 ? (
          <div
            style={{
              background: '#0f3460',
              padding: '16px',
              borderRadius: '8px',
              textAlign: 'center',
            }}
          >
            <span style={{ fontSize: '24px' }}>🎉</span>
            <p style={{ margin: '8px 0 0 0', fontSize: '13px', color: '#4ade80' }}>
              动画性能良好，无需优化!
            </p>
          </div>
        ) : (
          suggestions.map((suggestion) => (
            <div
              key={suggestion.id}
              style={{
                background: '#0f3460',
                borderRadius: '8px',
                padding: '12px',
                marginBottom: '10px',
                borderLeft: `3px solid ${
                  suggestion.severity === 'high'
                    ? '#ef4444'
                    : suggestion.severity === 'medium'
                    ? '#facc15'
                    : '#888'
                }`,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '6px' }}>
                <span style={{ fontSize: '14px', fontWeight: 500 }}>
                  {suggestion.type === 'warning' && '⚠️ '}
                  {suggestion.type === 'suggestion' && '💡 '}
                  {suggestion.type === 'info' && 'ℹ️ '}
                  {suggestion.title}
                </span>
                <span
                  style={{
                    fontSize: '10px',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    background:
                      suggestion.severity === 'high'
                        ? '#ef444433'
                        : suggestion.severity === 'medium'
                        ? '#facc1533'
                        : '#888333',
                    color:
                      suggestion.severity === 'high'
                        ? '#ef4444'
                        : suggestion.severity === 'medium'
                        ? '#facc15'
                        : '#888',
                  }}
                >
                  {suggestion.severity === 'high' ? '高' : suggestion.severity === 'medium' ? '中' : '低'}
                </span>
              </div>
              <p style={{ fontSize: '12px', color: '#aaa', margin: '0 0 8px 0' }}>
                {suggestion.description}
              </p>
              <div style={{ fontSize: '12px', background: '#16213e', padding: '8px', borderRadius: '4px' }}>
                <strong style={{ color: '#e94560' }}>影响: </strong>
                <span style={{ color: '#ccc' }}>{suggestion.impact}</span>
              </div>
              <div
                style={{
                  fontSize: '12px',
                  background: '#16213e',
                  padding: '8px',
                  borderRadius: '4px',
                  marginTop: '4px',
                  whiteSpace: 'pre-line',
                }}
              >
                <strong style={{ color: '#4ade80' }}>修复: </strong>
                <span style={{ color: '#ccc' }}>{suggestion.howToFix}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

function MetricItem({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={{ background: '#0f3460', padding: '8px', borderRadius: '6px' }}>
      <div style={{ fontSize: '11px', color: '#888', marginBottom: '2px' }}>{label}</div>
      <div style={{ fontSize: '14px', fontWeight: 500, color: color || 'white' }}>{value}</div>
    </div>
  )
}

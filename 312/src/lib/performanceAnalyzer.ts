import { Project, PerformanceReport, PerformanceMetrics, OptimizationSuggestion } from '@/types'
import { nanoid } from 'nanoid'

export function analyzePerformance(project: Project): PerformanceReport {
  const metrics = calculateMetrics(project)
  const suggestions = generateSuggestions(project, metrics)
  const score = calculateScore(metrics, suggestions)
  const grade = calculateGrade(score)

  return {
    metrics,
    suggestions,
    score,
    grade,
  }
}

function calculateMetrics(project: Project): PerformanceMetrics {
  const totalLayers = project.layers.length
  const animatedLayers = project.layers.filter((l) => l.tracks.length > 0).length
  const totalTracks = project.layers.reduce((acc, l) => acc + l.tracks.length, 0)
  const totalKeyframes = project.layers.reduce(
    (acc, l) => acc + l.tracks.reduce((a, t) => a + t.keyframes.length, 0),
    0
  )

  const elements = Object.values(project.elements)
  const pathCount = elements.filter((el) => el.type === 'path').length
  const bezierCount = elements.filter((el) => {
    if (el.type !== 'path') return false
    const d = el.attributes.d || ''
    return (d.match(/[CcSsQqTt]/g) || []).length
  }).length

  const gradientCount = elements.filter((el) => {
    const fill = el.attributes.fill || ''
    const stroke = el.attributes.stroke || ''
    return fill.includes('gradient') || stroke.includes('gradient')
  }).length

  const filterEffects = elements.filter((el) => {
    const style = el.attributes.style || ''
    return style.includes('filter') || el.attributes.filter
  }).length

  const transformOperations = animatedLayers * 5

  const keyframeDensity = totalKeyframes / (project.duration / 1000)
  const complexityScore = Math.min(1, (animatedLayers * 0.3 + totalKeyframes * 0.02 + bezierCount * 0.1) / 10)

  let renderComplexity: PerformanceMetrics['renderComplexity'] = 'low'
  if (complexityScore > 0.75) {
    renderComplexity = 'very-high'
  } else if (complexityScore > 0.5) {
    renderComplexity = 'high'
  } else if (complexityScore > 0.25) {
    renderComplexity = 'medium'
  }

  const estimatedFps = Math.max(30, Math.min(60, 60 - complexityScore * 30))
  const memoryEstimate = (totalKeyframes * 64 + elements.length * 256) / 1024
  const fileSizeEstimate = (totalKeyframes * 32 + elements.length * 128) / 1024

  return {
    totalLayers,
    animatedLayers,
    totalKeyframes,
    totalTracks,
    estimatedFps,
    renderComplexity,
    pathCount,
    bezierCount,
    gradientCount,
    filterEffects,
    transformOperations,
    memoryEstimate,
    fileSizeEstimate,
  }
}

function generateSuggestions(project: Project, metrics: PerformanceMetrics): OptimizationSuggestion[] {
  const suggestions: OptimizationSuggestion[] = []

  if (metrics.totalKeyframes > 50) {
    suggestions.push({
      id: nanoid(),
      type: 'warning',
      severity: 'medium',
      title: '关键帧数量过多',
      description: `当前有 ${metrics.totalKeyframes} 个关键帧，可能影响性能`,
      impact: '关键帧越多，动画计算越复杂，可能导致帧率下降',
      howToFix: '1. 使用导出时的压缩功能合并相似关键帧\n2. 简化动画曲线，减少不必要的关键帧\n3. 考虑使用循环动画替代长序列',
    })
  }

  if (metrics.animatedLayers > 5) {
    suggestions.push({
      id: nanoid(),
      type: 'suggestion',
      severity: 'low',
      title: '同时动画的图层较多',
      description: `${metrics.animatedLayers} 个图层同时进行动画`,
      impact: '多个图层同时动画会增加每帧的渲染开销',
      howToFix: '1. 考虑错开各图层的动画时间\n2. 合并可以一起动画的图层\n3. 使用预合成减少重绘区域',
    })
  }

  if (metrics.bezierCount > 10) {
    suggestions.push({
      id: nanoid(),
      type: 'warning',
      severity: 'medium',
      title: '贝塞尔曲线复杂度高',
      description: `检测到 ${metrics.bezierCount} 个贝塞尔曲线控制点`,
      impact: '复杂路径在动画时需要更多计算资源',
      howToFix: '1. 简化SVG路径，减少控制点数量\n2. 对复杂元素考虑使用CSS transform替代路径变形\n3. 使用关键帧插值替代逐帧路径动画',
    })
  }

  if (metrics.gradientCount > 0) {
    suggestions.push({
      id: nanoid(),
      type: 'suggestion',
      severity: 'low',
      title: '使用了渐变效果',
      description: `${metrics.gradientCount} 个元素使用了渐变填充/描边`,
      impact: '渐变渲染比纯色更消耗性能，尤其在移动设备上',
      howToFix: '1. 考虑使用纯色或图片替代渐变\n2. 减少渐变的颜色停止点数量\n3. 静态元素的渐变影响较小',
    })
  }

  if (metrics.filterEffects > 0) {
    suggestions.push({
      id: nanoid(),
      type: 'warning',
      severity: 'high',
      title: '使用了滤镜效果',
      description: `检测到 ${metrics.filterEffects} 个滤镜效果`,
      impact: 'SVG滤镜是性能消耗最大的操作之一，可能显著降低帧率',
      howToFix: '1. 尽量避免在动画元素上使用滤镜\n2. 考虑使用图片替代滤镜效果\n3. 阴影可使用多层元素模拟',
      affectedElements: Object.values(project.elements)
        .filter((el) => el.attributes.filter || el.attributes.style?.includes('filter'))
        .map((el) => el.name),
    })
  }

  if (metrics.totalTracks > 0 && metrics.totalKeyframes / metrics.totalTracks > 10) {
    suggestions.push({
      id: nanoid(),
      type: 'info',
      severity: 'low',
      title: '可启用导出压缩',
      description: '关键帧密度较高，启用压缩可显著减少文件体积',
      impact: '压缩后文件体积可减少 30%-70%，对视觉效果影响极小',
      howToFix: '导出时勾选"启用压缩"选项，调整容差滑块平衡精度和体积',
    })
  }

  if (project.duration > 10000) {
    suggestions.push({
      id: nanoid(),
      type: 'suggestion',
      severity: 'low',
      title: '动画时长较长',
      description: `动画时长 ${(project.duration / 1000).toFixed(0)} 秒`,
      impact: '长动画会增加文件体积和内存占用',
      howToFix: '1. 考虑使用循环动画模式\n2. 识别可复用的动画片段进行循环\n3. 过长动画可考虑拆分为多个文件',
    })
  }

  if (metrics.renderComplexity === 'high' || metrics.renderComplexity === 'very-high') {
    suggestions.push({
      id: nanoid(),
      type: 'warning',
      severity: 'high',
      title: '渲染复杂度较高',
      description: `当前复杂度评级为 ${metrics.renderComplexity}`,
      impact: '在低端设备上可能出现卡顿或掉帧，影响用户体验',
      howToFix:
        '1. 减少同时动画的元素数量\n2. 简化路径和动画曲线\n3. 避免使用滤镜和复杂渐变\n4. 考虑降低帧率（如从60fps降到30fps）',
    })
  }

  return suggestions
}

function calculateScore(metrics: PerformanceMetrics, suggestions: OptimizationSuggestion[]): number {
  let score = 100
  const highSeverity = suggestions.filter((s) => s.severity === 'high').length
  const mediumSeverity = suggestions.filter((s) => s.severity === 'medium').length
  const lowSeverity = suggestions.filter((s) => s.severity === 'low').length

  score -= highSeverity * 15
  score -= mediumSeverity * 8
  score -= lowSeverity * 3

  if (metrics.estimatedFps < 40) {
    score -= 10
  }

  if (metrics.totalKeyframes > 100) {
    score -= 10
  }

  return Math.max(0, Math.min(100, score))
}

function calculateGrade(score: number): PerformanceReport['grade'] {
  if (score >= 90) return 'A'
  if (score >= 80) return 'B'
  if (score >= 70) return 'C'
  if (score >= 60) return 'D'
  return 'F'
}

export function formatBytes(kb: number): string {
  if (kb < 1) {
    return `${Math.round(kb * 1024)} B`
  }
  return `${kb.toFixed(1)} KB`
}

export function getComplexityColor(complexity: PerformanceMetrics['renderComplexity']): string {
  const colors: Record<string, string> = {
    low: '#4ade80',
    medium: '#facc15',
    high: '#fb923c',
    'very-high': '#ef4444',
  }
  return colors[complexity] || '#888'
}

export function getGradeColor(grade: PerformanceReport['grade']): string {
  const colors: Record<string, string> = {
    A: '#4ade80',
    B: '#facc15',
    C: '#fb923c',
    D: '#f97316',
    F: '#ef4444',
  }
  return colors[grade] || '#888'
}

export interface Point {
  x: number
  y: number
}

export interface PathAnimation {
  id: string
  pathData: string
  sampler: any
}

export interface Keyframe {
  id: string
  time: number
  value: number | Point | string
  easing: EasingType
  property: string
}

export interface KeyframeSnapOptions {
  enabled: boolean
  gridSize: number
  snapToOtherKeyframes: boolean
  snapToMarkers: boolean
}

export interface ExportOptions {
  compress: boolean
  keyframeTolerance: number
  optimizePaths: boolean
  minify: boolean
}

export type EasingType = 
  | 'linear'
  | 'easeIn'
  | 'easeOut'
  | 'easeInOut'
  | 'easeInQuad'
  | 'easeOutQuad'
  | 'easeInOutQuad'
  | 'easeInCubic'
  | 'easeOutCubic'
  | 'easeInOutCubic'
  | 'easeInSine'
  | 'easeOutSine'
  | 'easeInOutSine'
  | 'easeOutBounce'
  | 'elastic'
  | 'bounce'

export interface AnimationTrack {
  id: string
  property: string
  keyframes: Keyframe[]
}

export interface SvgElement {
  id: string
  name: string
  type: 'path' | 'rect' | 'circle' | 'ellipse' | 'line' | 'polyline' | 'polygon' | 'g'
  attributes: Record<string, string>
  transform: Transform
  parentId: string | null
  children: string[]
}

export interface Transform {
  position: Point
  rotation: number
  scale: Point
  anchor: Point
  opacity: number
}

export interface Layer {
  id: string
  name: string
  elementId: string
  visible: boolean
  locked: boolean
  tracks: AnimationTrack[]
}

export interface Project {
  id: string
  name: string
  createdAt: number
  updatedAt: number
  duration: number
  framerate: number
  width: number
  height: number
  svgContent: string
  elements: Record<string, SvgElement>
  layers: Layer[]
  versions: Version[]
}

export interface Version {
  id: string
  name: string
  createdAt: number
  description: string
  snapshot: ProjectSnapshot
}

export interface ProjectSnapshot {
  elements: Record<string, SvgElement>
  layers: Layer[]
  duration: number
}

export interface Collaborator {
  id: string
  name: string
  avatar: string
  color: string
}

export interface AnimationSuggestion {
  id: string
  name: string
  description: string
  iconType: IconType
  animationType: AnimationType
  duration: number
  tracks: AnimationTrackTemplate[]
  confidence: number
  tags: string[]
}

export type IconType = 
  | 'button'
  | 'icon'
  | 'logo'
  | 'illustration'
  | 'loading'
  | 'notification'
  | 'arrow'
  | 'check'
  | 'close'
  | 'menu'
  | 'search'
  | 'other'

export type AnimationType =
  | 'bounce'
  | 'pulse'
  | 'spin'
  | 'shake'
  | 'fade'
  | 'slide'
  | 'scale'
  | 'wiggle'
  | 'heartbeat'
  | 'ripple'
  | 'float'
  | 'swing'

export interface AnimationTrackTemplate {
  property: string
  keyframes: KeyframeTemplate[]
}

export interface KeyframeTemplate {
  time: number
  value: number | Point
  easing: EasingType
}

export interface AnimationTemplate {
  id: string
  name: string
  description: string
  author: string
  authorAvatar?: string
  createdAt: number
  updatedAt: number
  likes: number
  downloads: number
  isPublic: boolean
  tags: string[]
  category: string
  previewUrl?: string
  animation: {
    duration: number
    framerate: number
    tracks: AnimationTrackTemplate[]
    targetElements: string[]
  }
}

export interface PerformanceMetrics {
  totalLayers: number
  animatedLayers: number
  totalKeyframes: number
  totalTracks: number
  estimatedFps: number
  renderComplexity: 'low' | 'medium' | 'high' | 'very-high'
  pathCount: number
  bezierCount: number
  gradientCount: number
  filterEffects: number
  transformOperations: number
  memoryEstimate: number
  fileSizeEstimate: number
}

export interface OptimizationSuggestion {
  id: string
  type: 'warning' | 'suggestion' | 'info'
  severity: 'low' | 'medium' | 'high'
  title: string
  description: string
  impact: string
  howToFix: string
  affectedElements?: string[]
}

export interface PerformanceReport {
  metrics: PerformanceMetrics
  suggestions: OptimizationSuggestion[]
  score: number
  grade: 'A' | 'B' | 'C' | 'D' | 'F'
}

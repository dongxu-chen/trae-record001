import { AnimationSuggestion, IconType, AnimationType, AnimationTrackTemplate, SvgElement } from '@/types'
import { nanoid } from 'nanoid'

export function detectIconType(elements: Record<string, SvgElement>): IconType {
  const elementTypes = Object.values(elements).map((el) => el.type)
  const elementCount = elementTypes.length
  const hasPath = elementTypes.includes('path')
  const hasCircle = elementTypes.includes('circle')
  const hasRect = elementTypes.includes('rect')
  const hasPolygon = elementTypes.includes('polygon')

  if (elementCount <= 3 && hasCircle) {
    return 'loading'
  }

  if (elementCount <= 5 && hasPath && !hasRect) {
    return 'icon'
  }

  if (elementCount >= 10) {
    return 'illustration'
  }

  if (hasRect && elementCount <= 4) {
    return 'button'
  }

  if (hasPolygon) {
    return 'arrow'
  }

  return 'other'
}

export function analyzeIconFeatures(elements: Record<string, SvgElement>): {
  complexity: number
  symmetry: number
  hasCircularElements: boolean
  hasLinearElements: boolean
  elementCount: number
  averagePathLength: number
} {
  const elementArray = Object.values(elements)
  const paths = elementArray.filter((el) => el.type === 'path')

  let totalPathLength = 0
  paths.forEach((path) => {
    const d = path.attributes.d || ''
    totalPathLength += d.length
  })

  const circularElements = elementArray.filter(
    (el) => el.type === 'circle' || el.type === 'ellipse'
  )
  const linearElements = elementArray.filter(
    (el) => el.type === 'line' || el.type === 'polyline'
  )

  return {
    complexity: Math.min(1, elementArray.length / 20),
    symmetry: 0.5,
    hasCircularElements: circularElements.length > 0,
    hasLinearElements: linearElements.length > 0,
    elementCount: elementArray.length,
    averagePathLength: paths.length > 0 ? totalPathLength / paths.length : 0,
  }
}

function createBounceAnimation(duration: number = 1000): AnimationTrackTemplate[] {
  return [
    {
      property: 'position.y',
      keyframes: [
        { time: 0, value: 0, easing: 'easeOutCubic' },
        { time: duration * 0.5, value: -30, easing: 'easeInCubic' },
        { time: duration, value: 0, easing: 'easeOutBounce' },
      ],
    },
    {
      property: 'scale.y',
      keyframes: [
        { time: 0, value: 1, easing: 'easeOut' },
        { time: duration * 0.45, value: 1.1, easing: 'easeIn' },
        { time: duration * 0.55, value: 0.9, easing: 'easeOut' },
        { time: duration, value: 1, easing: 'easeOut' },
      ],
    },
  ]
}

function createPulseAnimation(duration: number = 1500): AnimationTrackTemplate[] {
  return [
    {
      property: 'scale.x',
      keyframes: [
        { time: 0, value: 1, easing: 'easeInOutSine' },
        { time: duration * 0.5, value: 1.15, easing: 'easeInOutSine' },
        { time: duration, value: 1, easing: 'easeInOutSine' },
      ],
    },
    {
      property: 'scale.y',
      keyframes: [
        { time: 0, value: 1, easing: 'easeInOutSine' },
        { time: duration * 0.5, value: 1.15, easing: 'easeInOutSine' },
        { time: duration, value: 1, easing: 'easeInOutSine' },
      ],
    },
    {
      property: 'opacity',
      keyframes: [
        { time: 0, value: 1, easing: 'easeInOut' },
        { time: duration * 0.5, value: 0.8, easing: 'easeInOut' },
        { time: duration, value: 1, easing: 'easeInOut' },
      ],
    },
  ]
}

function createSpinAnimation(duration: number = 1000): AnimationTrackTemplate[] {
  return [
    {
      property: 'rotation',
      keyframes: [
        { time: 0, value: 0, easing: 'linear' },
        { time: duration, value: 360, easing: 'linear' },
      ],
    },
  ]
}

function createShakeAnimation(duration: number = 500): AnimationTrackTemplate[] {
  const intensity = 5
  return [
    {
      property: 'position.x',
      keyframes: [
        { time: 0, value: 0, easing: 'easeInOut' },
        { time: duration * 0.1, value: -intensity, easing: 'easeInOut' },
        { time: duration * 0.2, value: intensity, easing: 'easeInOut' },
        { time: duration * 0.3, value: -intensity, easing: 'easeInOut' },
        { time: duration * 0.4, value: intensity, easing: 'easeInOut' },
        { time: duration * 0.5, value: -intensity / 2, easing: 'easeInOut' },
        { time: duration * 0.6, value: intensity / 2, easing: 'easeInOut' },
        { time: duration * 0.7, value: -intensity / 4, easing: 'easeInOut' },
        { time: duration * 0.8, value: intensity / 4, easing: 'easeInOut' },
        { time: duration, value: 0, easing: 'easeOut' },
      ],
    },
  ]
}

function createFadeAnimation(duration: number = 1000): AnimationTrackTemplate[] {
  return [
    {
      property: 'opacity',
      keyframes: [
        { time: 0, value: 0, easing: 'easeInOut' },
        { time: duration * 0.5, value: 1, easing: 'easeInOut' },
        { time: duration, value: 0, easing: 'easeInOut' },
      ],
    },
  ]
}

function createHeartbeatAnimation(duration: number = 1000): AnimationTrackTemplate[] {
  return [
    {
      property: 'scale.x',
      keyframes: [
        { time: 0, value: 1, easing: 'easeOut' },
        { time: duration * 0.15, value: 1.1, easing: 'easeIn' },
        { time: duration * 0.3, value: 1, easing: 'easeOut' },
        { time: duration * 0.45, value: 1.15, easing: 'easeIn' },
        { time: duration * 0.6, value: 1, easing: 'easeOut' },
        { time: duration, value: 1, easing: 'linear' },
      ],
    },
    {
      property: 'scale.y',
      keyframes: [
        { time: 0, value: 1, easing: 'easeOut' },
        { time: duration * 0.15, value: 1.1, easing: 'easeIn' },
        { time: duration * 0.3, value: 1, easing: 'easeOut' },
        { time: duration * 0.45, value: 1.15, easing: 'easeIn' },
        { time: duration * 0.6, value: 1, easing: 'easeOut' },
        { time: duration, value: 1, easing: 'linear' },
      ],
    },
  ]
}

function createWiggleAnimation(duration: number = 1000): AnimationTrackTemplate[] {
  return [
    {
      property: 'rotation',
      keyframes: [
        { time: 0, value: 0, easing: 'easeInOut' },
        { time: duration * 0.25, value: -10, easing: 'easeInOut' },
        { time: duration * 0.5, value: 10, easing: 'easeInOut' },
        { time: duration * 0.75, value: -5, easing: 'easeInOut' },
        { time: duration, value: 0, easing: 'easeOut' },
      ],
    },
  ]
}

function createFloatAnimation(duration: number = 2000): AnimationTrackTemplate[] {
  return [
    {
      property: 'position.y',
      keyframes: [
        { time: 0, value: 0, easing: 'easeInOutSine' },
        { time: duration * 0.5, value: -15, easing: 'easeInOutSine' },
        { time: duration, value: 0, easing: 'easeInOutSine' },
      ],
    },
  ]
}

function createRippleAnimation(duration: number = 1500): AnimationTrackTemplate[] {
  return [
    {
      property: 'scale.x',
      keyframes: [
        { time: 0, value: 0.8, easing: 'easeOut' },
        { time: duration, value: 1.5, easing: 'easeOut' },
      ],
    },
    {
      property: 'scale.y',
      keyframes: [
        { time: 0, value: 0.8, easing: 'easeOut' },
        { time: duration, value: 1.5, easing: 'easeOut' },
      ],
    },
    {
      property: 'opacity',
      keyframes: [
        { time: 0, value: 1, easing: 'linear' },
        { time: duration, value: 0, easing: 'linear' },
      ],
    },
  ]
}

const animationFactories: Record<AnimationType, (duration?: number) => AnimationTrackTemplate[]> = {
  bounce: createBounceAnimation,
  pulse: createPulseAnimation,
  spin: createSpinAnimation,
  shake: createShakeAnimation,
  fade: createFadeAnimation,
  slide: createFadeAnimation,
  scale: createPulseAnimation,
  wiggle: createWiggleAnimation,
  heartbeat: createHeartbeatAnimation,
  ripple: createRippleAnimation,
  float: createFloatAnimation,
  swing: createWiggleAnimation,
}

const animationNames: Record<AnimationType, string> = {
  bounce: '弹跳',
  pulse: '脉冲',
  spin: '旋转',
  shake: '抖动',
  fade: '淡入淡出',
  slide: '滑动',
  scale: '缩放',
  wiggle: '摇摆',
  heartbeat: '心跳',
  ripple: '涟漪',
  float: '漂浮',
  swing: '摆动',
}

const animationDescriptions: Record<AnimationType, string> = {
  bounce: '经典弹跳效果，带来活泼的感觉',
  pulse: '呼吸般的缩放效果，增加生命力',
  spin: '360度旋转，适合加载动画',
  shake: '左右抖动，表达错误或提醒',
  fade: '淡入淡出过渡，优雅简洁',
  slide: '滑动入场效果',
  scale: '缩放动画，吸引注意力',
  wiggle: '左右摇摆，增添趣味',
  heartbeat: '心跳节奏，表达喜爱',
  ripple: '涟漪扩散效果',
  float: '上下漂浮，轻盈优雅',
  swing: '钟摆摆动效果',
}

export function generateAnimationSuggestions(
  elements: Record<string, SvgElement>
): AnimationSuggestion[] {
  const iconType = detectIconType(elements)
  const features = analyzeIconFeatures(elements)
  const suggestions: AnimationSuggestion[] = []

  const recommendedAnimations: { type: AnimationType; confidence: number; tags: string[] }[] = []

  if (features.hasCircularElements || iconType === 'loading') {
    recommendedAnimations.push({ type: 'spin', confidence: 0.9, tags: ['加载', '循环', '旋转'] })
    recommendedAnimations.push({ type: 'pulse', confidence: 0.8, tags: ['加载', '循环', '呼吸'] })
  }

  if (iconType === 'button') {
    recommendedAnimations.push({ type: 'bounce', confidence: 0.85, tags: ['按钮', '点击', '反馈'] })
    recommendedAnimations.push({ type: 'pulse', confidence: 0.75, tags: ['按钮', '悬停'] })
    recommendedAnimations.push({ type: 'scale', confidence: 0.7, tags: ['按钮', '点击'] })
  }

  if (iconType === 'notification') {
    recommendedAnimations.push({ type: 'shake', confidence: 0.9, tags: ['通知', '提醒', '抖动'] })
    recommendedAnimations.push({ type: 'bounce', confidence: 0.8, tags: ['通知', '提醒'] })
  }

  if (iconType === 'arrow' || features.hasLinearElements) {
    recommendedAnimations.push({ type: 'bounce', confidence: 0.7, tags: ['箭头', '引导'] })
    recommendedAnimations.push({ type: 'float', confidence: 0.65, tags: ['箭头', '引导'] })
  }

  if (iconType === 'illustration') {
    recommendedAnimations.push({ type: 'float', confidence: 0.8, tags: ['插画', '轻盈'] })
    recommendedAnimations.push({ type: 'pulse', confidence: 0.7, tags: ['插画', '呼吸'] })
    recommendedAnimations.push({ type: 'wiggle', confidence: 0.6, tags: ['插画', '趣味'] })
  }

  if (iconType === 'icon') {
    recommendedAnimations.push({ type: 'bounce', confidence: 0.75, tags: ['通用', '活泼'] })
    recommendedAnimations.push({ type: 'heartbeat', confidence: 0.7, tags: ['收藏', '喜欢'] })
    recommendedAnimations.push({ type: 'wiggle', confidence: 0.65, tags: ['趣味', '活泼'] })
    recommendedAnimations.push({ type: 'fade', confidence: 0.6, tags: ['过渡', '优雅'] })
  }

  recommendedAnimations.push({ type: 'ripple', confidence: 0.5, tags: ['扩散', '特效'] })
  recommendedAnimations.push({ type: 'swing', confidence: 0.45, tags: ['摆动', '趣味'] })

  const uniqueTypes = new Set<AnimationType>()
  const filteredRecommendations = recommendedAnimations.filter((rec) => {
    if (uniqueTypes.has(rec.type)) return false
    uniqueTypes.add(rec.type)
    return true
  })

  filteredRecommendations.forEach((rec, index) => {
    const duration = rec.type === 'spin' ? 1000 : rec.type === 'float' ? 2000 : 1000
    const tracks = animationFactories[rec.type](duration)

    suggestions.push({
      id: nanoid(),
      name: animationNames[rec.type],
      description: animationDescriptions[rec.type],
      iconType,
      animationType: rec.type,
      duration,
      tracks,
      confidence: Math.max(0.3, rec.confidence - index * 0.05),
      tags: rec.tags,
    })
  })

  return suggestions.sort((a, b) => b.confidence - a.confidence)
}

export function applyAnimationSuggestion(
  suggestion: AnimationSuggestion,
  layerId: string,
  elementId: string,
  elements: Record<string, SvgElement>
): { tracks: any[] } {
  const element = elements[elementId]
  if (!element) return { tracks: [] }

  const tracks = suggestion.tracks.map((trackTemplate) => ({
    id: nanoid(),
    property: trackTemplate.property,
    keyframes: trackTemplate.keyframes.map((kf) => ({
      id: nanoid(),
      time: kf.time,
      value: kf.value,
      easing: kf.easing,
      property: trackTemplate.property,
    })),
  }))

  return { tracks }
}

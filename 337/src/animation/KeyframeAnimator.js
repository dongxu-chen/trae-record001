import gsap from 'gsap'
import { CustomEase } from 'gsap/CustomEase'

gsap.registerPlugin(CustomEase)

export class KeyframeAnimator {
  constructor(particleEngine) {
    this.engine = particleEngine
    this.timelines = []
    this.currentTimeline = null
    this.isPlaying = false
    this.customEases = new Map()
    this.currentEaseParams = { x1: 0.25, y1: 0.1, x2: 0.25, y2: 1 }
    this.currentEaseName = 'custom_bezier'
  }

  registerCustomEase(name, bezierParams) {
    const { x1, y1, x2, y2 } = bezierParams
    const easeString = `M0,0 C${x1},${y1} ${x2},${y2} 1,1`
    
    try {
      CustomEase.create(name, easeString)
      this.customEases.set(name, { params: bezierParams, easeString })
      return true
    } catch (e) {
      console.error('Failed to register custom ease:', e)
      return false
    }
  }

  getBezierEase(bezierParams) {
    const { x1, y1, x2, y2 } = bezierParams
    const easeName = `bezier_${x1}_${y1}_${x2}_${y2}`.replace(/\./g, 'p')
    
    if (!this.customEases.has(easeName)) {
      this.registerCustomEase(easeName, bezierParams)
    }
    
    return easeName
  }

  createTimeline(config = {}) {
    const timeline = gsap.timeline({
      paused: true,
      repeat: config.repeat || 0,
      yoyo: config.yoyo || false,
      onComplete: () => {
        this.isPlaying = false
      }
    })
    this.timelines.push(timeline)
    this.currentTimeline = timeline
    return timeline
  }

  addKeyframe(timeline, keyframe) {
    const { time, properties, duration = 0.5, ease = 'power2.inOut', bezier = null } = keyframe
    const configSnapshot = JSON.parse(JSON.stringify(this.engine.config))
    
    let actualEase = ease
    if (bezier) {
      actualEase = this.getBezierEase(bezier)
    }
    
    const targetProps = {}
    this.buildTargetProps(configSnapshot, properties, targetProps)

    timeline.to(this.engine.config, {
      ...targetProps,
      duration,
      ease: actualEase,
      delay: time,
      onUpdate: () => {
        this.engine.updateConfig({})
      }
    })
  }

  buildTargetProps(source, target, result, prefix = '') {
    for (const key in target) {
      const fullKey = prefix ? `${prefix}.${key}` : key
      if (typeof target[key] === 'object' && !Array.isArray(target[key])) {
        this.buildTargetProps(source[key], target[key], result, fullKey)
      } else {
        result[fullKey] = target[key]
      }
    }
  }

  createAnimationFromKeyframes(keyframes, config = {}) {
    const timeline = this.createTimeline(config)
    
    keyframes.sort((a, b) => a.time - b.time)
    
    for (let i = 0; i < keyframes.length; i++) {
      const current = keyframes[i]
      const next = keyframes[i + 1]
      const duration = next ? next.time - current.time : 0.5
      
      this.addKeyframe(timeline, {
        time: i === 0 ? 0 : keyframes[i - 1].time,
        properties: current.properties,
        duration,
        ease: current.ease || 'power2.inOut',
        bezier: current.bezier || null
      })
    }
    
    return timeline
  }

  createPresetAnimation(type, bezierParams = null) {
    const presets = {
      pulse: [
        { time: 0, properties: { emissionRate: 100, size: { min: 0.1, max: 0.3 } }, ease: 'power2.inOut' },
        { time: 1, properties: { emissionRate: 500, size: { min: 0.3, max: 0.8 } }, ease: 'power2.inOut' },
        { time: 2, properties: { emissionRate: 100, size: { min: 0.1, max: 0.3 } }, ease: 'power2.inOut' }
      ],
      colorShift: [
        { time: 0, properties: { color: { start: '#ff0000', end: '#ff6600' } }, ease: 'power1.inOut' },
        { time: 2, properties: { color: { start: '#00ff00', end: '#00ff66' } }, ease: 'power1.inOut' },
        { time: 4, properties: { color: { start: '#0000ff', end: '#6600ff' } }, ease: 'power1.inOut' },
        { time: 6, properties: { color: { start: '#ff0000', end: '#ff6600' } }, ease: 'power1.inOut' }
      ],
      explosion: [
        { time: 0, properties: { emissionRate: 10, speed: { min: 1, max: 3 } }, ease: 'power4.out' },
        { time: 0.5, properties: { emissionRate: 1000, speed: { min: 5, max: 15 } }, ease: 'power4.out' },
        { time: 1, properties: { emissionRate: 50, speed: { min: 1, max: 3 } }, ease: 'power2.out' }
      ],
      spiral: [
        { time: 0, properties: { direction: { x: 1, y: 0, z: 0 }, emitterPosition: { x: 0, y: 0, z: 0 } }, ease: 'none' },
        { time: 2, properties: { direction: { x: 0, y: 1, z: 0 }, emitterPosition: { x: 2, y: 0, z: 0 } }, ease: 'none' },
        { time: 4, properties: { direction: { x: -1, y: 0, z: 0 }, emitterPosition: { x: 0, y: 2, z: 0 } }, ease: 'none' },
        { time: 6, properties: { direction: { x: 0, y: -1, z: 0 }, emitterPosition: { x: -2, y: 0, z: 0 } }, ease: 'none' },
        { time: 8, properties: { direction: { x: 1, y: 0, z: 0 }, emitterPosition: { x: 0, y: -2, z: 0 } }, ease: 'none' }
      ]
    }

    let keyframes = presets[type] || presets.pulse
    
    if (bezierParams) {
      keyframes = keyframes.map(kf => ({
        ...kf,
        ease: null,
        bezier: bezierParams
      }))
    }
    
    return this.createAnimationFromKeyframes(keyframes, { repeat: -1, yoyo: false })
  }

  setCustomBezierEase(bezierParams) {
    this.currentEaseParams = { ...bezierParams }
    this.registerCustomEase(this.currentEaseName, bezierParams)
  }

  playAnimationWithCustomEase(type, bezierParams) {
    this.stopAll()
    this.createPresetAnimation(type, bezierParams)
    this.play()
  }

  play(timeline = this.currentTimeline) {
    if (timeline) {
      timeline.play()
      this.isPlaying = true
    }
  }

  pause(timeline = this.currentTimeline) {
    if (timeline) {
      timeline.pause()
      this.isPlaying = false
    }
  }

  restart(timeline = this.currentTimeline) {
    if (timeline) {
      timeline.restart()
      this.isPlaying = true
    }
  }

  seek(time, timeline = this.currentTimeline) {
    if (timeline) {
      timeline.seek(time)
    }
  }

  stop(timeline = this.currentTimeline) {
    if (timeline) {
      timeline.pause(0)
      this.isPlaying = false
    }
  }

  stopAll() {
    this.timelines.forEach(timeline => timeline.pause(0))
    this.isPlaying = false
  }

  dispose() {
    this.stopAll()
    this.timelines.forEach(timeline => timeline.kill())
    this.timelines = []
    this.currentTimeline = null
    this.customEases.clear()
  }
}

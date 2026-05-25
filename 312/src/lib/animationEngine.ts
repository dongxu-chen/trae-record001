import { gsap } from 'gsap'
import { Project, Layer, SvgElement } from '@/types'

export class AnimationEngine {
  private tl: gsap.core.Timeline | null = null
  private elements: Map<string, any> = new Map()
  private onUpdate: ((time: number) => void) | null = null

  setOnUpdate(callback: (time: number) => void) {
    this.onUpdate = callback
  }

  buildTimeline(project: Project, getElementState: (id: string) => any) {
    if (this.tl) {
      this.tl.kill()
    }

    this.tl = gsap.timeline({
      paused: true,
      duration: project.duration / 1000,
      onUpdate: () => {
        if (this.onUpdate && this.tl) {
          this.onUpdate(this.tl.time() * 1000)
        }
      },
    })

    project.layers.forEach((layer) => {
      const element = project.elements[layer.elementId]
      if (!element) return

      layer.tracks.forEach((track) => {
        if (track.keyframes.length < 2) return

        const sortedKeyframes = [...track.keyframes].sort((a, b) => a.time - b.time)

        sortedKeyframes.forEach((kf, i) => {
          if (i === 0) return
          const prevKf = sortedKeyframes[i - 1]
          const duration = (kf.time - prevKf.time) / 1000
          const startTime = prevKf.time / 1000

          const target = getElementState(layer.elementId)
          if (!target) return

          const ease = this.convertEasing(kf.easing)

          this.tl!.to(
            target,
            {
              [this.mapProperty(track.property)]: this.getValue(kf.value),
              duration,
              ease,
            },
            startTime
          )
        })
      })
    })

    return this.tl
  }

  private mapProperty(prop: string): string {
    const map: Record<string, string> = {
      position: 'x',
      rotation: 'rotation',
      scale: 'scale',
      opacity: 'opacity',
    }
    return map[prop] || prop
  }

  private getValue(value: any): any {
    if (typeof value === 'object' && 'x' in value) {
      return value.x
    }
    return value
  }

  private convertEasing(easing: string): string {
    const map: Record<string, string> = {
      linear: 'none',
      easeIn: 'power1.in',
      easeOut: 'power1.out',
      easeInOut: 'power1.inOut',
      easeInQuad: 'power2.in',
      easeOutQuad: 'power2.out',
      easeInOutQuad: 'power2.inOut',
      easeInCubic: 'power3.in',
      easeOutCubic: 'power3.out',
      easeInOutCubic: 'power3.inOut',
      easeInSine: 'sine.in',
      easeOutSine: 'sine.out',
      easeInOutSine: 'sine.inOut',
      easeOutBounce: 'bounce.out',
      elastic: 'elastic.out(1, 0.5)',
      bounce: 'bounce.out',
    }
    return map[easing] || 'power1.inOut'
  }

  play() {
    this.tl?.play()
  }

  pause() {
    this.tl?.pause()
  }

  seek(time: number) {
    if (this.tl) {
      this.tl.seek(time / 1000)
    }
  }

  stop() {
    if (this.tl) {
      this.tl.pause(0)
    }
  }

  getTime(): number {
    return this.tl ? this.tl.time() * 1000 : 0
  }

  isPlaying(): boolean {
    return this.tl ? this.tl.isActive() : false
  }

  destroy() {
    if (this.tl) {
      this.tl.kill()
      this.tl = null
    }
    this.elements.clear()
  }
}

export const animationEngine = new AnimationEngine()

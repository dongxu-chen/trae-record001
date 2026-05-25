import { Project, Layer, Keyframe, EasingType, ExportOptions } from '@/types'

interface LottieKeyframe {
  t: number
  s: number[]
  e?: number[]
  o?: { i: { x: number; y: number }; o: { x: number; y: number } }
}

interface LottieProperty {
  a: number
  k: LottieKeyframe[] | number[]
}

interface LottieTransform {
  a: LottieProperty
  p: LottieProperty
  r: LottieProperty
  s: LottieProperty
  o: LottieProperty
}

interface LottieLayer {
  ddd: number
  ind: number
  ty: number
  nm: string
  sr: number
  ks: LottieTransform
  ip: number
  op: number
  st: number
  shapes?: any[]
}

interface LottieAsset {
  id: string
  layers: LottieLayer[]
}

interface LottieAnimation {
  v: string
  fr: number
  ip: number
  op: number
  w: number
  h: number
  nm: string
  ddd: number
  assets: LottieAsset[]
  layers: LottieLayer[]
}

const easingMap: Record<EasingType, { i: { x: number; y: number }; o: { x: number; y: number } }> = {
  linear: { i: { x: 0, y: 0 }, o: { x: 0, y: 0 } },
  easeIn: { i: { x: 0.42, y: 0 }, o: { x: 0, y: 0 } },
  easeOut: { i: { x: 0, y: 0 }, o: { x: 0.58, y: 1 } },
  easeInOut: { i: { x: 0.42, y: 0 }, o: { x: 0.58, y: 1 } },
  easeInQuad: { i: { x: 0.55, y: 0.085 }, o: { x: 0, y: 0 } },
  easeOutQuad: { i: { x: 0, y: 0 }, o: { x: 0.25, y: 0.46 } },
  easeInOutQuad: { i: { x: 0.455, y: 0.03 }, o: { x: 0.515, y: 0.955 } },
  easeInCubic: { i: { x: 0.55, y: 0.055 }, o: { x: 0, y: 0 } },
  easeOutCubic: { i: { x: 0, y: 0 }, o: { x: 0.32, y: 0.975 } },
  easeInOutCubic: { i: { x: 0.645, y: 0.045 }, o: { x: 0.355, y: 1 } },
  easeInSine: { i: { x: 0.47, y: 0 }, o: { x: 0.745, y: 0.715 } },
  easeOutSine: { i: { x: 0.39, y: 0.575 }, o: { x: 0.565, y: 1 } },
  easeInOutSine: { i: { x: 0.445, y: 0.05 }, o: { x: 0.55, y: 0.95 } },
  easeOutBounce: { i: { x: 0.68, y: 0.1 }, o: { x: 0.32, y: 0.9 } },
  elastic: { i: { x: 0.68, y: -0.55 }, o: { x: 0.32, y: 1.55 } },
  bounce: { i: { x: 0.68, y: 0.1 }, o: { x: 0.32, y: 0.9 } },
}

const defaultExportOptions: ExportOptions = {
  compress: false,
  keyframeTolerance: 0.01,
  optimizePaths: true,
  minify: false,
}

function mergeSimilarKeyframes(keyframes: Keyframe[], tolerance: number): Keyframe[] {
  if (keyframes.length <= 2) return keyframes

  const sorted = [...keyframes].sort((a, b) => a.time - b.time)
  const result: Keyframe[] = [sorted[0]]

  for (let i = 1; i < sorted.length - 1; i++) {
    const prev = result[result.length - 1]
    const curr = sorted[i]
    const next = sorted[i + 1]

    if (!canRemoveKeyframe(prev, curr, next, tolerance)) {
      result.push(curr)
    }
  }

  result.push(sorted[sorted.length - 1])
  return result
}

function canRemoveKeyframe(
  prev: Keyframe,
  curr: Keyframe,
  next: Keyframe,
  tolerance: number
): boolean {
  if (prev.easing !== curr.easing || curr.easing !== next.easing) {
    return false
  }

  const prevVal = getValueAsNumber(prev.value)
  const currVal = getValueAsNumber(curr.value)
  const nextVal = getValueAsNumber(next.value)

  if (prevVal.length !== currVal.length || currVal.length !== nextVal.length) {
    return false
  }

  const t = (curr.time - prev.time) / (next.time - prev.time)

  for (let i = 0; i < prevVal.length; i++) {
    const interpolated = prevVal[i] + t * (nextVal[i] - prevVal[i])
    const error = Math.abs(currVal[i] - interpolated)
    const range = Math.abs(nextVal[i] - prevVal[i])

    if (range > 0 && error / range > tolerance) {
      return false
    }
  }

  return true
}

function getValueAsNumber(value: number | { x: number; y: number } | string): number[] {
  if (typeof value === 'number') {
    return [value]
  }
  if (typeof value === 'object' && 'x' in value) {
    return [value.x, value.y]
  }
  return [0, 0]
}

function roundValue(value: number, precision: number = 3): number {
  const factor = Math.pow(10, precision)
  return Math.round(value * factor) / factor
}

function convertKeyframes(
  keyframes: Keyframe[],
  defaultValue: number[],
  frameRate: number,
  options: ExportOptions
): LottieProperty {
  const processedKeyframes = options.compress
    ? mergeSimilarKeyframes(keyframes, options.keyframeTolerance)
    : keyframes

  if (processedKeyframes.length === 0) {
    return { a: 0, k: defaultValue.map((v) => roundValue(v)) }
  }

  if (processedKeyframes.length === 1) {
    const val = processedKeyframes[0].value
    const arr = Array.isArray(val) ? val : typeof val === 'number' ? [val] : [0, 0]
    return { a: 0, k: arr.map((v) => roundValue(v)) }
  }

  const lottieKeyframes: LottieKeyframe[] = processedKeyframes.map((kf, i) => {
    const val = kf.value
    const s = Array.isArray(val) ? val : typeof val === 'number' ? [val] : [0, 0]
    const result: LottieKeyframe = {
      t: roundValue((kf.time / 1000) * frameRate, 2),
      s: s.map((v) => roundValue(v)),
    }

    if (i < processedKeyframes.length - 1) {
      const nextVal = processedKeyframes[i + 1].value
      result.e = (
        Array.isArray(nextVal) ? nextVal : typeof nextVal === 'number' ? [nextVal] : [0, 0]
      ).map((v) => roundValue(v))
      result.o = easingMap[kf.easing]
    }

    return result
  })

  return { a: 1, k: lottieKeyframes }
}

function getTrackValue(
  tracks: any[],
  property: string,
  defaultValue: number[],
  frameRate: number,
  options: ExportOptions
): LottieProperty {
  const track = tracks.find((t: any) => t.property === property)
  return convertKeyframes(track?.keyframes || [], defaultValue, frameRate, options)
}

export function exportToLottie(project: Project, options: Partial<ExportOptions> = {}): LottieAnimation {
  const opts = { ...defaultExportOptions, ...options }
  const frameRate = project.framerate
  const durationFrames = (project.duration / 1000) * frameRate

  const lottieLayers: LottieLayer[] = project.layers
    .map((layer, index) => {
      const element = project.elements[layer.elementId]
      if (!element) return null as any

      const anchor = getTrackValue(
        layer.tracks,
        'anchor',
        [element.transform.anchor.x, element.transform.anchor.y],
        frameRate,
        opts
      )
      const position = getTrackValue(
        layer.tracks,
        'position',
        [element.transform.position.x, element.transform.position.y],
        frameRate,
        opts
      )
      const rotation = getTrackValue(
        layer.tracks,
        'rotation',
        [element.transform.rotation],
        frameRate,
        opts
      )
      const scale = getTrackValue(
        layer.tracks,
        'scale',
        [element.transform.scale.x * 100, element.transform.scale.y * 100],
        frameRate,
        opts
      )
      const opacity = getTrackValue(
        layer.tracks,
        'opacity',
        [element.transform.opacity * 100],
        frameRate,
        opts
      )

      const shapes = convertToLottieShapes(element, frameRate, layer.tracks, opts)

      return {
        ddd: 0,
        ind: index + 1,
        ty: 4,
        nm: layer.name,
        sr: 1,
        ks: {
          a: anchor,
          p: position,
          r: rotation,
          s: scale,
          o: opacity,
        },
        ip: 0,
        op: roundValue(durationFrames, 2),
        st: 0,
        shapes,
      }
    })
    .filter(Boolean)

  return {
    v: '5.7.4',
    fr: roundValue(frameRate, 2),
    ip: 0,
    op: roundValue(durationFrames, 2),
    w: project.width,
    h: project.height,
    nm: project.name,
    ddd: 0,
    assets: [],
    layers: lottieLayers,
  }
}

function convertToLottieShapes(
  element: any,
  frameRate: number,
  tracks: any[],
  options: ExportOptions
): any[] {
  const shapes: any[] = []

  if (element.type === 'path') {
    shapes.push({
      ty: 'sh',
      nm: 'Path 1',
      d: convertPathToLottie(element.attributes.d, options),
    })
  } else if (element.type === 'rect') {
    shapes.push({
      ty: 'rc',
      nm: 'Rectangle 1',
      p: {
        a: 0,
        k: [
          roundValue(parseFloat(element.attributes.x || '0')),
          roundValue(parseFloat(element.attributes.y || '0')),
        ],
      },
      s: {
        a: 0,
        k: [
          roundValue(parseFloat(element.attributes.width || '100')),
          roundValue(parseFloat(element.attributes.height || '100')),
        ],
      },
      r: { a: 0, k: roundValue(parseFloat(element.attributes.rx || '0')) },
    })
  } else if (element.type === 'circle') {
    shapes.push({
      ty: 'el',
      nm: 'Ellipse 1',
      p: {
        a: 0,
        k: [
          roundValue(parseFloat(element.attributes.cx || '0')),
          roundValue(parseFloat(element.attributes.cy || '0')),
        ],
      },
      s: {
        a: 0,
        k: [
          roundValue(parseFloat(element.attributes.r || '50') * 2),
          roundValue(parseFloat(element.attributes.r || '50') * 2),
        ],
      },
    })
  }

  if (element.attributes.fill) {
    shapes.push({
      ty: 'fl',
      nm: 'Fill 1',
      c: { a: 0, k: parseColor(element.attributes.fill) },
      o: { a: 0, k: 100 },
      r: 1,
    })
  }

  if (element.attributes.stroke) {
    shapes.push({
      ty: 'st',
      nm: 'Stroke 1',
      c: { a: 0, k: parseColor(element.attributes.stroke) },
      o: { a: 0, k: 100 },
      w: { a: 0, k: roundValue(parseFloat(element.attributes['stroke-width'] || '1')) },
      lc: 2,
      lj: 2,
    })
  }

  return shapes
}

function convertPathToLottie(d: string, options: ExportOptions): any {
  if (options.optimizePaths && options.compress) {
    d = optimizePathData(d)
  }

  return {
    a: 0,
    k: {
      i: [[0, 0]],
      o: [[0, 0]],
      v: [[0, 0]],
      c: false,
    },
  }
}

function optimizePathData(d: string): string {
  return d
    .replace(/\s+/g, ' ')
    .replace(/(\d)\.0+(?=\D|$)/g, '$1')
    .replace(/(\d)\.(\d*?)0+(?=\D|$)/g, '$1.$2')
    .replace(/0\./g, '.')
    .trim()
}

function parseColor(color: string): number[] {
  if (color.startsWith('#')) {
    const hex = color.slice(1)
    const r = roundValue(parseInt(hex.substring(0, 2), 16) / 255, 3)
    const g = roundValue(parseInt(hex.substring(2, 4), 16) / 255, 3)
    const b = roundValue(parseInt(hex.substring(4, 6), 16) / 255, 3)
    return [r, g, b, 1]
  }
  return [0, 0, 0, 1]
}

export function getExportStats(
  project: Project,
  options: Partial<ExportOptions> = {}
): {
  originalSize: number
  compressedSize: number
  keyframesReduced: number
  compressionRatio: number
} {
  const original = exportToLottie(project, { compress: false })
  const compressed = exportToLottie(project, { compress: true, ...options })

  const originalStr = JSON.stringify(original)
  const compressedStr = JSON.stringify(compressed)

  let originalKeyframes = 0
  let compressedKeyframes = 0

  project.layers.forEach((layer) => {
    layer.tracks.forEach((track) => {
      originalKeyframes += track.keyframes.length
    })
  })

  compressed.layers.forEach((layer: any) => {
    ;['a', 'p', 'r', 's', 'o'].forEach((prop) => {
      if (layer.ks[prop].a === 1) {
        compressedKeyframes += layer.ks[prop].k.length
      }
    })
  })

  return {
    originalSize: originalStr.length,
    compressedSize: compressedStr.length,
    keyframesReduced: originalKeyframes - compressedKeyframes,
    compressionRatio: 1 - compressedStr.length / originalStr.length,
  }
}

export function downloadLottie(
  project: Project,
  options: Partial<ExportOptions> = {}
): void {
  const lottie = exportToLottie(project, options)
  const jsonStr = options.minify ? JSON.stringify(lottie) : JSON.stringify(lottie, null, 2)
  const blob = new Blob([jsonStr], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = options.compress ? `${project.name}-compressed.json` : `${project.name}.json`
  a.click()
  URL.revokeObjectURL(url)
}

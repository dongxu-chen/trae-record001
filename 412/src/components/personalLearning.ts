import type { Stroke, Point } from './DrawingCanvas'

export interface UserSample {
  char: string
  strokes: Stroke[]
  bbox: { x: number; y: number; w: number; h: number }
  pixels: Uint8Array
  timestamp: number
}

const STORAGE_KEY = 'hr_user_templates_v1'
const IMG_SIZE = 40

export function computeBBox(strokes: Stroke[]): { x: number; y: number; w: number; h: number } {
  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity
  for (const s of strokes) {
    for (const p of s) {
      if (p.x < minX) minX = p.x
      if (p.y < minY) minY = p.y
      if (p.x > maxX) maxX = p.x
      if (p.y > maxY) maxY = p.y
    }
  }
  return { x: minX, y: minY, w: maxX - minX, h: maxY - minY }
}

export function rasterizeStrokesToUint8(
  strokes: Stroke[],
  size: number,
  bbox: { x: number; y: number; w: number; h: number },
): Uint8Array {
  const canvas = new OffscreenCanvas(size, size)
  const ctx = canvas.getContext('2d')!
  ctx.fillStyle = '#000'
  ctx.fillRect(0, 0, size, size)
  const pad = 4
  const scale = Math.min((size - pad * 2) / Math.max(bbox.w, 1), (size - pad * 2) / Math.max(bbox.h, 1))
  const offX = pad + (size - pad * 2 - bbox.w * scale) / 2 - bbox.x * scale
  const offY = pad + (size - pad * 2 - bbox.h * scale) / 2 - bbox.y * scale
  ctx.strokeStyle = '#fff'
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  ctx.lineWidth = Math.max(2.5, 3.5 * scale)
  for (const stroke of strokes) {
    if (stroke.length === 0) continue
    ctx.beginPath()
    ctx.moveTo(stroke[0].x * scale + offX, stroke[0].y * scale + offY)
    for (let i = 1; i < stroke.length; i++) {
      ctx.lineTo(stroke[i].x * scale + offX, stroke[i].y * scale + offY)
    }
    ctx.stroke()
  }
  const img = ctx.getImageData(0, 0, size, size)
  const data = new Uint8Array(size * size)
  for (let i = 0; i < size * size; i++) {
    data[i] = img.data[i * 4]
  }
  return data
}

export function serializeUserSample(sample: UserSample): string {
  const strokesCompact = sample.strokes.map((s) => s.map((p) => [p.x, p.y, p.p, p.t]))
  return JSON.stringify({
    c: sample.char,
    s: strokesCompact,
    b: sample.bbox,
    p: Array.from(sample.pixels),
    t: sample.timestamp,
  })
}

export function deserializeUserSample(raw: string): UserSample | null {
  try {
    const obj = JSON.parse(raw)
    return {
      char: obj.c,
      strokes: obj.s.map((s: number[][]) =>
        s.map((p) => ({ x: p[0], y: p[1], p: p[2], t: p[3] } as Point)),
      ),
      bbox: obj.b,
      pixels: new Uint8Array(obj.p),
      timestamp: obj.t,
    }
  } catch {
    return null
  }
}

export function loadUserSamples(): Map<string, UserSample> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return new Map()
    const arr = JSON.parse(raw) as string[]
    const map = new Map<string, UserSample>()
    for (const s of arr) {
      const sample = deserializeUserSample(s)
      if (sample) map.set(sample.char, sample)
    }
    return map
  } catch {
    return new Map()
  }
}

export function saveUserSamples(samples: Map<string, UserSample>) {
  try {
    const arr = Array.from(samples.values()).map(serializeUserSample)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(arr))
  } catch {
    /* quota */
  }
}

export function addUserSample(
  samples: Map<string, UserSample>,
  char: string,
  strokes: Stroke[],
): UserSample {
  const bbox = computeBBox(strokes)
  const pixels = rasterizeStrokesToUint8(strokes, IMG_SIZE, bbox)
  const sample: UserSample = { char, strokes, bbox, pixels, timestamp: Date.now() }
  samples.set(char, sample)
  saveUserSamples(samples)
  return sample
}

export function clearUserSamples() {
  localStorage.removeItem(STORAGE_KEY)
}

export function computeNormUint8(arr: Uint8Array): number {
  let sum = 0
  for (let i = 0; i < arr.length; i++) sum += arr[i] * arr[i]
  return Math.sqrt(sum)
}

export function dotUint8(a: Uint8Array, b: Uint8Array): number {
  let sum = 0
  for (let i = 0; i < a.length; i++) sum += a[i] * b[i]
  return sum
}

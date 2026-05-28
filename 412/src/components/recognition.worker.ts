/// <reference lib="webworker" />
import * as tf from '@tensorflow/tfjs'
import type { Segment, Candidate, WorkerRequest, WorkerResponse, Stroke } from './types'

const CHARS_DIGITS = '0123456789'.split('')
const CHARS_UPPER = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('')
const CHARS_LOWER = 'abcdefghijklmnopqrstuvwxyz'.split('')
const CHARS_CN =
  '的一是了我不人在他有这个上们来到时大地为子中你说生国年着就那和要她出也得里后自以会家可下而过天去能对小多然于心学么之都好看起发当没成只如事把还用第样道想作种开美总从无情己面最女但现前些所同日手又行意动方期它头经长儿回位分爱老因很给名法间斯知世什两次使身者被高已亲其进此话常与活正感'.split('')

const CHAR_SET = [...CHARS_DIGITS, ...CHARS_UPPER, ...CHARS_LOWER, ...CHARS_CN]

const IMG_SIZE = 40
const LOW_CONF_THRESHOLD = 0.28
const USER_TEMPLATE_WEIGHT = 4.0

interface QuantizedTemplate {
  char: string
  pixels: Uint8Array
  norm: number
  tensor: tf.Tensor2D | null
  isUser: boolean
  weight: number
}

let templates: QuantizedTemplate[] = []
let ready = false

function computeBBox(strokes: Stroke[]) {
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

function rasterizeStrokesUint8(
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

function renderCharTemplateUint8(char: string, size: number, font: string): Uint8Array {
  const canvas = new OffscreenCanvas(size, size)
  const ctx = canvas.getContext('2d')!
  ctx.fillStyle = '#000'
  ctx.fillRect(0, 0, size, size)
  ctx.fillStyle = '#fff'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.font = font
  ctx.fillText(char, size / 2, size / 2 + 1)
  const img = ctx.getImageData(0, 0, size, size)
  const data = new Uint8Array(size * size)
  for (let i = 0; i < size * size; i++) {
    data[i] = img.data[i * 4]
  }
  return data
}

const FONTS = [
  `bold ${IMG_SIZE - 8}px "Microsoft YaHei", "PingFang SC", sans-serif`,
  `${IMG_SIZE - 8}px "SimSun", "Songti SC", serif`,
  `bold ${IMG_SIZE - 8}px Arial, sans-serif`,
  `bold italic ${IMG_SIZE - 8}px Arial, sans-serif`,
]

function computeNormFromUint8(pixels: Uint8Array): number {
  let sum = 0
  for (let i = 0; i < pixels.length; i++) {
    const v = pixels[i]
    sum += v * v
  }
  return Math.sqrt(sum)
}

async function buildQuantizedTemplates(): Promise<QuantizedTemplate[]> {
  const tpls: QuantizedTemplate[] = []
  const total = CHAR_SET.length * FONTS.length
  let done = 0
  for (const char of CHAR_SET) {
    for (const font of FONTS) {
      const pixels = renderCharTemplateUint8(char, IMG_SIZE, font)
      const norm = computeNormFromUint8(pixels)
      tpls.push({ char, pixels, norm, tensor: null, isUser: false, weight: 1 })
      done++
      if (done % 40 === 0) {
        post({ type: 'warmupProgress', percent: Math.round((done / total) * 60) } as WorkerResponse)
      }
    }
  }
  return tpls
}

function ensureTplTensor(tpl: QuantizedTemplate) {
  if (!tpl.tensor) {
    const floatBuf = new Float32Array(tpl.pixels.length)
    for (let i = 0; i < tpl.pixels.length; i++) floatBuf[i] = tpl.pixels[i] / 255
    tpl.tensor = tf.tensor2d(floatBuf, [IMG_SIZE, IMG_SIZE])
  }
}

function ensureAllTensors() {
  for (const tpl of templates) ensureTplTensor(tpl)
}

function addUserTemplate(char: string, pixels: Uint8Array, norm: number) {
  const idx = templates.findIndex((t) => t.isUser && t.char === char)
  if (idx >= 0) {
    const old = templates[idx]
    if (old.tensor) old.tensor.dispose()
    templates.splice(idx, 1)
  }
  const tpl: QuantizedTemplate = {
    char,
    pixels,
    norm,
    tensor: null,
    isUser: true,
    weight: USER_TEMPLATE_WEIGHT,
  }
  ensureTplTensor(tpl)
  templates.unshift(tpl)
  post({ type: 'userTemplateAdded', char } as WorkerResponse)
}

function removeUserTemplate(char: string) {
  const idx = templates.findIndex((t) => t.isUser && t.char === char)
  if (idx >= 0) {
    const old = templates[idx]
    if (old.tensor) old.tensor.dispose()
    templates.splice(idx, 1)
  }
}

function clearUserTemplates() {
  templates = templates.filter((t) => {
    if (t.isUser) {
      if (t.tensor) t.tensor.dispose()
      return false
    }
    return true
  })
}

function segmentStrokes(strokes: Stroke[]): Segment[] {
  if (strokes.length === 0) return []
  const bboxes = strokes.map((s) => {
    let minX = Infinity
    let minY = Infinity
    let maxX = -Infinity
    let maxY = -Infinity
    for (const p of s) {
      if (p.x < minX) minX = p.x
      if (p.y < minY) minY = p.y
      if (p.x > maxX) maxX = p.x
      if (p.y > maxY) maxY = p.y
    }
    return { x: minX, y: minY, w: maxX - minX, h: maxY - minY, cx: (minX + maxX) / 2 }
  })
  const avgH = bboxes.reduce((a, b) => a + Math.max(b.h, 1), 0) / bboxes.length
  const gapThreshold = avgH * 1.2

  const groups: Stroke[][] = []
  let current: Stroke[] = [strokes[0]]
  let currentMaxCx = bboxes[0].cx
  for (let i = 1; i < strokes.length; i++) {
    const prev = bboxes[i - 1]
    const cur = bboxes[i]
    const gap = cur.cx - Math.max(prev.cx, currentMaxCx)
    const prevRight = prev.x + prev.w
    const curLeft = cur.x
    const horizontalGap = curLeft - prevRight
    if (horizontalGap > gapThreshold || gap > gapThreshold * 1.2) {
      groups.push(current)
      current = [strokes[i]]
      currentMaxCx = cur.cx
    } else {
      current.push(strokes[i])
      currentMaxCx = Math.max(currentMaxCx, cur.cx)
    }
  }
  groups.push(current)

  return groups.map((group) => {
    let minX = Infinity
    let minY = Infinity
    let maxX = -Infinity
    let maxY = -Infinity
    for (const s of group) {
      for (const p of s) {
        if (p.x < minX) minX = p.x
        if (p.y < minY) minY = p.y
        if (p.x > maxX) maxX = p.x
        if (p.y > maxY) maxY = p.y
      }
    }
    return {
      strokes: group,
      bbox: { x: minX, y: minY, w: maxX - minX, h: maxY - minY },
    }
  })
}

function mergeSegments(a: Segment, b: Segment): Segment {
  return {
    strokes: [...a.strokes, ...b.strokes],
    bbox: {
      x: Math.min(a.bbox.x, b.bbox.x),
      y: Math.min(a.bbox.y, b.bbox.y),
      w: Math.max(a.bbox.x + a.bbox.w, b.bbox.x + b.bbox.w) - Math.min(a.bbox.x, b.bbox.x),
      h: Math.max(a.bbox.y + a.bbox.h, b.bbox.y + b.bbox.h) - Math.min(a.bbox.y, b.bbox.y),
    },
  }
}

function recognizePixels(
  inputPixels: Uint8Array,
  topK: number,
): Candidate[] {
  const inputNorm = computeNormFromUint8(inputPixels)
  if (inputNorm < 1) return []

  let inputTensor: tf.Tensor2D | null = null
  try {
    const floatBuf = new Float32Array(inputPixels.length)
    for (let i = 0; i < inputPixels.length; i++) floatBuf[i] = inputPixels[i] / 255
    inputTensor = tf.tensor2d(floatBuf, [IMG_SIZE, IMG_SIZE])

    const scores = new Map<string, number>()
    const weights = new Map<string, number>()

    for (const tpl of templates) {
      if (!tpl.tensor) continue
      const prod = tf.mul(inputTensor, tpl.tensor)
      const dot = tf.sum(prod).dataSync()[0] as number
      prod.dispose()
      const sim = tpl.norm > 0 ? dot / (inputNorm / 255 * tpl.norm / 255) : 0
      const s = Number.isFinite(sim) ? sim : 0
      const weighted = s * tpl.weight
      scores.set(tpl.char, (scores.get(tpl.char) ?? 0) + weighted)
      weights.set(tpl.char, (weights.get(tpl.char) ?? 0) + tpl.weight)
    }

    const agg: Candidate[] = []
    for (const [char, sum] of scores) {
      const w = weights.get(char) ?? 1
      agg.push({ char, score: sum / w })
    }
    agg.sort((a, b) => b.score - a.score)
    return agg.slice(0, topK)
  } finally {
    if (inputTensor) inputTensor.dispose()
  }
}

function recognizeSegment(segment: Segment, topK: number): Candidate[] {
  const bbox = computeBBox(segment.strokes)
  if (bbox.w < 1 || bbox.h < 1) return []
  const pixels = rasterizeStrokesUint8(segment.strokes, IMG_SIZE, bbox)
  return recognizePixels(pixels, topK)
}

function warmup() {
  const dummyBBox = { x: 0, y: 0, w: IMG_SIZE, h: IMG_SIZE }
  const dummyStroke: Stroke = [
    { x: 10, y: 20, p: 0.5, t: 0 },
    { x: 30, y: 20, p: 0.5, t: 1 },
    { x: 30, y: 35, p: 0.5, t: 2 },
  ]
  const dummyPixels = rasterizeStrokesUint8([dummyStroke], IMG_SIZE, dummyBBox)
  recognizePixels(dummyPixels, 3)
  post({ type: 'warmupProgress', percent: 100 } as WorkerResponse)
}

async function handleInit() {
  try {
    await tf.ready()
    tf.setBackend('webgl')
    post({ type: 'warmupProgress', percent: 5 } as WorkerResponse)
    templates = await buildQuantizedTemplates()
    post({ type: 'warmupProgress', percent: 70 } as WorkerResponse)
    ensureAllTensors()
    warmup()
    ready = true
    post({ type: 'ready' } as WorkerResponse)
  } catch (err) {
    post({ type: 'error', message: String(err) } as WorkerResponse)
  }
}

async function handleRecognize(strokes: Stroke[], topK: number) {
  if (!ready) {
    post({ type: 'error', message: 'Model not ready' } as WorkerResponse)
    return
  }
  try {
    const segments = segmentStrokes(strokes)
    if (segments.length === 0) {
      post({ type: 'recognized', results: [], segments: [] } as WorkerResponse)
      return
    }

    const results: Candidate[][] = segments.map((seg) => recognizeSegment(seg, topK))

    const needsResegment = results.some(
      (r) => (r[0]?.score ?? 0) < LOW_CONF_THRESHOLD,
    )

    if (needsResegment && segments.length > 1) {
      const mergedSegs: Segment[] = []
      let i = 0
      while (i < segments.length) {
        const seg = segments[i]
        const res = results[i]
        const topScore = res[0]?.score ?? 0
        if (topScore < LOW_CONF_THRESHOLD && i + 1 < segments.length) {
          const nextScore = results[i + 1][0]?.score ?? 0
          if (nextScore < LOW_CONF_THRESHOLD + 0.15) {
            mergedSegs.push(mergeSegments(seg, segments[i + 1]))
            i += 2
            continue
          }
        }
        mergedSegs.push(seg)
        i++
      }
      if (mergedSegs.length !== segments.length) {
        const newResults: Candidate[][] = mergedSegs.map((seg) => recognizeSegment(seg, topK))
        post({ type: 'recognized', results: newResults, segments: mergedSegs } as WorkerResponse)
        return
      }
    }

    post({ type: 'recognized', results, segments } as WorkerResponse)
  } catch (err) {
    post({ type: 'error', message: String(err) } as WorkerResponse)
  }
}

function post(msg: WorkerResponse) {
  self.postMessage(msg)
}

self.addEventListener('message', async (ev: MessageEvent<WorkerRequest>) => {
  const req = ev.data
  if (!req || !req.type) return
  if (req.type === 'init') {
    await handleInit()
  } else if (req.type === 'recognize') {
    await handleRecognize(req.strokes, req.topK)
  } else if (req.type === 'addUserTemplate') {
    addUserTemplate(req.char, req.pixels, req.norm)
  } else if (req.type === 'removeUserTemplate') {
    removeUserTemplate(req.char)
  } else if (req.type === 'clearUserTemplates') {
    clearUserTemplates()
  }
})

export {}

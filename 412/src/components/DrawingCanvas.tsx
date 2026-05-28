import { useCallback, useEffect, useImperativeHandle, useRef, forwardRef } from 'react'

export type Point = { x: number; y: number; p: number; t: number }
export type Stroke = Point[]

export interface DrawingCanvasHandle {
  clear: () => void
  getStrokes: () => Stroke[]
  getCurrentStroke: () => Stroke | null
}

interface Props {
  width?: number
  height?: number
  penColor?: string
  penWidth?: number
  onStrokeStart?: () => void
  onStrokeMove?: (stroke: Stroke) => void
  onStrokeEnd?: (stroke: Stroke, allStrokes: Stroke[]) => void
}

const CORNER_ANGLE_THRESHOLD = 0.55
const CORNER_MIN_DIST = 4

function detectCorners(points: Point[]): boolean[] {
  const n = points.length
  const corners = new Array<boolean>(n).fill(false)
  if (n < 3) return corners
  corners[0] = true
  corners[n - 1] = true
  for (let i = 1; i < n - 1; i++) {
    const p0 = points[i - 1]
    const p1 = points[i]
    const p2 = points[i + 1]
    const dx1 = p1.x - p0.x
    const dy1 = p1.y - p0.y
    const dx2 = p2.x - p1.x
    const dy2 = p2.y - p1.y
    const len1 = Math.hypot(dx1, dy1)
    const len2 = Math.hypot(dx2, dy2)
    if (len1 < CORNER_MIN_DIST || len2 < CORNER_MIN_DIST) continue
    const dot = dx1 * dx2 + dy1 * dy2
    const cosAngle = dot / (len1 * len2)
    const angle = Math.acos(Math.max(-1, Math.min(1, cosAngle)))
    if (angle > CORNER_ANGLE_THRESHOLD) {
      corners[i] = true
    }
  }
  for (let i = 1; i < n - 1; i++) {
    if (!corners[i]) continue
    for (let j = i - 1; j >= 0 && j > i - 3; j--) {
      if (corners[j]) break
      const d = Math.hypot(points[i].x - points[j].x, points[i].y - points[j].y)
      if (d < 6) corners[j] = false
    }
    for (let j = i + 1; j < n && j < i + 3; j++) {
      if (corners[j]) break
      const d = Math.hypot(points[i].x - points[j].x, points[i].y - points[j].y)
      if (d < 6) corners[j] = false
    }
  }
  return corners
}

function smoothSegmentCatmullRom(points: Point[]): Point[] {
  if (points.length < 3) return points.slice()
  const out: Point[] = [points[0]]
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i - 1] ?? points[i]
    const p1 = points[i]
    const p2 = points[i + 1]
    const p3 = points[i + 2] ?? p2
    const steps = 4
    for (let s = 1; s <= steps; s++) {
      const t = s / steps
      const t2 = t * t
      const t3 = t2 * t
      const x =
        0.5 *
        (2 * p1.x +
          (-p0.x + p2.x) * t +
          (2 * p0.x - 5 * p1.x + 4 * p2.x - p3.x) * t2 +
          (-p0.x + 3 * p1.x - 3 * p2.x + p3.x) * t3)
      const y =
        0.5 *
        (2 * p1.y +
          (-p0.y + p2.y) * t +
          (2 * p0.y - 5 * p1.y + 4 * p2.y - p3.y) * t2 +
          (-p0.y + 3 * p1.y - 3 * p2.y + p3.y) * t3)
      out.push({ x, y, p: (p1.p + p2.p) / 2, t: p1.t + (p2.t - p1.t) * t })
    }
  }
  out.push(points[points.length - 1])
  return out
}

function smoothStrokeWithCornerPreserve(points: Point[]): Point[] {
  if (points.length < 3) return points.slice()
  const corners = detectCorners(points)
  const result: Point[] = []
  let segStart = 0
  for (let i = 1; i < points.length; i++) {
    if (corners[i]) {
      const seg = points.slice(segStart, i + 1)
      const smoothed = smoothSegmentCatmullRom(seg)
      if (result.length > 0 && smoothed.length > 0) {
        result.pop()
      }
      for (const p of smoothed) result.push(p)
      segStart = i
    }
  }
  if (segStart < points.length - 1) {
    const seg = points.slice(segStart)
    const smoothed = smoothSegmentCatmullRom(seg)
    if (result.length > 0 && smoothed.length > 0) {
      result.pop()
    }
    for (const p of smoothed) result.push(p)
  }
  return result
}

function drawStrokePath(ctx: CanvasRenderingContext2D, stroke: Stroke) {
  if (stroke.length === 0) return
  ctx.beginPath()
  ctx.moveTo(stroke[0].x, stroke[0].y)
  for (let i = 1; i < stroke.length - 1; i++) {
    const midX = (stroke[i].x + stroke[i + 1].x) / 2
    const midY = (stroke[i].y + stroke[i + 1].y) / 2
    ctx.quadraticCurveTo(stroke[i].x, stroke[i].y, midX, midY)
  }
  const last = stroke[stroke.length - 1]
  ctx.lineTo(last.x, last.y)
}

export const DrawingCanvas = forwardRef<DrawingCanvasHandle, Props>(function DrawingCanvas(
  {
    width = 640,
    height = 240,
    penColor = '#1a1a1a',
    penWidth = 6,
    onStrokeStart,
    onStrokeMove,
    onStrokeEnd,
  },
  ref,
) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const strokesRef = useRef<Stroke[]>([])
  const currentRef = useRef<Stroke | null>(null)
  const drawingRef = useRef(false)

  const redraw = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const dpr = window.devicePixelRatio || 1
    ctx.setTransform(1, 0, 0, 1, 0, 0)
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.scale(dpr, dpr)
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    ctx.strokeStyle = penColor
    const all = currentRef.current
      ? [...strokesRef.current, currentRef.current]
      : strokesRef.current
    for (const stroke of all) {
      const smoothed = smoothStrokeWithCornerPreserve(stroke)
      if (smoothed.length < 2) {
        ctx.fillStyle = penColor
        ctx.beginPath()
        ctx.arc(smoothed[0].x, smoothed[0].y, penWidth / 2, 0, Math.PI * 2)
        ctx.fill()
        continue
      }
      for (let i = 1; i < smoothed.length; i++) {
        const prev = smoothed[i - 1]
        const cur = smoothed[i]
        const pressure = 0.6 + 0.4 * ((prev.p + cur.p) / 2)
        ctx.lineWidth = penWidth * pressure
        ctx.beginPath()
        ctx.moveTo(prev.x, prev.y)
        ctx.lineTo(cur.x, cur.y)
        ctx.stroke()
      }
      drawStrokePath(ctx, smoothed)
    }
  }, [penColor, penWidth])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const dpr = window.devicePixelRatio || 1
    canvas.width = width * dpr
    canvas.height = height * dpr
    canvas.style.width = `${width}px`
    canvas.style.height = `${height}px`
    redraw()
  }, [width, height, redraw])

  const getPoint = (e: PointerEvent): Point => {
    const canvas = canvasRef.current!
    const rect = canvas.getBoundingClientRect()
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
      p: e.pressure && e.pressure > 0 ? e.pressure : 0.5,
      t: performance.now(),
    }
  }

  const handlePointerDown = (e: PointerEvent) => {
    e.preventDefault()
    ;(e.target as Element).setPointerCapture?.(e.pointerId)
    drawingRef.current = true
    currentRef.current = [getPoint(e)]
    onStrokeStart?.()
    redraw()
  }

  const handlePointerMove = (e: PointerEvent) => {
    if (!drawingRef.current || !currentRef.current) return
    e.preventDefault()
    const p = getPoint(e)
    const last = currentRef.current[currentRef.current.length - 1]
    const dx = p.x - last.x
    const dy = p.y - last.y
    if (dx * dx + dy * dy < 1.2) return
    currentRef.current.push(p)
    onStrokeMove?.(currentRef.current)
    redraw()
  }

  const handlePointerUp = (e: PointerEvent) => {
    if (!drawingRef.current || !currentRef.current) return
    e.preventDefault()
    drawingRef.current = false
    const finished = currentRef.current
    currentRef.current = null
    strokesRef.current.push(finished)
    onStrokeEnd?.(finished, strokesRef.current.slice())
    redraw()
  }

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const down = (e: PointerEvent) => handlePointerDown(e)
    const move = (e: PointerEvent) => handlePointerMove(e)
    const up = (e: PointerEvent) => handlePointerUp(e)
    canvas.addEventListener('pointerdown', down)
    canvas.addEventListener('pointermove', move)
    canvas.addEventListener('pointerup', up)
    canvas.addEventListener('pointercancel', up)
    canvas.addEventListener('pointerleave', up)
    return () => {
      canvas.removeEventListener('pointerdown', down)
      canvas.removeEventListener('pointermove', move)
      canvas.removeEventListener('pointerup', up)
      canvas.removeEventListener('pointercancel', up)
      canvas.removeEventListener('pointerleave', up)
    }
  })

  useImperativeHandle(ref, () => ({
    clear: () => {
      strokesRef.current = []
      currentRef.current = null
      redraw()
    },
    getStrokes: () => strokesRef.current.slice(),
    getCurrentStroke: () => currentRef.current,
  }))

  return (
    <canvas
      ref={canvasRef}
      className="drawing-canvas"
      style={{ touchAction: 'none' }}
      aria-label="Handwriting canvas"
    />
  )
})

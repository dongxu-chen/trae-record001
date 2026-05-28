import type { Stroke, Segment, Candidate } from './types'

export function computeStrokeBBoxes(strokes: Stroke[]) {
  return strokes.map((s) => {
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
}

export function segmentStrokes(strokes: Stroke[]): Segment[] {
  if (strokes.length === 0) return []
  const bboxes = computeStrokeBBoxes(strokes)
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

export function mergeSegments(a: Segment, b: Segment): Segment {
  const strokes = [...a.strokes, ...b.strokes]
  let minX = Math.min(a.bbox.x, b.bbox.x)
  let minY = Math.min(a.bbox.y, b.bbox.y)
  let maxX = Math.max(a.bbox.x + a.bbox.w, b.bbox.x + b.bbox.w)
  let maxY = Math.max(a.bbox.y + a.bbox.h, b.bbox.y + b.bbox.h)
  return {
    strokes,
    bbox: { x: minX, y: minY, w: maxX - minX, h: maxY - minY },
  }
}

export function resegmentByConfidence(
  segments: Segment[],
  results: Candidate[][],
  lowThreshold: number,
): Segment[] {
  if (segments.length <= 1) return segments
  const out: Segment[] = []
  let i = 0
  while (i < segments.length) {
    const seg = segments[i]
    const res = results[i]
    const topScore = res[0]?.score ?? 0
    if (topScore < lowThreshold && i + 1 < segments.length) {
      const nextRes = results[i + 1]
      const nextScore = nextRes[0]?.score ?? 0
      if (nextScore < lowThreshold + 0.15) {
        const merged = mergeSegments(seg, segments[i + 1])
        out.push(merged)
        i += 2
        continue
      }
    }
    out.push(seg)
    i++
  }
  return out
}

export function topCandidate(results: Candidate[][]): string {
  return results.map((r) => (r[0] ? r[0].char : '')).join('')
}

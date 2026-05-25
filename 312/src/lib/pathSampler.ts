export interface PathPoint {
  x: number
  y: number
  t: number
}

export interface ArcLengthSample {
  t: number
  length: number
}

export class PathArcLengthSampler {
  private samples: ArcLengthSample[] = []
  private totalLength: number = 0
  private pathCommands: PathCommand[] = []

  constructor(pathData: string) {
    this.parsePath(pathData)
    this.computeArcLengthTable()
  }

  private parsePath(d: string): void {
    const commands: PathCommand[] = []
    const regex = /([MmLlHhVvCcSsQqTtAaZz])|(-?\d+\.?\d*(?:e[-+]?\d+)?)/gi
    const tokens: string[] = []
    let match

    while ((match = regex.exec(d)) !== null) {
      tokens.push(match[0])
    }

    let i = 0
    let currentX = 0
    let currentY = 0
    let startX = 0
    let startY = 0

    while (i < tokens.length) {
      const cmd = tokens[i]
      i++

      const isRelative = cmd === cmd.toLowerCase()

      switch (cmd.toUpperCase()) {
        case 'M': {
          const x = parseFloat(tokens[i++])
          const y = parseFloat(tokens[i++])
          currentX = isRelative ? currentX + x : x
          currentY = isRelative ? currentY + y : y
          startX = currentX
          startY = currentY
          commands.push({ type: 'M', x: currentX, y: currentY })
          break
        }
        case 'L': {
          const x = parseFloat(tokens[i++])
          const y = parseFloat(tokens[i++])
          const endX = isRelative ? currentX + x : x
          const endY = isRelative ? currentY + y : y
          commands.push({ type: 'L', x1: currentX, y1: currentY, x2: endX, y2: endY })
          currentX = endX
          currentY = endY
          break
        }
        case 'H': {
          const x = parseFloat(tokens[i++])
          const endX = isRelative ? currentX + x : x
          commands.push({ type: 'L', x1: currentX, y1: currentY, x2: endX, y2: currentY })
          currentX = endX
          break
        }
        case 'V': {
          const y = parseFloat(tokens[i++])
          const endY = isRelative ? currentY + y : y
          commands.push({ type: 'L', x1: currentX, y1: currentY, x2: currentX, y2: endY })
          currentY = endY
          break
        }
        case 'C': {
          const cp1x = parseFloat(tokens[i++])
          const cp1y = parseFloat(tokens[i++])
          const cp2x = parseFloat(tokens[i++])
          const cp2y = parseFloat(tokens[i++])
          const x = parseFloat(tokens[i++])
          const y = parseFloat(tokens[i++])
          const endX = isRelative ? currentX + x : x
          const endY = isRelative ? currentY + y : y
          const cp1X = isRelative ? currentX + cp1x : cp1x
          const cp1Y = isRelative ? currentY + cp1y : cp1y
          const cp2X = isRelative ? currentX + cp2x : cp2x
          const cp2Y = isRelative ? currentY + cp2y : cp2y
          commands.push({
            type: 'C',
            x1: currentX,
            y1: currentY,
            cp1x: cp1X,
            cp1y: cp1Y,
            cp2x: cp2X,
            cp2y: cp2Y,
            x2: endX,
            y2: endY,
          })
          currentX = endX
          currentY = endY
          break
        }
        case 'Q': {
          const cpx = parseFloat(tokens[i++])
          const cpy = parseFloat(tokens[i++])
          const x = parseFloat(tokens[i++])
          const y = parseFloat(tokens[i++])
          const endX = isRelative ? currentX + x : x
          const endY = isRelative ? currentY + y : y
          const cpX = isRelative ? currentX + cpx : cpx
          const cpY = isRelative ? currentY + cpy : cpy
          commands.push({
            type: 'Q',
            x1: currentX,
            y1: currentY,
            cpx: cpX,
            cpy: cpY,
            x2: endX,
            y2: endY,
          })
          currentX = endX
          currentY = endY
          break
        }
        case 'Z':
          commands.push({
            type: 'L',
            x1: currentX,
            y1: currentY,
            x2: startX,
            y2: startY,
          })
          currentX = startX
          currentY = startY
          break
      }
    }

    this.pathCommands = commands
  }

  private computeArcLengthTable(samplesPerSegment: number = 50): void {
    this.samples = [{ t: 0, length: 0 }]
    let accumulatedLength = 0
    let prevPoint = this.getPointAtT(0)

    const totalSamples = samplesPerSegment * this.pathCommands.length

    for (let i = 1; i <= totalSamples; i++) {
      const t = i / totalSamples
      const point = this.getPointAtT(t)
      const dx = point.x - prevPoint.x
      const dy = point.y - prevPoint.y
      accumulatedLength += Math.sqrt(dx * dx + dy * dy)
      this.samples.push({ t, length: accumulatedLength })
      prevPoint = point
    }

    this.totalLength = accumulatedLength
  }

  private getPointAtT(t: number): { x: number; y: number } {
    if (this.pathCommands.length === 0) return { x: 0, y: 0 }

    const segmentIndex = Math.min(
      Math.floor(t * this.pathCommands.length),
      this.pathCommands.length - 1
    )
    const segmentT = (t * this.pathCommands.length) % 1

    const cmd = this.pathCommands[segmentIndex]

    switch (cmd.type) {
      case 'M':
        return { x: cmd.x ?? 0, y: cmd.y ?? 0 }
      case 'L':
        return {
          x: (cmd.x1 ?? 0) + segmentT * ((cmd.x2 ?? 0) - (cmd.x1 ?? 0)),
          y: (cmd.y1 ?? 0) + segmentT * ((cmd.y2 ?? 0) - (cmd.y1 ?? 0)),
        }
      case 'C':
        return this.cubicBezier(
          cmd.x1 ?? 0,
          cmd.y1 ?? 0,
          cmd.cp1x ?? 0,
          cmd.cp1y ?? 0,
          cmd.cp2x ?? 0,
          cmd.cp2y ?? 0,
          cmd.x2 ?? 0,
          cmd.y2 ?? 0,
          segmentT
        )
      case 'Q':
        return this.quadraticBezier(
          cmd.x1 ?? 0,
          cmd.y1 ?? 0,
          cmd.cpx ?? 0,
          cmd.cpy ?? 0,
          cmd.x2 ?? 0,
          cmd.y2 ?? 0,
          segmentT
        )
      default:
        return { x: 0, y: 0 }
    }
  }

  private cubicBezier(
    x1: number,
    y1: number,
    cp1x: number,
    cp1y: number,
    cp2x: number,
    cp2y: number,
    x2: number,
    y2: number,
    t: number
  ): { x: number; y: number } {
    const mt = 1 - t
    const mt2 = mt * mt
    const mt3 = mt2 * mt
    const t2 = t * t
    const t3 = t2 * t

    return {
      x: mt3 * x1 + 3 * mt2 * t * cp1x + 3 * mt * t2 * cp2x + t3 * x2,
      y: mt3 * y1 + 3 * mt2 * t * cp1y + 3 * mt * t2 * cp2y + t3 * y2,
    }
  }

  private quadraticBezier(
    x1: number,
    y1: number,
    cpx: number,
    cpy: number,
    x2: number,
    y2: number,
    t: number
  ): { x: number; y: number } {
    const mt = 1 - t
    const mt2 = mt * mt
    const t2 = t * t

    return {
      x: mt2 * x1 + 2 * mt * t * cpx + t2 * x2,
      y: mt2 * y1 + 2 * mt * t * cpy + t2 * y2,
    }
  }

  getTotalLength(): number {
    return this.totalLength
  }

  getPointAtArcLength(arcLength: number): { x: number; y: number; t: number } {
    if (this.totalLength === 0) return { x: 0, y: 0, t: 0 }

    const clampedLength = Math.max(0, Math.min(this.totalLength, arcLength))

    let low = 0
    let high = this.samples.length - 1

    while (low < high) {
      const mid = Math.floor((low + high) / 2)
      if (this.samples[mid].length < clampedLength) {
        low = mid + 1
      } else {
        high = mid
      }
    }

    if (low === 0) {
      return { ...this.getPointAtT(0), t: 0 }
    }

    const prev = this.samples[low - 1]
    const curr = this.samples[low]
    const segmentT = (clampedLength - prev.length) / (curr.length - prev.length)
    const t = prev.t + segmentT * (curr.t - prev.t)

    return { ...this.getPointAtT(t), t }
  }

  sampleUniformly(numSamples: number): PathPoint[] {
    const samples: PathPoint[] = []
    const step = this.totalLength / (numSamples - 1)

    for (let i = 0; i < numSamples; i++) {
      const arcLength = i * step
      const point = this.getPointAtArcLength(arcLength)
      samples.push({ x: point.x, y: point.y, t: point.t })
    }

    return samples
  }

  getUniformSamplingFunction(): (progress: number) => { x: number; y: number } {
    return (progress: number) => {
      const arcLength = progress * this.totalLength
      return this.getPointAtArcLength(arcLength)
    }
  }
}

interface PathCommand {
  type: string
  x?: number
  y?: number
  x1?: number
  y1?: number
  x2?: number
  y2?: number
  cp1x?: number
  cp1y?: number
  cp2x?: number
  cp2y?: number
  cpx?: number
  cpy?: number
}

export function createPathSampler(pathData: string) {
  return new PathArcLengthSampler(pathData)
}

export function getPathPositionAtProgress(
  pathData: string,
  progress: number
): { x: number; y: number } {
  const sampler = new PathArcLengthSampler(pathData)
  return sampler.getPointAtArcLength(progress * sampler.getTotalLength())
}

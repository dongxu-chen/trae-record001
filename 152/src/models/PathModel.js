export class PathModel {
  constructor(options = {}) {
    this.id = options.id || Date.now() + Math.random()
    this.pathData = options.pathData || ''
    this.fillColor = options.fillColor || [0.2, 0.6, 1, 1]
    this.strokeColor = options.strokeColor || [0, 0.5, 0.8, 1]
    this.strokeWidth = options.strokeWidth || 2
    this.visible = options.visible !== undefined ? options.visible : true
    this.locked = options.locked || false
    this.name = options.name || '路径'
    this.matrix = options.matrix || [1, 0, 0, 1, 0, 0]
    this._cache = null
    this._cacheKey = null
  }

  getPath(CanvasKit) {
    const key = this.pathData
    if (this._cacheKey === key && this._cache) {
      return this._cache
    }
    
    this._cache = CanvasKit.Path.MakeFromSVGString(this.pathData)
    this._cacheKey = key
    
    if (this.matrix) {
      const matrix = CanvasKit.Matrix.makeAll(
        this.matrix[0], this.matrix[2], this.matrix[4],
        this.matrix[1], this.matrix[3], this.matrix[5],
        0, 0, 1
      )
      this._cache.transform(matrix)
    }
    
    return this._cache
  }

  moveTo(x, y) {
    this.pathData += `M${x},${y}`
    this.invalidateCache()
    return this
  }

  lineTo(x, y) {
    this.pathData += `L${x},${y}`
    this.invalidateCache()
    return this
  }

  cubicTo(cp1x, cp1y, cp2x, cp2y, x, y) {
    this.pathData += `C${cp1x},${cp1y},${cp2x},${cp2y},${x},${y}`
    this.invalidateCache()
    return this
  }

  quadTo(cpx, cpy, x, y) {
    this.pathData += `Q${cpx},${cpy},${x},${y}`
    this.invalidateCache()
    return this
  }

  close() {
    this.pathData += 'Z'
    this.invalidateCache()
    return this
  }

  addRect(x, y, width, height) {
    this.pathData += `M${x},${y}L${x + width},${y}L${x + width},${y + height}L${x},${y + height}Z`
    this.invalidateCache()
    return this
  }

  addCircle(cx, cy, r) {
    this.pathData += `M${cx},${cy - r}A${r},${r} 0 1,1 ${cx},${cy + r}A${r},${r} 0 1,1 ${cx},${cy - r}Z`
    this.invalidateCache()
    return this
  }

  transform(matrix) {
    this.matrix = matrix
    this.invalidateCache()
    return this
  }

  translate(dx, dy) {
    this.matrix[4] += dx
    this.matrix[5] += dy
    this.invalidateCache()
    return this
  }

  scale(sx, sy) {
    this.matrix[0] *= sx
    this.matrix[3] *= sy
    this.invalidateCache()
    return this
  }

  rotate(angle, cx = 0, cy = 0) {
    const cos = Math.cos(angle)
    const sin = Math.sin(angle)
    const m = this.matrix
    
    const x = m[4] - cx
    const y = m[5] - cy
    
    m[4] = x * cos - y * sin + cx
    m[5] = x * sin + y * cos + cy
    
    const a = m[0], b = m[2], c = m[1], d = m[3]
    m[0] = a * cos - c * sin
    m[2] = b * cos - d * sin
    m[1] = a * sin + c * cos
    m[3] = b * sin + d * cos
    
    this.invalidateCache()
    return this
  }

  invalidateCache() {
    if (this._cache) {
      this._cache.delete()
      this._cache = null
    }
    this._cacheKey = null
  }

  getBounds(CanvasKit) {
    const path = this.getPath(CanvasKit)
    return path.computeTightBounds()
  }

  containsPoint(x, y, CanvasKit) {
    const path = this.getPath(CanvasKit)
    return path.contains(x, y)
  }

  clone() {
    return new PathModel({
      id: Date.now() + Math.random(),
      pathData: this.pathData,
      fillColor: [...this.fillColor],
      strokeColor: [...this.strokeColor],
      strokeWidth: this.strokeWidth,
      visible: this.visible,
      locked: this.locked,
      name: this.name + ' 副本',
      matrix: [...this.matrix]
    })
  }

  toJSON() {
    return {
      id: this.id,
      pathData: this.pathData,
      fillColor: this.fillColor,
      strokeColor: this.strokeColor,
      strokeWidth: this.strokeWidth,
      visible: this.visible,
      locked: this.locked,
      name: this.name,
      matrix: this.matrix
    }
  }

  static fromJSON(json) {
    return new PathModel(json)
  }

  dispose() {
    this.invalidateCache()
  }
}

export default PathModel

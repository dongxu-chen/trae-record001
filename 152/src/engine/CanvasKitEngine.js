import CanvasKitInit from 'canvaskit-wasm'

class CanvasKitEngine {
  constructor() {
    this.CanvasKit = null
    this.surface = null
    this.canvas = null
    this.paint = null
    this.width = 0
    this.height = 0
    this.initialized = false
  }

  async init(canvasElement, width, height) {
    if (this.initialized) return

    this.CanvasKit = await CanvasKitInit({
      locateFile: (file) => `/canvaskit/${file}`
    })

    this.width = width
    this.height = height

    this.surface = this.CanvasKit.MakeCanvasSurface(canvasElement)
    this.canvas = this.surface.getCanvas()

    this.paint = new this.CanvasKit.Paint()
    this.paint.setAntiAlias(true)

    this.initialized = true
    console.log('CanvasKit initialized - GPU accelerated')
  }

  resize(width, height) {
    if (!this.initialized) return
    this.width = width
    this.height = height
    this.surface = this.CanvasKit.MakeCanvasSurface(
      this.surface._canvas._canvas
    )
    this.canvas = this.surface.getCanvas()
  }

  clear(color = [1, 1, 1, 1]) {
    this.canvas.clear(color)
  }

  flush() {
    this.surface.flush()
  }

  createPaint(options = {}) {
    const paint = new this.CanvasKit.Paint()
    paint.setAntiAlias(true)
    
    if (options.color) paint.setColor(options.color)
    if (options.strokeWidth !== undefined) paint.setStrokeWidth(options.strokeWidth)
    if (options.style !== undefined) paint.setStyle(options.style)
    if (options.antiAlias !== undefined) paint.setAntiAlias(options.antiAlias)
    
    return paint
  }

  createPath() {
    return new this.CanvasKit.Path()
  }

  pathFromSVG(svgPathData) {
    return this.CanvasKit.Path.MakeFromSVGString(svgPathData)
  }

  drawPath(path, paint) {
    this.canvas.drawPath(path, paint)
  }

  drawRect(left, top, right, bottom, paint) {
    const rect = this.CanvasKit.LTRBRect(left, top, right, bottom)
    this.canvas.drawRect(rect, paint)
  }

  drawRRect(rect, rx, ry, paint) {
    const rrect = this.CanvasKit.RRectXY(rect, rx, ry)
    this.canvas.drawRRect(rrect, paint)
  }

  drawCircle(cx, cy, radius, paint) {
    this.canvas.drawCircle(cx, cy, radius, paint)
  }

  drawLine(x1, y1, x2, y2, paint) {
    this.canvas.drawLine(x1, y1, x2, y2, paint)
  }

  union(path1, path2) {
    return path1.op(path2, this.CanvasKit.PathOp.Union)
  }

  intersect(path1, path2) {
    return path1.op(path2, this.CanvasKit.PathOp.Intersect)
  }

  subtract(path1, path2) {
    return path1.op(path2, this.CanvasKit.PathOp.Difference)
  }

  xor(path1, path2) {
    return path1.op(path2, this.CanvasKit.PathOp.XOR)
  }

  simplifyPath(path) {
    return path.simplify()
  }

  computeTightBounds(path) {
    return path.computeTightBounds()
  }

  getPathFromPathEffect(path, strokeWidth, join = 0, cap = 0, miter = 4) {
    const strokeRec = new this.CanvasKit.StrokeRec()
    strokeRec.width = strokeWidth
    strokeRec.join = join
    strokeRec.cap = cap
    strokeRec.miter_limit = miter
    
    return this.CanvasKit.Path.MakeFromPathEffect(path, strokeRec)
  }

  get Color() {
    return this.CanvasKit.Color
  }

  get PaintStyle() {
    return {
      Fill: this.CanvasKit.PaintStyle.Fill,
      Stroke: this.CanvasKit.PaintStyle.Stroke,
      StrokeAndFill: this.CanvasKit.PaintStyle.StrokeAndFill
    }
  }

  get PathOp() {
    return this.CanvasKit.PathOp
  }

  dispose() {
    if (this.paint) this.paint.delete()
    if (this.surface) this.surface.delete()
  }
}

export const engine = new CanvasKitEngine()
export default CanvasKitEngine

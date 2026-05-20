const SNAP_THRESHOLD = 10
const GUIDELINE_COLOR = '#1890ff'
const GUIDELINE_STROKE_WIDTH = 1

class AlignmentSnap {
  constructor(canvas) {
    this.canvas = canvas
    this.guidelines = []
    this.snapThreshold = SNAP_THRESHOLD
    this.enabled = true
  }

  setEnabled(enabled) {
    this.enabled = enabled
    if (!enabled) {
      this.clearGuidelines()
    }
  }

  clearGuidelines() {
    this.guidelines.forEach(line => {
      this.canvas.remove(line)
    })
    this.guidelines = []
  }

  snapToNearest(movingNode, allNodes) {
    if (!this.enabled) return { x: movingNode.x, y: movingNode.y, snapped: false }

    const otherNodes = allNodes.filter(n => n.id !== movingNode.id && !n.collapsed)

    let snapX = movingNode.x
    let snapY = movingNode.y
    let snapped = false

    const movingEdges = this._getNodeEdges(movingNode)

    let bestXDist = Infinity
    let bestYDist = Infinity
    let bestX = null
    let bestY = null
    let bestXEdge = null
    let bestYEdge = null

    for (const node of otherNodes) {
      const edges = this._getNodeEdges(node)

      for (const [movingEdgeName, movingEdgeVal] of Object.entries(movingEdges)) {
        for (const [edgeName, edgeVal] of Object.entries(edges)) {
          const dist = Math.abs(movingEdgeVal - edgeVal)
          if (dist < this.snapThreshold && dist < bestXDist && 
              (movingEdgeName.includes('X') || movingEdgeName === 'centerX')) {
            bestXDist = dist
            bestX = edgeVal
            bestXEdge = { moving: movingEdgeName, target: edgeName, value: edgeVal, targetNode: node }
          }
          if (dist < this.snapThreshold && dist < bestYDist && 
              (movingEdgeName.includes('Y') || movingEdgeName === 'centerY')) {
            bestYDist = dist
            bestY = edgeVal
            bestYEdge = { moving: movingEdgeName, target: edgeName, value: edgeVal, targetNode: node }
          }
        }
      }
    }

    if (bestX !== null) {
      const offset = this._getEdgeOffset(movingNode, bestXEdge.moving)
      snapX = bestX - offset
      snapped = true
      this._drawXGuideline(bestX, movingNode, bestXEdge.targetNode)
    }

    if (bestY !== null) {
      const offset = this._getEdgeOffset(movingNode, bestYEdge.moving)
      snapY = bestY - offset
      snapped = true
      this._drawYGuideline(bestY, movingNode, bestYEdge.targetNode)
    }

    return { x: snapX, y: snapY, snapped }
  }

  _getNodeEdges(node) {
    return {
      leftX: node.x,
      centerX: node.x + node.width / 2,
      rightX: node.x + node.width,
      topY: node.y,
      centerY: node.y + node.height / 2,
      bottomY: node.y + node.height
    }
  }

  _getEdgeOffset(node, edgeName) {
    switch (edgeName) {
      case 'leftX': return 0
      case 'centerX': return node.width / 2
      case 'rightX': return node.width
      case 'topY': return 0
      case 'centerY': return node.height / 2
      case 'bottomY': return node.height
      default: return 0
    }
  }

  _drawXGuideline(x, movingNode, targetNode) {
    const minY = Math.min(movingNode.y, targetNode.y)
    const maxY = Math.max(movingNode.y + movingNode.height, targetNode.y + targetNode.height)

    const line = new fabric.Line([x, minY - 20, x, maxY + 20], {
      stroke: GUIDELINE_COLOR,
      strokeWidth: GUIDELINE_STROKE_WIDTH,
      strokeDashArray: [4, 4],
      selectable: false,
      evented: false,
      isGuideline: true
    })

    this.canvas.add(line)
    this.guidelines.push(line)
    line.sendToBack()
  }

  _drawYGuideline(y, movingNode, targetNode) {
    const minX = Math.min(movingNode.x, targetNode.x)
    const maxX = Math.max(movingNode.x + movingNode.width, targetNode.x + targetNode.width)

    const line = new fabric.Line([minX - 20, y, maxX + 20, y], {
      stroke: GUIDELINE_COLOR,
      strokeWidth: GUIDELINE_STROKE_WIDTH,
      strokeDashArray: [4, 4],
      selectable: false,
      evented: false,
      isGuideline: true
    })

    this.canvas.add(line)
    this.guidelines.push(line)
    line.sendToBack()
  }

  onObjectMoving(obj, allNodes) {
    this.clearGuidelines()

    const node = {
      id: obj.nodeId,
      x: obj.left,
      y: obj.top,
      width: obj.width || (obj.getScaledWidth ? obj.getScaledWidth() : 100),
      height: obj.height || (obj.getScaledHeight ? obj.getScaledHeight() : 100)
    }

    const result = this.snapToNearest(node, allNodes)

    if (result.snapped) {
      obj.set({
        left: result.x,
        top: result.y
      })
      obj.setCoords()
    }
  }

  onObjectModified() {
    this.clearGuidelines()
  }

  dispose() {
    this.clearGuidelines()
  }
}

export default AlignmentSnap

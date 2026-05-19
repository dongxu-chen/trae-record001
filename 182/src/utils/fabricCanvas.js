import { fabric } from 'fabric'
import { calculateAllAStarPaths, updateAStarPathsOnNodeMove } from './aStarRouter'
import { calculateGroupBounds } from './layoutEngine'
import { NODE_TYPES } from './graphData'
import AlignmentSnap from './alignmentSnap'

export class FlowCanvas {
  constructor(canvasElement, options = {}) {
    this.canvas = new fabric.Canvas(canvasElement, {
      width: options.width || 2000,
      height: options.height || 1500,
      backgroundColor: '#fafafa',
      selection: true,
      preserveObjectStacking: true
    })

    this.nodes = []
    this.edges = []
    this.edgePaths = {}
    this.fabricObjects = new Map()
    this.edgeObjects = new Map()
    this.tempLine = null
    this.isConnecting = false
    this.connectionStart = null
    this.selectedObject = null
    this.zoom = 1
    this.alignmentSnap = new AlignmentSnap(this.canvas)
    this.snapEnabled = options.snapEnabled !== false

    this.onNodeMove = options.onNodeMove || (() => {})
    this.onSelectionChange = options.onSelectionChange || (() => {})
    this.onEdgeCreate = options.onEdgeCreate || (() => {})
    this.onNodeDoubleClick = options.onNodeDoubleClick || (() => {})

    this._setupEventListeners()
  }

  setSnapEnabled(enabled) {
    this.snapEnabled = enabled
    this.alignmentSnap.setEnabled(enabled)
  }

  _setupEventListeners() {
    this.canvas.on('object:moving', (e) => {
      const obj = e.target
      if (obj && obj.nodeId) {
        if (this.snapEnabled) {
          this.alignmentSnap.onObjectMoving(obj, this.nodes)
        }

        const node = this.nodes.find(n => n.id === obj.nodeId)
        if (node) {
          node.x = obj.left
          node.y = obj.top

          if (node.isGroup && !node.collapsed) {
            this._updateGroupChildren(node)
          }

          this.onNodeMove(node.id)
          this._updateAffectedEdges(node.id)
        }
      }
    })

    this.canvas.on('object:modified', (e) => {
      this.alignmentSnap.onObjectModified()

      const obj = e.target
      if (obj && obj.nodeId) {
        const node = this.nodes.find(n => n.id === obj.nodeId)
        if (node && node.isGroup && !node.collapsed) {
          this._updateGroupBounds(node)
        }
      }
    })

    this.canvas.on('selection:created', (e) => {
      const selected = e.selected && e.selected[0]
      this._handleSelection(selected)
    })

    this.canvas.on('selection:updated', (e) => {
      const selected = e.selected && e.selected[0]
      this._handleSelection(selected)
    })

    this.canvas.on('selection:cleared', () => {
      this.selectedObject = null
      this.onSelectionChange(null)
    })

    this.canvas.on('mouse:down', (e) => {
      if (e.target && e.target.isConnectionPoint) {
        this._startConnection(e.target)
      }
    })

    this.canvas.on('mouse:move', (e) => {
      if (this.isConnecting && this.tempLine) {
        const pointer = this.canvas.getPointer(e.e)
        this.tempLine.set({ x2: pointer.x, y2: pointer.y })
        this.canvas.renderAll()
      }
    })

    this.canvas.on('mouse:up', (e) => {
      if (this.isConnecting) {
        if (e.target && e.target.isConnectionTarget && e.target.nodeId !== this.connectionStart.nodeId) {
          this._finishConnection(e.target.nodeId)
        } else {
          this._cancelConnection()
        }
      }
    })

    this.canvas.on('mouse:dblclick', (e) => {
      if (e.target && e.target.nodeId) {
        const node = this.nodes.find(n => n.id === e.target.nodeId)
        if (node) {
          this.onNodeDoubleClick(node)
        }
      }
    })

    this.canvas.on('mouse:wheel', (opt) => {
      const delta = opt.e.deltaY
      let zoom = this.canvas.getZoom()
      zoom *= 0.999 ** delta
      if (zoom > 5) zoom = 5
      if (zoom < 0.1) zoom = 0.1
      this.canvas.zoomToPoint({ x: opt.e.offsetX, y: opt.e.offsetY }, zoom)
      this.zoom = zoom
      opt.e.preventDefault()
      opt.e.stopPropagation()
    })
  }

  _handleSelection(obj) {
    if (!obj) {
      this.selectedObject = null
      this.onSelectionChange(null)
      return
    }

    if (obj.nodeId) {
      const node = this.nodes.find(n => n.id === obj.nodeId)
      this.selectedObject = { type: 'node', data: node }
      this.onSelectionChange(this.selectedObject)
    } else if (obj.edgeId) {
      const edge = this.edges.find(e => e.id === obj.edgeId)
      this.selectedObject = { type: 'edge', data: edge }
      this.onSelectionChange(this.selectedObject)
    }
  }

  _startConnection(target) {
    this.isConnecting = true
    this.connectionStart = target

    const points = [target.left + target.width / 2, target.top + target.height / 2, target.left + target.width / 2, target.top + target.height / 2]
    this.tempLine = new fabric.Line(points, {
      stroke: '#1890ff',
      strokeWidth: 2,
      strokeDashArray: [5, 5],
      selectable: false,
      evented: false
    })

    this.canvas.add(this.tempLine)
  }

  _finishConnection(targetNodeId) {
    if (this.tempLine) {
      this.canvas.remove(this.tempLine)
      this.tempLine = null
    }

    const sourceId = this.connectionStart.nodeId
    const exists = this.edges.some(e => e.sourceId === sourceId && e.targetId === targetNodeId)

    if (!exists && sourceId !== targetNodeId) {
      this.onEdgeCreate(sourceId, targetNodeId)
    }

    this.isConnecting = false
    this.connectionStart = null
  }

  _cancelConnection() {
    if (this.tempLine) {
      this.canvas.remove(this.tempLine)
      this.tempLine = null
    }
    this.isConnecting = false
    this.connectionStart = null
  }

  addNode(node) {
    this.nodes.push(node)
    this._renderNode(node)
    this.updateAllEdges()
  }

  removeNode(nodeId) {
    const node = this.nodes.find(n => n.id === nodeId)
    if (!node) return

    const fabricObj = this.fabricObjects.get(nodeId)
    if (fabricObj) {
      this.canvas.remove(fabricObj)
      this.fabricObjects.delete(nodeId)
    }

    this.edges = this.edges.filter(e => {
      if (e.sourceId === nodeId || e.targetId === nodeId) {
        const edgeObj = this.edgeObjects.get(e.id)
        if (edgeObj) {
          this.canvas.remove(edgeObj)
          this.edgeObjects.delete(e.id)
        }
        return false
      }
      return true
    })

    this.nodes = this.nodes.filter(n => n.id !== nodeId)

    this.nodes.forEach(n => {
      if (n.isGroup && n.childNodes.includes(nodeId)) {
        n.childNodes = n.childNodes.filter(id => id !== nodeId)
      }
    })

    this.updateAllEdges()
  }

  addEdge(edge) {
    this.edges.push(edge)
    this.updateAllEdges()
  }

  removeEdge(edgeId) {
    const edgeObj = this.edgeObjects.get(edgeId)
    if (edgeObj) {
      this.canvas.remove(edgeObj)
      this.edgeObjects.delete(edgeId)
    }
    this.edges = this.edges.filter(e => e.id !== edgeId)
  }

  _renderNode(node) {
    const existing = this.fabricObjects.get(node.id)
    if (existing) {
      this.canvas.remove(existing)
    }

    if (node.collapsed && !node.isGroup) return

    let shape

    if (node.type === NODE_TYPES.RECTANGLE || node.type === NODE_TYPES.GROUP) {
      shape = new fabric.Rect({
        width: node.width,
        height: node.height,
        fill: node.fill,
        stroke: node.stroke,
        strokeWidth: node.strokeWidth,
        strokeDashArray: node.strokeDashArray || null,
        rx: 8,
        ry: 8
      })
    } else if (node.type === NODE_TYPES.CIRCLE) {
      shape = new fabric.Ellipse({
        rx: node.width / 2,
        ry: node.height / 2,
        fill: node.fill,
        stroke: node.stroke,
        strokeWidth: node.strokeWidth
      })
    } else if (node.type === NODE_TYPES.DIAMOND) {
      shape = new fabric.Polygon([
        { x: node.width / 2, y: 0 },
        { x: node.width, y: node.height / 2 },
        { x: node.width / 2, y: node.height },
        { x: 0, y: node.height / 2 }
      ], {
        fill: node.fill,
        stroke: node.stroke,
        strokeWidth: node.strokeWidth
      })
    } else if (node.type === NODE_TYPES.PARALLELOGRAM) {
      const skew = 20
      shape = new fabric.Polygon([
        { x: skew, y: 0 },
        { x: node.width, y: 0 },
        { x: node.width - skew, y: node.height },
        { x: 0, y: node.height }
      ], {
        fill: node.fill,
        stroke: node.stroke,
        strokeWidth: node.strokeWidth
      })
    } else if (node.type === NODE_TYPES.DOCUMENT) {
      shape = new fabric.Group([
        new fabric.Path(`M 0 10 L 0 ${node.height} L ${node.width} ${node.height} L ${node.width} 10 Q ${node.width} 0 ${node.width - 10} 0 L 10 0 Q 0 0 0 10`, {
          fill: node.fill,
          stroke: node.stroke,
          strokeWidth: node.strokeWidth
        }),
        new fabric.Line([node.width - 10, 0, node.width - 10, 10], {
          stroke: node.stroke,
          strokeWidth: node.strokeWidth
        }),
        new fabric.Line([node.width - 10, 10, node.width, 10], {
          stroke: node.stroke,
          strokeWidth: node.strokeWidth
        })
      ])
    }

    const textY = node.isGroup && !node.collapsed ? 20 : node.height / 2
    const text = new fabric.Text(node.label, {
      fontSize: node.fontSize,
      fill: node.fontColor,
      originX: 'center',
      originY: 'center',
      left: node.width / 2,
      top: textY
    })

    const group = new fabric.Group([shape, text], {
      left: node.x,
      top: node.y,
      nodeId: node.id,
      hasControls: true,
      lockRotation: true,
      isConnectionTarget: true
    })

    if (node.isGroup) {
      const collapseBtn = this._createCollapseButton(node)
      group.add(collapseBtn)
    }

    const connectionPoints = this._createConnectionPoints(node)
    connectionPoints.forEach(p => group.add(p))

    this.canvas.add(group)
    this.fabricObjects.set(node.id, group)

    group.on('mousedblclick', (e) => {
      e.e.stopPropagation()
      if (node.isGroup) {
        this._toggleGroupCollapse(node)
      }
    })

    return group
  }

  _createConnectionPoints(node) {
    const points = []
    const positions = [
      { x: node.width / 2, y: 0, name: 'top' },
      { x: node.width, y: node.height / 2, name: 'right' },
      { x: node.width / 2, y: node.height, name: 'bottom' },
      { x: 0, y: node.height / 2, name: 'left' }
    ]

    positions.forEach(pos => {
      const circle = new fabric.Circle({
        radius: 6,
        fill: '#fff',
        stroke: '#1890ff',
        strokeWidth: 2,
        left: pos.x - 6,
        top: pos.y - 6,
        selectable: false,
        isConnectionPoint: true,
        nodeId: node.id,
        connectionType: pos.name
      })

      circle.on('mouseover', () => {
        circle.set({ fill: '#1890ff', radius: 8 })
        this.canvas.renderAll()
      })

      circle.on('mouseout', () => {
        circle.set({ fill: '#fff', radius: 6 })
        this.canvas.renderAll()
      })

      points.push(circle)
    })

    return points
  }

  _createCollapseButton(node) {
    const btnX = node.width - 20
    const btnY = 12

    const btnGroup = new fabric.Group([], {
      left: btnX,
      top: btnY,
      selectable: false,
      originX: 'center',
      originY: 'center'
    })

    const circle = new fabric.Circle({
      radius: 10,
      fill: '#fff',
      stroke: '#1890ff',
      strokeWidth: 1,
      originX: 'center',
      originY: 'center',
      left: 0,
      top: 0
    })

    const text = new fabric.Text(node.collapsed ? '+' : '−', {
      fontSize: 16,
      fill: '#1890ff',
      originX: 'center',
      originY: 'center',
      left: 0,
      top: 2
    })

    btnGroup.add(circle)
    btnGroup.add(text)

    btnGroup.on('mousedown', (e) => {
      e.e.stopPropagation()
      this._toggleGroupCollapse(node)
    })

    return btnGroup
  }

  _toggleGroupCollapse(group) {
    group.collapsed = !group.collapsed

    if (group.collapsed) {
      group.originalWidth = group.width
      group.originalHeight = group.height
      group.width = 150
      group.height = 60
    } else {
      group.width = group.originalWidth || group.width
      group.height = group.originalHeight || group.height
    }

    group.childNodes.forEach(childId => {
      const childNode = this.nodes.find(n => n.id === childId)
      if (childNode) {
        childNode.collapsed = group.collapsed
        const childObj = this.fabricObjects.get(childId)
        if (childObj) {
          if (group.collapsed) {
            this.canvas.remove(childObj)
          } else {
            this.canvas.add(childObj)
          }
        }
      }
    })

    this._renderNode(group)
    this.updateAllEdges()
  }

  _renderEdge(edge, path) {
    const existing = this.edgeObjects.get(edge.id)
    if (existing) {
      this.canvas.remove(existing)
    }

    if (!path || path.length < 2) return

    const fabricPath = path.map((p, i) => {
      return i === 0 ? `M ${p.x} ${p.y}` : `L ${p.x} ${p.y}`
    }).join(' ')

    const line = new fabric.Path(fabricPath, {
      fill: null,
      stroke: edge.stroke,
      strokeWidth: edge.strokeWidth,
      selectable: true,
      edgeId: edge.id
    })

    const arrowHead = this._createArrowHead(path)
    if (arrowHead) {
      this.canvas.add(arrowHead)
    }

    const group = new fabric.Group([line], {
      selectable: true,
      edgeId: edge.id
    })

    if (edge.label && path.length > 1) {
      const midIndex = Math.floor(path.length / 2)
      const midPoint = path[midIndex]
      const label = new fabric.Text(edge.label, {
        fontSize: edge.fontSize,
        fill: edge.fontColor,
        backgroundColor: '#fff',
        originX: 'center',
        originY: 'center',
        left: midPoint.x,
        top: midPoint.y
      })
      group.add(label)
    }

    this.canvas.add(group)
    this.edgeObjects.set(edge.id, group)

    line.sendToBack()

    return group
  }

  _createArrowHead(path) {
    if (path.length < 2) return null

    const end = path[path.length - 1]
    const prev = path[path.length - 2]

    const angle = Math.atan2(end.y - prev.y, end.x - prev.x)
    const arrowLength = 10
    const arrowWidth = 6

    const points = [
      { x: end.x, y: end.y },
      { x: end.x - arrowLength * Math.cos(angle - Math.PI / 6), y: end.y - arrowLength * Math.sin(angle - Math.PI / 6) },
      { x: end.x - arrowLength * Math.cos(angle + Math.PI / 6), y: end.y - arrowLength * Math.sin(angle + Math.PI / 6) }
    ]

    return new fabric.Polygon(points, {
      fill: '#666',
      selectable: false,
      edgeId: 'arrow'
    })
  }

  _updateGroupBounds(group) {
    const bounds = calculateGroupBounds(group, this.nodes)
    group.x = bounds.x
    group.y = bounds.y
    group.width = bounds.width
    group.height = bounds.height

    const obj = this.fabricObjects.get(group.id)
    if (obj) {
      obj.set({ left: bounds.x, top: bounds.y })
      this._renderNode(group)
    }
  }

  _updateGroupChildren(group) {
    const obj = this.fabricObjects.get(group.id)
    if (!obj) return

    const groupX = obj.left
    const groupY = obj.top

    group.childNodes.forEach(childId => {
      const childNode = this.nodes.find(n => n.id === childId)
      const childObj = this.fabricObjects.get(childId)
      if (childNode && childObj) {
        const relX = childNode.x - group.originalX
        const relY = childNode.y - group.originalY
        childNode.x = groupX + relX
        childNode.y = groupY + relY
        childObj.set({ left: childNode.x, top: childNode.y })
      }
    })

    group.originalX = groupX
    group.originalY = groupY
  }

  updateAllEdges() {
    this.edgeObjects.forEach((obj) => {
      this.canvas.remove(obj)
    })
    this.edgeObjects.clear()

    this.edgePaths = calculateAllAStarPaths(this.nodes, this.edges)

    this.edges.forEach(edge => {
      const path = this.edgePaths[edge.id]
      if (path) {
        this._renderEdge(edge, path)
      }
    })

    this.canvas.renderAll()
  }

  _updateAffectedEdges(nodeId) {
    const updatedPaths = updateAStarPathsOnNodeMove(this.nodes, this.edges, nodeId)

    Object.entries(updatedPaths).forEach(([edgeId, path]) => {
      this.edgePaths[edgeId] = path
      const edge = this.edges.find(e => e.id === edgeId)
      if (edge) {
        const existing = this.edgeObjects.get(edgeId)
        if (existing) {
          this.canvas.remove(existing)
        }
        this._renderEdge(edge, path)
      }
    })

    this.canvas.renderAll()
  }

  updateNode(nodeId, updates) {
    const node = this.nodes.find(n => n.id === nodeId)
    if (!node) return

    Object.assign(node, updates)
    this._renderNode(node)

    if (updates.x !== undefined || updates.y !== undefined || updates.width !== undefined || updates.height !== undefined) {
      this.updateAllEdges()
    }

    this.canvas.renderAll()
  }

  clear() {
    this.canvas.clear()
    this.nodes = []
    this.edges = []
    this.edgePaths = {}
    this.fabricObjects.clear()
    this.edgeObjects.clear()
    this.selectedObject = null
  }

  setZoom(zoom) {
    this.zoom = zoom
    this.canvas.setZoom(zoom)
    this.canvas.renderAll()
  }

  getZoom() {
    return this.zoom
  }

  dispose() {
    this.alignmentSnap.dispose()
    this.canvas.dispose()
  }
}

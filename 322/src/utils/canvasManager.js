import { fabric } from 'fabric'
import { ref } from 'vue'
import { TOOL_MODES, ANNOTATION_TYPES, ANNOTATION_CATEGORIES, SNAP_CONFIG } from '../constants'
import ot from './ot'

class CanvasManager {
  constructor() {
    this.canvas = null
    this.container = null
    this.currentTool = ref(TOOL_MODES.SELECT)
    this.currentCategory = ref(ANNOTATION_CATEGORIES[0].id)
    this.annotations = ref([])
    this.selectedAnnotation = ref(null)
    this.isDrawing = false
    this.drawingObject = null
    this.startPoint = null
    this.backgroundImage = null
    this.imageInfo = null
    this.historyStack = []
    this.redoStack = []
    this.maxHistory = 50
    this.remoteCursors = new Map()
    this.zoom = 1
    this.panOffset = { x: 0, y: 0 }
    this.isPanning = false
    this.lastPanPoint = null
    this.listeners = new Map()
    this.textInput = null
    
    this.snapEnabled = ref(SNAP_CONFIG.ENABLED)
    this.snapThreshold = SNAP_CONFIG.THRESHOLD
    this.snapSmoothing = SNAP_CONFIG.SMOOTHING_FACTOR
    this.guidelines = []
    this.snapTargets = []
    this.currentSnapInfo = ref(null)
    
    this.ot = ot
    this.userId = null
  }

  init(container, canvasElement) {
    this.container = container
    this.canvas = new fabric.Canvas(canvasElement, {
      selection: true,
      preserveObjectStacking: true,
      fireRightClick: true,
      stopContextMenu: true,
      allowTouchScrolling: true
    })

    this.setupEventListeners()
    this.canvas.setWidth(container.clientWidth)
    this.canvas.setHeight(container.clientHeight)
    
    this.setTool(TOOL_MODES.SELECT)
  }

  setupEventListeners() {
    this.canvas.on('mouse:down', (e) => this.onMouseDown(e))
    this.canvas.on('mouse:move', (e) => this.onMouseMove(e))
    this.canvas.on('mouse:up', (e) => this.onMouseUp(e))
    this.canvas.on('object:modified', (e) => this.onObjectModified(e))
    this.canvas.on('object:selected', (e) => this.onObjectSelected(e))
    this.canvas.on('before:selection:cleared', () => this.onSelectionCleared())
    this.canvas.on('mouse:wheel', (e) => this.onMouseWheel(e))

    document.addEventListener('keydown', (e) => this.onKeyDown(e))
    window.addEventListener('resize', () => this.handleResize())
  }

  handleResize() {
    if (this.container && this.canvas) {
      this.canvas.setWidth(this.container.clientWidth)
      this.canvas.setHeight(this.container.clientHeight)
      this.canvas.renderAll()
    }
  }

  async loadImage(dataUrl, imageInfo = {}) {
    return new Promise((resolve, reject) => {
      fabric.Image.fromURL(dataUrl, (img) => {
        try {
          this.clearCanvas()

          const containerWidth = this.container.clientWidth
          const containerHeight = this.container.clientHeight
          const imgWidth = img.width || imageInfo.width || 800
          const imgHeight = img.height || imageInfo.height || 600

          const scaleX = (containerWidth * 0.9) / imgWidth
          const scaleY = (containerHeight * 0.9) / imgHeight
          const scale = Math.min(scaleX, scaleY, 1)

          img.set({
            left: (containerWidth - imgWidth * scale) / 2,
            top: (containerHeight - imgHeight * scale) / 2,
            selectable: false,
            evented: false,
            scaleX: scale,
            scaleY: scale
          })

          this.backgroundImage = img
          this.imageInfo = {
            ...imageInfo,
            width: imgWidth,
            height: imgHeight,
            displayWidth: imgWidth * scale,
            displayHeight: imgHeight * scale,
            scale: scale,
            offsetX: (containerWidth - imgWidth * scale) / 2,
            offsetY: (containerHeight - imgHeight * scale) / 2
          }

          this.canvas.add(img)
          img.sendToBack()
          this.canvas.renderAll()

          this.annotations.value = []
          this.historyStack = []
          this.redoStack = []

          resolve(img)
        } catch (error) {
          reject(error)
        }
      }, { crossOrigin: 'anonymous' })
    })
  }

  setTool(tool) {
    this.currentTool.value = tool
    if (!this.canvas) return
    this.canvas.selection = tool === TOOL_MODES.SELECT

    if (tool === TOOL_MODES.SELECT) {
      this.canvas.defaultCursor = 'default'
      this.canvas.forEachObject((obj) => {
        if (obj !== this.backgroundImage) {
          obj.selectable = true
          obj.evented = true
        }
      })
    } else if (tool === TOOL_MODES.PAN) {
      this.canvas.defaultCursor = 'grab'
      this.canvas.forEachObject((obj) => {
        obj.selectable = false
        obj.evented = false
      })
    } else {
      this.canvas.defaultCursor = 'crosshair'
      this.canvas.forEachObject((obj) => {
        obj.selectable = false
        obj.evented = false
      })
    }
  }

  setCategory(categoryId) {
    this.currentCategory.value = categoryId
  }

  getCategoryColor(categoryId) {
    const category = ANNOTATION_CATEGORIES.find(c => c.id === categoryId)
    return category ? category.color : '#409eff'
  }

  setSnapEnabled(enabled) {
    this.snapEnabled.value = enabled
    if (!enabled) {
      this.clearGuidelines()
    }
  }

  buildSnapTargets() {
    this.snapTargets = []
    
    if (!this.backgroundImage || !this.imageInfo) return

    const { offsetX, offsetY, displayWidth, displayHeight } = this.imageInfo
    const imgEdges = {
      left: offsetX,
      right: offsetX + displayWidth,
      top: offsetY,
      bottom: offsetY + displayHeight,
      hcenter: offsetX + displayWidth / 2,
      vcenter: offsetY + displayHeight / 2,
      type: 'image',
      isImage: true
    }
    this.snapTargets.push(imgEdges)

    this.annotations.value.forEach(ann => {
      if (!ann.canvasCoords) return
      const { left, top, width, height } = ann.canvasCoords
      const edges = {
        left,
        right: left + width,
        top,
        bottom: top + height,
        hcenter: left + width / 2,
        vcenter: top + height / 2,
        type: 'annotation',
        annotationId: ann.id,
        category: ann.category,
        isImage: false
      }
      this.snapTargets.push(edges)
    })
  }

  calculateSnap(point, currentObject = null, ignoreId = null) {
    if (!this.snapEnabled.value || !this.snapTargets.length) {
      return { x: point.x, y: point.y, snapped: false, info: null }
    }

    let closestSnap = null
    let minDistance = this.snapThreshold
    let snapInfo = null

    this.snapTargets.forEach(target => {
      if (target.annotationId === ignoreId) return

      const edges = ['left', 'right', 'hcenter']
      edges.forEach(edge => {
        const distance = Math.abs(point.x - target[edge])
        if (distance < minDistance) {
          minDistance = distance
          closestSnap = { x: target[edge], y: point.y }
          snapInfo = {
            type: 'vertical',
            edge,
            targetType: target.type,
            targetId: target.annotationId || 'image',
            distance
          }
        }
      })

      const vedges = ['top', 'bottom', 'vcenter']
      vedges.forEach(edge => {
        const distance = Math.abs(point.y - target[edge])
        if (distance < minDistance) {
          minDistance = distance
          closestSnap = { x: point.x, y: target[edge] }
          snapInfo = {
            type: 'horizontal',
            edge,
            targetType: target.type,
            targetId: target.annotationId || 'image',
            distance
          }
        }
      })
    })

    if (closestSnap) {
      const smoothFactor = this.easeInOutQuad(minDistance / this.snapThreshold)
      const finalX = point.x + (closestSnap.x - point.x) * smoothFactor
      const finalY = point.y + (closestSnap.y - point.y) * smoothFactor

      return {
        x: finalX,
        y: finalY,
        snapped: true,
        info: snapInfo,
        rawX: closestSnap.x,
        rawY: closestSnap.y
      }
    }

    return { x: point.x, y: point.y, snapped: false, info: null }
  }

  easeInOutQuad(t) {
    return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2
  }

  smoothLerp(current, target, factor) {
    return current + (target - current) * factor
  }

  showGuidelines(snapInfo) {
    if (!SNAP_CONFIG.SHOW_GUIDELINES || !snapInfo) return

    this.clearGuidelines()

    const { type, edge, targetType, targetId } = snapInfo
    let line = null

    if (type === 'vertical') {
      let x
      const target = this.snapTargets.find(t => 
        (t.annotationId === targetId || (targetId === 'image' && t.isImage))
      )
      if (target) x = target[edge]

      if (x !== undefined) {
        line = new fabric.Line([x, 0, x, this.canvas.height], {
          stroke: SNAP_CONFIG.GUIDELINE_COLOR,
          strokeWidth: 1,
          strokeDashArray: [5, 5],
          opacity: SNAP_CONFIG.GUIDELINE_OPACITY,
          selectable: false,
          evented: false,
          isGuideline: true
        })
      }
    } else {
      let y
      const target = this.snapTargets.find(t => 
        (t.annotationId === targetId || (targetId === 'image' && t.isImage))
      )
      if (target) y = target[edge]

      if (y !== undefined) {
        line = new fabric.Line([0, y, this.canvas.width, y], {
          stroke: SNAP_CONFIG.GUIDELINE_COLOR,
          strokeWidth: 1,
          strokeDashArray: [5, 5],
          opacity: SNAP_CONFIG.GUIDELINE_OPACITY,
          selectable: false,
          evented: false,
          isGuideline: true
        })
      }
    }

    if (line) {
      this.guidelines.push(line)
      this.canvas.add(line)
      line.sendToBack()
      if (this.backgroundImage) {
        this.backgroundImage.sendToBack()
      }
    }
  }

  clearGuidelines() {
    this.guidelines.forEach(line => {
      if (line.canvas) {
        this.canvas.remove(line)
      }
    })
    this.guidelines = []
  }

  applySnapToObject(obj, point, ignoreId = null) {
    if (!this.snapEnabled.value) return point

    const snapResult = this.calculateSnap(point, obj, ignoreId)
    
    if (snapResult.snapped && snapResult.info) {
      this.showGuidelines(snapResult.info)
      this.currentSnapInfo.value = snapResult.info
    } else {
      this.clearGuidelines()
      this.currentSnapInfo.value = null
    }

    return { x: snapResult.x, y: snapResult.y }
  }

  calculateRectSnap(left, top, width, height, ignoreId = null) {
    if (!this.snapEnabled.value) {
      return { left, top, width, height, snapped: false }
    }

    const corners = [
      { x: left, y: top, corner: 'tl' },
      { x: left + width, y: top, corner: 'tr' },
      { x: left, y: top + height, corner: 'bl' },
      { x: left + width, y: top + height, corner: 'br' }
    ]

    let finalLeft = left
    let finalTop = top
    let snapped = false

    corners.forEach(corner => {
      const snap = this.calculateSnap(corner, null, ignoreId)
      if (snap.snapped) {
        snapped = true
        if (snap.info.type === 'vertical') {
          if (corner.corner === 'tl' || corner.corner === 'bl') {
            finalLeft = snap.x
          } else {
            finalLeft = snap.x - width
          }
        } else {
          if (corner.corner === 'tl' || corner.corner === 'tr') {
            finalTop = snap.y
          } else {
            finalTop = snap.y - height
          }
        }
      }
    })

    const centerSnap = this.calculateSnap(
      { x: left + width / 2, y: top + height / 2 },
      null,
      ignoreId
    )
    
    if (centerSnap.snapped) {
      snapped = true
      if (centerSnap.info.edge === 'hcenter') {
        finalLeft = centerSnap.x - width / 2
      }
      if (centerSnap.info.edge === 'vcenter') {
        finalTop = centerSnap.y - height / 2
      }
    }

    return {
      left: finalLeft,
      top: finalTop,
      width,
      height,
      snapped
    }
  }

  onMouseDown(e) {
    const pointer = this.canvas.getPointer(e.e)

    if (this.currentTool.value === TOOL_MODES.PAN) {
      this.isPanning = true
      this.lastPanPoint = pointer
      this.canvas.defaultCursor = 'grabbing'
      return
    }

    if (this.currentTool.value === TOOL_MODES.SELECT) {
      const activeObj = this.canvas.getActiveObject()
      if (activeObj && activeObj.annotationId) {
        this.draggingAnnotationId = activeObj.annotationId
        this.prevCoords = {
          left: activeObj.left,
          top: activeObj.top,
          width: activeObj.width * activeObj.scaleX,
          height: activeObj.height * activeObj.scaleY
        }
      }
      this.buildSnapTargets()
      return
    }

    if (!this.backgroundImage) return
    if (!this.isInImageBounds(pointer)) return

    this.isDrawing = true
    this.startPoint = pointer
    this.canvas.selection = false
    
    this.buildSnapTargets()

    const category = this.currentCategory.value
    const color = this.getCategoryColor(category)

    switch (this.currentTool.value) {
      case TOOL_MODES.RECTANGLE:
        this.drawingObject = new fabric.Rect({
          left: pointer.x,
          top: pointer.y,
          width: 0,
          height: 0,
          fill: 'transparent',
          stroke: color,
          strokeWidth: 2,
          selectable: false,
          evented: false,
          annotationType: ANNOTATION_TYPES.RECTANGLE,
          category: category,
          label: '',
          isDrawing: true
        })
        break

      case TOOL_MODES.ARROW:
        this.drawingObject = new fabric.Line([pointer.x, pointer.y, pointer.x, pointer.y], {
          stroke: color,
          strokeWidth: 2,
          selectable: false,
          evented: false,
          annotationType: ANNOTATION_TYPES.ARROW,
          category: category,
          label: '',
          isDrawing: true,
          hasControls: false
        })
        break

      case TOOL_MODES.TEXT:
        this.showTextInput(pointer, category, color)
        this.isDrawing = false
        return
    }

    if (this.drawingObject) {
      this.canvas.add(this.drawingObject)
    }
  }

  onMouseMove(e) {
    const pointer = this.canvas.getPointer(e.e)

    this.emit('cursor:move', pointer)

    if (this.isPanning && this.lastPanPoint) {
      const deltaX = pointer.x - this.lastPanPoint.x
      const deltaY = pointer.y - this.lastPanPoint.y

      this.canvas.relativePan(new fabric.Point(deltaX, deltaY))
      this.lastPanPoint = pointer
      return
    }

    const activeObj = this.canvas.getActiveObject()
    if (this.currentTool.value === TOOL_MODES.SELECT && activeObj && activeObj.annotationId && !activeObj.isGuideline) {
      const ignoreId = activeObj.annotationId
      const left = activeObj.left
      const top = activeObj.top
      const width = activeObj.width * activeObj.scaleX
      const height = activeObj.height * activeObj.scaleY

      const snapResult = this.calculateRectSnap(left, top, width, height, ignoreId)
      
      if (snapResult.snapped && (Math.abs(snapResult.left - left) > 0.5 || Math.abs(snapResult.top - top) > 0.5)) {
        activeObj.set({
          left: snapResult.left,
          top: snapResult.top
        })
        this.canvas.renderAll()
      } else if (!snapResult.snapped) {
        this.clearGuidelines()
        this.currentSnapInfo.value = null
      }
      return
    }

    if (!this.isDrawing || !this.drawingObject) return

    if (this.currentTool.value === TOOL_MODES.RECTANGLE) {
      let left = Math.min(this.startPoint.x, pointer.x)
      let top = Math.min(this.startPoint.y, pointer.y)
      let width = Math.abs(pointer.x - this.startPoint.x)
      let height = Math.abs(pointer.y - this.startPoint.y)

      const snapResult = this.calculateRectSnap(left, top, width, height)
      
      if (snapResult.snapped) {
        this.showGuidelines(this.currentSnapInfo.value)
        left = snapResult.left
        top = snapResult.top
      } else {
        this.clearGuidelines()
      }

      this.drawingObject.set({ left, top, width, height })
    } else if (this.currentTool.value === TOOL_MODES.ARROW) {
      const endSnap = this.applySnapToObject(this.drawingObject, pointer)
      this.drawingObject.set({ x2: endSnap.x, y2: endSnap.y })
    }

    this.canvas.renderAll()
  }

  onMouseUp(e) {
    if (this.isPanning) {
      this.isPanning = false
      this.lastPanPoint = null
      this.canvas.defaultCursor = 'grab'
      return
    }

    this.clearGuidelines()
    this.currentSnapInfo.value = null

    if (this.draggingAnnotationId && this.prevCoords) {
      const obj = this.findObjectById(this.draggingAnnotationId)
      if (obj) {
        const newLeft = obj.left
        const newTop = obj.top
        const newWidth = obj.width * obj.scaleX
        const newHeight = obj.height * obj.scaleY
        
        const hasMoved = Math.abs(newLeft - this.prevCoords.left) > 1 || 
                        Math.abs(newTop - this.prevCoords.top) > 1
        const hasResized = Math.abs(newWidth - this.prevCoords.width) > 1 || 
                           Math.abs(newHeight - this.prevCoords.height) > 1

        if (hasMoved || hasResized) {
          const annotation = this.annotations.value.find(a => a.id === this.draggingAnnotationId)
          if (annotation) {
            const opType = hasResized ? 'resize' : 'move'
            const data = {
              canvasCoords: {
                left: newLeft,
                top: newTop,
                width: newWidth,
                height: newHeight
              },
              prevLeft: this.prevCoords.left,
              prevTop: this.prevCoords.top,
              prevWidth: this.prevCoords.width,
              prevHeight: this.prevCoords.height
            }
            
            const operation = this.ot.createOperation(opType, annotation.id, data, this.userId)
            this.emit('ot:operation', operation)
          }
        }
      }
      this.draggingAnnotationId = null
      this.prevCoords = null
    }

    if (!this.isDrawing || !this.drawingObject) {
      this.isDrawing = false
      return
    }

    const pointer = this.canvas.getPointer(e.e)
    const minSize = 5

    if (this.currentTool.value === TOOL_MODES.RECTANGLE) {
      const width = Math.abs(pointer.x - this.startPoint.x)
      const height = Math.abs(pointer.y - this.startPoint.y)

      if (width < minSize || height < minSize) {
        this.canvas.remove(this.drawingObject)
        this.drawingObject = null
        this.isDrawing = false
        return
      }
    } else if (this.currentTool.value === TOOL_MODES.ARROW) {
      const dx = pointer.x - this.startPoint.x
      const dy = pointer.y - this.startPoint.y
      const length = Math.sqrt(dx * dx + dy * dy)

      if (length < minSize) {
        this.canvas.remove(this.drawingObject)
        this.drawingObject = null
        this.isDrawing = false
        return
      }
    }

    this.finalizeDrawing()
  }

  finalizeDrawing() {
    const obj = this.drawingObject
    obj.set({
      selectable: true,
      evented: true,
      isDrawing: false,
      id: `ann_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    })

    if (obj.annotationType === ANNOTATION_TYPES.ARROW) {
      obj.set({
        strokeWidth: 3,
        hasBorders: true,
        hasControls: true
      })
      this.addArrowHead(obj)
    }

    const annotation = this.createAnnotationData(obj)
    obj.annotationId = annotation.id

    const operation = this.ot.createOperation('create', annotation.id, annotation, this.userId)
    this.annotations.value = this.ot.applyOperation(operation, this.annotations.value)
    
    this.saveHistory('add', annotation)
    this.emit('annotation:add', annotation)
    this.emit('ot:operation', operation)

    this.drawingObject = null
    this.isDrawing = false
    this.canvas.setActiveObject(obj)
    this.canvas.renderAll()
  }

  addArrowHead(line) {
    const x1 = line.x1, y1 = line.y1, x2 = line.x2, y2 = line.y2
    const angle = Math.atan2(y2 - y1, x2 - x1)
    const headLength = 15
    const headWidth = 8

    const points = [
      { x: x2, y: y2 },
      { x: x2 - headLength * Math.cos(angle - Math.PI / 6), y: y2 - headLength * Math.sin(angle - Math.PI / 6) },
      { x: x2 - headLength * Math.cos(angle + Math.PI / 6), y: y2 - headLength * Math.sin(angle + Math.PI / 6) }
    ]

    const triangle = new fabric.Polygon(points, {
      fill: line.stroke,
      stroke: line.stroke,
      strokeWidth: 1,
      selectable: false,
      evented: false
    })

    const group = new fabric.Group([line, triangle], {
      selectable: true,
      evented: true,
      annotationType: ANNOTATION_TYPES.ARROW,
      category: line.category,
      label: line.label || '',
      id: line.id
    })

    this.canvas.remove(line)
    this.canvas.add(group)

    return group
  }

  showTextInput(position, category, color) {
    if (this.textInput) {
      this.textInput.remove()
    }

    const input = document.createElement('input')
    input.type = 'text'
    input.placeholder = '输入文本...'
    input.style.position = 'absolute'
    input.style.left = `${position.x}px`
    input.style.top = `${position.y}px`
    input.style.zIndex = '1000'
    input.style.padding = '8px 12px'
    input.style.border = `2px solid ${color}`
    input.style.borderRadius = '4px'
    input.style.fontSize = '14px'
    input.style.outline = 'none'
    input.style.background = '#fff'
    input.style.minWidth = '150px'

    this.container.appendChild(input)
    input.focus()
    this.textInput = input

    const finishText = (cancel = false) => {
      const text = input.value.trim()
      input.remove()
      this.textInput = null

      if (!cancel && text) {
        this.createTextAnnotation(position, text, category, color)
      }
    }

    input.addEventListener('blur', () => finishText(false))
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        input.blur()
      } else if (e.key === 'Escape') {
        finishText(true)
      }
    })
  }

  createTextAnnotation(position, text, category, color) {
    const textObj = new fabric.Textbox(text, {
      left: position.x,
      top: position.y,
      fontSize: 16,
      fill: color,
      backgroundColor: 'rgba(255, 255, 255, 0.9)',
      padding: 4,
      selectable: true,
      evented: true,
      annotationType: ANNOTATION_TYPES.TEXT,
      category: category,
      label: text,
      id: `ann_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      editable: true
    })

    this.canvas.add(textObj)
    const annotation = this.createAnnotationData(textObj)
    textObj.annotationId = annotation.id

    const operation = this.ot.createOperation('create', annotation.id, annotation, this.userId)
    this.annotations.value = this.ot.applyOperation(operation, this.annotations.value)
    
    this.saveHistory('add', annotation)
    this.emit('annotation:add', annotation)
    this.emit('ot:operation', operation)

    this.canvas.setActiveObject(textObj)
    this.canvas.renderAll()
  }

  createAnnotationData(obj) {
    const imageCoords = this.canvasToImageCoords(obj)
    const category = obj.category || this.currentCategory.value

    return {
      id: obj.id,
      type: obj.annotationType,
      category: category,
      label: obj.label || '',
      createdAt: Date.now(),
      updatedAt: Date.now(),
      canvasCoords: {
        left: obj.left,
        top: obj.top,
        width: obj.width * (obj.scaleX || 1),
        height: obj.height * (obj.scaleY || 1),
        x1: obj.x1,
        y1: obj.y1,
        x2: obj.x2,
        y2: obj.y2,
        scaleX: obj.scaleX || 1,
        scaleY: obj.scaleY || 1,
        angle: obj.angle || 0
      },
      imageCoords: imageCoords,
      color: this.getCategoryColor(category)
    }
  }

  canvasToImageCoords(obj) {
    if (!this.imageInfo) return null

    const { offsetX, offsetY, scale } = this.imageInfo
    const getLeft = (o) => o.left - offsetX
    const getTop = (o) => o.top - offsetY

    if (obj.annotationType === ANNOTATION_TYPES.RECTANGLE) {
      return {
        x: getLeft(obj) / scale,
        y: getTop(obj) / scale,
        width: (obj.width * (obj.scaleX || 1)) / scale,
        height: (obj.height * (obj.scaleY || 1)) / scale
      }
    } else if (obj.annotationType === ANNOTATION_TYPES.ARROW) {
      return {
        x1: (obj.x1 - offsetX) / scale,
        y1: (obj.y1 - offsetY) / scale,
        x2: (obj.x2 - offsetX) / scale,
        y2: (obj.y2 - offsetY) / scale
      }
    } else if (obj.annotationType === ANNOTATION_TYPES.TEXT) {
      return {
        x: getLeft(obj) / scale,
        y: getTop(obj) / scale,
        text: obj.text || obj.label
      }
    }
    return null
  }

  imageToCanvasCoords(imageCoords, type) {
    if (!this.imageInfo) return null

    const { offsetX, offsetY, scale } = this.imageInfo

    if (type === ANNOTATION_TYPES.RECTANGLE) {
      return {
        left: imageCoords.x * scale + offsetX,
        top: imageCoords.y * scale + offsetY,
        width: imageCoords.width * scale,
        height: imageCoords.height * scale
      }
    } else if (type === ANNOTATION_TYPES.ARROW) {
      return {
        x1: imageCoords.x1 * scale + offsetX,
        y1: imageCoords.y1 * scale + offsetY,
        x2: imageCoords.x2 * scale + offsetX,
        y2: imageCoords.y2 * scale + offsetY
      }
    } else if (type === ANNOTATION_TYPES.TEXT) {
      return {
        left: imageCoords.x * scale + offsetX,
        top: imageCoords.y * scale + offsetY
      }
    }
    return null
  }

  loadAnnotations(annotations) {
    this.clearAnnotations()

    for (const ann of annotations) {
      try {
        this.addAnnotationFromData(ann)
      } catch (e) {
        console.error('加载标注失败:', e)
      }
    }

    this.annotations.value = [...annotations]
  }

  addAnnotationFromData(annotation) {
    const color = this.getCategoryColor(annotation.category)
    const canvasCoords = this.imageToCanvasCoords(annotation.imageCoords, annotation.type)

    if (!canvasCoords) return null

    let obj = null

    if (annotation.type === ANNOTATION_TYPES.RECTANGLE) {
      obj = new fabric.Rect({
        ...canvasCoords,
        fill: 'transparent',
        stroke: color,
        strokeWidth: 2,
        annotationType: annotation.type,
        category: annotation.category,
        label: annotation.label || '',
        id: annotation.id
      })
    } else if (annotation.type === ANNOTATION_TYPES.ARROW) {
      const line = new fabric.Line(
        [canvasCoords.x1, canvasCoords.y1, canvasCoords.x2, canvasCoords.y2],
        {
          stroke: color,
          strokeWidth: 3,
          annotationType: annotation.type,
          category: annotation.category,
          label: annotation.label || '',
          id: annotation.id
        }
      )
      obj = this.addArrowHead(line)
    } else if (annotation.type === ANNOTATION_TYPES.TEXT) {
      obj = new fabric.Textbox(annotation.label || annotation.imageCoords?.text || '', {
        ...canvasCoords,
        fontSize: 16,
        fill: color,
        backgroundColor: 'rgba(255, 255, 255, 0.9)',
        padding: 4,
        annotationType: annotation.type,
        category: annotation.category,
        label: annotation.label || '',
        id: annotation.id
      })
    }

    if (obj) {
      obj.annotationId = annotation.id
      this.canvas.add(obj)
      this.canvas.renderAll()
    }

    return obj
  }

  updateAnnotation(annotationId, updates) {
    const obj = this.findObjectById(annotationId)
    if (!obj) return null

    if (updates.category) {
      const color = this.getCategoryColor(updates.category)
      if (obj.type === 'group') {
        obj.getObjects().forEach(o => {
          if (o.type === 'line') o.set('stroke', color)
          if (o.type === 'polygon') {
            o.set('fill', color)
            o.set('stroke', color)
          }
        })
      } else {
        if (obj.type === 'rect') obj.set('stroke', color)
        if (obj.type === 'textbox') obj.set('fill', color)
      }
      obj.category = updates.category
    }

    if (updates.label !== undefined) {
      obj.label = updates.label
      if (obj.type === 'textbox') {
        obj.setText(updates.label)
      }
    }

    this.canvas.renderAll()

    const annIndex = this.annotations.value.findIndex(a => a.id === annotationId)
    if (annIndex !== -1) {
      const updated = {
        ...this.annotations.value[annIndex],
        ...updates,
        updatedAt: Date.now(),
        canvasCoords: this.createAnnotationData(obj).canvasCoords,
        imageCoords: this.canvasToImageCoords(obj)
      }
      this.annotations.value[annIndex] = updated
      this.saveHistory('update', updated)
      this.emit('annotation:update', updated)
      return updated
    }

    return null
  }

  deleteAnnotation(annotationId) {
    if (!this.canvas) return null
    
    const obj = this.findObjectById(annotationId)
    if (obj) {
      this.canvas.remove(obj)
    }

    const annIndex = this.annotations.value.findIndex(a => a.id === annotationId)
    if (annIndex !== -1) {
      const deleted = this.annotations.value[annIndex]
      
      const operation = this.ot.createOperation('delete', annotationId, deleted, this.userId)
      this.annotations.value = this.ot.applyOperation(operation, this.annotations.value)
      
      this.saveHistory('delete', deleted)
      this.emit('annotation:delete', deleted)
      this.emit('ot:operation', operation)
      
      return deleted
    }

    return null
  }

  applyRemoteOperation(operation) {
    const { type, annotationId, data } = operation
    
    switch (type) {
      case 'create': {
        const existing = this.annotations.value.find(a => a.id === annotationId)
        if (!existing) {
          this.annotations.value = this.ot.applyOperation(operation, this.annotations.value)
          this.addAnnotationFromData(data)
          this.saveHistory('add', data)
          this.emit('annotation:add', data)
        }
        break
      }
      case 'update':
      case 'move':
      case 'resize': {
        const obj = this.findObjectById(annotationId)
        if (obj && data.canvasCoords) {
          const { left, top, width, height } = data.canvasCoords
          
          if (obj.type === 'rect' || obj.type === 'image') {
            obj.set({ left, top, width, height })
          } else if (obj.type === 'group') {
            obj.set({ left, top })
            obj.setCoords()
          }
          
          this.canvas.renderAll()
        }
        
        this.annotations.value = this.ot.applyOperation(operation, this.annotations.value)
        const updated = this.annotations.value.find(a => a.id === annotationId)
        if (updated) {
          this.saveHistory('update', updated)
          this.emit('annotation:update', updated)
        }
        break
      }
      case 'delete': {
        const obj = this.findObjectById(annotationId)
        if (obj) {
          this.canvas.remove(obj)
        }
        this.annotations.value = this.ot.applyOperation(operation, this.annotations.value)
        this.saveHistory('delete', data)
        this.emit('annotation:delete', data)
        break
      }
    }
    
    this.canvas.renderAll()
  }

  findObjectById(annotationId) {
    if (!this.canvas) return null
    return this.canvas.getObjects().find(obj => obj.annotationId === annotationId)
  }

  clearAnnotations() {
    if (!this.canvas) return
    const objects = this.canvas.getObjects().filter(obj => obj !== this.backgroundImage)
    objects.forEach(obj => this.canvas.remove(obj))
    this.annotations.value = []
    this.selectedAnnotation.value = null
    this.canvas.renderAll()
  }

  clearCanvas() {
    if (!this.canvas) return
    this.canvas.clear()
    this.annotations.value = []
    this.selectedAnnotation.value = null
    this.backgroundImage = null
    this.imageInfo = null
    this.historyStack = []
    this.redoStack = []
  }

  onObjectModified(e) {
    const obj = e.target
    if (!obj || obj === this.backgroundImage || obj.isGuideline) return

    const annotationId = obj.annotationId
    if (annotationId) {
      const annIndex = this.annotations.value.findIndex(a => a.id === annotationId)
      if (annIndex !== -1) {
        const canvasCoords = this.createAnnotationData(obj).canvasCoords
        const imageCoords = this.canvasToImageCoords(obj)
        const updated = {
          ...this.annotations.value[annIndex],
          updatedAt: Date.now(),
          canvasCoords,
          imageCoords
        }
        
        const operation = this.ot.createOperation('update', annotationId, {
          canvasCoords,
          imageCoords,
          label: updated.label
        }, this.userId)
        
        this.annotations.value = this.ot.applyOperation(operation, this.annotations.value)
        this.saveHistory('update', updated)
        this.emit('annotation:update', updated)
        this.emit('ot:operation', operation)
      }
    }
  }

  onObjectSelected(e) {
    const obj = e.target
    if (obj && obj.annotationId) {
      this.selectedAnnotation.value = this.annotations.value.find(a => a.id === obj.annotationId)
      this.emit('annotation:select', this.selectedAnnotation.value)
    }
  }

  onSelectionCleared() {
    this.selectedAnnotation.value = null
    this.emit('annotation:select', null)
  }

  onKeyDown(e) {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return

    if ((e.key === 'Delete' || e.key === 'Backspace') && this.selectedAnnotation.value) {
      e.preventDefault()
      this.deleteAnnotation(this.selectedAnnotation.value.id)
    }

    if (e.ctrlKey || e.metaKey) {
      if (e.key === 'z' && !e.shiftKey) {
        e.preventDefault()
        this.undo()
      } else if (e.key === 'y' || (e.key === 'z' && e.shiftKey)) {
        e.preventDefault()
        this.redo()
      } else if (e.key === 'a') {
        e.preventDefault()
        if (this.currentTool.value === TOOL_MODES.SELECT) {
          const selectable = this.canvas.getObjects().filter(obj => obj !== this.backgroundImage)
          this.canvas.setActiveObject(new fabric.ActiveSelection(selectable, { canvas: this.canvas }))
          this.canvas.renderAll()
        }
      }
    }

    if (e.key === 'Escape') {
      if (this.textInput) {
        this.textInput.remove()
        this.textInput = null
      }
      if (this.drawingObject) {
        this.canvas.remove(this.drawingObject)
        this.drawingObject = null
      }
      this.isDrawing = false
      this.canvas.discardActiveObject()
      this.canvas.renderAll()
    }

    if (e.key === 'v' || e.key === 'V') this.setTool(TOOL_MODES.SELECT)
    if (e.key === 'r' || e.key === 'R') this.setTool(TOOL_MODES.RECTANGLE)
    if (e.key === 'a' || e.key === 'A') this.setTool(TOOL_MODES.ARROW)
    if (e.key === 't' || e.key === 'T') this.setTool(TOOL_MODES.TEXT)
    if (e.key === 'h' || e.key === 'H') this.setTool(TOOL_MODES.PAN)
  }

  onMouseWheel(e) {
    e.e.preventDefault()
    e.e.stopPropagation()

    const delta = e.e.deltaY > 0 ? 0.9 : 1.1
    const pointer = this.canvas.getPointer(e.e)

    this.canvas.zoomToPoint({ x: pointer.x, y: pointer.y }, this.canvas.getZoom() * delta)
    this.zoom = this.canvas.getZoom()
  }

  saveHistory(action, data) {
    const snapshot = JSON.stringify(this.annotations.value)
    this.historyStack.push({ action, data, snapshot, timestamp: Date.now() })

    if (this.historyStack.length > this.maxHistory) {
      this.historyStack.shift()
    }

    this.redoStack = []
  }

  undo() {
    if (!this.canvas || this.historyStack.length === 0) return null

    const history = this.historyStack.pop()
    this.redoStack.push(history)

    if (this.historyStack.length > 0) {
      const prevSnapshot = this.historyStack[this.historyStack.length - 1].snapshot
      const annotations = JSON.parse(prevSnapshot)
      this.loadAnnotations(annotations)
    } else {
      this.clearAnnotations()
    }

    this.emit('undo', history)
    return history
  }

  redo() {
    if (!this.canvas || this.redoStack.length === 0) return null

    const history = this.redoStack.pop()
    this.historyStack.push(history)

    const annotations = JSON.parse(history.snapshot)
    this.loadAnnotations(annotations)

    this.emit('redo', history)
    return history
  }

  isInImageBounds(pointer) {
    if (!this.backgroundImage || !this.imageInfo) return false

    const { offsetX, offsetY, displayWidth, displayHeight } = this.imageInfo
    return (
      pointer.x >= offsetX &&
      pointer.x <= offsetX + displayWidth &&
      pointer.y >= offsetY &&
      pointer.y <= offsetY + displayHeight
    )
  }

  addRemoteCursor(userId, user) {
    if (this.remoteCursors.has(userId)) {
      this.removeRemoteCursor(userId)
    }

    const cursor = new fabric.Group([
      new fabric.Line([0, 0, 10, 0], {
        stroke: user.color,
        strokeWidth: 2,
        selectable: false,
        evented: false
      }),
      new fabric.Line([0, 0, 0, 10], {
        stroke: user.color,
        strokeWidth: 2,
        selectable: false,
        evented: false
      }),
      new fabric.Text(user.name, {
        fontSize: 12,
        fill: '#fff',
        backgroundColor: user.color,
        padding: 2,
        left: 8,
        top: 8,
        selectable: false,
        evented: false
      })
    ], {
      selectable: false,
      evented: false,
      visible: false
    })

    this.remoteCursors.set(userId, { cursor, user })
    this.canvas.add(cursor)
  }

  updateRemoteCursor(userId, position) {
    const remote = this.remoteCursors.get(userId)
    if (remote) {
      remote.cursor.set({
        left: position.x,
        top: position.y,
        visible: true
      })
      this.canvas.renderAll()
    }
  }

  removeRemoteCursor(userId) {
    const remote = this.remoteCursors.get(userId)
    if (remote) {
      this.canvas.remove(remote.cursor)
      this.remoteCursors.delete(userId)
      this.canvas.renderAll()
    }
  }

  showAnnotations(show = true) {
    this.canvas.getObjects().forEach(obj => {
      if (obj !== this.backgroundImage && !this.remoteCursors.has(obj.annotationId)) {
        obj.visible = show
      }
    })
    this.canvas.renderAll()
  }

  on(eventType, callback) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set())
    }
    this.listeners.get(eventType).add(callback)
    return () => this.off(eventType, callback)
  }

  off(eventType, callback) {
    if (this.listeners.has(eventType)) {
      this.listeners.get(eventType).delete(callback)
    }
  }

  emit(eventType, data) {
    if (this.listeners.has(eventType)) {
      this.listeners.get(eventType).forEach(callback => {
        try {
          callback(data)
        } catch (error) {
          console.error(`画布事件错误 [${eventType}]:`, error)
        }
      })
    }
  }

  destroy() {
    if (this.canvas) {
      this.canvas.dispose()
      this.canvas = null
    }
    if (this.textInput) {
      this.textInput.remove()
    }
    this.listeners.clear()
    this.remoteCursors.clear()
    window.removeEventListener('resize', () => this.handleResize())
    document.removeEventListener('keydown', (e) => this.onKeyDown(e))
  }
}

export const canvasManager = new CanvasManager()
export default canvasManager

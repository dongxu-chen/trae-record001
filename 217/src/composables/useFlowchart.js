import { ref } from 'vue'
import { fabric } from 'fabric'

let nodeIdCounter = 0
let connectionIdCounter = 0
let commentIdCounter = 0

export function useFlowchart() {
  const nodes = ref([])
  const connections = ref([])
  const comments = ref([])
  const selectedNode = ref(null)
  const collaborators = ref([])
  let isConnecting = false
  let connectionStart = null
  let tempLine = null
  let onConnectionCreated = null

  const nodeConfigs = {
    start: {
      width: 100,
      height: 50,
      fill: '#28a745',
      label: '开始',
      shape: 'circle'
    },
    end: {
      width: 100,
      height: 50,
      fill: '#dc3545',
      label: '结束',
      shape: 'circle'
    },
    process: {
      width: 120,
      height: 60,
      fill: '#007bff',
      label: '处理',
      shape: 'rect'
    },
    decision: {
      width: 100,
      height: 80,
      fill: '#ffc107',
      label: '判断',
      shape: 'diamond'
    }
  }

  const initCanvas = (canvasElement, width, height, connectionCallback) => {
    const canvas = new fabric.Canvas(canvasElement, {
      width: width,
      height: height,
      backgroundColor: '#ffffff',
      selection: true
    })

    onConnectionCreated = connectionCallback
    setupConnectionHandlers(canvas)
    return canvas
  }

  const canConnect = (fromNodeId, toNodeId) => {
    if (fromNodeId === toNodeId) {
      return { valid: false, reason: 'SELF_LOOP', message: '不能连接到自身' }
    }

    const exists = connections.value.some(
      c => c.fromNodeId === fromNodeId && c.toNodeId === toNodeId
    )
    if (exists) {
      return { valid: false, reason: 'DUPLICATE', message: '连线已存在' }
    }

    return { valid: true }
  }

  const setupConnectionHandlers = (canvas) => {
    canvas.on('mouse:down', (opt) => {
      const target = opt.target
      if (target && target.nodeId && !target.isConnection) {
        isConnecting = true
        connectionStart = target
        
        const center = target.getCenterPoint()
        const points = [center.x, center.y, center.x, center.y]
        
        tempLine = new fabric.Line(points, {
          stroke: '#666',
          strokeWidth: 2,
          strokeDashArray: [5, 5],
          selectable: false,
          evented: false
        })
        canvas.add(tempLine)
      }
    })

    canvas.on('mouse:move', (opt) => {
      if (isConnecting && tempLine) {
        const pointer = canvas.getPointer(opt.e)
        tempLine.set({ x2: pointer.x, y2: pointer.y })
        canvas.renderAll()
      }
    })

    canvas.on('mouse:up', (opt) => {
      if (isConnecting && tempLine) {
        const target = opt.target
        if (target && target.nodeId && target !== connectionStart && !target.isConnection) {
          const check = canConnect(connectionStart.nodeId, target.nodeId)
          if (check.valid) {
            const conn = createConnectionInternal(connectionStart, target, canvas)
            if (onConnectionCreated && conn) {
              onConnectionCreated(conn)
            }
          }
        }
        canvas.remove(tempLine)
        tempLine = null
        isConnecting = false
        connectionStart = null
      }
    })
  }

  const createArrowHead = (from, to) => {
    const angle = Math.atan2(to.y - from.y, to.x - from.x)
    const headLength = 10

    const points = [
      to.x - headLength * Math.cos(angle - Math.PI / 6),
      to.y - headLength * Math.sin(angle - Math.PI / 6),
      to.x,
      to.y,
      to.x - headLength * Math.cos(angle + Math.PI / 6),
      to.y - headLength * Math.sin(angle + Math.PI / 6)
    ]

    return new fabric.Polyline(points, {
      stroke: '#333',
      strokeWidth: 2,
      fill: '#333',
      selectable: false
    })
  }

  const createConnectionInternal = (fromObj, toObj, canvas) => {
    const fromCenter = fromObj.getCenterPoint()
    const toCenter = toObj.getCenterPoint()

    const line = new fabric.Line([fromCenter.x, fromCenter.y, toCenter.x, toCenter.y], {
      stroke: '#333',
      strokeWidth: 2,
      selectable: true,
      hasControls: false,
      isConnection: true
    })

    const arrow = createArrowHead(fromCenter, toCenter)

    const connId = ++connectionIdCounter
    const connectionGroup = new fabric.Group([line, arrow], {
      selectable: true,
      hasControls: false,
      isConnection: true,
      connectionId: connId,
      fromNodeId: fromObj.nodeId,
      toNodeId: toObj.nodeId
    })

    canvas.add(connectionGroup)
    canvas.sendToBack(connectionGroup)

    const connData = {
      id: connId,
      fromNodeId: fromObj.nodeId,
      toNodeId: toObj.nodeId,
      fabricObject: connectionGroup
    }

    connections.value.push(connData)
    return connData
  }

  const addConnectionFromData = (connData, canvas) => {
    const id = connData.id
    if (id > connectionIdCounter) connectionIdCounter = id

    const fromNode = nodes.value.find(n => n.id === connData.fromNodeId)
    const toNode = nodes.value.find(n => n.id === connData.toNodeId)
    
    if (fromNode && toNode && fromNode.fabricObject && toNode.fabricObject) {
      const fromCenter = fromNode.fabricObject.getCenterPoint()
      const toCenter = toNode.fabricObject.getCenterPoint()

      const line = new fabric.Line([fromCenter.x, fromCenter.y, toCenter.x, toCenter.y], {
        stroke: '#333',
        strokeWidth: 2,
        selectable: true,
        hasControls: false,
        isConnection: true
      })

      const arrow = createArrowHead(fromCenter, toCenter)

      const connectionGroup = new fabric.Group([line, arrow], {
        selectable: true,
        hasControls: false,
        isConnection: true,
        connectionId: connData.id,
        fromNodeId: connData.fromNodeId,
        toNodeId: connData.toNodeId
      })

      canvas.add(connectionGroup)
      canvas.sendToBack(connectionGroup)

      const existing = connections.value.find(c => c.id === connData.id)
      if (existing) {
        existing.fabricObject = connectionGroup
      } else {
        connections.value.push({
          ...connData,
          fabricObject: connectionGroup
        })
      }
    }
  }

  const updateConnections = (canvas) => {
    connections.value.forEach(conn => {
      const fromNode = nodes.value.find(n => n.id === conn.fromNodeId)
      const toNode = nodes.value.find(n => n.id === conn.toNodeId)
      
      if (fromNode && toNode && conn.fabricObject) {
        const fromObj = fromNode.fabricObject
        const toObj = toNode.fabricObject
        
        if (fromObj && toObj) {
          const fromCenter = fromObj.getCenterPoint()
          const toCenter = toObj.getCenterPoint()
          
          const line = conn.fabricObject.item(0)
          line.set({
            x1: fromCenter.x,
            y1: fromCenter.y,
            x2: toCenter.x,
            y2: toCenter.y
          })

          const newArrow = createArrowHead(fromCenter, toCenter)
          conn.fabricObject.removeWithUpdate(conn.fabricObject.item(1))
          conn.fabricObject.addWithUpdate(newArrow)
        }
      }
    })
    canvas.renderAll()
  }

  const createFabricNode = (nodeType, x, y, nodeData, canvas) => {
    const config = nodeConfigs[nodeType]
    let shape

    switch (config.shape) {
      case 'circle':
        shape = new fabric.Circle({
          radius: config.width / 2,
          fill: config.fill,
          stroke: '#333',
          strokeWidth: 2,
          originX: 'center',
          originY: 'center'
        })
        break
      case 'rect':
        shape = new fabric.Rect({
          width: config.width,
          height: config.height,
          fill: config.fill,
          stroke: '#333',
          strokeWidth: 2,
          rx: 5,
          ry: 5,
          originX: 'center',
          originY: 'center'
        })
        break
      case 'diamond':
        const diamondPoints = [
          { x: 0, y: -config.height / 2 },
          { x: config.width / 2, y: 0 },
          { x: 0, y: config.height / 2 },
          { x: -config.width / 2, y: 0 }
        ]
        shape = new fabric.Polygon(diamondPoints, {
          fill: config.fill,
          stroke: '#333',
          strokeWidth: 2,
          originX: 'center',
          originY: 'center'
        })
        break
    }

    const text = new fabric.Text(nodeData.name || config.label, {
      fontSize: 14,
      fill: '#fff',
      originX: 'center',
      originY: 'center',
      fontWeight: 'bold'
    })

    const group = new fabric.Group([shape, text], {
      left: x,
      top: y,
      selectable: true,
      hasControls: true,
      nodeId: nodeData.id,
      nodeType: nodeType
    })

    return group
  }

  const addNode = (nodeType, x, y, canvas) => {
    const config = nodeConfigs[nodeType]
    const nodeId = ++nodeIdCounter
    
    const nodeData = {
      id: nodeId,
      nodeType: nodeType,
      name: config.label,
      description: '',
      x: x,
      y: y
    }

    return addNodeFromData(nodeData, canvas)
  }

  const addNodeFromData = (nodeData, canvas) => {
    const id = nodeData.id
    if (id > nodeIdCounter) nodeIdCounter = id

    const fabricObject = createFabricNode(nodeData.nodeType, nodeData.x, nodeData.y, nodeData, canvas)
    
    fabricObject.on('moving', () => {
      const node = nodes.value.find(n => n.id === id)
      if (node) {
        node.x = fabricObject.left
        node.y = fabricObject.top
        updateConnections(canvas)
      }
    })

    fabricObject.on('modified', () => {
      const node = nodes.value.find(n => n.id === id)
      if (node) {
        node.x = fabricObject.left
        node.y = fabricObject.top
        updateConnections(canvas)
      }
    })

    canvas.add(fabricObject)
    
    const existing = nodes.value.find(n => n.id === id)
    if (existing) {
      existing.fabricObject = fabricObject
      existing.x = nodeData.x
      existing.y = nodeData.y
      existing.name = nodeData.name
      existing.description = nodeData.description
    } else {
      nodes.value.push({
        ...nodeData,
        fabricObject
      })
    }

    return existing || { ...nodeData, fabricObject }
  }

  const moveNode = (nodeId, x, y, canvas) => {
    const node = nodes.value.find(n => n.id === nodeId)
    if (node && node.fabricObject) {
      node.fabricObject.set({ left: x, top: y })
      node.fabricObject.setCoords()
      node.x = x
      node.y = y
      updateConnections(canvas)
    }
  }

  const updateNode = (nodeId, updates, canvas) => {
    const node = nodes.value.find(n => n.id === nodeId)
    if (node) {
      const oldData = { name: node.name, description: node.description }
      Object.assign(node, updates)
      
      if (node.fabricObject && updates.name !== undefined) {
        const text = node.fabricObject.item(1)
        text.set('text', updates.name)
        canvas.renderAll()
      }
      return oldData
    }
    return null
  }

  const deleteNode = (nodeId, canvas) => {
    const nodeIndex = nodes.value.findIndex(n => n.id === nodeId)
    if (nodeIndex > -1) {
      const node = nodes.value[nodeIndex]
      
      const relatedConnections = connections.value.filter(
        c => c.fromNodeId === nodeId || c.toNodeId === nodeId
      )
      
      relatedConnections.forEach(conn => {
        if (conn.fabricObject) {
          canvas.remove(conn.fabricObject)
        }
      })
      
      connections.value = connections.value.filter(
        c => c.fromNodeId !== nodeId && c.toNodeId !== nodeId
      )
      
      if (node.fabricObject) {
        canvas.remove(node.fabricObject)
      }
      
      nodes.value.splice(nodeIndex, 1)
      return { node, relatedConnections }
    }
    return null
  }

  const deleteConnection = (connectionId, canvas) => {
    const connIndex = connections.value.findIndex(c => c.id === connectionId)
    if (connIndex > -1) {
      const conn = connections.value[connIndex]
      if (conn.fabricObject) {
        canvas.remove(conn.fabricObject)
      }
      connections.value.splice(connIndex, 1)
      return conn
    }
    return null
  }

  const selectNodeByFabric = (fabricObj) => {
    const node = nodes.value.find(n => n.id === fabricObj.nodeId)
    if (node) {
      selectedNode.value = node
    }
  }

  const getNodeById = (nodeId) => {
    return nodes.value.find(n => n.id === nodeId)
  }

  const clearAll = (canvas) => {
    nodes.value.forEach(node => {
      if (node.fabricObject) {
        canvas.remove(node.fabricObject)
      }
    })
    
    connections.value.forEach(conn => {
      if (conn.fabricObject) {
        canvas.remove(conn.fabricObject)
      }
    })
    
    nodes.value = []
    connections.value = []
    comments.value = []
    nodeIdCounter = 0
    connectionIdCounter = 0
    commentIdCounter = 0
  }

  const computeLevels = () => {
    if (nodes.value.length === 0) return { levels: {}, maxLevel: 0 }

    const inDegree = new Map()
    const adjList = new Map()
    
    nodes.value.forEach(n => {
      inDegree.set(n.id, 0)
      adjList.set(n.id, [])
    })

    connections.value.forEach(c => {
      if (adjList.has(c.fromNodeId) && inDegree.has(c.toNodeId)) {
        adjList.get(c.fromNodeId).push(c.toNodeId)
        inDegree.set(c.toNodeId, inDegree.get(c.toNodeId) + 1)
      }
    })

    const queue = []
    const levels = new Map()
    
    nodes.value.forEach(n => {
      if (inDegree.get(n.id) === 0) {
        queue.push({ id: n.id, level: 0 })
        levels.set(n.id, 0)
      }
    })

    let maxLevel = 0

    while (queue.length > 0) {
      const { id, level } = queue.shift()
      maxLevel = Math.max(maxLevel, level)

      adjList.get(id).forEach(neighbor => {
        const newLevel = level + 1
        const currentLevel = levels.get(neighbor)
        if (currentLevel === undefined || newLevel > currentLevel) {
          levels.set(neighbor, newLevel)
        }

        inDegree.set(neighbor, inDegree.get(neighbor) - 1)
        if (inDegree.get(neighbor) === 0) {
          queue.push({ id: neighbor, level: levels.get(neighbor) })
        }
      })
    }

    nodes.value.forEach(n => {
      if (!levels.has(n.id)) {
        levels.set(n.id, 0)
      }
    })

    const levelsGrouped = {}
    for (const [nodeId, level] of levels) {
      if (!levelsGrouped[level]) levelsGrouped[level] = []
      levelsGrouped[level].push(nodeId)
    }

    return { levels: levelsGrouped, maxLevel, nodeLevels: levels }
  }

  const minimizeCrossings = (levels, adjList) => {
    const levelKeys = Object.keys(levels).sort((a, b) => a - b)
    
    for (let i = 1; i < levelKeys.length; i++) {
      const currentLevel = levels[levelKeys[i]]
      const prevLevel = levels[levelKeys[i - 1]]
      
      const barycenter = new Map()
      currentLevel.forEach(nodeId => {
        let sum = 0
        let count = 0
        prevLevel.forEach((prevId, idx) => {
          const isConnected = adjList.get(prevId)?.includes(nodeId)
          if (isConnected) {
            sum += idx
            count++
          }
        })
        barycenter.set(nodeId, count > 0 ? sum / count : prevLevel.length / 2)
      })

      currentLevel.sort((a, b) => barycenter.get(a) - barycenter.get(b))
    }

    return levels
  }

  const autoLayout = (canvas) => {
    if (nodes.value.length === 0) return { oldPositions: [], newPositions: [] }

    const oldPositions = nodes.value.map(n => ({
      id: n.id,
      x: n.x,
      y: n.y
    }))

    const { levels, nodeLevels } = computeLevels()

    const adjList = new Map()
    nodes.value.forEach(n => adjList.set(n.id, []))
    connections.value.forEach(c => {
      if (adjList.has(c.fromNodeId)) {
        adjList.get(c.fromNodeId).push(c.toNodeId)
      }
    })

    const optimizedLevels = minimizeCrossings({ ...levels }, adjList)

    const startX = 150
    const startY = 80
    const levelGap = 220
    const nodeGap = 120

    const newPositions = []

    Object.keys(optimizedLevels).sort((a, b) => a - b).forEach((level) => {
      const levelNodeIds = optimizedLevels[level]
      const levelNodes = levelNodeIds
        .map(id => nodes.value.find(n => n.id === id))
        .filter(Boolean)

      const totalHeight = levelNodes.reduce((sum, node) => {
        const config = nodeConfigs[node.nodeType]
        return sum + (config?.height || 60)
      }, 0) + (levelNodes.length - 1) * nodeGap

      let currentY = startY + (canvas.height - totalHeight) / 2

      levelNodes.forEach((node) => {
        const config = nodeConfigs[node.nodeType]
        const nodeHeight = config?.height || 60
        
        const newX = startX + parseInt(level) * levelGap
        const newY = currentY

        newPositions.push({ id: node.id, x: newX, y: newY })

        node.x = newX
        node.y = newY
        
        if (node.fabricObject) {
          node.fabricObject.set({ left: newX, top: newY })
          node.fabricObject.setCoords()
        }
        
        currentY += nodeHeight + nodeGap
      })
    })

    updateConnections(canvas)
    canvas.renderAll()

    return { oldPositions, newPositions }
  }

  const addComment = (nodeId, content, author = '我') => {
    const commentId = ++commentIdCounter
    const comment = {
      id: commentId,
      nodeId,
      content,
      author,
      createdAt: new Date().toISOString(),
      resolved: false,
      resolvedAt: null,
      resolvedBy: null,
      replies: []
    }
    comments.value.push(comment)
    return comment
  }

  const replyComment = (commentId, content, author = '我') => {
    const comment = comments.value.find(c => c.id === commentId)
    if (comment) {
      const reply = {
        id: Date.now(),
        content,
        author,
        createdAt: new Date().toISOString()
      }
      comment.replies.push(reply)
      return reply
    }
    return null
  }

  const resolveComment = (commentId, resolved = true, resolvedBy = '我') => {
    const comment = comments.value.find(c => c.id === commentId)
    if (comment) {
      comment.resolved = resolved
      comment.resolvedAt = resolved ? new Date().toISOString() : null
      comment.resolvedBy = resolved ? resolvedBy : null
      return comment
    }
    return null
  }

  const getNodeComments = (nodeId) => {
    return comments.value.filter(c => c.nodeId === nodeId)
  }

  const addCollaborator = (collaborator) => {
    const existing = collaborators.value.find(c => c.id === collaborator.id)
    if (!existing) {
      collaborators.value.push({
        id: collaborator.id,
        name: collaborator.name,
        color: collaborator.color,
        x: 0,
        y: 0
      })
    }
  }

  const removeCollaborator = (collaboratorId) => {
    const index = collaborators.value.findIndex(c => c.id === collaboratorId)
    if (index > -1) {
      collaborators.value.splice(index, 1)
    }
  }

  const updateCollaboratorPosition = (collaboratorId, x, y) => {
    const collaborator = collaborators.value.find(c => c.id === collaboratorId)
    if (collaborator) {
      collaborator.x = x
      collaborator.y = y
    }
  }

  const exportToJSON = () => {
    return {
      nodes: nodes.value.map(n => ({
        id: n.id,
        nodeType: n.nodeType,
        name: n.name,
        description: n.description,
        x: n.x,
        y: n.y
      })),
      connections: connections.value.map(c => ({
        id: c.id,
        fromNodeId: c.fromNodeId,
        toNodeId: c.toNodeId
      })),
      comments: comments.value.map(c => ({
        id: c.id,
        nodeId: c.nodeId,
        content: c.content,
        author: c.author,
        createdAt: c.createdAt,
        resolved: c.resolved,
        resolvedAt: c.resolvedAt,
        resolvedBy: c.resolvedBy,
        replies: c.replies
      }))
    }
  }

  return {
    nodes,
    connections,
    comments,
    selectedNode,
    collaborators,
    initCanvas,
    addNode,
    addNodeFromData,
    moveNode,
    updateNode,
    deleteNode,
    addConnectionFromData,
    deleteConnection,
    selectNodeByFabric,
    getNodeById,
    clearAll,
    autoLayout,
    exportToJSON,
    updateConnections,
    canConnect,
    nodeConfigs,
    addComment,
    replyComment,
    resolveComment,
    getNodeComments,
    addCollaborator,
    removeCollaborator,
    updateCollaboratorPosition
  }
}

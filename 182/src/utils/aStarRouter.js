const GRID_SIZE = 10
const DIAGONAL_COST = 1.414
const STRAIGHT_COST = 1
const CORNER_PENALTY = 5

class PriorityQueue {
  constructor() {
    this.items = []
  }

  enqueue(item, priority) {
    this.items.push({ item, priority })
    this.items.sort((a, b) => a.priority - b.priority)
  }

  dequeue() {
    return this.items.shift()?.item
  }

  isEmpty() {
    return this.items.length === 0
  }
}

function getNodeBounds(node) {
  return {
    left: node.x,
    right: node.x + node.width,
    top: node.y,
    bottom: node.y + node.height
  }
}

function getNodeCenter(node) {
  return {
    x: node.x + node.width / 2,
    y: node.y + node.height / 2
  }
}

function expandBounds(bounds, padding) {
  return {
    left: bounds.left - padding,
    right: bounds.right + padding,
    top: bounds.top - padding,
    bottom: bounds.bottom + padding
  }
}

function isPointInBounds(px, py, bounds) {
  return px >= bounds.left && px <= bounds.right && py >= bounds.top && py <= bounds.bottom
}

function getConnectionPoint(node, targetX, targetY, padding = 10) {
  const bounds = getNodeBounds(node)
  const center = getNodeCenter(node)

  const dx = targetX - center.x
  const dy = targetY - center.y

  if (Math.abs(dx) * node.height > Math.abs(dy) * node.width) {
    if (dx > 0) {
      return { x: bounds.right + padding, y: center.y }
    } else {
      return { x: bounds.left - padding, y: center.y }
    }
  } else {
    if (dy > 0) {
      return { x: center.x, y: bounds.bottom + padding }
    } else {
      return { x: center.x, y: bounds.top - padding }
    }
  }
}

function createGrid(nodes, sourceNode, targetNode, padding = 20) {
  let minX = Infinity
  let maxX = -Infinity
  let minY = Infinity
  let maxY = -Infinity

  const sourceBounds = expandBounds(getNodeBounds(sourceNode), padding)
  const targetBounds = expandBounds(getNodeBounds(targetNode), padding)

  minX = Math.min(sourceBounds.left, targetBounds.left)
  maxX = Math.max(sourceBounds.right, targetBounds.right)
  minY = Math.min(sourceBounds.top, targetBounds.top)
  maxY = Math.max(sourceBounds.bottom, targetBounds.bottom)

  nodes.forEach(node => {
    if (node.id === sourceNode.id || node.id === targetNode.id) return
    if (node.collapsed) return
    const bounds = expandBounds(getNodeBounds(node), padding)
    minX = Math.min(minX, bounds.left)
    maxX = Math.max(maxX, bounds.right)
    minY = Math.min(minY, bounds.top)
    maxY = Math.max(maxY, bounds.bottom)
  })

  minX -= GRID_SIZE * 5
  maxX += GRID_SIZE * 5
  minY -= GRID_SIZE * 5
  maxY += GRID_SIZE * 5

  const cols = Math.ceil((maxX - minX) / GRID_SIZE)
  const rows = Math.ceil((maxY - minY) / GRID_SIZE)

  const grid = []
  for (let y = 0; y < rows; y++) {
    grid[y] = []
    for (let x = 0; x < cols; x++) {
      const wx = minX + x * GRID_SIZE
      const wy = minY + y * GRID_SIZE
      let blocked = false

      for (const node of nodes) {
        if (node.id === sourceNode.id || node.id === targetNode.id) continue
        if (node.collapsed) continue
        const bounds = expandBounds(getNodeBounds(node), padding / 2)
        if (isPointInBounds(wx, wy, bounds)) {
          blocked = true
          break
        }
      }

      grid[y][x] = {
        x,
        y,
        wx,
        wy,
        blocked,
        g: 0,
        h: 0,
        f: 0,
        parent: null
      }
    }
  }

  return { grid, minX, minY, cols, rows }
}

function worldToGrid(wx, wy, minX, minY) {
  return {
    x: Math.floor((wx - minX) / GRID_SIZE),
    y: Math.floor((wy - minY) / GRID_SIZE)
  }
}

function gridToWorld(gx, gy, minX, minY) {
  return {
    x: minX + gx * GRID_SIZE + GRID_SIZE / 2,
    y: minY + gy * GRID_SIZE + GRID_SIZE / 2
  }
}

function heuristic(a, b) {
  const dx = Math.abs(a.wx - b.wx)
  const dy = Math.abs(a.wy - b.wy)
  return Math.max(dx, dy) + 0.4 * Math.min(dx, dy)
}

function getNeighbors(grid, node) {
  const neighbors = []
  const { x, y } = node
  const rows = grid.length
  const cols = grid[0].length

  const directions = [
    { dx: 0, dy: -1, cost: STRAIGHT_COST },
    { dx: 1, dy: 0, cost: STRAIGHT_COST },
    { dx: 0, dy: 1, cost: STRAIGHT_COST },
    { dx: -1, dy: 0, cost: STRAIGHT_COST },
    { dx: 1, dy: -1, cost: DIAGONAL_COST },
    { dx: 1, dy: 1, cost: DIAGONAL_COST },
    { dx: -1, dy: 1, cost: DIAGONAL_COST },
    { dx: -1, dy: -1, cost: DIAGONAL_COST }
  ]

  for (const dir of directions) {
    const nx = x + dir.dx
    const ny = y + dir.dy

    if (nx >= 0 && nx < cols && ny >= 0 && ny < rows) {
      const neighbor = grid[ny][nx]
      if (!neighbor.blocked) {
        if (dir.cost === DIAGONAL_COST) {
          if (grid[y][nx].blocked || grid[ny][x].blocked) {
            continue
          }
        }
        neighbor.moveCost = dir.cost
        neighbors.push(neighbor)
      }
    }
  }

  return neighbors
}

function getDirectionChangePenalty(parent, current, neighbor) {
  if (!parent) return 0

  const dx1 = current.x - parent.x
  const dy1 = current.y - parent.y
  const dx2 = neighbor.x - current.x
  const dy2 = neighbor.y - current.y

  if (dx1 !== dx2 || dy1 !== dy2) {
    return CORNER_PENALTY
  }
  return 0
}

function aStar(grid, start, goal) {
  const openSet = new PriorityQueue()
  const closedSet = new Set()

  start.g = 0
  start.h = heuristic(start, goal)
  start.f = start.g + start.h

  openSet.enqueue(start, start.f)

  while (!openSet.isEmpty()) {
    const current = openSet.dequeue()
    const currentKey = `${current.x},${current.y}`

    if (current.x === goal.x && current.y === goal.y) {
      const path = []
      let node = current
      while (node) {
        path.unshift({ x: node.wx, y: node.wy })
        node = node.parent
      }
      return path
    }

    if (closedSet.has(currentKey)) continue
    closedSet.add(currentKey)

    const neighbors = getNeighbors(grid, current)
    for (const neighbor of neighbors) {
      const neighborKey = `${neighbor.x},${neighbor.y}`
      if (closedSet.has(neighborKey)) continue

      const directionPenalty = getDirectionChangePenalty(current.parent, current, neighbor)
      const tentativeG = current.g + neighbor.moveCost + directionPenalty

      if (tentativeG < neighbor.g || !neighbor.parent) {
        neighbor.parent = current
        neighbor.g = tentativeG
        neighbor.h = heuristic(neighbor, goal)
        neighbor.f = neighbor.g + neighbor.h
        openSet.enqueue(neighbor, neighbor.f)
      }
    }
  }

  return null
}

function simplifyPath(path, maxPoints = 12) {
  if (path.length <= 2) return path

  const simplified = [path[0]]
  let lastDirection = null

  for (let i = 1; i < path.length - 1; i++) {
    const prev = simplified[simplified.length - 1]
    const curr = path[i]
    const next = path[i + 1]

    const dx1 = curr.x - prev.x
    const dy1 = curr.y - prev.y
    const dx2 = next.x - curr.x
    const dy2 = next.y - curr.y

    const direction = { dx1, dy1, dx2, dy2 }

    const directionChanged = Math.sign(dx1) !== Math.sign(dx2) || Math.sign(dy1) !== Math.sign(dy2)
    const axisChanged = (dx1 !== 0 && dx2 === 0) || (dy1 !== 0 && dy2 === 0)

    if (directionChanged || axisChanged) {
      simplified.push(curr)
      lastDirection = direction
    }
  }

  simplified.push(path[path.length - 1])

  if (simplified.length > maxPoints) {
    const result = [simplified[0]]
    const step = (simplified.length - 1) / (maxPoints - 1)
    for (let i = 1; i < maxPoints - 1; i++) {
      const idx = Math.round(i * step)
      result.push(simplified[idx])
    }
    result.push(simplified[simplified.length - 1])
    return result
  }

  return simplified
}

function snapToCardinal(path, startNode, endNode) {
  if (path.length < 2) return path

  const startCenter = getNodeCenter(startNode)
  const endCenter = getNodeCenter(endNode)

  const result = []

  const firstPoint = path[0]
  const snapTo = { ...firstPoint }
  if (Math.abs(firstPoint.x - startCenter.x) < Math.abs(firstPoint.y - startCenter.y)) {
    snapTo.x = startCenter.x
  } else {
    snapTo.y = startCenter.y
  }
  result.push(snapTo)

  for (let i = 1; i < path.length - 1; i++) {
    const prev = result[result.length - 1]
    const curr = path[i]

    if (Math.abs(curr.x - prev.x) < 5) {
      result.push({ x: prev.x, y: curr.y })
    } else if (Math.abs(curr.y - prev.y) < 5) {
      result.push({ x: curr.x, y: prev.y })
    } else {
      result.push({ x: curr.x, y: prev.y })
      result.push({ x: curr.x, y: curr.y })
    }
  }

  const lastPoint = path[path.length - 1]
  const lastSnap = { ...lastPoint }
  if (Math.abs(lastPoint.x - endCenter.x) < Math.abs(lastPoint.y - endCenter.y)) {
    lastSnap.x = endCenter.x
  } else {
    lastSnap.y = endCenter.y
  }

  const prev = result[result.length - 1]
  if (Math.abs(lastSnap.x - prev.x) < 5) {
    lastSnap.x = prev.x
  } else if (Math.abs(lastSnap.y - prev.y) < 5) {
    lastSnap.y = prev.y
  } else {
    result.push({ x: lastSnap.x, y: prev.y })
  }
  result.push(lastSnap)

  return result
}

export function calculateAStarPath(sourceNode, targetNode, nodes, options = {}) {
  const { padding = 15 } = options

  const sourceCenter = getNodeCenter(sourceNode)
  const targetCenter = getNodeCenter(targetNode)

  const startPoint = getConnectionPoint(sourceNode, targetCenter.x, targetCenter.y, padding)
  const endPoint = getConnectionPoint(targetNode, sourceCenter.x, sourceCenter.y, padding)

  const { grid, minX, minY } = createGrid(nodes, sourceNode, targetNode, padding)

  const startGrid = worldToGrid(startPoint.x, startPoint.y, minX, minY)
  const endGrid = worldToGrid(endPoint.x, endPoint.y, minX, minY)

  const startNode = grid[Math.max(0, Math.min(grid.length - 1, startGrid.y))]?.[Math.max(0, Math.min(grid[0].length - 1, startGrid.x))]
  const goalNode = grid[Math.max(0, Math.min(grid.length - 1, endGrid.y))]?.[Math.max(0, Math.min(grid[0].length - 1, endGrid.x))]

  if (!startNode || !goalNode) {
    return [startPoint, { x: startPoint.x, y: endPoint.y }, endPoint]
  }

  startNode.blocked = false
  goalNode.blocked = false

  let path = aStar(grid, startNode, goalNode)

  if (!path || path.length === 0) {
    const midX = (startPoint.x + endPoint.x) / 2
    const midY = (startPoint.y + endPoint.y) / 2
    path = [
      startPoint,
      { x: startPoint.x, y: midY },
      { x: endPoint.x, y: midY },
      endPoint
    ]
  } else {
    path[0] = startPoint
    path[path.length - 1] = endPoint
  }

  const simplified = simplifyPath(path, 8)
  const orthogonal = snapToCardinal(simplified, sourceNode, targetNode)

  return orthogonal
}

export function calculateAllAStarPaths(nodes, edges) {
  const result = {}

  for (const edge of edges) {
    const sourceNode = nodes.find(n => n.id === edge.sourceId)
    const targetNode = nodes.find(n => n.id === edge.targetId)

    if (sourceNode && targetNode) {
      const visibleNodes = nodes.filter(n => !n.collapsed || n.id === sourceNode.id || n.id === targetNode.id)
      const path = calculateAStarPath(sourceNode, targetNode, visibleNodes)
      result[edge.id] = path
    }
  }

  return result
}

export function updateAStarPathsOnNodeMove(nodes, edges, movedNodeId) {
  const movedNode = nodes.find(n => n.id === movedNodeId)
  if (!movedNode) return {}

  const affectedEdges = edges.filter(
    e => e.sourceId === movedNodeId || e.targetId === movedNodeId
  )

  return calculateAllAStarPaths(nodes, affectedEdges)
}

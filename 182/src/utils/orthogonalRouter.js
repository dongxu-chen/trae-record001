const GAP = 20

function getNodeCenter(node) {
  return {
    x: node.x + node.width / 2,
    y: node.y + node.height / 2
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

function getConnectionPoint(node, targetX, targetY) {
  const bounds = getNodeBounds(node)
  const center = getNodeCenter(node)

  const dx = targetX - center.x
  const dy = targetY - center.y

  if (Math.abs(dx) * node.height > Math.abs(dy) * node.width) {
    if (dx > 0) {
      return { x: bounds.right, y: center.y }
    } else {
      return { x: bounds.left, y: center.y }
    }
  } else {
    if (dy > 0) {
      return { x: center.x, y: bounds.bottom }
    } else {
      return { x: center.x, y: bounds.top }
    }
  }
}

function isPointInRect(px, py, rect) {
  return px >= rect.left && px <= rect.right && py >= rect.top && py <= rect.bottom
}

function doesLineIntersectRect(x1, y1, x2, y2, rect) {
  if (isPointInRect(x1, y1, rect) || isPointInRect(x2, y2, rect)) {
    return true
  }

  const edges = [
    [rect.left, rect.top, rect.right, rect.top],
    [rect.right, rect.top, rect.right, rect.bottom],
    [rect.right, rect.bottom, rect.left, rect.bottom],
    [rect.left, rect.bottom, rect.left, rect.top]
  ]

  for (const [ex1, ey1, ex2, ey2] of edges) {
    if (doLinesIntersect(x1, y1, x2, y2, ex1, ey1, ex2, ey2)) {
      return true
    }
  }

  return false
}

function doLinesIntersect(x1, y1, x2, y2, x3, y3, x4, y4) {
  const denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
  if (Math.abs(denom) < 0.0001) return false

  const t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
  const u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

  return t >= 0 && t <= 1 && u >= 0 && u <= 1
}

function findPath(start, end, nodes, sourceNode, targetNode) {
  const waypoints = [start]
  
  const otherNodes = nodes.filter(n => n.id !== sourceNode.id && n.id !== targetNode.id)
  
  const midX = (start.x + end.x) / 2
  const midY = (start.y + end.y) / 2
  
  const candidates = [
    [{ x: start.x, y: end.y }],
    [{ x: end.x, y: start.y }],
    [{ x: midX, y: start.y }, { x: midX, y: end.y }],
    [{ x: start.x, y: midY }, { x: end.x, y: midY }],
    [{ x: midX, y: start.y }, { x: midX, y: midY }, { x: end.x, y: midY }],
    [{ x: start.x, y: midY }, { x: midX, y: midY }, { x: midX, y: end.y }]
  ]

  let bestPath = null
  let bestScore = Infinity

  for (const candidate of candidates) {
    const path = [start, ...candidate, end]
    let valid = true
    let score = 0

    for (let i = 0; i < path.length - 1; i++) {
      const p1 = path[i]
      const p2 = path[i + 1]
      score += Math.abs(p2.x - p1.x) + Math.abs(p2.y - p1.y)

      for (const node of otherNodes) {
        const bounds = getNodeBounds(node)
        if (doesLineIntersectRect(p1.x, p1.y, p2.x, p2.y, bounds)) {
          score += 1000
          break
        }
      }
    }

    score += candidate.length * 10

    if (score < bestScore) {
      bestScore = score
      bestPath = path
    }
  }

  return bestPath || [start, { x: start.x, y: end.y }, end]
}

export function calculateOrthogonalPath(sourceNode, targetNode, nodes) {
  const sourceCenter = getNodeCenter(sourceNode)
  const targetCenter = getNodeCenter(targetNode)

  const startPoint = getConnectionPoint(sourceNode, targetCenter.x, targetCenter.y)
  const endPoint = getConnectionPoint(targetNode, sourceCenter.x, sourceCenter.y)

  const path = findPath(startPoint, endPoint, nodes, sourceNode, targetNode)

  return path
}

export function calculateAllEdgePaths(nodes, edges) {
  const result = {}

  for (const edge of edges) {
    const sourceNode = nodes.find(n => n.id === edge.sourceId)
    const targetNode = nodes.find(n => n.id === edge.targetId)

    if (sourceNode && targetNode) {
      const visibleNodes = nodes.filter(n => !n.collapsed || n.id === sourceNode.id || n.id === targetNode.id)
      const path = calculateOrthogonalPath(sourceNode, targetNode, visibleNodes)
      result[edge.id] = path
    }
  }

  return result
}

export function updateEdgePathsOnNodeMove(nodes, edges, movedNodeId) {
  const movedNode = nodes.find(n => n.id === movedNodeId)
  if (!movedNode) return {}

  const affectedEdges = edges.filter(
    e => e.sourceId === movedNodeId || e.targetId === movedNodeId
  )

  return calculateAllEdgePaths(nodes, affectedEdges)
}

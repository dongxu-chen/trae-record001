const HORIZONTAL_GAP = 80
const VERTICAL_GAP = 30
const NODE_WIDTH = 120
const NODE_HEIGHT = 40

export function calculateSubtreeSize(node, nodes, collapsedMap = {}) {
  if (!node) return { width: 0, height: 0 }
  
  if (node.collapsed || collapsedMap[node.id]) {
    return {
      width: NODE_WIDTH + HORIZONTAL_GAP,
      height: NODE_HEIGHT
    }
  }

  const children = node.children
    .map(id => nodes[id])
    .filter(Boolean)
    .filter(child => !collapsedMap[child.id])

  if (children.length === 0) {
    return {
      width: NODE_WIDTH + HORIZONTAL_GAP,
      height: NODE_HEIGHT
    }
  }

  let totalHeight = 0
  let maxChildWidth = 0

  children.forEach(child => {
    const childSize = calculateSubtreeSize(child, nodes, collapsedMap)
    totalHeight += childSize.height
    maxChildWidth = Math.max(maxChildWidth, childSize.width)
  })

  totalHeight += Math.max(0, children.length - 1) * VERTICAL_GAP

  return {
    width: NODE_WIDTH + HORIZONTAL_GAP + maxChildWidth,
    height: Math.max(NODE_HEIGHT, totalHeight)
  }
}

export function layoutMindMap(rootNodeId, nodes, direction = 'right') {
  const positions = {}
  const rootNode = nodes[rootNodeId]
  
  if (!rootNode) return positions

  function layout(node, x, y, parentDirection = direction) {
    positions[node.id] = { x, y }

    if (node.collapsed) return

    const children = node.children
      .map(id => nodes[id])
      .filter(Boolean)

    if (children.length === 0) return

    const childSizes = children.map(child => calculateSubtreeSize(child, nodes))
    const totalHeight = childSizes.reduce((sum, size) => sum + size.height, 0) + 
                       Math.max(0, children.length - 1) * VERTICAL_GAP

    let currentY = y - totalHeight / 2 + childSizes[0].height / 2
    
    const childX = parentDirection === 'right' 
      ? x + NODE_WIDTH + HORIZONTAL_GAP 
      : x - NODE_WIDTH - HORIZONTAL_GAP

    children.forEach((child, index) => {
      const childSize = childSizes[index]
      layout(child, childX, currentY, parentDirection)
      currentY += childSize.height + VERTICAL_GAP
    })
  }

  layout(rootNode, 0, 0)
  return positions
}

export function layoutMindMapBalanced(rootNodeId, nodes) {
  const positions = {}
  const rootNode = nodes[rootNodeId]
  
  if (!rootNode) return positions

  const children = rootNode.children
    .map(id => nodes[id])
    .filter(Boolean)

  positions[rootNode.id] = { x: 0, y: 0 }

  if (children.length === 0) return positions

  const mid = Math.ceil(children.length / 2)
  const leftChildren = children.slice(0, mid)
  const rightChildren = children.slice(mid)

  function layoutChildren(childList, startX, direction) {
    if (childList.length === 0) return

    const childSizes = childList.map(child => calculateSubtreeSize(child, nodes))
    const totalHeight = childSizes.reduce((sum, size) => sum + size.height, 0) + 
                       Math.max(0, childList.length - 1) * VERTICAL_GAP

    let currentY = -totalHeight / 2 + childSizes[0].height / 2

    childList.forEach((child, index) => {
      const childSize = childSizes[index]
      const childX = direction === 'right' 
        ? startX 
        : startX - NODE_WIDTH
      
      layoutSubtree(child, childX, currentY, direction)
      currentY += childSize.height + VERTICAL_GAP
    })
  }

  function layoutSubtree(node, x, y, direction) {
    positions[node.id] = { x, y }

    if (node.collapsed) return

    const children = node.children
      .map(id => nodes[id])
      .filter(Boolean)

    if (children.length === 0) return

    const childSizes = children.map(child => calculateSubtreeSize(child, nodes))
    const totalHeight = childSizes.reduce((sum, size) => sum + size.height, 0) + 
                       Math.max(0, children.length - 1) * VERTICAL_GAP

    let currentY = y - totalHeight / 2 + childSizes[0].height / 2
    
    const childX = direction === 'right' 
      ? x + NODE_WIDTH + HORIZONTAL_GAP 
      : x - NODE_WIDTH - HORIZONTAL_GAP

    children.forEach((child, index) => {
      const childSize = childSizes[index]
      layoutSubtree(child, childX, currentY, direction)
      currentY += childSize.height + VERTICAL_GAP
    })
  }

  const rightStartX = NODE_WIDTH + HORIZONTAL_GAP
  const leftStartX = -HORIZONTAL_GAP

  layoutChildren(rightChildren, rightStartX, 'right')
  layoutChildren(leftChildren, leftStartX, 'left')

  return positions
}

export function layoutMindMapRadial(rootNodeId, nodes) {
  const positions = {}
  const rootNode = nodes[rootNodeId]
  
  if (!rootNode) return positions

  positions[rootNode.id] = { x: 0, y: 0 }

  const children = rootNode.children
    .map(id => nodes[id])
    .filter(Boolean)

  if (children.length === 0) return positions

  const level1Radius = 200
  const angleStep = (2 * Math.PI) / children.length

  function layoutRadial(node, centerX, centerY, radius, startAngle, endAngle, level = 1) {
    if (node.collapsed) return

    const children = node.children
      .map(id => nodes[id])
      .filter(Boolean)

    if (children.length === 0) return

    const angleRange = endAngle - startAngle
    const childAngleStep = angleRange / children.length

    children.forEach((child, index) => {
      const angle = startAngle + index * childAngleStep + childAngleStep / 2
      const x = centerX + Math.cos(angle) * radius
      const y = centerY + Math.sin(angle) * radius
      
      positions[child.id] = { x, y }

      const childStartAngle = angle - childAngleStep / 2
      const childEndAngle = angle + childAngleStep / 2
      
      layoutRadial(child, x, y, radius * 0.8, childStartAngle, childEndAngle, level + 1)
    })
  }

  children.forEach((child, index) => {
    const angle = index * angleStep
    const x = Math.cos(angle) * level1Radius
    const y = Math.sin(angle) * level1Radius
    
    positions[child.id] = { x, y }

    const childStartAngle = angle - angleStep / 2
    const childEndAngle = angle + angleStep / 2
    
    layoutRadial(child, x, y, level1Radius * 0.8, childStartAngle, childEndAngle, 2)
  })

  return positions
}

export function applyLayout(nodes, positions) {
  Object.keys(positions).forEach(nodeId => {
    if (nodes[nodeId]) {
      nodes[nodeId].x = positions[nodeId].x
      nodes[nodeId].y = positions[nodeId].y
    }
  })
}

export function autoLayout(rootNodeId, nodes, layoutType = 'balanced') {
  let positions
  
  switch (layoutType) {
    case 'right':
      positions = layoutMindMap(rootNodeId, nodes, 'right')
      break
    case 'left':
      positions = layoutMindMap(rootNodeId, nodes, 'left')
      break
    case 'radial':
      positions = layoutMindMapRadial(rootNodeId, nodes)
      break
    case 'balanced':
    default:
      positions = layoutMindMapBalanced(rootNodeId, nodes)
  }
  
  applyLayout(nodes, positions)
  return positions
}

export function getNodeBounds(nodes) {
  const nodeArray = Object.values(nodes)
  if (nodeArray.length === 0) {
    return { minX: 0, minY: 0, maxX: 0, maxY: 0, width: 0, height: 0 }
  }

  let minX = Infinity, minY = Infinity
  let maxX = -Infinity, maxY = -Infinity

  nodeArray.forEach(node => {
    minX = Math.min(minX, node.x)
    minY = Math.min(minY, node.y)
    maxX = Math.max(maxX, node.x + node.width)
    maxY = Math.max(maxY, node.y + node.height)
  })

  return {
    minX,
    minY,
    maxX,
    maxY,
    width: maxX - minX,
    height: maxY - minY
  }
}

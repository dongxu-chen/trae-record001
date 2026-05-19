import dagre from 'dagre'
import * as d3Force from 'd3-force'

export const LAYOUT_TYPES = {
  HIERARCHICAL: 'hierarchical',
  FORCE_DIRECTED: 'forceDirected',
  CIRCULAR: 'circular'
}

export function prepareLayoutNodes(nodes, edges) {
  const layoutNodes = []
  const nodeMap = new Map()
  const placeholderMap = new Map()

  nodes.forEach(node => {
    nodeMap.set(node.id, node)

    if (node.isGroup && node.collapsed) {
      const placeholder = {
        id: node.id,
        x: node.x,
        y: node.y,
        width: node.width,
        height: node.height,
        isGroup: true,
        collapsed: true,
        childNodes: [...node.childNodes],
        originalX: node.originalX !== undefined ? node.originalX : node.x,
        originalY: node.originalY !== undefined ? node.originalY : node.y,
        originalWidth: node.originalWidth || node.width,
        originalHeight: node.originalHeight || node.height,
        isPlaceholder: true,
        label: node.label,
        fill: node.fill,
        stroke: node.stroke,
        strokeWidth: node.strokeWidth,
        fontSize: node.fontSize,
        fontColor: node.fontColor
      }
      layoutNodes.push(placeholder)
      placeholderMap.set(node.id, placeholder)
    } else if (!node.groupId || !placeholderMap.has(node.groupId)) {
      layoutNodes.push(node)
    }
  })

  const layoutEdges = edges.filter(edge => {
    const sourceNode = nodeMap.get(edge.sourceId)
    const targetNode = nodeMap.get(edge.targetId)
    if (!sourceNode || !targetNode) return false

    const sourceCollapsed = sourceNode.groupId && placeholderMap.has(sourceNode.groupId)
    const targetCollapsed = targetNode.groupId && placeholderMap.has(targetNode.groupId)

    if (sourceCollapsed || targetCollapsed) {
      return false
    }

    return true
  })

  return { layoutNodes, layoutEdges, placeholderMap, nodeMap }
}

export function restoreChildPositions(node, placeholder, nodes) {
  if (!node.isGroup || !node.collapsed || !node.childNodes) return

  const centerX = placeholder.x + placeholder.width / 2
  const centerY = placeholder.y + placeholder.height / 2
  const originalCenterX = placeholder.originalX + placeholder.originalWidth / 2
  const originalCenterY = placeholder.originalY + placeholder.originalHeight / 2

  const offsetX = centerX - originalCenterX
  const offsetY = centerY - originalCenterY

  node.childNodes.forEach(childId => {
    const child = nodes.find(n => n.id === childId)
    if (child) {
      child.x += offsetX
      child.y += offsetY
    }
  })
}

function createDagreGraph() {
  try {
    if (dagre.graphlib && dagre.graphlib.Graph) {
      return new dagre.graphlib.Graph()
    }
    if (dagre.Graph) {
      return new dagre.Graph()
    }
    if (typeof dagre === 'function') {
      return new dagre()
    }
  } catch (e) {
    console.error('Failed to create dagre graph:', e)
  }
  return null
}

export function applyHierarchicalLayout(nodes, edges, options = {}) {
  const {
    rankdir = 'TB',
    nodesep = 50,
    ranksep = 70,
    marginx = 50,
    marginy = 50
  } = options

  const { layoutNodes, layoutEdges, placeholderMap } = prepareLayoutNodes(nodes, edges)

  const g = createDagreGraph()
  if (!g) {
    console.warn('Dagre not available, falling back to simple layout')
    return fallbackLayout(nodes)
  }
  g.setGraph({
    rankdir,
    nodesep,
    ranksep,
    marginx,
    marginy
  })
  g.setDefaultEdgeLabel(() => ({}))

  layoutNodes.forEach(node => {
    g.setNode(node.id, {
      width: node.width,
      height: node.height
    })
  })

  layoutEdges.forEach(edge => {
    g.setEdge(edge.sourceId, edge.targetId)
  })

  dagre.layout(g)

  const nodePositions = {}
  g.nodes().forEach(id => {
    const layoutNode = g.node(id)
    nodePositions[id] = {
      x: layoutNode.x - layoutNode.width / 2,
      y: layoutNode.y - layoutNode.height / 2
    }
  })

  placeholderMap.forEach((placeholder, groupId) => {
    const pos = nodePositions[groupId]
    if (pos) {
      placeholder.x = pos.x
      placeholder.y = pos.y
      const groupNode = nodes.find(n => n.id === groupId)
      if (groupNode) {
        restoreChildPositions(groupNode, placeholder, nodes)
      }
    }
  })

  return nodePositions
}

export function applyForceDirectedLayout(nodes, edges, options = {}) {
  const {
    width = 800,
    height = 600,
    linkDistance = 120,
    charge = -300,
    iterations = 300
  } = options

  const { layoutNodes, layoutEdges, placeholderMap } = prepareLayoutNodes(nodes, edges)

  const d3Nodes = layoutNodes.map(node => ({
    id: node.id,
    x: node.x + node.width / 2,
    y: node.y + node.height / 2,
    width: node.width,
    height: node.height
  }))

  const d3Edges = layoutEdges
    .filter(edge => {
      const source = d3Nodes.find(n => n.id === edge.sourceId)
      const target = d3Nodes.find(n => n.id === edge.targetId)
      return source && target
    })
    .map(edge => ({
      source: edge.sourceId,
      target: edge.targetId
    }))

  const simulation = d3Force.forceSimulation(d3Nodes)
    .force('link', d3Force.forceLink(d3Edges).id(d => d.id).distance(linkDistance))
    .force('charge', d3Force.forceManyBody().strength(charge))
    .force('center', d3Force.forceCenter(width / 2, height / 2))
    .force('collision', d3Force.forceCollide().radius(d => Math.max(d.width, d.height) / 2 + 20))
    .stop()

  for (let i = 0; i < iterations; ++i) {
    simulation.tick()
  }

  const nodePositions = {}
  d3Nodes.forEach(d => {
    nodePositions[d.id] = {
      x: d.x - d.width / 2,
      y: d.y - d.height / 2
    }
  })

  placeholderMap.forEach((placeholder, groupId) => {
    const pos = nodePositions[groupId]
    if (pos) {
      placeholder.x = pos.x
      placeholder.y = pos.y
      const groupNode = nodes.find(n => n.id === groupId)
      if (groupNode) {
        restoreChildPositions(groupNode, placeholder, nodes)
      }
    }
  })

  return nodePositions
}

export function applyCircularLayout(nodes, edges, options = {}) {
  const {
    centerX = 400,
    centerY = 300,
    radius = 200
  } = options

  const { layoutNodes, placeholderMap } = prepareLayoutNodes(nodes, edges)
  const nodePositions = {}

  layoutNodes.forEach((node, index) => {
    const angle = (2 * Math.PI * index) / layoutNodes.length - Math.PI / 2
    nodePositions[node.id] = {
      x: centerX + radius * Math.cos(angle) - node.width / 2,
      y: centerY + radius * Math.sin(angle) - node.height / 2
    }
  })

  placeholderMap.forEach((placeholder, groupId) => {
    const pos = nodePositions[groupId]
    if (pos) {
      placeholder.x = pos.x
      placeholder.y = pos.y
      const groupNode = nodes.find(n => n.id === groupId)
      if (groupNode) {
        restoreChildPositions(groupNode, placeholder, nodes)
      }
    }
  })

  return nodePositions
}

export function applyLayout(type, nodes, edges, options = {}) {
  switch (type) {
    case LAYOUT_TYPES.HIERARCHICAL:
      return applyHierarchicalLayout(nodes, edges, options)
    case LAYOUT_TYPES.FORCE_DIRECTED:
      return applyForceDirectedLayout(nodes, edges, options)
    case LAYOUT_TYPES.CIRCULAR:
      return applyCircularLayout(nodes, edges, options)
    default:
      return applyHierarchicalLayout(nodes, edges, options)
  }
}

export function calculateGroupBounds(group, nodes) {
  const childNodes = nodes.filter(n => group.childNodes.includes(n.id) && !n.collapsed)
  
  if (childNodes.length === 0) {
    return { x: group.x, y: group.y, width: group.width, height: group.height }
  }

  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity

  childNodes.forEach(node => {
    minX = Math.min(minX, node.x)
    minY = Math.min(minY, node.y)
    maxX = Math.max(maxX, node.x + node.width)
    maxY = Math.max(maxY, node.y + node.height)
  })

  const padding = 30
  return {
    x: minX - padding,
    y: minY - padding - 30,
    width: maxX - minX + padding * 2,
    height: maxY - minY + padding * 2 + 30
  }
}

export function toggleGroupCollapse(group, nodes, edges) {
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
}

function fallbackLayout(nodes) {
  const positions = {}
  const visibleNodes = nodes.filter(n => !n.collapsed)
  const cols = Math.ceil(Math.sqrt(visibleNodes.length))
  const spacing = 150

  visibleNodes.forEach((node, index) => {
    const col = index % cols
    const row = Math.floor(index / cols)
    positions[node.id] = {
      x: 100 + col * spacing,
      y: 100 + row * spacing
    }
  })

  return positions
}

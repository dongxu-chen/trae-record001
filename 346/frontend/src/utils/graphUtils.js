import * as d3 from 'd3'

export const generateNodeColors = (count) => {
  const colorScale = d3.scaleOrdinal(d3.schemeCategory10)
  return Array.from({ length: count }, (_, i) => colorScale(i))
}

export const getCommunityColor = (communities, nodeId) => {
  const colorScale = d3.scaleOrdinal(d3.schemeCategory10)
  for (let i = 0; i < communities.length; i++) {
    if (communities[i].nodes.includes(nodeId)) {
      return colorScale(i)
    }
  }
  return '#999'
}

export const calculateNodeSize = (degree, minSize = 5, maxSize = 25) => {
  if (!degree || degree === 0) return minSize
  const logDegree = Math.log(degree + 1)
  return Math.min(maxSize, Math.max(minSize, logDegree * 5))
}

export const filterGraphByTime = (graphData, startTime, endTime, timeKey = 'timestamp') => {
  if (!startTime && !endTime) return graphData

  const filteredEdges = graphData.edges.filter((edge) => {
    const timestamp = edge[timeKey]
    if (timestamp === undefined || timestamp === null) return true
    const ts = typeof timestamp === 'number' ? timestamp : new Date(timestamp).getTime()
    const start = startTime ? new Date(startTime).getTime() : -Infinity
    const end = endTime ? new Date(endTime).getTime() : Infinity
    return ts >= start && ts <= end
  })

  const connectedNodeIds = new Set()
  filteredEdges.forEach((edge) => {
    connectedNodeIds.add(edge.source)
    connectedNodeIds.add(edge.target)
  })

  const filteredNodes = graphData.nodes.filter((node) => connectedNodeIds.has(node.id))

  return {
    ...graphData,
    nodes: filteredNodes,
    edges: filteredEdges,
  }
}

export const getNodeDegrees = (graphData) => {
  const degrees = {}
  graphData.edges.forEach((edge) => {
    degrees[edge.source] = (degrees[edge.source] || 0) + 1
    degrees[edge.target] = (degrees[edge.target] || 0) + 1
  })
  return degrees
}

export const formatInfluenceScore = (score, method) => {
  if (method === 'degree' || method === 'betweenness' || method === 'closeness') {
    return score.toFixed(4)
  }
  return score.toFixed(4)
}

export const getInfluenceMethodLabel = (method) => {
  const labels = {
    degree: '度数中心性',
    betweenness: '介数中心性',
    closeness: '接近中心性',
    eigenvector: '特征向量中心性',
    pagerank: 'PageRank',
  }
  return labels[method] || method
}

export const runForceSimulation = (nodes, edges, width, height) => {
  const simulation = d3
    .forceSimulation(nodes)
    .force(
      'link',
      d3
        .forceLink(edges)
        .id((d) => d.id)
        .distance(50)
        .strength(0.3)
    )
    .force('charge', d3.forceManyBody().strength(-200))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(20))
    .stop()

  for (let i = 0; i < 300; i++) {
    simulation.tick()
  }

  return { nodes, edges }
}

export const getNodeLabel = (node) => {
  return node.name || node.label || node.id
}

export const highlightPath = (graphData, path) => {
  if (!path || path.length < 2) return graphData

  const pathSet = new Set(path)
  const pathEdges = new Set()

  for (let i = 0; i < path.length - 1; i++) {
    pathEdges.add(`${path[i]}-${path[i + 1]}`)
    pathEdges.add(`${path[i + 1]}-${path[i]}`)
  }

  return {
    ...graphData,
    nodes: graphData.nodes.map((node) => ({
      ...node,
      highlighted: pathSet.has(node.id),
    })),
    edges: graphData.edges.map((edge) => ({
      ...edge,
      highlighted: pathEdges.has(`${edge.source}-${edge.target}`),
    })),
  }
}

export const calculateLayout = (nodes, edges, layoutType = 'force', width = 800, height = 600) => {
  switch (layoutType) {
    case 'circular':
      return circularLayout(nodes, width, height)
    case 'grid':
      return gridLayout(nodes, width, height)
    case 'force':
    default:
      return runForceSimulation(nodes, edges, width, height).nodes
  }
}

export const circularLayout = (nodes, width, height) => {
  const centerX = width / 2
  const centerY = height / 2
  const radius = Math.min(width, height) * 0.4

  return nodes.map((node, index) => {
    const angle = (index / nodes.length) * 2 * Math.PI - Math.PI / 2
    return {
      ...node,
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
    }
  })
}

export const gridLayout = (nodes, width, height) => {
  const cols = Math.ceil(Math.sqrt(nodes.length))
  const rows = Math.ceil(nodes.length / cols)
  const cellWidth = width / (cols + 1)
  const cellHeight = height / (rows + 1)

  return nodes.map((node, index) => {
    const col = index % cols
    const row = Math.floor(index / cols)
    return {
      ...node,
      x: cellWidth * (col + 1),
      y: cellHeight * (row + 1),
    }
  })
}

export const RELATIONSHIP_TYPE_COLORS = {
  FOLLOW: '#1890ff',
  LIKE: '#52c41a',
  COMMENT: '#faad14',
  FRIEND: '#722ed1',
  COLLEAGUE: '#eb2f96',
}

export const getRelationshipColor = (type) => {
  return RELATIONSHIP_TYPE_COLORS[type] || '#999'
}

export const filterGraphByRelationshipTypes = (graphData, relationshipTypes = []) => {
  if (!relationshipTypes || relationshipTypes.length === 0) {
    return {
      ...graphData,
      nodes: graphData.nodes,
      edges: [],
    }
  }

  const typeSet = new Set(relationshipTypes.map((t) => t.toUpperCase()))

  const filteredEdges = graphData.edges.filter((edge) => {
    const edgeType = (edge.type || edge.relationship_type || '').toUpperCase()
    return typeSet.has(edgeType)
  })

  const connectedNodeIds = new Set()
  filteredEdges.forEach((edge) => {
    connectedNodeIds.add(edge.source)
    connectedNodeIds.add(edge.target)
  })

  const filteredNodes = graphData.nodes.filter((node) => connectedNodeIds.has(node.id))

  return {
    ...graphData,
    nodes: filteredNodes,
    edges: filteredEdges,
  }
}

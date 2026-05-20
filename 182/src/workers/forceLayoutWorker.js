import * as d3Force from 'd3-force'

self.onmessage = function(e) {
  const { requestId, nodes, edges, options } = e.data
  
  try {
    const result = calculateForceLayout(nodes, edges, options)
    self.postMessage({ requestId, type: 'success', result })
  } catch (error) {
    self.postMessage({ requestId, type: 'error', error: error.message })
  }
}

function calculateForceLayout(nodes, edges, options) {
  const {
    width = 800,
    height = 600,
    linkDistance = 120,
    charge = -300,
    iterations = 300
  } = options

  const d3Nodes = nodes.map(node => ({
    id: node.id,
    x: node.x + node.width / 2,
    y: node.y + node.height / 2,
    width: node.width,
    height: node.height
  }))

  const d3Edges = edges
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

  return nodePositions
}

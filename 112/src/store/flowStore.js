import { create } from 'zustand'
import { addEdge, applyNodeChanges, applyEdgeChanges } from 'reactflow'

const generateId = () => 'node_' + Math.random().toString(36).substr(2, 9)

export const useFlowStore = create((set, get) => ({
  nodes: [],
  edges: [],
  selectedNode: null,

  setNodes: (nodes) => set({ nodes }),
  setEdges: (edges) => set({ edges }),
  setSelectedNode: (node) => set({ selectedNode: node }),

  onNodesChange: (changes) => set({
    nodes: applyNodeChanges(changes, get().nodes)
  }),

  onEdgesChange: (changes) => set({
    edges: applyEdgeChanges(changes, get().edges)
  }),

  onConnect: (connection) => set({
    edges: addEdge({ ...connection, animated: true }, get().edges)
  }),

  addNode: (nodeData) => {
    const newNode = {
      id: generateId(),
      position: { x: 200, y: 200 },
      ...nodeData
    }
    set({
      nodes: [...get().nodes, newNode],
      selectedNode: newNode
    })
  },

  updateNode: (nodeId, data) => set({
    nodes: get().nodes.map(node =>
      node.id === nodeId
        ? { ...node, data: { ...node.data, ...data } }
        : node
    )
  }),

  deleteNode: (nodeId) => {
    const newNodes = get().nodes.filter(node => node.id !== nodeId)
    const newEdges = get().edges.filter(
      edge => edge.source !== nodeId && edge.target !== nodeId
    )
    set({
      nodes: newNodes,
      edges: newEdges,
      selectedNode: null
    })
  },

  exportFlow: () => {
    const { nodes, edges } = get()
    return JSON.stringify({ nodes, edges }, null, 2)
  },

  importFlow: (jsonString) => {
    try {
      const { nodes, edges } = JSON.parse(jsonString)
      set({ nodes, edges, selectedNode: null })
      return true
    } catch (e) {
      return false
    }
  },

  clearFlow: () => set({
    nodes: [],
    edges: [],
    selectedNode: null
  })
}))

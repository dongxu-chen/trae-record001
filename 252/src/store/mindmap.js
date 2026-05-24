import { reactive, computed } from 'vue'
import { storage } from '../utils/storage.js'

const state = reactive({
  currentMindMapId: null,
  title: '',
  nodes: {},
  rootNodeId: null,
  selectedNodeId: null,
  editingNodeId: null,
  searchKeyword: '',
  searchResults: [],
  theme: 'light',
  scale: 1,
  offsetX: 0,
  offsetY: 0,
  isDragging: false,
  isSaving: false
})

export function useMindMapStore() {
  const nodesArray = computed(() => Object.values(state.nodes))
  
  const selectedNode = computed(() => 
    state.selectedNodeId ? state.nodes[state.selectedNodeId] : null
  )

  const rootNode = computed(() => 
    state.rootNodeId ? state.nodes[state.rootNodeId] : null
  )

  function createNode(text = '新节点', parentId = null, x = 0, y = 0) {
    const id = storage.generateId()
    const node = {
      id,
      text,
      parentId,
      x,
      y,
      width: 120,
      height: 40,
      color: '#409eff',
      fontSize: 14,
      fontWeight: 'normal',
      fontStyle: 'normal',
      textDecoration: 'none',
      children: [],
      collapsed: false,
      createdAt: Date.now(),
      updatedAt: Date.now()
    }
    
    if (parentId && state.nodes[parentId]) {
      state.nodes[parentId].children.push(id)
      state.nodes[parentId].updatedAt = Date.now()
    }
    
    state.nodes[id] = node
    return node
  }

  function updateNode(id, updates) {
    if (!state.nodes[id]) return
    state.nodes[id] = {
      ...state.nodes[id],
      ...updates,
      updatedAt: Date.now()
    }
  }

  function deleteNode(id) {
    const node = state.nodes[id]
    if (!node) return

    const childrenIds = [...node.children]
    childrenIds.forEach(childId => deleteNode(childId))

    if (node.parentId && state.nodes[node.parentId]) {
      const parent = state.nodes[node.parentId]
      parent.children = parent.children.filter(cid => cid !== id)
      parent.updatedAt = Date.now()
    }

    delete state.nodes[id]

    if (state.selectedNodeId === id) {
      state.selectedNodeId = null
    }
    if (state.editingNodeId === id) {
      state.editingNodeId = null
    }
    if (state.rootNodeId === id) {
      state.rootNodeId = null
    }
  }

  function getNode(id) {
    return state.nodes[id] || null
  }

  function getChildren(id) {
    const node = state.nodes[id]
    if (!node) return []
    return node.children.map(cid => state.nodes[cid]).filter(Boolean)
  }

  function getSiblings(id) {
    const node = state.nodes[id]
    if (!node || !node.parentId) return []
    const parent = state.nodes[node.parentId]
    return parent.children
      .filter(cid => cid !== id)
      .map(cid => state.nodes[cid])
      .filter(Boolean)
  }

  function getDescendants(id) {
    const descendants = []
    const collect = (nodeId) => {
      const node = state.nodes[nodeId]
      if (!node) return
      descendants.push(node)
      node.children.forEach(childId => collect(childId))
    }
    collect(id)
    return descendants
  }

  function getAncestors(id) {
    const ancestors = []
    let currentId = state.nodes[id]?.parentId
    while (currentId) {
      const node = state.nodes[currentId]
      if (node) {
        ancestors.push(node)
        currentId = node.parentId
      } else {
        break
      }
    }
    return ancestors
  }

  function searchNodes(keyword) {
    if (!keyword.trim()) {
      state.searchKeyword = ''
      state.searchResults = []
      return []
    }
    const lowerKeyword = keyword.toLowerCase()
    const results = nodesArray.value.filter(node => 
      node.text.toLowerCase().includes(lowerKeyword)
    )
    state.searchKeyword = keyword
    state.searchResults = results.map(n => n.id)
    return results
  }

  function selectNode(id) {
    state.selectedNodeId = id
    state.editingNodeId = null
  }

  function clearSelection() {
    state.selectedNodeId = null
    state.editingNodeId = null
  }

  function startEditing(id) {
    state.selectedNodeId = id
    state.editingNodeId = id
  }

  function stopEditing() {
    state.editingNodeId = null
  }

  function setScale(scale) {
    state.scale = Math.max(0.25, Math.min(4, scale))
  }

  function setOffset(x, y) {
    state.offsetX = x
    state.offsetY = y
  }

  function setTheme(theme) {
    state.theme = theme
    document.documentElement.setAttribute('data-theme', theme)
    storage.saveSettings({ theme })
  }

  async function createNewMindMap() {
    const id = storage.generateId()
    state.currentMindMapId = id
    state.title = '未命名思维导图'
    state.nodes = {}
    state.rootNodeId = null
    state.selectedNodeId = null
    state.editingNodeId = null
    state.scale = 1
    state.offsetX = 0
    state.offsetY = 0

    const rootNode = createNode('中心主题', null, 0, 0)
    state.rootNodeId = rootNode.id
    state.selectedNodeId = rootNode.id

    await saveToStorage()
    return id
  }

  async function loadMindMap(id) {
    const data = await storage.getMindMap(id)
    if (!data) return false

    state.currentMindMapId = id
    state.title = data.title || '未命名思维导图'
    state.nodes = data.nodes || {}
    state.rootNodeId = data.rootNodeId
    state.selectedNodeId = null
    state.editingNodeId = null
    state.scale = data.scale || 1
    state.offsetX = data.offsetX || 0
    state.offsetY = data.offsetY || 0

    return true
  }

  async function saveToStorage() {
    if (!state.currentMindMapId) return
    
    state.isSaving = true
    try {
      await storage.saveMindMap(state.currentMindMapId, {
        title: state.title,
        nodes: state.nodes,
        rootNodeId: state.rootNodeId,
        scale: state.scale,
        offsetX: state.offsetX,
        offsetY: state.offsetY,
        createdAt: Date.now()
      })
    } finally {
      setTimeout(() => {
        state.isSaving = false
      }, 500)
    }
  }

  function exportToJSON() {
    return {
      title: state.title,
      version: '1.0',
      createdAt: Date.now(),
      rootNode: exportNode(state.rootNodeId)
    }
  }

  function exportNode(id) {
    const node = state.nodes[id]
    if (!node) return null
    return {
      text: node.text,
      color: node.color,
      fontSize: node.fontSize,
      fontWeight: node.fontWeight,
      fontStyle: node.fontStyle,
      textDecoration: node.textDecoration,
      collapsed: node.collapsed,
      children: node.children.map(cid => exportNode(cid)).filter(Boolean)
    }
  }

  function importFromJSON(data) {
    state.nodes = {}
    state.rootNodeId = null

    function importNode(nodeData, parentId = null, x = 0, y = 0) {
      const id = storage.generateId()
      const node = {
        id,
        text: nodeData.text || '新节点',
        parentId,
        x,
        y,
        width: 120,
        height: 40,
        color: nodeData.color || '#409eff',
        fontSize: nodeData.fontSize || 14,
        fontWeight: nodeData.fontWeight || 'normal',
        fontStyle: nodeData.fontStyle || 'normal',
        textDecoration: nodeData.textDecoration || 'none',
        children: [],
        collapsed: nodeData.collapsed || false,
        createdAt: Date.now(),
        updatedAt: Date.now()
      }
      
      if (parentId && state.nodes[parentId]) {
        state.nodes[parentId].children.push(id)
      }
      
      state.nodes[id] = node
      
      if (nodeData.children) {
        nodeData.children.forEach((childData, index) => {
          importNode(childData, id, x + 200, y + (index - nodeData.children.length / 2) * 60)
        })
      }
      
      return id
    }

    if (data.rootNode) {
      state.rootNodeId = importNode(data.rootNode)
      state.title = data.title || '导入的思维导图'
    }
  }

  function exportToMarkdown() {
    if (!state.rootNodeId) return ''
    
    function exportNodeMD(id, level = 0) {
      const node = state.nodes[id]
      if (!node) return ''
      
      const prefix = '#'.repeat(Math.min(level + 1, 6))
      let md = `${prefix} ${node.text}\n\n`
      
      if (!node.collapsed && node.children.length > 0) {
        node.children.forEach(childId => {
          md += exportNodeMD(childId, level + 1)
        })
      }
      
      return md
    }
    
    return exportNodeMD(state.rootNodeId)
  }

  function cloneNode(id, newParentId = null) {
    const original = state.nodes[id]
    if (!original) return null

    const newId = storage.generateId()
    const cloned = {
      ...original,
      id: newId,
      parentId: newParentId,
      children: [],
      createdAt: Date.now(),
      updatedAt: Date.now()
    }

    if (newParentId && state.nodes[newParentId]) {
      state.nodes[newParentId].children.push(newId)
      state.nodes[newParentId].updatedAt = Date.now()
    }

    state.nodes[newId] = cloned

    original.children.forEach(childId => {
      cloneNode(childId, newId)
    })

    return cloned
  }

  function moveNode(id, newParentId) {
    const node = state.nodes[id]
    if (!node) return

    if (node.parentId && state.nodes[node.parentId]) {
      const oldParent = state.nodes[node.parentId]
      oldParent.children = oldParent.children.filter(cid => cid !== id)
      oldParent.updatedAt = Date.now()
    }

    node.parentId = newParentId
    if (newParentId && state.nodes[newParentId]) {
      state.nodes[newParentId].children.push(id)
      state.nodes[newParentId].updatedAt = Date.now()
    }
    node.updatedAt = Date.now()
  }

  function collapseNode(id) {
    const node = state.nodes[id]
    if (node) {
      node.collapsed = true
      node.updatedAt = Date.now()
    }
  }

  function expandNode(id) {
    const node = state.nodes[id]
    if (node) {
      node.collapsed = false
      node.updatedAt = Date.now()
    }
  }

  function toggleCollapse(id) {
    const node = state.nodes[id]
    if (node) {
      node.collapsed = !node.collapsed
      node.updatedAt = Date.now()
    }
  }

  return {
    state,
    nodesArray,
    selectedNode,
    rootNode,
    createNode,
    updateNode,
    deleteNode,
    getNode,
    getChildren,
    getSiblings,
    getDescendants,
    getAncestors,
    searchNodes,
    selectNode,
    clearSelection,
    startEditing,
    stopEditing,
    setScale,
    setOffset,
    setTheme,
    createNewMindMap,
    loadMindMap,
    saveToStorage,
    exportToJSON,
    importFromJSON,
    exportToMarkdown,
    cloneNode,
    moveNode,
    collapseNode,
    expandNode,
    toggleCollapse
  }
}

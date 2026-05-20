<template>
  <div class="app-container">
    <TabBar
      v-if="tabs.length > 0"
      :tabs="tabs"
      :activeTabId="activeTabId"
      @switchTab="switchTab"
      @closeTab="closeTab"
      @addTab="addTab"
    />

    <Toolbar
      :layoutType="layoutType"
      :selectedObject="selectedObject"
      :snapEnabled="snapEnabled"
      @layout="applyLayout"
      @addNode="addNode"
      @deleteSelected="deleteSelected"
      @clearAll="clearAll"
      @exportSVG="handleExportSVG"
      @exportPNG="handleExportPNG"
      @exportJSON="handleExportJSON"
      @createGroup="createGroup"
      @ungroup="ungroup"
      @toggleSnap="toggleSnap"
      @importFile="handleImportFile"
    />

    <div class="main-content">
      <div class="canvas-container-wrapper">
        <div class="canvas-container" ref="canvasContainer">
          <canvas v-for="tab in tabs" :key="tab.id" :ref="el => setCanvasRef(tab.id, el)" :id="'canvas-' + tab.id" :width="canvasWidth" :height="canvasHeight" :style="{ display: tab.id === activeTabId ? 'block' : 'none' }"></canvas>
        </div>
        <div class="zoom-controls">
          <button class="zoom-btn" @click="zoomIn">+</button>
          <button class="zoom-btn" @click="zoomOut">−</button>
          <button class="zoom-btn" @click="resetZoom">⟲</button>
        </div>
      </div>

      <Sidebar
        :selectedObject="selectedObject"
        @updateNode="updateNode"
        @updateEdge="updateEdge"
        @addNode="addNode"
      />
    </div>

    <StatusBar :nodeCount="nodes.length" :edgeCount="edges.length" :zoom="zoom" />

    <input
      ref="fileInput"
      type="file"
      accept=".drawio,.xml,.vsdx"
      style="display: none"
      @change="onFileSelected"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, computed, watch } from 'vue'
import { v4 as uuidv4 } from 'uuid'
import { FlowCanvas } from './utils/fabricCanvas'
import { createNode, createEdge, createGroup as createGroupNode, NODE_TYPES } from './utils/graphData'
import { applyLayout as runLayout, LAYOUT_TYPES, calculateGroupBounds } from './utils/layoutEngine'
import { applyForceDirectedLayoutAsync, getForceLayoutWorker } from './utils/forceLayoutAsync'
import { exportSVG, exportPNG, exportJSON } from './utils/exporter'
import { importFile } from './utils/drawioParser'
import Toolbar from './components/Toolbar.vue'
import Sidebar from './components/Sidebar.vue'
import StatusBar from './components/StatusBar.vue'
import TabBar from './components/TabBar.vue'

const canvasContainer = ref(null)
const fileInput = ref(null)

const tabs = ref([])
const activeTabId = ref(null)
const canvasMap = new Map()
const canvasRefs = {}

const nodes = ref([])
const edges = ref([])
const selectedObject = ref(null)
const layoutType = ref(LAYOUT_TYPES.HIERARCHICAL)
const zoom = ref(1)
const snapEnabled = ref(true)

const canvasWidth = 2000
const canvasHeight = 1500

function setCanvasRef(tabId, el) {
  if (el) {
    canvasRefs[tabId] = el
  }
}

const activeTab = computed(() => tabs.value.find(t => t.id === activeTabId.value))

const currentFlowCanvas = computed(() => {
  if (!activeTabId.value) return null
  return canvasMap.get(activeTabId.value) || null
})

function createNewTab(name = '新流程图') {
  const tabId = uuidv4()
  const tab = {
    id: tabId,
    name,
    nodes: [],
    edges: [],
    flowCanvas: null,
    selectedObject: null,
    zoom: 1,
    layoutType: LAYOUT_TYPES.HIERARCHICAL
  }
  tabs.value.push(tab)
  return tab
}

async function initTabCanvas(tab) {
  await nextTick()
  
  const canvasEl = canvasRefs[tab.id]
  if (!canvasEl) return

  const flowCanvas = new FlowCanvas(canvasEl, {
    width: canvasWidth,
    height: canvasHeight,
    snapEnabled: snapEnabled.value,
    onNodeMove: (nodeId) => handleNodeMove(tab.id, nodeId),
    onSelectionChange: (selection) => handleSelectionChange(tab.id, selection),
    onEdgeCreate: (sourceId, targetId) => handleEdgeCreate(tab.id, sourceId, targetId),
    onNodeDoubleClick: (node) => handleNodeDoubleClick(tab.id, node)
  })

  tab.flowCanvas = flowCanvas
  canvasMap.set(tab.id, flowCanvas)

  if (tab.nodes.length === 0) {
    loadDemoDataToTab(tab)
  } else {
    tab.nodes.forEach(node => flowCanvas.addNode(node))
    tab.edges.forEach(edge => flowCanvas.addEdge(edge))
  }

  syncTabState(tab)
}

function loadDemoDataToTab(tab) {
  const node1 = createNode(NODE_TYPES.RECTANGLE, 200, 100, '开始')
  const node2 = createNode(NODE_TYPES.RECTANGLE, 200, 250, '处理数据')
  const node3 = createNode(NODE_TYPES.DIAMOND, 200, 400, '判断条件')
  const node4 = createNode(NODE_TYPES.RECTANGLE, 400, 400, '分支A')
  const node5 = createNode(NODE_TYPES.RECTANGLE, 400, 550, '结束')

  tab.nodes = [node1, node2, node3, node4, node5]

  const edge1 = createEdge(node1.id, node2.id)
  const edge2 = createEdge(node2.id, node3.id)
  const edge3 = createEdge(node3.id, node4.id, '是')
  const edge4 = createEdge(node3.id, node5.id, '否')

  tab.edges = [edge1, edge2, edge3, edge4]

  tab.nodes.forEach(node => tab.flowCanvas.addNode(node))
  tab.edges.forEach(edge => tab.flowCanvas.addEdge(edge))
}

function syncTabState(tab) {
  if (tab.id === activeTabId.value) {
    nodes.value = tab.nodes
    edges.value = tab.edges
    selectedObject.value = tab.selectedObject
    zoom.value = tab.zoom
    layoutType.value = tab.layoutType
  }
}

function switchTab(tabId) {
  if (activeTabId.value === tabId) return

  saveCurrentTabState()
  activeTabId.value = tabId
  
  const tab = tabs.value.find(t => t.id === tabId)
  if (tab && !tab.flowCanvas) {
    initTabCanvas(tab)
  }
  
  syncTabState(tab)
}

function saveCurrentTabState() {
  const tab = tabs.value.find(t => t.id === activeTabId.value)
  if (tab && tab.flowCanvas) {
    tab.nodes = [...tab.flowCanvas.nodes]
    tab.edges = [...tab.flowCanvas.edges]
    tab.selectedObject = selectedObject.value
    tab.zoom = zoom.value
    tab.layoutType = layoutType.value
  }
}

async function addTab() {
  saveCurrentTabState()
  const newTab = createNewTab(`流程图 ${tabs.value.length + 1}`)
  activeTabId.value = newTab.id
  await nextTick()
  await initTabCanvas(newTab)
}

function closeTab(tabId) {
  const tabIndex = tabs.value.findIndex(t => t.id === tabId)
  if (tabIndex === -1) return

  const tab = tabs.value[tabIndex]
  if (tab.flowCanvas) {
    tab.flowCanvas.dispose()
    canvasMap.delete(tabId)
  }

  tabs.value.splice(tabIndex, 1)

  if (tabs.value.length === 0) {
    addTab()
  } else if (activeTabId.value === tabId) {
    const newIndex = Math.min(tabIndex, tabs.value.length - 1)
    activeTabId.value = tabs.value[newIndex].id
    syncTabState(tabs.value[newIndex])
  }
}

function handleNodeMove(tabId, nodeId) {
  if (tabId !== activeTabId.value) return
  const tab = tabs.value.find(t => t.id === tabId)
  if (!tab) return

  const node = tab.nodes.find(n => n.id === nodeId)
  if (node && node.isGroup && !node.collapsed) {
    const bounds = calculateGroupBounds(node, tab.nodes)
    node.width = bounds.width
    node.height = bounds.height
  }
}

function handleSelectionChange(tabId, selection) {
  if (tabId !== activeTabId.value) return
  selectedObject.value = selection
  const tab = tabs.value.find(t => t.id === tabId)
  if (tab) tab.selectedObject = selection
}

function handleEdgeCreate(tabId, sourceId, targetId) {
  if (tabId !== activeTabId.value) return
  const tab = tabs.value.find(t => t.id === tabId)
  if (!tab) return

  const edge = createEdge(sourceId, targetId)
  tab.edges.push(edge)
  tab.flowCanvas.addEdge(edge)
}

function handleNodeDoubleClick(tabId, node) {
  if (tabId !== activeTabId.value) return
  if (node.isGroup) {
    const tab = tabs.value.find(t => t.id === tabId)
    if (tab) {
      node.childNodes.forEach(childId => {
        const child = tab.nodes.find(n => n.id === childId)
        if (child) {
          child.collapsed = node.collapsed
        }
      })
    }
  }
}

function addNode(type) {
  if (!currentFlowCanvas.value) return
  const tab = activeTab.value
  if (!tab) return

  const node = createNode(type, 300 + Math.random() * 100, 200 + Math.random() * 100)
  tab.nodes.push(node)
  currentFlowCanvas.value.addNode(node)
}

function deleteSelected() {
  if (!selectedObject.value || !currentFlowCanvas.value) return
  const tab = activeTab.value
  if (!tab) return

  if (selectedObject.value.type === 'node') {
    const nodeId = selectedObject.value.data.id
    tab.nodes = tab.nodes.filter(n => n.id !== nodeId)
    currentFlowCanvas.value.removeNode(nodeId)
  } else if (selectedObject.value.type === 'edge') {
    const edgeId = selectedObject.value.data.id
    tab.edges = tab.edges.filter(e => e.id !== edgeId)
    currentFlowCanvas.value.removeEdge(edgeId)
  }

  selectedObject.value = null
  tab.selectedObject = null
}

function clearAll() {
  if (!confirm('确定要清空所有内容吗？') || !currentFlowCanvas.value) return
  const tab = activeTab.value
  if (!tab) return

  tab.nodes = []
  tab.edges = []
  currentFlowCanvas.value.clear()
  selectedObject.value = null
  tab.selectedObject = null
}

async function applyLayout(type) {
  if (!currentFlowCanvas.value) return
  const tab = activeTab.value
  if (!tab) return

  layoutType.value = type
  tab.layoutType = type

  let positions
  if (type === LAYOUT_TYPES.FORCE_DIRECTED) {
    positions = await applyForceDirectedLayoutAsync(tab.nodes, tab.edges)
  } else {
    positions = runLayout(type, tab.nodes, tab.edges)
  }

  Object.entries(positions).forEach(([nodeId, pos]) => {
    const node = tab.nodes.find(n => n.id === nodeId)
    if (node) {
      node.x = pos.x
      node.y = pos.y
      currentFlowCanvas.value.updateNode(nodeId, { x: pos.x, y: pos.y })
    }
  })

  tab.nodes.forEach(node => {
    if (node.isGroup && !node.collapsed) {
      const bounds = calculateGroupBounds(node, tab.nodes)
      node.x = bounds.x
      node.y = bounds.y
      node.width = bounds.width
      node.height = bounds.height
      currentFlowCanvas.value.updateNode(node.id, {
        x: bounds.x,
        y: bounds.y,
        width: bounds.width,
        height: bounds.height
      })
    }
  })

  currentFlowCanvas.value.updateAllEdges()
}

function createGroup() {
  if (!currentFlowCanvas.value) return
  const tab = activeTab.value
  if (!tab) return

  const selectedNodes = tab.nodes.filter(n => {
    const obj = currentFlowCanvas.value.fabricObjects.get(n.id)
    return obj && currentFlowCanvas.value.canvas.getActiveObjects().includes(obj)
  })

  if (selectedNodes.length < 2) {
    alert('请选择至少2个节点进行分组')
    return
  }

  const group = createGroupNode(selectedNodes.map(n => n.id))
  selectedNodes.forEach(node => {
    node.groupId = group.id
  })

  const bounds = calculateGroupBounds(group, tab.nodes)
  group.x = bounds.x
  group.y = bounds.y
  group.width = bounds.width
  group.height = bounds.height
  group.originalX = bounds.x
  group.originalY = bounds.y

  tab.nodes.push(group)
  currentFlowCanvas.value.addNode(group)
  currentFlowCanvas.value.updateAllEdges()
}

function ungroup() {
  if (!selectedObject.value || selectedObject.value.type !== 'node' || !currentFlowCanvas.value) return
  const tab = activeTab.value
  if (!tab) return
  
  const node = selectedObject.value.data
  if (!node.isGroup) return

  node.childNodes.forEach(childId => {
    const child = tab.nodes.find(n => n.id === childId)
    if (child) {
      child.groupId = null
      child.collapsed = false
      const childObj = currentFlowCanvas.value.fabricObjects.get(childId)
      if (childObj) {
        currentFlowCanvas.value.canvas.add(childObj)
      }
    }
  })

  tab.nodes = tab.nodes.filter(n => n.id !== node.id)
  currentFlowCanvas.value.removeNode(node.id)
  selectedObject.value = null
  tab.selectedObject = null
  currentFlowCanvas.value.updateAllEdges()
}

function updateNode(nodeId, updates) {
  if (!currentFlowCanvas.value) return
  const tab = activeTab.value
  if (!tab) return

  const node = tab.nodes.find(n => n.id === nodeId)
  if (node) {
    Object.assign(node, updates)
    currentFlowCanvas.value.updateNode(nodeId, updates)
  }
}

function updateEdge(edgeId, updates) {
  if (!currentFlowCanvas.value) return
  const tab = activeTab.value
  if (!tab) return

  const edge = tab.edges.find(e => e.id === edgeId)
  if (edge) {
    Object.assign(edge, updates)
    currentFlowCanvas.value.updateAllEdges()
  }
}

function handleExportSVG() {
  const tab = activeTab.value
  if (!tab || !currentFlowCanvas.value) return
  exportSVG(tab.nodes, tab.edges, currentFlowCanvas.value.edgePaths, `${tab.name}.svg`)
}

function handleExportPNG() {
  const tab = activeTab.value
  if (!tab || !currentFlowCanvas.value) return
  exportPNG(tab.nodes, tab.edges, currentFlowCanvas.value.edgePaths, `${tab.name}.png`)
}

function handleExportJSON() {
  const tab = activeTab.value
  if (!tab) return
  exportJSON(tab.nodes, tab.edges, `${tab.name}.json`)
}

function toggleSnap() {
  snapEnabled.value = !snapEnabled.value
  canvasMap.forEach(canvas => {
    canvas.setSnapEnabled(snapEnabled.value)
  })
}

function handleImportFile() {
  fileInput.value?.click()
}

async function onFileSelected(event) {
  const file = event.target.files?.[0]
  if (!file) return

  try {
    const result = await importFile(file)
    
    const tab = createNewTab(file.name.replace(/\.[^.]+$/, ''))
    activeTabId.value = tab.id
    
    await nextTick()
    await initTabCanvas(tab)
    
    tab.flowCanvas.clear()
    tab.nodes = result.nodes
    tab.edges = result.edges
    
    result.nodes.forEach(node => tab.flowCanvas.addNode(node))
    result.edges.forEach(edge => tab.flowCanvas.addEdge(edge))
    
    syncTabState(tab)
    
    alert(`成功导入 ${result.nodes.length} 个节点和 ${result.edges.length} 条连线`)
  } catch (error) {
    alert('导入失败: ' + error.message)
    console.error('Import error:', error)
  } finally {
    event.target.value = ''
  }
}

function zoomIn() {
  if (!currentFlowCanvas.value) return
  zoom.value = Math.min(5, zoom.value + 0.1)
  currentFlowCanvas.value.setZoom(zoom.value)
}

function zoomOut() {
  if (!currentFlowCanvas.value) return
  zoom.value = Math.max(0.1, zoom.value - 0.1)
  currentFlowCanvas.value.setZoom(zoom.value)
}

function resetZoom() {
  if (!currentFlowCanvas.value) return
  zoom.value = 1
  currentFlowCanvas.value.setZoom(1)
}

onMounted(async () => {
  await nextTick()
  const initialTab = createNewTab('流程图 1')
  activeTabId.value = initialTab.id
  await nextTick()
  await initTabCanvas(initialTab)
})

onUnmounted(() => {
  canvasMap.forEach(canvas => {
    canvas.dispose()
  })
  canvasMap.clear()
  getForceLayoutWorker().dispose()
})
</script>

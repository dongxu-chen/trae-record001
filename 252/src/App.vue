<template>
  <div class="app-container" :data-theme="currentTheme">
    <Header
      :title="state.title"
      :scale="state.scale"
      :current-theme="currentTheme"
      :current-layout="currentLayout"
      :is-saving="state.isSaving"
      @update:title="updateTitle"
      @zoom-in="zoomIn"
      @zoom-out="zoomOut"
      @reset-view="resetView"
      @change-theme="changeTheme"
      @change-layout="changeLayout"
      @new="handleNew"
      @open="handleOpenList"
      @save="handleSave"
      @export-json="handleExportJSON"
      @export-image="handleExportImage"
      @export-markdown="handleExportMarkdown"
      @import-json="handleImportJSON"
      @auto-layout="handleAutoLayout"
    />

    <div class="main-content">
      <Sidebar
        ref="sidebarRef"
        :mindmaps="mindmaps"
        :current-id="state.currentMindMapId"
        :selected-node="selectedNode"
        :is-collapsed="isSidebarCollapsed"
        @toggle-collapse="toggleSidebar"
        @search="handleSearch"
        @focus-node="handleFocusNode"
        @new="handleNew"
        @open="handleOpen"
        @delete="handleDeleteMindmap"
        @add-child="handleAddChild"
        @edit-node="handleEditNode"
        @delete-node="handleDeleteNode"
      />

      <div class="canvas-wrapper">
        <MindMapCanvas
          ref="canvasRef"
          :width="canvasSize.width"
          :height="canvasSize.height"
          @node-selected="handleNodeSelected"
          @node-edited="handleNodeEdited"
          @node-deleted="handleNodeDeleted"
        />
      </div>
    </div>

    <div v-if="showOpenModal" class="modal-overlay" @click.self="showOpenModal = false">
      <div class="modal">
        <div class="modal-header">
          <h2>打开思维导图</h2>
          <button @click="showOpenModal = false" class="close-btn">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        <div class="modal-body">
          <div v-if="mindmaps.length === 0" class="empty-modal">
            <p>暂无保存的思维导图</p>
            <button @click="handleNew; showOpenModal = false" class="primary-btn">创建新思维导图</button>
          </div>
          <div v-else class="mindmap-grid">
            <div
              v-for="mindmap in mindmaps"
              :key="mindmap.id"
              :class="{ active: state.currentMindMapId === mindmap.id }"
              class="mindmap-card"
              @click="selectMindmap(mindmap.id)"
            >
              <div class="card-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <circle cx="12" cy="12" r="3"></circle>
                  <line x1="12" y1="9" x2="12" y2="3"></line>
                  <line x1="12" y1="15" x2="12" y2="21"></line>
                  <line x1="9" y1="12" x2="3" y2="12"></line>
                  <line x1="15" y1="12" x2="21" y2="12"></line>
                </svg>
              </div>
              <div class="card-info">
                <h3>{{ mindmap.title }}</h3>
                <p>{{ formatDate(mindmap.updatedAt) }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showShortcuts" class="shortcuts-panel">
      <div class="shortcuts-header">
        <h3>快捷键</h3>
        <button @click="showShortcuts = false" class="close-btn">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
      <div class="shortcuts-content">
        <div class="shortcut-item">
          <kbd>Tab</kbd>
          <span>添加子节点</span>
        </div>
        <div class="shortcut-item">
          <kbd>Delete</kbd>
          <span>删除节点</span>
        </div>
        <div class="shortcut-item">
          <kbd>Ctrl</kbd> + <kbd>Z</kbd>
          <span>撤销</span>
        </div>
        <div class="shortcut-item">
          <kbd>Ctrl</kbd> + <kbd>Y</kbd>
          <span>重做</span>
        </div>
        <div class="shortcut-item">
          <kbd>Ctrl</kbd> + <kbd>S</kbd>
          <span>保存</span>
        </div>
        <div class="shortcut-item">
          <kbd>Ctrl</kbd> + <kbd>F</kbd>
          <span>搜索</span>
        </div>
        <div class="shortcut-item">
          <kbd>Ctrl</kbd> + <kbd>+</kbd>
          <span>放大</span>
        </div>
        <div class="shortcut-item">
          <kbd>Ctrl</kbd> + <kbd>-</kbd>
          <span>缩小</span>
        </div>
        <div class="shortcut-item">
          <kbd>Space</kbd> + 拖拽
          <span>平移画布</span>
        </div>
        <div class="shortcut-item">
          <kbd>?</kbd>
          <span>显示快捷键</span>
        </div>
      </div>
    </div>

    <button @click="showShortcuts = !showShortcuts" class="help-btn" title="快捷键 (?)">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"></circle>
        <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
        <line x1="12" y1="17" x2="12.01" y2="17"></line>
      </svg>
    </button>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import Header from './components/Header.vue'
import Sidebar from './components/Sidebar.vue'
import MindMapCanvas from './components/MindMapCanvas.vue'
import { useMindMapStore } from './store/mindmap.js'
import { storage } from './utils/storage.js'
import { autoLayout } from './utils/layout.js'
import { exportAsJSON, exportAsMarkdown, exportAsImage } from './utils/export.js'
import { createShortcutManager } from './utils/shortcuts.js'

const store = useMindMapStore()
const { state, selectedNode } = store

const canvasRef = ref(null)
const sidebarRef = ref(null)
const canvasSize = ref({ width: 800, height: 600 })
const mindmaps = ref([])
const currentTheme = ref('light')
const currentLayout = ref('balanced')
const isSidebarCollapsed = ref(false)
const showOpenModal = ref(false)
const showShortcuts = ref(false)
const shortcutManager = createShortcutManager()

const nodeColors = [
  '#409eff', '#67c23a', '#e6a23c', '#f56c6c',
  '#909399', '#8b5cf6', '#ec4899', '#06b6d4'
]

function getRandomColor() {
  return nodeColors[Math.floor(Math.random() * nodeColors.length)]
}

async function initApp() {
  const settings = await storage.getSettings()
  currentTheme.value = settings.theme || 'light'
  document.documentElement.setAttribute('data-theme', currentTheme.value)
  store.setTheme(currentTheme.value)

  await loadMindmapsList()

  if (mindmaps.value.length > 0) {
    await store.loadMindMap(mindmaps.value[0].id)
  } else {
    await store.createNewMindMap()
  }

  handleAutoLayout()
  updateCanvasSize()
  setupShortcuts()
}

async function loadMindmapsList() {
  mindmaps.value = await storage.getAllMindMaps()
}

function updateCanvasSize() {
  const headerHeight = 60
  const sidebarWidth = isSidebarCollapsed.value ? 60 : 280
  canvasSize.value = {
    width: window.innerWidth - sidebarWidth,
    height: window.innerHeight - headerHeight
  }
}

function setupShortcuts() {
  shortcutManager.register('ctrl+s', () => handleSave())
  shortcutManager.register('ctrl+n', () => handleNew())
  shortcutManager.register('ctrl+o', () => { showOpenModal.value = true })
  shortcutManager.register('ctrl+f', () => { isSidebarCollapsed.value = false })
  shortcutManager.register('ctrl+equal', () => zoomIn())
  shortcutManager.register('ctrl+minus', () => zoomOut())
  shortcutManager.register('ctrl+0', () => resetView())
  shortcutManager.register('?', () => { showShortcuts.value = !showShortcuts.value })

  window.addEventListener('keydown', shortcutManager.handleKeyDown)
}

async function handleNew() {
  await store.createNewMindMap()
  handleAutoLayout()
  await loadMindmapsList()
}

async function handleOpen(id) {
  await store.loadMindMap(id)
  showOpenModal.value = false
}

function handleOpenList() {
  showOpenModal.value = true
}

async function selectMindmap(id) {
  await store.loadMindMap(id)
  showOpenModal.value = false
}

async function handleDeleteMindmap(id) {
  if (confirm('确定要删除这个思维导图吗？')) {
    await storage.deleteMindMap(id)
    await loadMindmapsList()
    if (state.currentMindMapId === id) {
      if (mindmaps.value.length > 0) {
        await store.loadMindMap(mindmaps.value[0].id)
      } else {
        await store.createNewMindMap()
      }
    }
  }
}

async function handleSave() {
  await store.saveToStorage()
  await loadMindmapsList()
}

function updateTitle(title) {
  state.title = title
  store.saveToStorage()
}

function zoomIn() {
  store.setScale(state.scale + 0.1)
}

function zoomOut() {
  store.setScale(state.scale - 0.1)
}

function resetView() {
  store.setScale(1)
  store.setOffset(0, 0)
}

function changeTheme(theme) {
  currentTheme.value = theme
  store.setTheme(theme)
}

function changeLayout(layout) {
  currentLayout.value = layout
  handleAutoLayout()
}

function handleAutoLayout() {
  if (state.rootNodeId) {
    autoLayout(state.rootNodeId, state.nodes, currentLayout.value)
    store.saveToStorage()
  }
}

function handleSearch(keyword) {
  const results = store.searchNodes(keyword)
  if (sidebarRef.value) {
    sidebarRef.value.updateSearchResults(results)
  }
}

function handleFocusNode(nodeId) {
  if (canvasRef.value) {
    canvasRef.value.focusNode(nodeId)
  }
}

function handleNodeSelected(nodeId) {
}

function handleNodeEdited(nodeId) {
}

function handleNodeDeleted(nodeId) {
  store.saveToStorage()
}

function handleAddChild() {
  if (state.selectedNodeId) {
    const parent = state.nodes[state.selectedNodeId]
    const newNode = store.createNode('新节点', state.selectedNodeId, parent.x + 200, parent.y)
    newNode.color = getRandomColor()
    store.selectNode(newNode.id)
    store.saveToStorage()
  }
}

function handleEditNode() {
  if (state.selectedNodeId && canvasRef.value) {
  }
}

function handleDeleteNode() {
  if (state.selectedNodeId && state.selectedNodeId !== state.rootNodeId) {
    store.deleteNode(state.selectedNodeId)
    store.saveToStorage()
  }
}

function handleExportJSON() {
  const data = store.exportToJSON()
  exportAsJSON(data, `${state.title || 'mindmap'}.json`)
}

function handleExportImage() {
  if (canvasRef.value) {
    const stage = canvasRef.value.getStage()
    if (stage) {
      const dataUrl = stage.toDataURL({ pixelRatio: 2 })
      const link = document.createElement('a')
      link.href = dataUrl
      link.download = `${state.title || 'mindmap'}.png`
      link.click()
    }
  }
}

function handleExportMarkdown() {
  const markdown = store.exportToMarkdown()
  exportAsMarkdown(markdown, `${state.title || 'mindmap'}.md`)
}

async function handleImportJSON(file) {
  try {
    const text = await file.text()
    const data = JSON.parse(text)
    store.importFromJSON(data)
    handleAutoLayout()
    store.saveToStorage()
    await loadMindmapsList()
  } catch (error) {
    alert('导入失败：无效的JSON文件')
    console.error(error)
  }
}

function toggleSidebar() {
  isSidebarCollapsed.value = !isSidebarCollapsed.value
  setTimeout(updateCanvasSize, 300)
}

function formatDate(timestamp) {
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

watch(() => state.nodes, () => {
  store.saveToStorage()
}, { deep: true })

onMounted(() => {
  initApp()
  window.addEventListener('resize', updateCanvasSize)
})

onUnmounted(() => {
  window.removeEventListener('resize', updateCanvasSize)
  window.removeEventListener('keydown', shortcutManager.handleKeyDown)
  shortcutManager.clear()
})
</script>

<style scoped>
.app-container {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-color);
  color: var(--text-color);
  transition: background 0.3s, color 0.3s;
}

.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.canvas-wrapper {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: var(--bg-color);
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  min-width: 500px;
  max-width: 80vw;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px;
  border-bottom: 1px solid var(--border-color);
}

.modal-header h2 {
  margin: 0;
  font-size: 18px;
}

.close-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.close-btn:hover {
  background: var(--border-color);
  color: var(--text-color);
}

.modal-body {
  padding: 20px;
  overflow-y: auto;
}

.empty-modal {
  text-align: center;
  padding: 40px;
}

.empty-modal p {
  color: var(--info-color);
  margin-bottom: 20px;
}

.primary-btn {
  padding: 10px 20px;
  background: var(--primary-color);
  color: white;
  border-radius: 6px;
  font-size: 14px;
  transition: opacity 0.2s;
}

.primary-btn:hover {
  opacity: 0.9;
}

.mindmap-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.mindmap-card {
  padding: 20px;
  border: 2px solid var(--border-color);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.mindmap-card:hover {
  border-color: var(--primary-color);
  transform: translateY(-2px);
}

.mindmap-card.active {
  border-color: var(--primary-color);
  background: rgba(64, 158, 255, 0.1);
}

.card-icon {
  color: var(--primary-color);
  margin-bottom: 12px;
}

.card-info h3 {
  margin: 0 0 8px 0;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-info p {
  margin: 0;
  font-size: 12px;
  color: var(--info-color);
}

.shortcuts-panel {
  position: fixed;
  bottom: 80px;
  right: 20px;
  background: var(--bg-color);
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
  padding: 16px;
  z-index: 999;
  min-width: 280px;
}

.shortcuts-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.shortcuts-header h3 {
  margin: 0;
  font-size: 14px;
}

.shortcuts-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.shortcut-item {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
}

.shortcut-item kbd {
  display: inline-block;
  padding: 2px 6px;
  background: var(--border-color);
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
  min-width: 20px;
  text-align: center;
}

.shortcut-item span {
  color: var(--text-secondary);
}

.help-btn {
  position: fixed;
  bottom: 20px;
  right: 20px;
  width: 48px;
  height: 48px;
  background: var(--primary-color);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.4);
  z-index: 999;
  transition: transform 0.2s, box-shadow 0.2s;
}

.help-btn:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.5);
}
</style>

<template>
  <header class="app-header">
    <div class="header-left">
      <div class="logo">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="3"></circle>
          <line x1="12" y1="9" x2="12" y2="3"></line>
          <line x1="12" y1="15" x2="12" y2="21"></line>
          <line x1="9" y1="12" x2="3" y2="12"></line>
          <line x1="15" y1="12" x2="21" y2="12"></line>
          <line x1="7.5" y1="7.5" x2="3.5" y2="3.5"></line>
          <line x1="16.5" y1="16.5" x2="20.5" y2="20.5"></line>
          <line x1="7.5" y1="16.5" x2="3.5" y2="20.5"></line>
          <line x1="16.5" y1="7.5" x2="20.5" y2="3.5"></line>
        </svg>
      </div>
      <div class="title-section">
        <input
          v-if="isEditingTitle"
          ref="titleInput"
          v-model="editingTitle"
          @blur="saveTitle"
          @keydown="handleTitleKeydown"
          class="title-input"
          placeholder="输入思维导图标题"
        />
        <h1 v-else class="app-title" @dblclick="startEditingTitle">{{ title }}</h1>
        <span v-if="isSaving" class="save-status">保存中...</span>
      </div>
    </div>

    <div class="header-center">
      <div class="layout-switcher">
        <button
          v-for="layout in layouts"
          :key="layout.value"
          :class="{ active: currentLayout === layout.value }"
          @click="selectLayout(layout.value)"
          :title="layout.label"
        >
          <span class="layout-icon">{{ layout.icon }}</span>
          <span class="layout-label">{{ layout.label }}</span>
        </button>
      </div>
    </div>

    <div class="header-right">
      <div class="zoom-controls">
        <button @click="zoomOut" title="缩小 (Ctrl+-)">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            <line x1="8" y1="11" x2="14" y2="11"></line>
          </svg>
        </button>
        <span class="zoom-level">{{ Math.round(scale * 100) }}%</span>
        <button @click="zoomIn" title="放大 (Ctrl++)">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            <line x1="11" y1="8" x2="11" y2="14"></line>
            <line x1="8" y1="11" x2="14" y2="11"></line>
          </svg>
        </button>
        <button @click="resetView" title="重置视图">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="1 4 1 10 7 10"></polyline>
            <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path>
          </svg>
        </button>
      </div>

      <div class="theme-switcher">
        <button
          v-for="theme in themes"
          :key="theme.value"
          :class="{ active: currentTheme === theme.value }"
          @click="selectTheme(theme.value)"
          :title="theme.label"
          :style="{ background: theme.color }"
        >
          <span v-if="currentTheme === theme.value">✓</span>
        </button>
      </div>

      <button class="menu-btn" @click="toggleMenu">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="3" y1="12" x2="21" y2="12"></line>
          <line x1="3" y1="6" x2="21" y2="6"></line>
          <line x1="3" y1="18" x2="21" y2="18"></line>
        </svg>
      </button>
    </div>

    <div v-if="showMenu" class="dropdown-menu">
      <div class="menu-section">
        <div class="menu-title">文件</div>
        <button @click="handleNew">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="12" y1="18" x2="12" y2="12"></line>
            <line x1="9" y1="15" x2="15" y2="15"></line>
          </svg>
          新建
          <span class="shortcut">Ctrl+N</span>
        </button>
        <button @click="handleOpen">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
          打开
          <span class="shortcut">Ctrl+O</span>
        </button>
        <button @click="handleSave">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
            <polyline points="17 21 17 13 7 13 7 21"></polyline>
            <polyline points="7 3 7 8 15 8"></polyline>
          </svg>
          保存
          <span class="shortcut">Ctrl+S</span>
        </button>
      </div>
      
      <div class="menu-section">
        <div class="menu-title">导出</div>
        <button @click="handleExportJSON">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="16 18 22 12 16 6"></polyline>
            <polyline points="8 6 2 12 8 18"></polyline>
          </svg>
          导出 JSON
        </button>
        <button @click="handleExportImage">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            <circle cx="8.5" cy="8.5" r="1.5"></circle>
            <polyline points="21 15 16 10 5 21"></polyline>
          </svg>
          导出图片
        </button>
        <button @click="handleExportMarkdown">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="8" y1="13" x2="8" y2="17"></line>
            <polyline points="10.5 15.5 8 13 5.5 15.5"></polyline>
            <line x1="13" y1="13" x2="13" y2="17"></line>
            <line x1="16" y1="13" x2="16" y2="17"></line>
          </svg>
          导出 Markdown
        </button>
      </div>

      <div class="menu-section">
        <div class="menu-title">导入</div>
        <label class="file-upload">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="17 8 12 3 7 8"></polyline>
            <line x1="12" y1="3" x2="12" y2="15"></line>
          </svg>
          导入 JSON
          <input type="file" accept=".json" @change="handleImportJSON" hidden />
        </label>
      </div>

      <div class="menu-section">
        <div class="menu-title">编辑</div>
        <button @click="handleAutoLayout">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="7" height="7"></rect>
            <rect x="14" y="3" width="7" height="7"></rect>
            <rect x="14" y="14" width="7" height="7"></rect>
            <rect x="3" y="14" width="7" height="7"></rect>
          </svg>
          自动布局
        </button>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'

const props = defineProps({
  title: {
    type: String,
    default: '未命名思维导图'
  },
  scale: {
    type: Number,
    default: 1
  },
  currentTheme: {
    type: String,
    default: 'light'
  },
  currentLayout: {
    type: String,
    default: 'balanced'
  },
  isSaving: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  'update:title',
  'zoom-in',
  'zoom-out',
  'reset-view',
  'change-theme',
  'change-layout',
  'new',
  'open',
  'save',
  'export-json',
  'export-image',
  'export-markdown',
  'import-json',
  'auto-layout'
])

const showMenu = ref(false)
const isEditingTitle = ref(false)
const editingTitle = ref('')
const titleInput = ref(null)

const themes = [
  { value: 'light', label: '亮色', color: '#ffffff' },
  { value: 'dark', label: '暗色', color: '#1a1a2e' },
  { value: 'green', label: '绿色', color: '#dcfce7' },
  { value: 'purple', label: '紫色', color: '#f3e8ff' }
]

const layouts = [
  { value: 'balanced', label: '平衡', icon: '⇔' },
  { value: 'right', label: '右向', icon: '→' },
  { value: 'left', label: '左向', icon: '←' },
  { value: 'radial', label: '辐射', icon: '◎' }
]

function startEditingTitle() {
  editingTitle.value = props.title
  isEditingTitle.value = true
  nextTick(() => {
    if (titleInput.value) {
      titleInput.value.focus()
      titleInput.value.select()
    }
  })
}

function saveTitle() {
  if (editingTitle.value.trim()) {
    emit('update:title', editingTitle.value.trim())
  }
  isEditingTitle.value = false
}

function handleTitleKeydown(e) {
  if (e.key === 'Enter') {
    e.preventDefault()
    saveTitle()
  } else if (e.key === 'Escape') {
    isEditingTitle.value = false
  }
}

function zoomIn() {
  emit('zoom-in')
}

function zoomOut() {
  emit('zoom-out')
}

function resetView() {
  emit('reset-view')
}

function selectTheme(theme) {
  emit('change-theme', theme)
}

function selectLayout(layout) {
  emit('change-layout', layout)
}

function toggleMenu() {
  showMenu.value = !showMenu.value
}

function handleNew() {
  showMenu.value = false
  emit('new')
}

function handleOpen() {
  showMenu.value = false
  emit('open')
}

function handleSave() {
  showMenu.value = false
  emit('save')
}

function handleExportJSON() {
  showMenu.value = false
  emit('export-json')
}

function handleExportImage() {
  showMenu.value = false
  emit('export-image')
}

function handleExportMarkdown() {
  showMenu.value = false
  emit('export-markdown')
}

function handleImportJSON(e) {
  showMenu.value = false
  const file = e.target.files?.[0]
  if (file) {
    emit('import-json', file)
  }
  e.target.value = ''
}

function handleAutoLayout() {
  showMenu.value = false
  emit('auto-layout')
}
</script>

<style scoped>
.app-header {
  height: 60px;
  background: var(--header-bg);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  position: relative;
  z-index: 100;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 200px;
}

.logo {
  color: var(--primary-color);
  display: flex;
  align-items: center;
  justify-content: center;
}

.title-section {
  display: flex;
  align-items: center;
  gap: 8px;
}

.app-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-color);
  cursor: pointer;
  margin: 0;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background 0.2s;
}

.app-title:hover {
  background: var(--border-color);
}

.title-input {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-color);
  background: var(--bg-color);
  border: 2px solid var(--primary-color);
  border-radius: 4px;
  padding: 4px 8px;
  outline: none;
  min-width: 200px;
}

.save-status {
  font-size: 12px;
  color: var(--info-color);
}

.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.layout-switcher {
  display: flex;
  background: var(--bg-color);
  border-radius: 8px;
  padding: 4px;
  gap: 4px;
}

.layout-switcher button {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.layout-switcher button:hover {
  background: var(--border-color);
}

.layout-switcher button.active {
  background: var(--primary-color);
  color: white;
}

.layout-icon {
  font-size: 14px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 200px;
  justify-content: flex-end;
}

.zoom-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-color);
  border-radius: 8px;
  padding: 4px 8px;
}

.zoom-controls button {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.zoom-controls button:hover {
  background: var(--border-color);
  color: var(--text-color);
}

.zoom-level {
  font-size: 12px;
  color: var(--text-secondary);
  min-width: 40px;
  text-align: center;
}

.theme-switcher {
  display: flex;
  gap: 6px;
}

.theme-switcher button {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 2px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  color: white;
  transition: transform 0.2s, border-color 0.2s;
}

.theme-switcher button:hover {
  transform: scale(1.1);
}

.theme-switcher button.active {
  border-color: var(--primary-color);
}

.menu-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.menu-btn:hover {
  background: var(--border-color);
  color: var(--text-color);
}

.dropdown-menu {
  position: absolute;
  top: 56px;
  right: 16px;
  background: var(--bg-color);
  border-radius: 8px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
  padding: 8px 0;
  min-width: 220px;
  z-index: 200;
}

.menu-section {
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
}

.menu-section:last-child {
  border-bottom: none;
}

.menu-title {
  padding: 4px 16px;
  font-size: 11px;
  font-weight: 600;
  color: var(--info-color);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.dropdown-menu button,
.file-upload {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  font-size: 14px;
  color: var(--text-color);
  text-align: left;
  transition: background 0.2s;
  cursor: pointer;
}

.dropdown-menu button:hover,
.file-upload:hover {
  background: var(--border-color);
}

.shortcut {
  margin-left: auto;
  font-size: 12px;
  color: var(--info-color);
}
</style>

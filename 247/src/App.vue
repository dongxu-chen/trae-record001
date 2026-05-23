<template>
  <div class="app-container">
    <div class="left-sidebar">
      <div class="sidebar-tabs">
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'components' }"
          @click="activeTab = 'components'"
        >
          🧩 组件
        </button>
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'versions' }"
          @click="activeTab = 'versions'"
        >
          📋 版本
        </button>
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'statistics' }"
          @click="activeTab = 'statistics'"
        >
          📊 统计
        </button>
      </div>

      <div class="sidebar-content">
        <LeftPanel v-if="activeTab === 'components'" @add-component="addComponent" />
        
        <VersionManager
          v-else-if="activeTab === 'versions'"
          :form-id="formId"
          :form-items="formItems"
          :current-version="currentVersion"
          @version-change="handleVersionChange"
          @restore-version="handleRestoreVersion"
        />
        
        <StatisticsPanel
          v-else-if="activeTab === 'statistics'"
          :form-id="formId"
          :form-items="formItems"
          :total-submissions="totalSubmissions"
          @optimize-layout="handleOptimizeLayout"
        />
      </div>
    </div>
    
    <div class="center-panel">
      <div class="toolbar">
        <div class="toolbar-left">
          <span class="form-title">{{ formName }}</span>
          <span class="version-badge">v{{ currentVersion }}</span>
          <span v-if="autoSaveStatus" class="save-status">{{ autoSaveStatus }}</span>
        </div>
        <div class="toolbar-right">
          <button class="btn btn-primary" @click="showJsonModal = true">
            生成 JSON Schema
          </button>
          <button class="btn btn-success" @click="showVueModal = true">
            生成 Vue 代码
          </button>
          <button class="btn btn-warning" @click="clearForm">
            清空画布
          </button>
        </div>
      </div>
      
      <FormCanvas
        ref="canvasRef"
        v-model:form-items="formItems"
        :selected-id="selectedId"
        @select-item="selectItem"
      />

      <div class="offline-status" v-if="!isOnline">
        <span class="offline-icon">📴</span>
        <span>离线模式 - 数据将自动同步</span>
        <span class="pending-count" v-if="pendingSubmissions > 0">
          {{ pendingSubmissions }} 条待同步
        </span>
      </div>
    </div>
    
    <RightPanel
      :selected-item="selectedItem"
      :form-items="formItems"
      @update-item="handleItemUpdate"
    />
    
    <div v-if="showJsonModal" class="modal-mask" @click.self="showJsonModal = false">
      <div class="modal">
        <div class="modal-header">
          <span class="modal-title">JSON Schema</span>
          <button class="modal-close" @click="showJsonModal = false">×</button>
        </div>
        <div class="modal-body">
          <pre class="code-block">{{ jsonSchema }}</pre>
        </div>
        <div class="modal-footer">
          <button class="btn btn-primary" @click="copyJson">复制代码</button>
          <button class="btn btn-default" @click="showJsonModal = false">关闭</button>
        </div>
      </div>
    </div>
    
    <div v-if="showVueModal" class="modal-mask" @click.self="showVueModal = false">
      <div class="modal">
        <div class="modal-header">
          <span class="modal-title">Vue 代码</span>
          <button class="modal-close" @click="showVueModal = false">×</button>
        </div>
        <div class="modal-body">
          <pre class="code-block">{{ vueCode }}</pre>
        </div>
        <div class="modal-footer">
          <button class="btn btn-primary" @click="copyVue">复制代码</button>
          <button class="btn btn-default" @click="showVueModal = false">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import LeftPanel from './components/LeftPanel.vue'
import FormCanvas from './components/FormCanvas.vue'
import RightPanel from './components/RightPanel.vue'
import VersionManager from './components/VersionManager.vue'
import StatisticsPanel from './components/StatisticsPanel.vue'
import { createComponent } from './components/componentConfig.js'
import { generateJsonSchema, generateVueCode } from './components/CodeGenerator.js'
import {
  FormDataStorage,
  StatisticsCollector,
  OfflineSubmission,
  setupAutoSave
} from './utils/IndexedDB.js'

const formId = 'default_form'
const formName = ref('可视化表单设计器')
const currentVersion = ref(1)
const totalSubmissions = ref(1)
const pendingSubmissions = ref(0)
const isOnline = ref(navigator.onLine)
const autoSaveStatus = ref('')
const activeTab = ref('components')

const formItems = ref([])
const selectedId = ref('')
const showJsonModal = ref(false)
const showVueModal = ref(false)
const canvasRef = ref(null)

const selectedItem = computed(() => {
  return formItems.value.find(item => item.id === selectedId.value) || null
})

const jsonSchema = computed(() => {
  return generateJsonSchema(formItems.value)
})

const vueCode = computed(() => {
  return generateVueCode(formItems.value)
})

let autoSaveHelper = null

const addComponent = (type) => {
  const newComponent = createComponent(type)
  formItems.value.push(newComponent)
  selectedId.value = newComponent.id
  
  StatisticsCollector.trackChange(formId, newComponent.field, undefined, newComponent.defaultValue)
}

const selectItem = (id) => {
  selectedId.value = id
}

const oldValues = new Map()

const handleItemUpdate = () => {
  formItems.value = [...formItems.value]
  triggerAutoSave()
}

const clearForm = () => {
  formItems.value = []
  selectedId.value = ''
  triggerAutoSave()
}

const copyJson = () => {
  navigator.clipboard.writeText(jsonSchema.value).then(() => {
    alert('JSON Schema 已复制到剪贴板')
  })
}

const copyVue = () => {
  navigator.clipboard.writeText(vueCode.value).then(() => {
    alert('Vue 代码已复制到剪贴板')
  })
}

const setupCanvasDrop = () => {
  nextTick(() => {
    const canvas = document.querySelector('.canvas')
    if (!canvas) return

    canvas.addEventListener('dragover', (e) => {
      e.preventDefault()
      e.dataTransfer.dropEffect = 'copy'
    })

    canvas.addEventListener('drop', (e) => {
      e.preventDefault()
      const type = e.dataTransfer.getData('text/plain')
      if (type) {
        addComponent(type)
      }
    })
  })
}

const triggerAutoSave = () => {
  if (autoSaveHelper) {
    autoSaveHelper.scheduleSave()
    autoSaveStatus.value = '保存中...'
    setTimeout(() => {
      autoSaveStatus.value = '已自动保存'
      setTimeout(() => {
        autoSaveStatus.value = ''
      }, 2000)
    }, 500)
  }
}

const loadSavedForm = async () => {
  const saved = await FormDataStorage.getLatestFormData(formId)
  if (saved && saved.data && saved.data.length > 0) {
    formItems.value = saved.data
    currentVersion.value = saved.version
  }
  
  const pending = await OfflineSubmission.getPendingSubmissions(formId)
  pendingSubmissions.value = pending.length
}

const handleVersionChange = (newVersion) => {
  currentVersion.value = newVersion
}

const handleRestoreVersion = (version) => {
  if (version.schema?.properties) {
    const newItems = []
    for (const [field, config] of Object.entries(version.schema.properties)) {
      const type = config.type === 'number' ? 'number' : 'input'
      const newItem = createComponent(type)
      newItem.field = field
      newItem.label = config.title || field
      newItem.required = version.schema.required?.includes(field) || false
      newItems.push(newItem)
    }
    formItems.value = newItems
    currentVersion.value = version.version
  }
}

const handleOptimizeLayout = (options) => {
  if (options.autoGroupByFillRate && options.fieldStats) {
    const sortedItems = [...formItems.value].sort((a, b) => {
      const statA = options.fieldStats.find(s => s.fieldName === a.label || s.fieldName === a.field)
      const statB = options.fieldStats.find(s => s.fieldName === b.label || s.fieldName === b.field)
      const rateA = statA ? parseFloat(statA.fillRate) : 0
      const rateB = statB ? parseFloat(statB.fillRate) : 0
      return rateB - rateA
    })
    formItems.value = sortedItems
  }
}

const syncOfflineData = async () => {
  if (!isOnline.value) return
  
  const results = await OfflineSubmission.syncPending(formId, async (data) => {
    console.log('同步离线数据:', data)
    return true
  })
  
  const successCount = results.filter(r => r.success).length
  if (successCount > 0) {
    const pending = await OfflineSubmission.getPendingSubmissions(formId)
    pendingSubmissions.value = pending.length
    console.log(`同步完成: ${successCount}/${results.length} 条`)
  }
}

const handleOnline = () => {
  isOnline.value = true
  syncOfflineData()
}

const handleOffline = () => {
  isOnline.value = false
}

watch(() => formItems.value, (newItems, oldItems) => {
  if (oldItems && newItems) {
    const oldItemMap = new Map(oldItems.map(item => [item.id, item]))
    
    newItems.forEach(newItem => {
      const oldItem = oldItemMap.get(newItem.id)
      if (oldItem && oldItem.defaultValue !== newItem.defaultValue) {
        StatisticsCollector.trackChange(
          formId,
          newItem.field,
          oldItem.defaultValue,
          newItem.defaultValue
        )
      }
    })
  }
}, { deep: true })

onMounted(async () => {
  setupCanvasDrop()
  await loadSavedForm()
  
  autoSaveHelper = setupAutoSave(formId, currentVersion.value, formItems, 1000)
  
  StatisticsCollector.init(formId, formItems.value.map(item => item.field))
  
  window.addEventListener('online', handleOnline)
  window.addEventListener('offline', handleOffline)
  
  if (isOnline.value) {
    syncOfflineData()
  }
})
</script>

<style>
.app-container {
  display: flex;
  height: 100%;
  width: 100%;
}

.left-sidebar {
  width: 320px;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-right: 1px solid #e8e8e8;
}

.sidebar-tabs {
  display: flex;
  border-bottom: 1px solid #e8e8e8;
}

.tab-btn {
  flex: 1;
  padding: 12px 8px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 13px;
  color: #606266;
  transition: all 0.2s;
}

.tab-btn:hover {
  background: #f5f7fa;
}

.tab-btn.active {
  color: #409eff;
  background: #ecf5ff;
  border-bottom: 2px solid #409eff;
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
}

.left-panel {
  width: 100% !important;
}

.center-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

.toolbar {
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.form-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.version-badge {
  padding: 2px 8px;
  background: #409eff;
  color: #fff;
  border-radius: 4px;
  font-size: 12px;
}

.save-status {
  font-size: 12px;
  color: #67c23a;
}

.toolbar-right {
  display: flex;
  gap: 8px;
}

.offline-status {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 10px 16px;
  background: #fdf6ec;
  color: #e6a23c;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.offline-icon {
  font-size: 16px;
}

.pending-count {
  margin-left: auto;
  padding: 2px 8px;
  background: #e6a23c;
  color: #fff;
  border-radius: 10px;
  font-size: 12px;
}

.modal {
  width: 900px !important;
}
</style>

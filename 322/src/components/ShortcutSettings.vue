<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content shortcut-modal">
      <div class="modal-header">
        <h3>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="4" width="20" height="16" rx="2" ry="2"></rect>
            <line x1="6" y1="8" x2="6" y2="8"></line>
            <line x1="10" y1="8" x2="10" y2="8"></line>
            <line x1="14" y1="8" x2="14" y2="8"></line>
            <line x1="18" y1="8" x2="18" y2="8"></line>
            <line x1="8" y1="12" x2="8" y2="12"></line>
            <line x1="12" y1="12" x2="12" y2="12"></line>
            <line x1="16" y1="12" x2="16" y2="12"></line>
            <line x1="10" y1="16" x2="14" y2="16"></line>
          </svg>
          快捷键设置
        </h3>
        <button class="modal-close" @click="$emit('close')">×</button>
      </div>

      <div class="modal-body shortcut-body">
        <div class="shortcut-header">
          <div class="shortcut-actions">
            <button class="btn btn-secondary" @click="resetAll">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path>
                <path d="M3 3v5h5"></path>
              </svg>
              重置全部
            </button>
            <button class="btn btn-secondary" @click="exportShortcuts">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
              </svg>
              导出
            </button>
            <button class="btn btn-secondary" @click="triggerImport">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="17 8 12 3 7 8"></polyline>
                <line x1="12" y1="3" x2="12" y2="15"></line>
              </svg>
              导入
            </button>
          </div>
          <div class="shortcut-enable">
            <label class="switch-label">
              <input type="checkbox" v-model="enabled" @change="toggleEnabled" />
              <span class="switch-slider"></span>
            </label>
            <span class="enable-text">{{ enabled ? '已启用' : '已禁用' }}</span>
          </div>
        </div>

        <div v-if="shortcutManager.isRecording.value" class="recording-overlay">
          <div class="recording-content">
            <div class="recording-animation">
              <div class="pulse"></div>
              <div class="pulse delay-1"></div>
              <div class="pulse delay-2"></div>
            </div>
            <p class="recording-text">请按下新的快捷键...</p>
            <p class="recording-hint">按 ESC 取消</p>
            <div v-if="shortcutManager.recordedKey.value" class="recorded-key">
              {{ shortcutManager.recordedKey.value }}
            </div>
          </div>
        </div>

        <div v-if="conflictMessage" class="conflict-alert">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          {{ conflictMessage }}
        </div>

        <div class="shortcut-groups">
          <div 
            v-for="group in groupedShortcuts" 
            :key="group.category"
            class="shortcut-group"
          >
            <h4 class="group-title">{{ group.category }}</h4>
            <div class="shortcut-list">
              <div 
                v-for="item in group.shortcuts" 
                :key="item.action"
                class="shortcut-item"
                :class="{ 
                  modified: !item.isDefault,
                  recording: recordingAction === item.action
                }"
              >
                <div class="shortcut-info">
                  <span class="shortcut-description">{{ item.description }}</span>
                  <span v-if="!item.isDefault" class="modified-badge">自定义</span>
                </div>
                <div class="shortcut-keys">
                  <button 
                    v-if="recordingAction !== item.action"
                    class="shortcut-key-btn"
                    @click="startRecording(item.action)"
                  >
                    <span class="key-combination">{{ item.display }}</span>
                    <span class="edit-icon">✎</span>
                  </button>
                  <div v-else class="recording-btn">
                    <span class="recording-dot"></span>
                    录制中...
                  </div>
                  <button 
                    v-if="!item.isDefault"
                    class="reset-btn"
                    @click="resetShortcut(item.action)"
                    title="恢复默认"
                  >
                    ↺
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="shortcut-tips">
          <h5>提示</h5>
          <ul>
            <li>点击快捷键组合可以重新录制</li>
            <li>支持 Ctrl、Alt、Shift 组合键</li>
            <li>设置会自动保存到本地</li>
            <li>在文本输入框中快捷键无效</li>
          </ul>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn btn-secondary" @click="$emit('close')">关闭</button>
      </div>
    </div>
  </div>
  <input 
    ref="fileInput" 
    type="file" 
    accept=".json" 
    style="display: none" 
    @change="handleImport"
  />
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import shortcutManager from '../utils/shortcutManager'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  }
})

defineEmits(['close'])

const fileInput = ref(null)
const enabled = ref(true)
const recordingAction = ref(null)
const conflictMessage = ref(null)

const groupedShortcuts = computed(() => shortcutManager.getShortcutsByCategory())

watch(() => props.visible, (val) => {
  if (val) {
    enabled.value = shortcutManager.enabled.value
    conflictMessage.value = null
  }
})

onMounted(() => {
  shortcutManager.on('shortcut:conflict', handleConflict)
})

onUnmounted(() => {
  shortcutManager.off('shortcut:conflict', handleConflict)
})

const toggleEnabled = () => {
  shortcutManager.setEnabled(enabled.value)
}

const startRecording = async (action) => {
  recordingAction.value = action
  conflictMessage.value = null
  
  try {
    const result = await shortcutManager.startRecording(action)
    
    if (result.success) {
      conflictMessage.value = null
    } else if (result.conflict) {
      conflictMessage.value = `快捷键与 "${getActionDescription(result.conflict)}" 冲突，请选择其他组合`
    }
  } catch (e) {
    console.error('Recording error:', e)
  } finally {
    recordingAction.value = null
  }
}

const resetShortcut = (action) => {
  shortcutManager.resetShortcut(action)
  conflictMessage.value = null
}

const resetAll = () => {
  if (confirm('确定要重置所有快捷键为默认吗？')) {
    shortcutManager.resetAll()
    conflictMessage.value = null
  }
}

const handleConflict = (data) => {
  conflictMessage.value = `快捷键冲突: ${data.conflict}`
  setTimeout(() => {
    conflictMessage.value = null
  }, 3000)
}

const getActionDescription = (action) => {
  const shortcut = shortcutManager.shortcuts[action]
  return shortcut ? shortcut.description : action
}

const exportShortcuts = () => {
  const data = shortcutManager.exportShortcuts()
  const blob = new Blob([data], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'shortcuts.json'
  a.click()
  URL.revokeObjectURL(url)
}

const triggerImport = () => {
  fileInput.value?.click()
}

const handleImport = (e) => {
  const file = e.target.files?.[0]
  if (!file) return
  
  const reader = new FileReader()
  reader.onload = (e) => {
    const success = shortcutManager.importShortcuts(e.target.result)
    if (success) {
      conflictMessage.value = '导入成功！'
      setTimeout(() => {
        conflictMessage.value = null
      }, 2000)
    } else {
      conflictMessage.value = '导入失败，请检查文件格式'
    }
  }
  reader.readAsText(file)
  e.target.value = ''
}
</script>

<style scoped>
.shortcut-modal {
  min-width: 600px;
  max-width: 700px;
  max-height: 85vh;
}

.shortcut-body {
  overflow-y: auto;
  max-height: calc(85vh - 120px);
  padding: 20px;
}

.shortcut-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #ebeef5;
}

.shortcut-actions {
  display: flex;
  gap: 8px;
}

.shortcut-enable {
  display: flex;
  align-items: center;
  gap: 10px;
}

.enable-text {
  font-size: 13px;
  color: #606266;
}

.switch-label {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
}

.switch-label input {
  opacity: 0;
  width: 0;
  height: 0;
}

.switch-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #dcdfe6;
  transition: 0.3s;
  border-radius: 24px;
}

.switch-slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.3s;
  border-radius: 50%;
}

.switch-label input:checked + .switch-slider {
  background-color: #409eff;
}

.switch-label input:checked + .switch-slider:before {
  transform: translateX(20px);
}

.recording-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  border-radius: 8px;
}

.recording-content {
  text-align: center;
  color: #fff;
}

.recording-animation {
  position: relative;
  width: 80px;
  height: 80px;
  margin: 0 auto 20px;
}

.pulse {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 20px;
  height: 20px;
  background: #f56c6c;
  border-radius: 50%;
  animation: pulse 1.5s ease-out infinite;
}

.pulse.delay-1 {
  animation-delay: 0.5s;
}

.pulse.delay-2 {
  animation-delay: 1s;
}

@keyframes pulse {
  0% {
    width: 20px;
    height: 20px;
    opacity: 1;
  }
  100% {
    width: 80px;
    height: 80px;
    opacity: 0;
  }
}

.recording-text {
  font-size: 18px;
  font-weight: 500;
  margin-bottom: 8px;
}

.recording-hint {
  font-size: 13px;
  color: #909399;
  margin-bottom: 16px;
}

.recorded-key {
  display: inline-block;
  padding: 8px 20px;
  background: rgba(64, 158, 255, 0.2);
  border: 1px solid #409eff;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  color: #409eff;
}

.conflict-alert {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #fef0f0;
  color: #f56c6c;
  border-radius: 6px;
  margin-bottom: 20px;
  font-size: 13px;
}

.shortcut-groups {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.group-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 2px solid #ebeef5;
}

.shortcut-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.shortcut-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 8px;
  border: 1px solid transparent;
  transition: all 0.2s ease;
}

.shortcut-item:hover {
  background: #ecf5ff;
  border-color: #d9ecff;
}

.shortcut-item.modified {
  background: #f0f9eb;
  border-color: #c2e7b0;
}

.shortcut-item.recording {
  background: #fef0f0;
  border-color: #fbc4c4;
}

.shortcut-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.shortcut-description {
  font-size: 14px;
  color: #303133;
}

.modified-badge {
  padding: 2px 8px;
  background: #67c23a;
  color: #fff;
  font-size: 11px;
  border-radius: 10px;
}

.shortcut-keys {
  display: flex;
  align-items: center;
  gap: 8px;
}

.shortcut-key-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: #fff;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: 'Courier New', monospace;
}

.shortcut-key-btn:hover {
  border-color: #409eff;
  background: #ecf5ff;
}

.key-combination {
  font-size: 13px;
  color: #606266;
  font-weight: 500;
}

.edit-icon {
  font-size: 12px;
  color: #909399;
}

.recording-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: #fef0f0;
  border: 1px solid #fbc4c4;
  border-radius: 6px;
  color: #f56c6c;
  font-size: 13px;
}

.recording-dot {
  width: 8px;
  height: 8px;
  background: #f56c6c;
  border-radius: 50%;
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.reset-btn {
  width: 28px;
  height: 28px;
  background: #fff;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  color: #909399;
  transition: all 0.2s ease;
}

.reset-btn:hover {
  border-color: #e6a23c;
  color: #e6a23c;
}

.shortcut-tips {
  margin-top: 24px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
}

.shortcut-tips h5 {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.shortcut-tips ul {
  margin: 0;
  padding-left: 20px;
  color: #606266;
  font-size: 12px;
  line-height: 1.8;
}
</style>

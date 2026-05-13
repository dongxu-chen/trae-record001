<template>
  <div class="key-browser-container">
    <div class="tabs-header">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="tab-btn"
        :class="{ active: activeTab === tab.id }"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>

    <div class="tabs-content">
      <div v-show="activeTab === 'keys'" class="tab-panel">
        <KeyTree
          ref="keyTreeRef"
          :connection-id="connectionId"
          @error="handleError"
          @data-changed="handleDataChanged"
        />
      </div>

      <div v-show="activeTab === 'console'" class="tab-panel">
        <Console
          :connection-id="connectionId"
          @error="handleError"
          @data-changed="handleDataChanged"
        />
      </div>

      <div v-show="activeTab === 'slowlog'" class="tab-panel">
        <SlowLog
          :connection-id="connectionId"
          @error="handleError"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import KeyTree from './KeyTree.vue'
import Console from './Console.vue'
import SlowLog from './SlowLog.vue'

const props = defineProps({
  connectionId: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['error'])

const tabs = [
  { id: 'keys', label: '键浏览' },
  { id: 'console', label: '控制台' },
  { id: 'slowlog', label: '慢查询' }
]

const activeTab = ref('keys')
const keyTreeRef = ref(null)

function handleError(msg) {
  emit('error', msg)
}

function handleDataChanged() {
  if (activeTab.value === 'keys' && keyTreeRef.value) {
    keyTreeRef.value.loadKeys()
  }
}

watch(() => props.connectionId, () => {
  activeTab.value = 'keys'
})
</script>

<style scoped>
.key-browser-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: white;
}

.tabs-header {
  display: flex;
  border-bottom: 1px solid #e0e0e0;
  background: #fafafa;
  padding: 0 16px;
}

.tab-btn {
  padding: 12px 20px;
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 13px;
  color: #666;
  position: relative;
}

.tab-btn:hover {
  color: #333;
  background: #f0f0f0;
}

.tab-btn.active {
  color: #3498db;
  font-weight: 500;
}

.tab-btn.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: #3498db;
}

.tabs-content {
  flex: 1;
  overflow: hidden;
}

.tab-panel {
  height: 100%;
}
</style>

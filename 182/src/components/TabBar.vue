<template>
  <div class="tab-bar">
    <div class="tabs-container">
      <div
        v-for="tab in tabs"
        :key="tab.id"
        class="tab-item"
        :class="{ active: tab.id === activeTabId }"
        @click="$emit('switchTab', tab.id)"
      >
        <span class="tab-title" :title="tab.name">{{ tab.name }}</span>
        <span v-if="tabs.length > 1" class="tab-close" @click.stop="$emit('closeTab', tab.id)">×</span>
      </div>
      <div class="tab-add" @click="$emit('addTab')">
        <span>+</span>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  tabs: {
    type: Array,
    required: true
  },
  activeTabId: {
    type: String,
    required: true
  }
})

defineEmits(['switchTab', 'closeTab', 'addTab'])
</script>

<style scoped>
.tab-bar {
  background: #fff;
  border-bottom: 1px solid #e0e0e0;
  display: flex;
  align-items: flex-end;
  padding: 0 8px;
}

.tabs-container {
  display: flex;
  align-items: flex-end;
  flex: 1;
  overflow-x: auto;
  scrollbar-width: thin;
}

.tabs-container::-webkit-scrollbar {
  height: 4px;
}

.tabs-container::-webkit-scrollbar-track {
  background: #f0f0f0;
}

.tabs-container::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 2px;
}

.tab-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  border: 1px solid transparent;
  border-bottom: none;
  border-radius: 4px 4px 0 0;
  cursor: pointer;
  margin-right: 4px;
  background: #fafafa;
  min-width: 120px;
  max-width: 200px;
  transition: all 0.2s;
  position: relative;
  bottom: -1px;
}

.tab-item:hover {
  background: #f0f0f0;
}

.tab-item.active {
  background: #fff;
  border-color: #e0e0e0;
  border-bottom: 1px solid #fff;
}

.tab-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  color: #333;
}

.tab-close {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  margin-left: 8px;
  font-size: 16px;
  color: #999;
  line-height: 1;
}

.tab-close:hover {
  background: #ff4d4f;
  color: #fff;
}

.tab-add {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border-radius: 4px;
  color: #666;
  font-size: 18px;
  margin-left: 4px;
}

.tab-add:hover {
  background: #f0f0f0;
  color: #1890ff;
}
</style>

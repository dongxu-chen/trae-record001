<script setup lang="ts">
import { ref, computed } from 'vue'
import draggable from 'vuedraggable'
import DesignerField from '@/components/fields/DesignerField.vue'
import { useDesignerStore } from '@/stores/designer'
import { Layout } from 'lucide-vue-next'

const store = useDesignerStore()
const dropZoneRef = ref<HTMLElement | null>(null)
const isDragOver = ref(false)

const fields = computed(() => store.currentTab?.fields || [])

function handleDragOver(e: DragEvent) {
  e.preventDefault()
  if (e.dataTransfer) {
    e.dataTransfer.dropEffect = 'copy'
  }
  isDragOver.value = true
}

function handleDragLeave() {
  isDragOver.value = false
}

function handleDrop(e: DragEvent) {
  e.preventDefault()
  isDragOver.value = false
  
  if (e.dataTransfer) {
    const type = e.dataTransfer.getData('component-type')
    const label = e.dataTransfer.getData('component-label')
    
    if (type && label) {
      store.addField(type, label)
    }
  }
}

function handleCanvasClick() {
  store.selectField(null)
}

function handleChange() {
  store.saveToHistory('move')
}
</script>

<template>
  <div 
    ref="dropZoneRef"
    class="design-canvas flex-1 bg-slate-100 overflow-auto p-6"
    :class="{ 'bg-primary-50': isDragOver }"
    @dragover="handleDragOver"
    @dragleave="handleDragLeave"
    @drop="handleDrop"
    @click="handleCanvasClick"
  >
    <div class="max-w-2xl mx-auto">
      <div 
        class="min-h-[500px] bg-white rounded-xl shadow-sm border border-slate-200 p-6"
        :class="{ 'border-primary-400 border-dashed': isDragOver }"
      >
        <div v-if="fields.length === 0" class="h-full flex flex-col items-center justify-center text-slate-400 py-20">
          <Layout :size="48" class="mb-4 opacity-50" />
          <p class="text-center">
            {{ isDragOver ? '松开鼠标添加组件' : '从左侧拖拽组件到这里' }}
          </p>
          <p class="text-xs mt-2">或点击左侧组件直接添加</p>
        </div>

        <draggable
          v-else
          v-model="store.currentTab!.fields"
          item-key="id"
          class="space-y-3"
          ghost-class="sortable-ghost"
          drag-class="sortable-drag"
          animation="200"
          handle=".cursor-move"
          @change="handleChange"
        >
          <template #item="{ element }">
            <DesignerField :field="element" />
          </template>
        </draggable>
      </div>
    </div>
  </div>
</template>

<style scoped>
.design-canvas {
  background-image: radial-gradient(circle, #cbd5e1 1px, transparent 1px);
  background-size: 20px 20px;
}
</style>

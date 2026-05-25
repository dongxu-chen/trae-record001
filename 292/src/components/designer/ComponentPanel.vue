<script setup lang="ts">
import { ref } from 'vue'
import * as Icons from 'lucide-vue-next'
import { componentConfigs, categories } from '@/config/components'
import { useDesignerStore } from '@/stores/designer'

const store = useDesignerStore()
const activeCategory = ref('basic')

function handleDragStart(e: DragEvent, config: typeof componentConfigs[0]) {
  if (e.dataTransfer) {
    e.dataTransfer.setData('component-type', config.type)
    e.dataTransfer.setData('component-label', config.label)
    e.dataTransfer.effectAllowed = 'copy'
  }
}

function handleClick(config: typeof componentConfigs[0]) {
  store.addField(config.type, config.label)
}

function getIcon(iconName: string) {
  const iconKey = iconName.split('-').map((s, i) => 
    i === 0 ? s : s.charAt(0).toUpperCase() + s.slice(1)
  ).join('')
  return (Icons as any)[iconKey.charAt(0).toUpperCase() + iconKey.slice(1)] || Icons.Type
}
</script>

<template>
  <div class="component-panel h-full flex flex-col bg-white border-r border-slate-200">
    <div class="p-4 border-b border-slate-200">
      <h2 class="font-semibold text-slate-800">组件库</h2>
      <p class="text-xs text-slate-500 mt-1">拖拽组件到画布或点击添加</p>
    </div>

    <div class="flex border-b border-slate-200">
      <button
        v-for="cat in categories"
        :key="cat.key"
        class="flex-1 px-2 py-2 text-xs font-medium transition-colors"
        :class="activeCategory === cat.key 
          ? 'text-primary-600 border-b-2 border-primary-500 bg-primary-50' 
          : 'text-slate-600 hover:text-slate-800 hover:bg-slate-50'"
        @click="activeCategory = cat.key"
      >
        {{ cat.label }}
      </button>
    </div>

    <div class="flex-1 overflow-y-auto p-3">
      <div class="grid grid-cols-2 gap-2">
        <div
          v-for="config in componentConfigs.filter(c => c.category === activeCategory)"
          :key="config.type"
          class="component-item p-3 bg-slate-50 border border-slate-200 rounded-lg cursor-grab hover:bg-white hover:border-primary-300 hover:shadow-sm transition-all duration-200"
          draggable="true"
          @dragstart="handleDragStart($event, config)"
          @click="handleClick(config)"
        >
          <div class="flex flex-col items-center gap-1.5">
            <div class="w-8 h-8 flex items-center justify-center rounded-lg bg-primary-100 text-primary-600">
              <component :is="getIcon(config.icon)" :size="18" />
            </div>
            <span class="text-xs text-slate-700 text-center">{{ config.label }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.component-item:active {
  cursor: grabbing;
}
</style>

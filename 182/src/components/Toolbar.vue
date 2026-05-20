<template>
  <div class="toolbar">
    <span class="toolbar-label">布局:</span>
    <button class="toolbar-btn" :class="{ primary: layoutType === 'hierarchical' }" @click="$emit('layout', 'hierarchical')">
      层次布局
    </button>
    <button class="toolbar-btn" :class="{ primary: layoutType === 'forceDirected' }" @click="$emit('layout', 'forceDirected')">
      力导向布局
    </button>
    <button class="toolbar-btn" :class="{ primary: layoutType === 'circular' }" @click="$emit('layout', 'circular')">
      环形布局
    </button>

    <div class="toolbar-divider"></div>

    <span class="toolbar-label">节点:</span>
    <button class="toolbar-btn" @click="$emit('addNode', 'rectangle')">矩形</button>
    <button class="toolbar-btn" @click="$emit('addNode', 'circle')">圆形</button>
    <button class="toolbar-btn" @click="$emit('addNode', 'diamond')">菱形</button>
    <button class="toolbar-btn" @click="$emit('addNode', 'parallelogram')">平行四边形</button>
    <button class="toolbar-btn" @click="$emit('addNode', 'document')">文档</button>

    <div class="toolbar-divider"></div>

    <button class="toolbar-btn" @click="$emit('createGroup')">
      分组
    </button>
    <button class="toolbar-btn" @click="$emit('ungroup')" :disabled="!isGroupSelected">
      取消分组
    </button>

    <div class="toolbar-divider"></div>

    <label class="toolbar-btn" :class="{ active: snapEnabled }" style="cursor: pointer;">
      <input type="checkbox" :checked="snapEnabled" @change="$emit('toggleSnap')" style="margin-right: 4px; vertical-align: middle;" />
      对齐吸附
    </label>

    <div class="toolbar-divider"></div>

    <button class="toolbar-btn" @click="$emit('importFile')">
      📁 导入
    </button>

    <div class="toolbar-divider"></div>

    <button class="toolbar-btn danger" @click="$emit('deleteSelected')" :disabled="!selectedObject">
      删除
    </button>
    <button class="toolbar-btn danger" @click="$emit('clearAll')">
      清空
    </button>

    <div class="toolbar-divider"></div>

    <span class="toolbar-label">导出:</span>
    <button class="toolbar-btn primary" @click="$emit('exportSVG')">SVG</button>
    <button class="toolbar-btn primary" @click="$emit('exportPNG')">PNG</button>
    <button class="toolbar-btn" @click="$emit('exportJSON')">JSON</button>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  layoutType: {
    type: String,
    default: 'hierarchical'
  },
  selectedObject: {
    type: Object,
    default: null
  },
  snapEnabled: {
    type: Boolean,
    default: true
  }
})

defineEmits(['layout', 'addNode', 'deleteSelected', 'clearAll', 'exportSVG', 'exportPNG', 'exportJSON', 'createGroup', 'ungroup', 'toggleSnap', 'importFile'])

const isGroupSelected = computed(() => {
  return props.selectedObject?.type === 'node' && props.selectedObject.data.isGroup
})
</script>

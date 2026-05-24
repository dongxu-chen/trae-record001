<template>
  <v-group :x="node.x" :y="node.y">
    <v-rect
      :config="{
        width: node.width,
        height: node.height,
        fill: isSelected ? lightenColor(node.color, 20) : node.color,
        stroke: isSelected ? '#fff' : 'transparent',
        strokeWidth: isSelected ? 3 : 0,
        cornerRadius: 8,
        shadowColor: 'rgba(0,0,0,0.2)',
        shadowBlur: isSelected ? 10 : 5,
        shadowOffset: { x: 0, y: 2 },
        shadowOpacity: 0.3
      }"
      @click="handleClick"
      @dblclick="handleDoubleClick"
      @dragstart="handleDragStart"
      @dragend="handleDragEnd"
    />
    
    <v-text
      :config="{
        x: 10,
        y: node.height / 2,
        text: displayText,
        fontSize: node.fontSize,
        fontFamily: 'Segoe UI, PingFang SC, Microsoft YaHei, sans-serif',
        fill: getContrastColor(node.color),
        fontStyle: `${node.fontWeight} ${node.fontStyle}`,
        textDecoration: node.textDecoration,
        align: 'left',
        verticalAlign: 'middle',
        width: node.width - 20,
        ellipsis: true
      }"
      @click="handleClick"
      @dblclick="handleDoubleClick"
    />

    <v-circle
      v-if="node.children && node.children.length > 0"
      :config="{
        x: node.width,
        y: node.height / 2,
        radius: 8,
        fill: node.color,
        stroke: '#fff',
        strokeWidth: 2,
        shadowColor: 'rgba(0,0,0,0.2)',
        shadowBlur: 3,
        shadowOffset: { x: 0, y: 1 },
        shadowOpacity: 0.3,
        cursor: 'pointer'
      }"
      @click="handleToggleCollapse"
    />
    
    <v-text
      v-if="node.children && node.children.length > 0"
      :config="{
        x: node.width,
        y: node.height / 2,
        text: node.collapsed ? '+' : '-',
        fontSize: 12,
        fontFamily: 'Arial',
        fill: '#fff',
        align: 'center',
        verticalAlign: 'middle',
        offsetX: 0,
        offsetY: 1
      }"
      @click="handleToggleCollapse"
    />

    <v-text
      v-if="isSearchResult"
      :config="{
        x: node.width - 20,
        y: 5,
        text: '●',
        fontSize: 10,
        fill: '#ff6b6b'
      }"
    />
  </v-group>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  node: {
    type: Object,
    required: true
  },
  isSelected: {
    type: Boolean,
    default: false
  },
  isSearchResult: {
    type: Boolean,
    default: false
  },
  searchKeyword: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['select', 'edit', 'dragstart', 'dragend', 'toggle-collapse'])

const displayText = computed(() => props.node.text || '未命名节点')

function handleClick(e) {
  e.cancelBubble = true
  emit('select', props.node.id)
}

function handleDoubleClick(e) {
  e.cancelBubble = true
  emit('edit', props.node.id)
}

function handleDragStart(e) {
  emit('dragstart', props.node.id, e)
}

function handleDragEnd(e) {
  emit('dragend', props.node.id, e)
}

function handleToggleCollapse(e) {
  e.cancelBubble = true
  emit('toggle-collapse', props.node.id)
}

function lightenColor(color, percent) {
  const num = parseInt(color.replace('#', ''), 16)
  const amt = Math.round(2.55 * percent)
  const R = Math.min(255, (num >> 16) + amt)
  const G = Math.min(255, ((num >> 8) & 0x00FF) + amt)
  const B = Math.min(255, (num & 0x0000FF) + amt)
  return `#${(0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1)}`
}

function getContrastColor(bgColor) {
  const hex = bgColor.replace('#', '')
  const r = parseInt(hex.substr(0, 2), 16)
  const g = parseInt(hex.substr(2, 2), 16)
  const b = parseInt(hex.substr(4, 2), 16)
  const brightness = (r * 299 + g * 587 + b * 114) / 1000
  return brightness > 128 ? '#333333' : '#ffffff'
}
</script>

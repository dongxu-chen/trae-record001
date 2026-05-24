<template>
  <v-line
    :config="{
      points: points,
      stroke: strokeColor,
      strokeWidth: 2,
      lineCap: 'round',
      lineJoin: 'round',
      bezier: true,
      tension: 0.5,
      shadowColor: 'rgba(0,0,0,0.1)',
      shadowBlur: 2,
      shadowOffset: { x: 0, y: 1 },
      shadowOpacity: 0.3
    }"
  />
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  fromNode: {
    type: Object,
    required: true
  },
  toNode: {
    type: Object,
    required: true
  },
  color: {
    type: String,
    default: '#909399'
  }
})

const points = computed(() => {
  const fromX = props.fromNode.x + props.fromNode.width
  const fromY = props.fromNode.y + props.fromNode.height / 2
  const toX = props.toNode.x
  const toY = props.toNode.y + props.toNode.height / 2

  const controlOffset = Math.abs(toX - fromX) * 0.5
  
  return [
    fromX,
    fromY,
    fromX + controlOffset * 0.3,
    fromY,
    toX - controlOffset * 0.3,
    toY,
    toX,
    toY
  ]
})

const strokeColor = computed(() => props.color)
</script>

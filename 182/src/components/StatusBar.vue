<template>
  <div class="status-bar">
    <div>
      节点: {{ nodeCount }} | 连线: {{ edgeCount }}
    </div>
    <div>
      缩放: {{ Math.round(zoom * 100) }}%
    </div>
  </div>
</template>

<script setup>
defineProps({
  nodeCount: {
    type: Number,
    default: 0
  },
  edgeCount: {
    type: Number,
    default: 0
  },
  zoom: {
    type: Number,
    default: 1
  }
})
</script>

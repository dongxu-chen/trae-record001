<template>
  <div class="danmaku-container" v-if="enabled">
    <div 
      v-for="danmaku in activeDanmaku" 
      :key="danmaku.id"
      class="danmaku-item"
      :style="{
        top: danmaku.top + '%',
        color: danmaku.color,
        fontSize: danmaku.fontSize + 'px',
        animationDuration: (8 + Math.random() * 4) + 's'
      }"
    >
      {{ danmaku.text }}
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { danmakuService } from '../services/danmakuService'

const props = defineProps({
  enabled: {
    type: Boolean,
    default: true
  },
  currentPage: {
    type: Number,
    default: 1
  }
})

const activeDanmaku = ref([])
const usedTracks = new Set()
let danmakuInterval = null

onMounted(() => {
  startDanmakuLoop()
})

onUnmounted(() => {
  if (danmakuInterval) {
    clearInterval(danmakuInterval)
  }
})

watch(() => props.currentPage, () => {
  activeDanmaku.value = []
  usedTracks.clear()
})

watch(() => props.enabled, (newVal) => {
  if (newVal) {
    startDanmakuLoop()
  } else {
    if (danmakuInterval) {
      clearInterval(danmakuInterval)
    }
    activeDanmaku.value = []
  }
})

function startDanmakuLoop() {
  if (danmakuInterval) {
    clearInterval(danmakuInterval)
  }

  danmakuInterval = setInterval(() => {
    if (!props.enabled) return
    
    const pageDanmaku = danmakuService.getDanmakuForPage(props.currentPage)
    if (pageDanmaku.length > 0) {
      const randomDanmaku = pageDanmaku[Math.floor(Math.random() * pageDanmaku.length)]
      addDanmaku(randomDanmaku)
    }
  }, 1500)
}

function addDanmaku(danmaku) {
  let track = findAvailableTrack()
  if (track === -1) return

  const newDanmaku = {
    ...danmaku,
    top: track * 8 + 5,
    uniqueId: danmaku.id + '_' + Date.now()
  }

  activeDanmaku.value.push(newDanmaku)
  usedTracks.add(track)

  setTimeout(() => {
    activeDanmaku.value = activeDanmaku.value.filter(d => d.uniqueId !== newDanmaku.uniqueId)
    usedTracks.delete(track)
  }, 10000)
}

function findAvailableTrack() {
  for (let i = 0; i < 10; i++) {
    if (!usedTracks.has(i)) {
      return i
    }
  }
  return -1
}

function addUserDanmaku(text, color) {
  const danmaku = {
    id: 'user_' + Date.now(),
    text,
    color,
    fontSize: 24,
    page: props.currentPage,
    timestamp: Date.now()
  }
  addDanmaku(danmaku)
}

defineExpose({
  addUserDanmaku
})
</script>

<style scoped>
.danmaku-container {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 80%;
  overflow: hidden;
  pointer-events: none;
  z-index: 60;
}

.danmaku-item {
  position: absolute;
  white-space: nowrap;
  font-weight: bold;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.8), -1px -1px 2px rgba(0, 0, 0, 0.5);
  animation: danmakuScroll linear forwards;
  will-change: transform;
}

@keyframes danmakuScroll {
  from {
    transform: translateX(100vw);
  }
  to {
    transform: translateX(-100%);
  }
}
</style>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps<{
  visible: boolean
  src: string
  alt?: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const scale = ref(1)
const position = ref({ x: 0, y: 0 })
const isDragging = ref(false)
const startPosition = ref({ x: 0, y: 0 })
const isLoading = ref(true)

const transformStyle = computed(() => {
  return `translate(${position.value.x}px, ${position.value.y}px) scale(${scale.value})`
})

const handleWheel = (e: WheelEvent) => {
  e.preventDefault()
  const delta = e.deltaY > 0 ? -0.1 : 0.1
  scale.value = Math.max(0.5, Math.min(5, scale.value + delta))
}

const handleMouseDown = (e: MouseEvent) => {
  if (scale.value > 1) {
    isDragging.value = true
    startPosition.value = {
      x: e.clientX - position.value.x,
      y: e.clientY - position.value.y
    }
  }
}

const handleMouseMove = (e: MouseEvent) => {
  if (isDragging.value) {
    position.value = {
      x: e.clientX - startPosition.value.x,
      y: e.clientY - startPosition.value.y
    }
  }
}

const handleMouseUp = () => {
  isDragging.value = false
}

const resetView = () => {
  scale.value = 1
  position.value = { x: 0, y: 0 }
}

const zoomIn = () => {
  scale.value = Math.min(5, scale.value + 0.25)
}

const zoomOut = () => {
  scale.value = Math.max(0.5, scale.value - 0.25)
}

const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Escape') {
    emit('close')
  }
}

watch(() => props.visible, (newVal) => {
  if (newVal) {
    resetView()
    isLoading.value = true
    document.body.style.overflow = 'hidden'
  } else {
    document.body.style.overflow = ''
  }
})

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  document.body.style.overflow = ''
})
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="visible"
        class="fixed inset-0 z-[100] flex items-center justify-center bg-black/90"
        @click.self="emit('close')"
      >
        <button
          @click="emit('close')"
          class="absolute top-4 right-4 p-2 rounded-full bg-white/10 text-white hover:bg-white/20 transition-colors"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        
        <div class="absolute bottom-4 left-1/2 transform -translate-x-1/2 flex items-center space-x-2">
          <button
            @click="zoomOut"
            class="p-2 rounded-full bg-white/10 text-white hover:bg-white/20 transition-colors"
            title="缩小"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4" />
            </svg>
          </button>
          
          <button
            @click="resetView"
            class="px-3 py-1 rounded-full bg-white/10 text-white hover:bg-white/20 transition-colors text-sm"
            title="重置"
          >
            {{ Math.round(scale * 100) }}%
          </button>
          
          <button
            @click="zoomIn"
            class="p-2 rounded-full bg-white/10 text-white hover:bg-white/20 transition-colors"
            title="放大"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
          </button>
        </div>
        
        <div
          class="relative max-w-[90vw] max-h-[90vh] overflow-hidden cursor-grab active:cursor-grabbing"
          @wheel="handleWheel"
          @mousedown="handleMouseDown"
          @mousemove="handleMouseMove"
          @mouseup="handleMouseUp"
          @mouseleave="handleMouseUp"
        >
          <div v-if="isLoading" class="absolute inset-0 flex items-center justify-center">
            <div class="w-8 h-8 border-4 border-white/30 border-t-white rounded-full animate-spin" />
          </div>
          
          <img
            :src="src"
            :alt="alt || ''"
            class="max-w-full max-h-[90vh] object-contain select-none transition-opacity duration-300"
            :style="{ transform: transformStyle, opacity: isLoading ? 0 : 1 }"
            @load="isLoading = false"
            draggable="false"
          />
        </div>
        
        <p class="absolute bottom-16 text-white/70 text-sm">
          滚动缩放 · 拖动移动 · ESC 关闭
        </p>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

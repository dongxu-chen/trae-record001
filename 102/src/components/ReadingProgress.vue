<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const progress = ref(0)
const isVisible = ref(false)

const updateProgress = () => {
  const scrollTop = window.scrollY
  const docHeight = document.documentElement.scrollHeight - window.innerHeight
  
  if (docHeight > 0) {
    progress.value = Math.min((scrollTop / docHeight) * 100, 100)
    isVisible.value = scrollTop > 100
  }
}

const scrollToTop = () => {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

onMounted(() => {
  window.addEventListener('scroll', updateProgress, { passive: true })
  updateProgress()
})

onUnmounted(() => {
  window.removeEventListener('scroll', updateProgress)
})
</script>

<template>
  <div class="fixed top-0 left-0 right-0 z-50 h-1 bg-gray-200 dark:bg-gray-700">
    <div
      class="h-full bg-gradient-to-r from-primary-500 to-primary-400 transition-all duration-150 ease-out"
      :style="{ width: `${progress}%` }"
    />
  </div>
  
  <button
    v-if="isVisible"
    @click="scrollToTop"
    class="fixed bottom-8 right-8 z-50 p-3 rounded-full bg-white dark:bg-gray-800 text-primary-500 shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-110 border border-gray-200 dark:border-gray-700"
    :title="`阅读进度: ${Math.round(progress)}%`"
  >
    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18" />
    </svg>
    <span class="absolute -top-1 -right-1 text-xs bg-primary-500 text-white rounded-full w-5 h-5 flex items-center justify-center font-medium">
      {{ Math.round(progress) }}
    </span>
  </button>
</template>

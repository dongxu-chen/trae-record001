<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  content: string
  createdAt?: string
  category?: string
}>()

const wordCount = computed(() => {
  const text = props.content.replace(/[#*`\[\]()\-_=+{};:,<.>]/g, '')
  const chinese = (text.match(/[\u4e00-\u9fa5]/g) || []).length
  const english = (text.match(/[a-zA-Z]+/g) || []).length
  return chinese + english
})

const charCount = computed(() => {
  return props.content.replace(/\s/g, '').length
})

const readTime = computed(() => {
  const wordsPerMinute = 300
  const minutes = Math.ceil(wordCount.value / wordsPerMinute)
  return Math.max(1, minutes)
})

const paragraphCount = computed(() => {
  return props.content.split(/\n\n+/).filter(p => p.trim()).length
})

const headingCount = computed(() => {
  return (props.content.match(/^#{1,6}\s/gm) || []).length
})

const codeBlockCount = computed(() => {
  return (props.content.match(/```/g) || []).length / 2
})
</script>

<template>
  <div class="bg-white dark:bg-gray-800 rounded-xl shadow-md border border-gray-200 dark:border-gray-700 p-6">
    <h3 class="text-lg font-bold text-gray-900 dark:text-white mb-4 flex items-center">
      <svg class="w-5 h-5 mr-2 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
      文章统计
    </h3>
    
    <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
      <div class="text-center p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
        <div class="text-2xl font-bold text-primary-500">{{ readTime }}</div>
        <div class="text-sm text-gray-600 dark:text-gray-400">分钟阅读</div>
      </div>
      
      <div class="text-center p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
        <div class="text-2xl font-bold text-primary-500">{{ wordCount.toLocaleString() }}</div>
        <div class="text-sm text-gray-600 dark:text-gray-400">字数</div>
      </div>
      
      <div class="text-center p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
        <div class="text-2xl font-bold text-primary-500">{{ charCount.toLocaleString() }}</div>
        <div class="text-sm text-gray-600 dark:text-gray-400">字符数</div>
      </div>
      
      <div class="text-center p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
        <div class="text-2xl font-bold text-primary-500">{{ paragraphCount }}</div>
        <div class="text-sm text-gray-600 dark:text-gray-400">段落数</div>
      </div>
      
      <div class="text-center p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
        <div class="text-2xl font-bold text-primary-500">{{ headingCount }}</div>
        <div class="text-sm text-gray-600 dark:text-gray-400">标题数</div>
      </div>
      
      <div class="text-center p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
        <div class="text-2xl font-bold text-primary-500">{{ codeBlockCount }}</div>
        <div class="text-sm text-gray-600 dark:text-gray-400">代码块</div>
      </div>
    </div>
    
    <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
      <div class="flex flex-wrap items-center justify-center gap-4 text-sm text-gray-600 dark:text-gray-400">
        <div v-if="createdAt" class="flex items-center">
          <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          发布于 {{ createdAt }}
        </div>
        <div v-if="category" class="flex items-center">
          <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
          </svg>
          {{ category }}
        </div>
      </div>
    </div>
  </div>
</template>

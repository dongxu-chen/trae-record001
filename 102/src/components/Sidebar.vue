<script setup lang="ts">
import { useCategories, useTags } from '../composables/useArticleQueries'
import type { Category, Tag } from '../types'

defineProps<{
  selectedCategory: string | null
  selectedTag: string | null
}>()

const emit = defineEmits<{
  (e: 'selectCategory', category: string | null): void
  (e: 'selectTag', tag: string | null): void
}>()

const { data: categories, isLoading: categoriesLoading } = useCategories()
const { data: tags, isLoading: tagsLoading } = useTags()
</script>

<template>
  <aside class="space-y-6">
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 border border-gray-200 dark:border-gray-700">
      <h3 class="text-lg font-bold text-gray-900 dark:text-white mb-4">分类</h3>
      <div v-if="categoriesLoading" class="space-y-2">
        <div class="h-8 bg-gray-200 dark:bg-gray-700 rounded animate-pulse"></div>
        <div class="h-8 bg-gray-200 dark:bg-gray-700 rounded animate-pulse"></div>
        <div class="h-8 bg-gray-200 dark:bg-gray-700 rounded animate-pulse"></div>
      </div>
      <div v-else class="space-y-2">
        <button
          @click="emit('selectCategory', null)"
          class="w-full text-left px-3 py-2 rounded-lg transition-colors"
          :class="!selectedCategory
            ? 'bg-primary-100 dark:bg-primary-900/50 text-primary-600 dark:text-primary-400 font-medium'
            : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'"
        >
          <span class="flex items-center justify-between">
            全部
          </span>
        </button>
        <button
          v-for="category in categories"
          :key="category.name"
          @click="emit('selectCategory', selectedCategory === category.name ? null : category.name)"
          class="w-full text-left px-3 py-2 rounded-lg transition-colors"
          :class="selectedCategory === category.name
            ? 'bg-primary-100 dark:bg-primary-900/50 text-primary-600 dark:text-primary-400 font-medium'
            : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'"
        >
          <span class="flex items-center justify-between">
            {{ category.name }}
            <span class="text-sm text-gray-500 dark:text-gray-400">{{ category.count }}</span>
          </span>
        </button>
      </div>
    </div>

    <div class="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 border border-gray-200 dark:border-gray-700">
      <h3 class="text-lg font-bold text-gray-900 dark:text-white mb-4">标签</h3>
      <div v-if="tagsLoading" class="flex flex-wrap gap-2">
        <div class="w-16 h-6 bg-gray-200 dark:bg-gray-700 rounded-full animate-pulse"></div>
        <div class="w-20 h-6 bg-gray-200 dark:bg-gray-700 rounded-full animate-pulse"></div>
        <div class="w-14 h-6 bg-gray-200 dark:bg-gray-700 rounded-full animate-pulse"></div>
      </div>
      <div v-else class="flex flex-wrap gap-2">
        <button
          v-for="tag in tags"
          :key="tag.name"
          @click="emit('selectTag', selectedTag === tag.name ? null : tag.name)"
          class="px-3 py-1 text-sm rounded-full transition-colors"
          :class="selectedTag === tag.name
            ? 'bg-primary-500 text-white'
            : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-primary-100 dark:hover:bg-primary-900/50 hover:text-primary-600 dark:hover:text-primary-400'"
        >
          {{ tag.name }}
        </button>
      </div>
    </div>
  </aside>
</template>

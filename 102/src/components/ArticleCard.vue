<script setup lang="ts">
import { useArticlePrefetch } from '../composables/useArticleQueries'
import type { Article } from '../types'

defineProps<{
  article: Article
}>()

const { prefetchArticle } = useArticlePrefetch()
</script>

<template>
  <a
    :href="`/article/${article.id}`"
    class="group block bg-white dark:bg-gray-800 rounded-xl shadow-md hover:shadow-xl transition-all duration-300 overflow-hidden border border-gray-200 dark:border-gray-700"
    @mouseenter="prefetchArticle(article.id)"
    @focus="prefetchArticle(article.id)"
  >
    <div class="relative overflow-hidden">
      <img
        :src="article.coverImage"
        :alt="article.title"
        class="w-full h-48 object-cover group-hover:scale-105 transition-transform duration-300"
        loading="lazy"
      />
      <span class="absolute top-4 left-4 px-3 py-1 bg-primary-500 text-white text-sm font-medium rounded-full">
        {{ article.category }}
      </span>
    </div>

    <div class="p-6">
      <h3 class="text-xl font-bold text-gray-900 dark:text-white mb-2 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
        {{ article.title }}
      </h3>

      <p class="text-gray-600 dark:text-gray-400 mb-4 line-clamp-2">
        {{ article.excerpt }}
      </p>

      <div class="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400">
        <div class="flex items-center space-x-4">
          <span class="flex items-center">
            <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            {{ article.createdAt }}
          </span>
          <span class="flex items-center">
            <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {{ article.readTime }} 分钟
          </span>
        </div>
      </div>

      <div class="mt-4 flex flex-wrap gap-2">
        <span
          v-for="tag in article.tags.slice(0, 3)"
          :key="tag"
          class="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 text-xs rounded-full"
        >
          {{ tag }}
        </span>
      </div>
    </div>
  </a>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { fetchArticles } from '../api/articles'
import { queryKeys } from '../config/vue-query'
import ArticleCard from '../components/ArticleCard.vue'
import Sidebar from '../components/Sidebar.vue'
import Pagination from '../components/Pagination.vue'

const selectedCategory = ref<string | null>(null)
const selectedTag = ref<string | null>(null)
const currentPage = ref(1)

const { data: articlesData, isLoading } = useQuery({
  queryKey: computed(() =>
    queryKeys.articles.lists({
      category: selectedCategory.value,
      tag: selectedTag.value,
      page: currentPage.value,
    })
  ),
  queryFn: () =>
    fetchArticles({
      category: selectedCategory.value,
      tag: selectedTag.value,
      page: currentPage.value,
    }),
})

const filteredArticles = computed(() => articlesData.value?.articles || [])
const total = computed(() => articlesData.value?.total || 0)
const totalPages = computed(() => Math.ceil(total.value / 4))

const handleSelectCategory = (category: string | null) => {
  selectedCategory.value = category
  currentPage.value = 1
}

const handleSelectTag = (tag: string | null) => {
  selectedTag.value = tag
  currentPage.value = 1
}

const handleChangePage = (page: number) => {
  currentPage.value = page
}
</script>

<template>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
    <div class="lg:col-span-2">
      <div class="mb-6">
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          最新文章
        </h1>
        <p class="text-gray-600 dark:text-gray-400">
          共 {{ total }} 篇文章
        </p>
      </div>

      <div v-if="isLoading" class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div v-for="i in 2" :key="i" class="bg-white dark:bg-gray-800 rounded-xl shadow-md overflow-hidden border border-gray-200 dark:border-gray-700">
          <div class="h-48 bg-gray-200 dark:bg-gray-700 animate-pulse"></div>
          <div class="p-6 space-y-4">
            <div class="h-6 bg-gray-200 dark:bg-gray-700 rounded animate-pulse"></div>
            <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded animate-pulse w-3/4"></div>
            <div class="flex space-x-2">
              <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded-full w-16 animate-pulse"></div>
              <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded-full w-16 animate-pulse"></div>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="filteredArticles.length > 0" class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <ArticleCard
          v-for="article in filteredArticles"
          :key="article.id"
          :article="article"
        />
      </div>

      <div v-else class="text-center py-12 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
        <svg class="w-16 h-16 mx-auto mb-4 text-gray-400 dark:text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <p class="text-gray-600 dark:text-gray-400">没有找到相关文章</p>
      </div>

      <Pagination
        v-if="totalPages > 1"
        :current-page="currentPage"
        :total-pages="totalPages"
        @change-page="handleChangePage"
      />
    </div>

    <div class="lg:col-span-1">
      <Sidebar
        :selected-category="selectedCategory"
        :selected-tag="selectedTag"
        @select-category="handleSelectCategory"
        @select-tag="handleSelectTag"
      />
    </div>
  </div>
</template>

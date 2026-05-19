<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useQuery } from '@tanstack/vue-query'
import { fetchArticleById } from '../api/articles'
import { queryKeys } from '../config/vue-query'
import { useSafeMarkdown } from '../composables/useMarkdown'
import ReadingProgress from '../components/ReadingProgress.vue'
import ArticleToc from '../components/ArticleToc.vue'
import ArticleStats from '../components/ArticleStats.vue'
import ImageViewer from '../components/ImageViewer.vue'

const route = useRoute()
const articleId = computed(() => parseInt(route.params.id as string, 10) || null)

const { data: article, isLoading } = useQuery({
  queryKey: computed(() => queryKeys.articles.detail(articleId.value ?? 0)),
  queryFn: () => (articleId.value ? fetchArticleById(articleId.value) : Promise.resolve(null)),
  enabled: !!articleId.value,
})

const { htmlContent, viewerVisible, viewerSrc, viewerAlt, renderMarkdown, closeViewer } = useSafeMarkdown()

watch(article, (newArticle) => {
  if (newArticle) {
    renderMarkdown(newArticle.content)
  }
})

const handleImageClick = (e: Event) => {
  const customEvent = e as CustomEvent<{ src: string; alt: string }>
  viewerSrc.value = customEvent.detail.src
  viewerAlt.value = customEvent.detail.alt
  viewerVisible.value = true
}

onMounted(() => {
  window.addEventListener('imageClick', handleImageClick as EventListener)
})

onUnmounted(() => {
  window.removeEventListener('imageClick', handleImageClick as EventListener)
})
</script>

<template>
  <ReadingProgress />

  <ImageViewer
    :visible="viewerVisible"
    :src="viewerSrc"
    :alt="viewerAlt"
    @close="closeViewer"
  />

  <div v-if="isLoading" class="max-w-4xl mx-auto">
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow-md overflow-hidden border border-gray-200 dark:border-gray-700">
      <div class="h-64 bg-gray-200 dark:bg-gray-700 animate-pulse"></div>
      <div class="p-6 md:p-8 space-y-6">
        <div class="h-8 bg-gray-200 dark:bg-gray-700 rounded animate-pulse w-3/4"></div>
        <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded animate-pulse w-1/2"></div>
        <div class="space-y-4">
          <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded animate-pulse"></div>
          <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded animate-pulse w-5/6"></div>
          <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded animate-pulse w-4/6"></div>
        </div>
      </div>
    </div>
  </div>

  <div v-else-if="article" class="max-w-6xl mx-auto">
    <div class="grid grid-cols-1 lg:grid-cols-4 gap-8">
      <div class="lg:col-span-3">
        <article class="bg-white dark:bg-gray-800 rounded-xl shadow-md overflow-hidden border border-gray-200 dark:border-gray-700">
          <div class="relative">
            <img
              :src="article.coverImage"
              :alt="article.title"
              class="w-full h-64 md:h-80 object-cover"
            />
            <div class="absolute bottom-4 left-6 right-6">
              <span class="inline-flex items-center px-3 py-1 bg-primary-500 text-white text-sm font-medium rounded-full mb-3">
                {{ article.category }}
              </span>
              <h1 class="text-2xl md:text-3xl font-bold text-white drop-shadow-lg">
                {{ article.title }}
              </h1>
            </div>
          </div>

          <div class="p-6 md:p-8">
            <div class="flex flex-wrap items-center gap-4 mb-6 text-sm text-gray-500 dark:text-gray-400">
              <span class="flex items-center">
                <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                {{ article.author }}
              </span>
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

            <div class="flex flex-wrap gap-2 mb-8">
              <span
                v-for="tag in article.tags"
                :key="tag"
                class="px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 text-sm rounded-full hover:bg-primary-100 dark:hover:bg-primary-900/50 hover:text-primary-600 dark:hover:text-primary-400 transition-colors cursor-pointer"
              >
                #{{ tag }}
              </span>
            </div>

            <div
              class="markdown-body"
              v-html="htmlContent"
            />
          </div>
        </article>

        <div class="mt-8">
          <ArticleStats
            :content="article.content"
            :created-at="article.createdAt"
            :category="article.category"
          />
        </div>

        <div class="mt-8">
          <a
            href="/"
            class="inline-flex items-center px-6 py-3 bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors shadow-md hover:shadow-lg"
          >
            <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            返回首页
          </a>
        </div>
      </div>

      <div class="lg:col-span-1">
        <div class="sticky top-24">
          <ArticleToc
            :content="article.content"
          />
        </div>
      </div>
    </div>
  </div>

  <div v-else class="text-center py-12">
    <p class="text-gray-600 dark:text-gray-400">文章不存在</p>
    <a
      href="/"
      class="inline-flex items-center mt-4 text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 font-medium"
    >
      返回首页
    </a>
  </div>
</template>

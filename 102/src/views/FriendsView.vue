<script setup lang="ts">
import { mockFriendLinks } from '../mock'
</script>

<template>
  <div class="max-w-4xl mx-auto">
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow-md overflow-hidden border border-gray-200 dark:border-gray-700">
      <div class="p-6 md:p-8">
        <div class="text-center mb-8">
          <h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            友情链接
          </h1>
          <p class="text-gray-600 dark:text-gray-400">
            优秀博主推荐，互相学习，共同进步
          </p>
        </div>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <a
            v-for="friend in mockFriendLinks"
            :key="friend.id"
            :href="friend.url"
            target="_blank"
            rel="noopener noreferrer"
            class="flex items-center space-x-4 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors group border border-gray-200 dark:border-gray-600"
          >
            <img
              :src="friend.avatar"
              :alt="friend.name"
              class="w-16 h-16 rounded-full object-cover border-2 border-white dark:border-gray-600 shadow-md"
            />
            <div class="flex-1 min-w-0">
              <h3 class="text-lg font-semibold text-gray-900 dark:text-white group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
                {{ friend.name }}
              </h3>
              <p class="text-gray-600 dark:text-gray-400 text-sm truncate">
                {{ friend.description }}
              </p>
            </div>
            <svg class="w-5 h-5 text-gray-400 group-hover:text-primary-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        </div>
        
        <div class="mt-8 p-6 bg-primary-50 dark:bg-primary-900/30 rounded-xl text-center border border-primary-100 dark:border-primary-900/50">
          <h2 class="text-xl font-bold text-gray-900 dark:text-white mb-2">
            申请友链
          </h2>
          <p class="text-gray-600 dark:text-gray-400 mb-4">
            如果你也有博客，欢迎与我交换友链！
          </p>
          <p class="text-gray-600 dark:text-gray-400 text-sm">
            请通过邮件联系我，附上你的博客地址和简介。
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

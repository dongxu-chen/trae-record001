<script setup lang="ts">
import { ref } from 'vue'
import { useThemeStore } from '../stores/theme'
import type { Theme } from '../stores/theme'

const themeStore = useThemeStore()
const showThemeMenu = ref(false)
const showMobileMenu = ref(false)

const navItems = [
  { name: '首页', path: '/' },
  { name: '关于', path: '/about' },
  { name: '友链', path: '/friends' },
]

const themeOptions: { value: Theme; label: string; icon: string }[] = [
  { value: 'light', label: '浅色', icon: '☀️' },
  { value: 'dark', label: '深色', icon: '🌙' },
  { value: 'system', label: '跟随系统', icon: '💻' },
]
</script>

<template>
  <nav class="bg-white dark:bg-gray-800 shadow-md sticky top-0 z-50 border-b border-gray-200 dark:border-gray-700">
    <div class="container mx-auto px-4 py-4 max-w-6xl">
      <div class="flex items-center justify-between">
        <a href="/" class="text-2xl font-bold text-primary-600 dark:text-primary-400">
          我的博客
        </a>

        <div class="hidden md:flex items-center space-x-8">
          <a
            v-for="item in navItems"
            :key="item.name"
            :href="item.path"
            class="text-gray-700 dark:text-gray-300 hover:text-primary-600 dark:hover:text-primary-400 font-medium transition-colors"
          >
            {{ item.name }}
          </a>

          <div class="relative">
            <button
              @click="showThemeMenu = !showThemeMenu"
              class="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
            >
              <span v-if="themeStore.theme === 'light'" class="text-yellow-500 text-lg">☀️</span>
              <span v-else-if="themeStore.theme === 'dark'" class="text-blue-300 text-lg">🌙</span>
              <span v-else class="text-gray-500 dark:text-gray-400 text-lg">💻</span>
            </button>

            <div
              v-if="showThemeMenu"
              class="absolute right-0 mt-2 w-40 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-2 z-50"
            >
              <button
                v-for="option in themeOptions"
                :key="option.value"
                @click="themeStore.setTheme(option.value); showThemeMenu = false"
                class="w-full px-4 py-2 text-left flex items-center space-x-2 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                :class="themeStore.theme === option.value ? 'text-primary-600 dark:text-primary-400 font-medium' : 'text-gray-700 dark:text-gray-300'"
              >
                <span>{{ option.icon }}</span>
                <span>{{ option.label }}</span>
              </button>
            </div>
          </div>
        </div>

        <div class="md:hidden flex items-center space-x-4">
          <button
            @click="themeStore.toggleTheme"
            class="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
          >
            <span v-if="themeStore.isDark" class="text-yellow-500 text-lg">☀️</span>
            <span v-else class="text-blue-300 text-lg">🌙</span>
          </button>

          <button
            @click="showMobileMenu = !showMobileMenu"
            class="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
          >
            <svg v-if="!showMobileMenu" class="w-6 h-6 text-gray-700 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
            <svg v-else class="w-6 h-6 text-gray-700 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      <div v-if="showMobileMenu" class="md:hidden mt-4 pb-2 border-t border-gray-200 dark:border-gray-700 pt-4">
        <a
          v-for="item in navItems"
          :key="item.name"
          :href="item.path"
          class="block py-2 text-gray-700 dark:text-gray-300 hover:text-primary-600 dark:hover:text-primary-400 font-medium transition-colors"
          @click="showMobileMenu = false"
        >
          {{ item.name }}
        </a>

        <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <p class="text-sm text-gray-500 dark:text-gray-400 mb-2">主题设置</p>
          <div class="flex space-x-2">
            <button
              v-for="option in themeOptions"
              :key="option.value"
              @click="themeStore.setTheme(option.value)"
              class="px-3 py-1 rounded-lg text-sm transition-colors"
              :class="themeStore.theme === option.value
                ? 'bg-primary-100 dark:bg-primary-900/50 text-primary-600 dark:text-primary-400 font-medium'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'"
            >
              {{ option.icon }} {{ option.label }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </nav>
</template>

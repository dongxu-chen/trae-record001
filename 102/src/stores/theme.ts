import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export type Theme = 'light' | 'dark' | 'system'

export const useThemeStore = defineStore('theme', () => {
  const theme = ref<Theme>('system')
  const isDark = ref(false)

  const updateDarkMode = () => {
    if (theme.value === 'system') {
      isDark.value = window.matchMedia('(prefers-color-scheme: dark)').matches
    } else {
      isDark.value = theme.value === 'dark'
    }

    if (isDark.value) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }

  const setTheme = (newTheme: Theme) => {
    theme.value = newTheme
    localStorage.setItem('theme', newTheme)
  }

  const toggleTheme = () => {
    if (theme.value === 'system') {
      theme.value = isDark.value ? 'light' : 'dark'
    } else {
      theme.value = theme.value === 'light' ? 'dark' : 'light'
    }
  }

  const initTheme = () => {
    const savedTheme = localStorage.getItem('theme') as Theme | null
    if (savedTheme && ['light', 'dark', 'system'].includes(savedTheme)) {
      theme.value = savedTheme
    }

    updateDarkMode()

    window
      .matchMedia('(prefers-color-scheme: dark)')
      .addEventListener('change', updateDarkMode)
  }

  watch(theme, updateDarkMode)

  return {
    theme,
    isDark,
    setTheme,
    toggleTheme,
    initTheme,
  }
})

import { ref, watch, onMounted, onUnmounted } from 'vue'

export type Theme = 'light' | 'dark' | 'system'

const theme = ref<Theme>('system')
const isDark = ref(false)
const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

const updateDarkMode = () => {
  if (theme.value === 'system') {
    isDark.value = mediaQuery.matches
  } else {
    isDark.value = theme.value === 'dark'
  }
  
  if (isDark.value) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}

const handleSystemThemeChange = (e: MediaQueryListEvent) => {
  if (theme.value === 'system') {
    isDark.value = e.matches
    updateDarkMode()
  }
}

export function useTheme() {
  const toggleTheme = () => {
    if (theme.value === 'system') {
      theme.value = isDark.value ? 'light' : 'dark'
    } else {
      theme.value = theme.value === 'light' ? 'dark' : 'light'
    }
  }

  const setTheme = (newTheme: Theme) => {
    theme.value = newTheme
  }

  onMounted(() => {
    const savedTheme = localStorage.getItem('theme') as Theme | null
    if (savedTheme && ['light', 'dark', 'system'].includes(savedTheme)) {
      theme.value = savedTheme
    }
    
    updateDarkMode()
    mediaQuery.addEventListener('change', handleSystemThemeChange)
  })

  onUnmounted(() => {
    mediaQuery.removeEventListener('change', handleSystemThemeChange)
  })

  watch(theme, (newValue) => {
    localStorage.setItem('theme', newValue)
    updateDarkMode()
  }, { immediate: true })

  return {
    theme,
    isDark,
    toggleTheme,
    setTheme
  }
}

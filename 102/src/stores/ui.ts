import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useUIStore = defineStore('ui', () => {
  const sidebarOpen = ref(true)
  const mobileMenuOpen = ref(false)
  const isLoading = ref(false)

  const toggleSidebar = () => {
    sidebarOpen.value = !sidebarOpen.value
  }

  const toggleMobileMenu = () => {
    mobileMenuOpen.value = !mobileMenuOpen.value
  }

  const closeMobileMenu = () => {
    mobileMenuOpen.value = false
  }

  const setLoading = (value: boolean) => {
    isLoading.value = value
  }

  return {
    sidebarOpen,
    mobileMenuOpen,
    isLoading,
    toggleSidebar,
    toggleMobileMenu,
    closeMobileMenu,
    setLoading,
  }
})

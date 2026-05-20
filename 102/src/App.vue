<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import { useThemeStore } from './stores/theme'
import NavBar from './components/NavBar.vue'
import Footer from './components/Footer.vue'

const themeStore = useThemeStore()

onMounted(() => {
  themeStore.initTheme()
})
</script>

<template>
  <div class="min-h-screen flex flex-col bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100">
    <NavBar />
    <main class="flex-1 container mx-auto px-4 py-8 max-w-6xl">
      <RouterView />
    </main>
    <Footer />
  </div>
</template>

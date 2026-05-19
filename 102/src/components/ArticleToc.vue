<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { marked } from 'marked'

interface TocItem {
  id: string
  text: string
  level: number
  active: boolean
}

const props = defineProps<{
  content: string
}>()

const emit = defineEmits<{
  (e: 'scrollTo', id: string): void
}>()

const tocItems = ref<TocItem[]>([])
const isOpen = ref(false)
const activeId = ref('')

const extractToc = async (markdown: string) => {
  const html = marked(markdown) as string
  const tempDiv = document.createElement('div')
  tempDiv.innerHTML = html
  
  const headings = tempDiv.querySelectorAll('h2, h3')
  const items: TocItem[] = []
  
  headings.forEach((heading, index) => {
    const text = heading.textContent || ''
    const level = parseInt(heading.tagName.charAt(1))
    const id = `heading-${index}-${text.slice(0, 10).toLowerCase().replace(/\s+/g, '-')}`
    
    items.push({
      id,
      text,
      level,
      active: false
    })
  })
  
  tocItems.value = items
  await nextTick()
  
  items.forEach((item, index) => {
    const elements = document.querySelectorAll('h2, h3')
    if (elements[index]) {
      (elements[index] as HTMLElement).id = item.id
    }
  })
}

const scrollToHeading = (id: string) => {
  const element = document.getElementById(id)
  if (element) {
    const offset = 100
    const elementPosition = element.getBoundingClientRect().top
    const offsetPosition = elementPosition + window.pageYOffset - offset
    
    window.scrollTo({
      top: offsetPosition,
      behavior: 'smooth'
    })
    emit('scrollTo', id)
  }
  if (window.innerWidth < 1024) {
    isOpen.value = false
  }
}

const updateActiveHeading = () => {
  const headings = document.querySelectorAll('h2, h3')
  const scrollPosition = window.scrollY + 150
  
  for (let i = headings.length - 1; i >= 0; i--) {
    const heading = headings[i] as HTMLElement
    if (heading.offsetTop <= scrollPosition) {
      activeId.value = heading.id
      tocItems.value.forEach(item => {
        item.active = item.id === heading.id
      })
      break
    }
  }
}

watch(() => props.content, async (newContent) => {
  if (newContent) {
    await extractToc(newContent)
  }
}, { immediate: true })

onMounted(() => {
  window.addEventListener('scroll', updateActiveHeading, { passive: true })
})

onUnmounted(() => {
  window.removeEventListener('scroll', updateActiveHeading)
})

const hasToc = computed(() => tocItems.value.length > 0)
</script>

<template>
  <div v-if="hasToc" class="relative">
    <button
      @click="isOpen = !isOpen"
      class="lg:hidden fixed bottom-24 right-8 z-40 p-3 rounded-full bg-white dark:bg-gray-800 text-primary-500 shadow-lg hover:shadow-xl transition-all duration-300 border border-gray-200 dark:border-gray-700"
      title="目录"
    >
      <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h7" />
      </svg>
    </button>
    
    <div
      :class="[
        'fixed right-4 top-24 w-64 z-30 transform transition-transform duration-300',
        'lg:translate-x-0 lg:relative lg:right-auto lg:top-auto lg:w-full',
        isOpen ? 'translate-x-0' : 'translate-x-full lg:translate-x-0'
      ]"
    >
      <div class="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 p-4">
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-bold text-gray-900 dark:text-white flex items-center">
            <svg class="w-5 h-5 mr-2 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h7" />
            </svg>
            目录
          </h3>
          <button
            @click="isOpen = false"
            class="lg:hidden text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        <nav class="space-y-1 max-h-96 overflow-y-auto">
          <button
            v-for="item in tocItems"
            :key="item.id"
            @click="scrollToHeading(item.id)"
            class="w-full text-left px-3 py-2 rounded-lg transition-all duration-200 text-sm"
            :class="[
              item.active
                ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 font-medium'
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700',
              item.level === 3 ? 'pl-6' : ''
            ]"
          >
            <span class="flex items-center">
              <span v-if="item.level === 2" class="w-1.5 h-1.5 rounded-full bg-primary-500 mr-2" />
              <span v-if="item.level === 3" class="w-1 h-1 rounded-full bg-gray-400 mr-2" />
              {{ item.text }}
            </span>
          </button>
        </nav>
      </div>
    </div>
    
    <div
      v-if="isOpen"
      @click="isOpen = false"
      class="lg:hidden fixed inset-0 bg-black/20 z-20"
    />
  </div>
</template>

<template>
  <span>{{ safeText }}</span>
</template>

<script setup>
import { computed } from 'vue'
import { escapeHtml, sanitizeText } from '../utils/security.js'

const props = defineProps({
  text: {
    type: String,
    default: ''
  }
})

const safeText = computed(() => {
  return escapeHtml(sanitizeText(props.text || ''))
})
</script>

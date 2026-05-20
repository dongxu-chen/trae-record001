<template>
  <div class="app-container">
    <FormDesigner />
  </div>
</template>

<script setup>
import FormDesigner from './components/FormDesigner/index.vue'
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.app-container {
  width: 100%;
  height: 100%;
}
</style>

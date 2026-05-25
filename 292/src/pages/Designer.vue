<script setup lang="ts">
import ToolBar from '@/components/designer/ToolBar.vue'
import TabBar from '@/components/designer/TabBar.vue'
import ComponentPanel from '@/components/designer/ComponentPanel.vue'
import DesignCanvas from '@/components/designer/DesignCanvas.vue'
import PropertyPanel from '@/components/designer/PropertyPanel.vue'
</script>

<template>
  <div class="designer-page h-screen flex flex-col bg-slate-100">
    <ToolBar />
    <TabBar />
    <div class="flex-1 flex overflow-hidden">
      <div class="w-64 flex-shrink-0">
        <ComponentPanel />
      </div>
      <DesignCanvas />
      <div class="w-80 flex-shrink-0">
        <PropertyPanel />
      </div>
    </div>
  </div>
</template>

<style scoped>
.designer-page {
  height: 100vh;
  height: 100dvh;
}
</style>

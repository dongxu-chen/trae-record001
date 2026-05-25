<script setup lang="ts">
import { ref } from 'vue'
import { Plus, X, Edit3, Check } from 'lucide-vue-next'
import { useDesignerStore } from '@/stores/designer'

const store = useDesignerStore()
const editingTabId = ref<string | null>(null)
const editingName = ref('')

function startEdit(tabId: string, name: string) {
  editingTabId.value = tabId
  editingName.value = name
}

function saveEdit(tabId: string) {
  if (editingName.value.trim()) {
    store.updateTab(tabId, { name: editingName.value.trim() })
  }
  editingTabId.value = null
}

function cancelEdit() {
  editingTabId.value = null
}

function addNewTab() {
  const newIndex = store.formSchema.tabs.length + 1
  store.addTab(`页签 ${newIndex}`)
}

function deleteTab(e: Event, tabId: string) {
  e.stopPropagation()
  store.deleteTab(tabId)
}
</script>

<template>
  <div class="tab-bar flex items-center gap-1 px-4 py-2 bg-white border-b border-slate-200 overflow-x-auto">
    <div
      v-for="tab in store.formSchema.tabs"
      :key="tab.id"
      class="tab-item flex items-center gap-1.5 px-3 py-1.5 rounded-lg cursor-pointer transition-all whitespace-nowrap"
      :class="store.selectedTabId === tab.id 
        ? 'bg-primary-500 text-white shadow-sm' 
        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
      @click="store.selectTab(tab.id)"
    >
      <template v-if="editingTabId === tab.id">
        <input
          v-model="editingName"
          class="w-20 px-1 py-0.5 text-sm bg-white text-slate-800 rounded border-none outline-none"
          @click.stop
          @keyup.enter="saveEdit(tab.id)"
          @keyup.escape="cancelEdit"
          @blur="saveEdit(tab.id)"
        />
        <button
          class="p-0.5 hover:bg-white/20 rounded"
          @click.stop="saveEdit(tab.id)"
        >
          <Check :size="12" />
        </button>
      </template>
      <template v-else>
        <span class="text-sm font-medium">{{ tab.name }}</span>
        <button
          v-if="store.formSchema.tabs.length > 1"
          class="p-0.5 opacity-60 hover:opacity-100 hover:bg-white/20 rounded"
          @click.stop="startEdit(tab.id, tab.name)"
        >
          <Edit3 :size="12" />
        </button>
        <button
          v-if="store.formSchema.tabs.length > 1"
          class="p-0.5 opacity-60 hover:opacity-100 hover:bg-red-500 hover:text-white rounded"
          @click.stop="deleteTab($event, tab.id)"
        >
          <X :size="12" />
        </button>
      </template>
    </div>

    <button
      class="add-tab-btn flex items-center gap-1 px-2 py-1.5 text-slate-500 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
      @click="addNewTab"
    >
      <Plus :size="16" />
      <span class="text-sm">添加页签</span>
    </button>
  </div>
</template>

<style scoped>
.tab-bar::-webkit-scrollbar {
  height: 4px;
}
</style>

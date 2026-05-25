<template>
  <div class="template-market">
    <div class="market-header">
      <h4>粒子模板市场</h4>
      <div class="market-actions">
        <button @click="$emit('save-current')" class="action-btn">💾 保存当前</button>
        <label class="file-input-label">
          📂 导入
          <input type="file" accept=".json" @change="handleImport" style="display: none" />
        </label>
      </div>
    </div>

    <div class="market-toolbar">
      <div class="categories">
        <button
          v-for="cat in categories"
          :key="cat.id"
          :class="['category-btn', { active: currentCategory === cat.id }]"
          @click="setCategory(cat.id)"
        >
          {{ cat.icon }} {{ cat.name }}
        </button>
      </div>
      <div class="search-sort">
        <input
          type="text"
          v-model="searchQuery"
          placeholder="🔍 搜索模板..."
          class="search-input"
          @input="updateSearch"
        />
        <select v-model="sortBy" @change="updateSort" class="sort-select">
          <option value="popular">🔥 最热</option>
          <option value="latest">🆕 最新</option>
          <option value="likes">👍 最多赞</option>
        </select>
      </div>
    </div>

    <div class="templates-grid">
      <div
        v-for="template in filteredTemplates"
        :key="template.id"
        class="template-card"
      >
        <div class="card-header">
          <span class="template-icon">{{ template.icon }}</span>
          <span class="template-name">{{ template.name }}</span>
        </div>
        <div class="card-body">
          <p class="template-description">{{ template.description }}</p>
          <div class="template-meta">
            <span>👤 {{ template.author }}</span>
            <span v-if="template.downloads">📥 {{ formatNumber(template.downloads) }}</span>
            <span v-if="template.likes">👍 {{ formatNumber(template.likes) }}</span>
          </div>
        </div>
        <div class="card-footer">
          <button @click="$emit('apply-template', template)" class="apply-btn">
            ✨ 使用
          </button>
          <div class="card-actions">
            <button @click="downloadTemplate(template)" class="icon-btn" title="下载">
              📥
            </button>
            <button @click="likeTemplate(template)" class="icon-btn" title="点赞">
              👍
            </button>
            <button
              v-if="template.author === 'Me' || template.category === 'user'"
              @click="deleteTemplate(template)"
              class="icon-btn"
              title="删除"
            >
              🗑️
            </button>
          </div>
        </div>
      </div>

      <div v-if="filteredTemplates.length === 0" class="empty-state">
        <span class="empty-icon">📭</span>
        <p>暂无模板</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { TemplateMarket } from '../market/TemplateMarket.js'

const emit = defineEmits(['apply-template', 'save-current', 'import-template'])

const market = new TemplateMarket()
const categories = ref(market.getCategories())
const currentCategory = ref('all')
const searchQuery = ref('')
const sortBy = ref('popular')

const filteredTemplates = computed(() => {
  market.setCategory(currentCategory.value)
  market.setSearchQuery(searchQuery.value)
  market.setSortBy(sortBy.value)
  return market.getTemplates()
})

function setCategory(categoryId) {
  currentCategory.value = categoryId
}

function updateSearch() {
  market.setSearchQuery(searchQuery.value)
}

function updateSort(event) {
  sortBy.value = event.target.value
  market.setSortBy(sortBy.value)
}

function downloadTemplate(template) {
  market.downloadTemplate(template)
}

function likeTemplate(template) {
  market.likeTemplate(template)
}

function deleteTemplate(template) {
  if (confirm(`确定要删除 "${template.name}" 吗？`)) {
    market.deleteUserTemplate(template.id)
  }
}

async function handleImport(event) {
  const file = event.target.files[0]
  if (file) {
    try {
      const template = await market.importTemplateFromFile(file)
      market.userTemplates.unshift(template)
      market.saveUserTemplates()
    } catch (error) {
      alert(error.message)
    }
  }
  event.target.value = ''
}

function formatNumber(num) {
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k'
  }
  return num.toString()
}
</script>

<style scoped>
.template-market {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: rgba(15, 15, 25, 0.95);
}

.market-header {
  padding: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.market-header h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
}

.market-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  padding: 8px 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.action-btn:hover {
  background: rgba(102, 126, 234, 0.3);
  border-color: rgba(102, 126, 234, 0.5);
}

.file-input-label {
  padding: 8px 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.file-input-label:hover {
  background: rgba(102, 126, 234, 0.3);
  border-color: rgba(102, 126, 234, 0.5);
}

.market-toolbar {
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.categories {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.category-btn {
  padding: 6px 10px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.7);
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
  transition: all 0.2s;
}

.category-btn:hover {
  background: rgba(102, 126, 234, 0.2);
  color: #fff;
}

.category-btn.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: transparent;
  color: #fff;
}

.search-sort {
  display: flex;
  gap: 8px;
}

.search-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
  border-radius: 6px;
  font-size: 12px;
  outline: none;
  transition: border-color 0.2s;
}

.search-input:focus {
  border-color: #667eea;
}

.search-input::placeholder {
  color: rgba(255, 255, 255, 0.4);
}

.sort-select {
  padding: 8px 10px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
  border-radius: 6px;
  font-size: 12px;
  outline: none;
  cursor: pointer;
}

.templates-grid {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 12px;
  align-content: start;
}

.templates-grid::-webkit-scrollbar {
  width: 6px;
}

.templates-grid::-webkit-scrollbar-track {
  background: transparent;
}

.templates-grid::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
}

.template-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
}

.template-card:hover {
  border-color: rgba(102, 126, 234, 0.5);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
}

.card-header {
  padding: 12px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%);
  display: flex;
  align-items: center;
  gap: 8px;
}

.template-icon {
  font-size: 20px;
}

.template-name {
  font-size: 13px;
  font-weight: 600;
  color: #fff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-body {
  padding: 10px 12px;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.template-description {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
  margin: 0 0 8px 0;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.template-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.5);
}

.card-footer {
  padding: 8px 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.apply-btn {
  padding: 6px 12px;
  border: none;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
  transition: all 0.2s;
}

.apply-btn:hover {
  transform: scale(1.05);
}

.card-actions {
  display: flex;
  gap: 4px;
}

.icon-btn {
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 12px;
  border-radius: 4px;
  transition: background 0.2s;
}

.icon-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 40px 20px;
  color: rgba(255, 255, 255, 0.5);
}

.empty-icon {
  font-size: 40px;
  display: block;
  margin-bottom: 8px;
}

.empty-state p {
  margin: 0;
  font-size: 14px;
}
</style>

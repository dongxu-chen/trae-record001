<template>
  <div class="key-browser">
    <div class="toolbar">
      <div class="search-box">
        <input
          v-model="searchPattern"
          @keyup.enter="loadKeys"
          placeholder="搜索键 (支持 * 通配符)"
        />
        <button @click="loadKeys" class="btn-search">搜索</button>
      </div>
      <button @click="loadKeys" class="btn-refresh">刷新</button>
      <button @click="handleExport" class="btn-export">导出</button>
      <button @click="handleImport" class="btn-import">导入</button>
    </div>

    <div class="split-view">
      <div class="tree-panel">
        <div class="tree-header">
          <span>键列表</span>
          <span class="key-count">{{ keys.length }} 个键</span>
        </div>
        <div class="tree-container">
          <div v-if="loading" class="loading">加载中...</div>

          <div v-else-if="keys.length === 0" class="empty-keys">
            暂无键
          </div>

          <div v-else class="tree">
            <div
              v-for="(item, index) in treeData"
              :key="index"
              class="tree-node"
            >
              <div
                v-if="item.type === 'folder'"
                class="folder"
                @click="toggleFolder(item.path)"
              >
                <span class="toggle">{{ expandedFolders.has(item.path) ? '▼' : '▶' }}</span>
                <span class="icon">📁</span>
                <span class="name">{{ item.name }}</span>
                <span class="count">({{ item.count }})</span>
              </div>

              <div
                v-else
                class="key-item"
                :class="{ active: selectedKey === item.key }"
                @click="selectKey(item.key)"
              >
                <span class="icon">{{ getTypeIcon(item.type) }}</span>
                <span class="name" :title="item.key">{{ item.displayName }}</span>
                <span class="type-badge" :class="item.type">{{ item.type }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="value-panel">
        <div class="value-header" v-if="selectedKey">
          <div class="key-info">
            <span class="key-label">键:</span>
            <span class="key-name">{{ selectedKey }}</span>
            <span class="type-badge" :class="selectedKeyType">{{ selectedKeyType }}</span>
          </div>
          <button @click="deleteKey" class="btn-delete-key">删除</button>
        </div>

        <div class="value-content" v-if="selectedKey">
          <div v-if="loadingValue" class="loading">加载中...</div>

          <div v-else-if="selectedKeyType === 'string'" class="value-string">
            <textarea v-model="valueDisplay" readonly></textarea>
          </div>

          <div v-else-if="selectedKeyType === 'hash'" class="value-hash">
            <table>
              <thead>
                <tr>
                  <th>Field</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(val, field) in hashValue" :key="field">
                  <td>{{ field }}</td>
                  <td>{{ val }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-else-if="selectedKeyType === 'list'" class="value-list">
            <table>
              <thead>
                <tr>
                  <th>Index</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(val, idx) in listValue" :key="idx">
                  <td>{{ idx }}</td>
                  <td>{{ val }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-else-if="selectedKeyType === 'set'" class="value-set">
            <table>
              <thead>
                <tr>
                  <th>Member</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(val, idx) in setValue" :key="idx">
                  <td>{{ val }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-else-if="selectedKeyType === 'zset'" class="value-zset">
            <table>
              <thead>
                <tr>
                  <th>Member</th>
                  <th>Score</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, idx) in zsetPairs" :key="idx">
                  <td>{{ item.member }}</td>
                  <td>{{ item.score }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-else class="value-unknown">
            不支持的类型: {{ selectedKeyType }}
          </div>
        </div>

        <div v-else class="no-key-selected">
          请从左侧选择一个键查看详情
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted } from 'vue'
import { redisClient } from './RedisClient.js'
import { exportData, importDataFile, importData } from './import_export.js'

const props = defineProps({
  connectionId: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['error', 'dataChanged'])

const searchPattern = ref('*')
const keys = ref([])
const loading = ref(false)
const expandedFolders = ref(new Set())

const selectedKey = ref('')
const selectedKeyType = ref('')
const loadingValue = ref(false)
const valueDisplay = ref('')
const hashValue = ref({})
const listValue = ref([])
const setValue = ref([])
const zsetValue = ref([])

const keyTypesMap = ref(new Map())

const treeData = computed(() => {
  const result = []
  const folderMap = new Map()

  for (const key of keys.value) {
    const parts = key.split(':')
    if (parts.length > 1) {
      const folderPath = parts.slice(0, -1).join(':')
      if (!folderMap.has(folderPath)) {
        folderMap.set(folderPath, {
          type: 'folder',
          path: folderPath,
          name: parts.slice(0, -1).join(': '),
          keys: [],
          count: 0
        })
      }
      folderMap.get(folderPath).count++
      folderMap.get(folderPath).keys.push({
        fullKey: key,
        displayName: parts[parts.length - 1]
      })
    }
  }

  const topLevelKeys = keys.value.filter(k => !k.includes(':'))

  for (const key of topLevelKeys) {
    result.push({
      type: 'key',
      key,
      displayName: key,
      type: getTypeForDisplay(key)
    })
  }

  for (const [path, folder] of folderMap) {
    const isExpanded = expandedFolders.value.has(path)
    result.push({
      type: 'folder',
      path,
      name: folder.name,
      count: folder.count
    })

    if (isExpanded) {
      for (const item of folder.keys) {
        result.push({
          type: 'key',
          key: item.fullKey,
          displayName: item.displayName,
          type: getTypeForDisplay(item.fullKey)
        })
      }
    }
  }

  return result
})

const zsetPairs = computed(() => {
  const pairs = []
  for (let i = 0; i < zsetValue.value.length; i += 2) {
    pairs.push({
      member: zsetValue.value[i],
      score: zsetValue.value[i + 1]
    })
  }
  return pairs
})

function getTypeForDisplay(key) {
  return keyTypesMap.value.get(key) || 'unknown'
}

function getTypeIcon(type) {
  const icons = {
    string: '📝',
    hash: '📦',
    list: '📋',
    set: '🔢',
    zset: '📊',
    unknown: '❓'
  }
  return icons[type] || icons.unknown
}

function toggleFolder(path) {
  if (expandedFolders.value.has(path)) {
    expandedFolders.value.delete(path)
  } else {
    expandedFolders.value.add(path)
  }
}

async function fetchKeyTypesInBatches(keyList, batchSize = 50) {
  const results = new Map()

  for (let i = 0; i < keyList.length; i += batchSize) {
    const batch = keyList.slice(i, i + batchSize)
    const promises = batch.map(async (key) => {
      try {
        const type = await redisClient.type(props.connectionId, key)
        return { key, type }
      } catch {
        return { key, type: 'unknown' }
      }
    })

    const batchResults = await Promise.all(promises)
    for (const { key, type } of batchResults) {
      results.set(key, type)
    }

    await new Promise((resolve) => setTimeout(resolve, 0))
  }

  return results
}

async function loadKeys() {
  if (!props.connectionId) return

  loading.value = true
  try {
    const loadedKeys = await redisClient.keys(props.connectionId, searchPattern.value)
    loadedKeys.sort()
    keys.value = [...loadedKeys]
    keyTypesMap.value = new Map()

    const types = await fetchKeyTypesInBatches(keys.value)
    keyTypesMap.value = types

    if (selectedKey.value && !keys.value.includes(selectedKey.value)) {
      selectedKey.value = ''
    }
  } catch (error) {
    emit('error', error.message)
  } finally {
    loading.value = false
  }
}

async function selectKey(key) {
  if (selectedKey.value === key) return

  selectedKey.value = key
  selectedKeyType.value = keyTypesMap.value.get(key) || 'unknown'
  loadingValue.value = true

  try {
    if (selectedKeyType.value === 'string') {
      valueDisplay.value = await redisClient.get(props.connectionId, key)
    } else if (selectedKeyType.value === 'hash') {
      hashValue.value = await redisClient.hgetall(props.connectionId, key)
    } else if (selectedKeyType.value === 'list') {
      listValue.value = await redisClient.lrange(props.connectionId, key)
    } else if (selectedKeyType.value === 'set') {
      setValue.value = await redisClient.smembers(props.connectionId, key)
    } else if (selectedKeyType.value === 'zset') {
      zsetValue.value = await redisClient.zrange(props.connectionId, key)
    }
  } catch (error) {
    emit('error', error.message)
  } finally {
    loadingValue.value = false
  }
}

async function deleteKey() {
  if (!selectedKey.value) return

  const confirmed = confirm(`确定要删除键 "${selectedKey.value}" 吗?`)
  if (!confirmed) return

  try {
    await redisClient.del(props.connectionId, selectedKey.value)
    selectedKey.value = ''
    await loadKeys()
    emit('dataChanged')
  } catch (error) {
    emit('error', error.message)
  }
}

async function handleExport() {
  const pattern = searchPattern.value || '*'
  const result = await exportData(props.connectionId, pattern)
  if (result.success) {
    alert(`已导出 ${result.count} 个键`)
  } else {
    emit('error', result.error)
  }
}

async function handleImport() {
  const fileResult = await importDataFile()
  if (!fileResult.success) {
    if (fileResult.error !== 'No file selected') {
      emit('error', fileResult.error)
    }
    return
  }

  const importResult = await importData(props.connectionId, fileResult.data)
  if (importResult.success) {
    alert(`已导入 ${importResult.imported} 个键`)
    await loadKeys()
    emit('dataChanged')
  } else {
    emit('error', importResult.error)
  }
}

watch(() => props.connectionId, () => {
  selectedKey.value = ''
  keys.value = []
  keyTypesMap.value = new Map()
  expandedFolders.value.clear()
  loadKeys()
})

onMounted(() => {
  loadKeys()
})

defineExpose({ loadKeys })
</script>

<style scoped>
.key-browser {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: white;
}

.toolbar {
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid #e0e0e0;
  background: #fafafa;
}

.search-box {
  display: flex;
  gap: 8px;
}

.search-box input {
  width: 250px;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.search-box input:focus {
  outline: none;
  border-color: #3498db;
}

.btn-search,
.btn-refresh {
  padding: 8px 16px;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}

.btn-search:hover,
.btn-refresh:hover {
  background: #2980b9;
}

.btn-export,
.btn-import {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}

.btn-export {
  background: #27ae60;
  color: white;
}

.btn-export:hover {
  background: #219653;
}

.btn-import {
  background: #f39c12;
  color: white;
}

.btn-import:hover {
  background: #e67e22;
}

.split-view {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.tree-panel {
  width: 350px;
  border-right: 1px solid #e0e0e0;
  display: flex;
  flex-direction: column;
}

.tree-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #e0e0e0;
  background: #fafafa;
  font-size: 13px;
  font-weight: 500;
  color: #666;
}

.key-count {
  color: #999;
  font-weight: normal;
}

.tree-container {
  flex: 1;
  overflow-y: auto;
}

.loading {
  padding: 40px 20px;
  text-align: center;
  color: #999;
  font-size: 13px;
}

.empty-keys {
  padding: 40px 20px;
  text-align: center;
  color: #999;
  font-size: 13px;
}

.tree-node {
  padding: 0;
}

.folder {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  cursor: pointer;
  user-select: none;
}

.folder:hover {
  background: #f8f9fa;
}

.toggle {
  font-size: 10px;
  color: #999;
  width: 12px;
  text-align: center;
}

.icon {
  font-size: 14px;
}

.folder .name {
  flex: 1;
  font-size: 13px;
  color: #333;
}

.folder .count {
  font-size: 12px;
  color: #999;
}

.key-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px 8px 46px;
  cursor: pointer;
}

.key-item:hover {
  background: #f8f9fa;
}

.key-item.active {
  background: #e8f4fc;
}

.key-item .name {
  flex: 1;
  font-size: 13px;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.type-badge {
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 500;
}

.type-badge.string { background: #e8f5e9; color: #2e7d32; }
.type-badge.hash { background: #e3f2fd; color: #1565c0; }
.type-badge.list { background: #fff3e0; color: #ef6c00; }
.type-badge.set { background: #fce4ec; color: #c2185b; }
.type-badge.zset { background: #f3e5f5; color: #7b1fa2; }

.value-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.value-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #e0e0e0;
  background: #fafafa;
}

.key-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.key-label {
  font-size: 13px;
  color: #666;
}

.key-name {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.btn-delete-key {
  padding: 6px 12px;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.btn-delete-key:hover {
  background: #c0392b;
}

.value-content {
  flex: 1;
  overflow: auto;
  padding: 16px;
}

.value-string textarea {
  width: 100%;
  min-height: 300px;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  resize: vertical;
  background: #fafafa;
}

.value-hash table,
.value-list table,
.value-set table,
.value-zset table {
  width: 100%;
  border-collapse: collapse;
}

.value-hash th,
.value-list th,
.value-set th,
.value-zset th {
  background: #f5f5f5;
  padding: 10px 12px;
  text-align: left;
  font-size: 13px;
  font-weight: 500;
  color: #666;
  border-bottom: 1px solid #e0e0e0;
}

.value-hash td,
.value-list td,
.value-set td,
.value-zset td {
  padding: 10px 12px;
  font-size: 13px;
  border-bottom: 1px solid #f0f0f0;
  word-break: break-all;
}

.value-hash tr:hover td,
.value-list tr:hover td,
.value-set tr:hover td,
.value-zset tr:hover td {
  background: #fafafa;
}

.value-unknown {
  padding: 40px 20px;
  text-align: center;
  color: #999;
  font-size: 14px;
}

.no-key-selected {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
  font-size: 14px;
}
</style>

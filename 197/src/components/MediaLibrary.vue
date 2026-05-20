<template>
  <div class="media-library">
    <div class="panel-header">
      <span>📁 媒体库</span>
      <button class="btn-add" @click="triggerFileInput" :disabled="!store.isFFmpegLoaded">
        + 导入
      </button>
    </div>

    <div class="library-content">
      <div 
        class="drop-zone" 
        :class="{ 'drag-over': isDragOver }"
        @dragover.prevent="handleDragOver"
        @dragleave="handleDragLeave"
        @drop.prevent="handleDrop"
      >
        <input 
          ref="fileInput"
          type="file" 
          accept="video/*,audio/*" 
          multiple 
          hidden
          @change="handleFileSelect"
        />
        <div class="drop-icon">📂</div>
        <p class="drop-text">拖拽视频/音频文件到这里</p>
        <p class="drop-hint">或点击上方"导入"按钮</p>
      </div>

      <div class="media-list" v-if="store.mediaLibrary.length > 0">
        <div 
          v-for="item in store.mediaLibrary" 
          :key="item.id" 
          class="media-item"
          :class="{ selected: selectedId === item.id }"
          draggable="true"
          @dragstart="handleDragStart($event, item)"
          @click="selectItem(item)"
          @dblclick="addToTrack(item)"
        >
          <div class="media-thumbnail" v-if="item.type === 'video'">
            <img :src="item.thumbnail" :alt="item.name" v-if="item.thumbnail" />
            <div class="thumbnail-placeholder" v-else>
              <span>🎬</span>
            </div>
            <span class="media-duration">{{ formatTimeShort(item.duration) }}</span>
          </div>
          <div class="media-thumbnail audio-thumb" v-else>
            <span>🎵</span>
            <span class="media-duration">{{ formatTimeShort(item.duration) }}</span>
          </div>
          <div class="media-info">
            <p class="media-name" :title="item.name">{{ item.name }}</p>
            <p class="media-meta">
              <span v-if="item.type === 'video'">{{ item.width }}×{{ item.height }}</span>
              <span v-else>音频</span>
              · {{ formatFileSize(item.size) }}
            </p>
          </div>
          <div class="media-actions">
            <button class="action-btn" @click.stop="addToTrack(item)" title="添加到轨道">
              ➕
            </button>
            <button class="action-btn delete" @click.stop="removeItem(item.id)" title="删除">
              🗑️
            </button>
          </div>
        </div>
      </div>

      <div class="empty-state" v-else>
        <span>📭</span>
        <p>暂无媒体文件</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useEditorStore } from '../stores/editor'
import { formatTimeShort, formatFileSize } from '../utils/format'

const emit = defineEmits(['add-to-track'])

const store = useEditorStore()
const fileInput = ref(null)
const isDragOver = ref(false)
const selectedId = ref(null)

function triggerFileInput() {
  fileInput.value?.click()
}

async function handleFileSelect(e) {
  const files = Array.from(e.target.files || [])
  await processFiles(files)
  e.target.value = ''
}

function handleDragOver(e) {
  isDragOver.value = true
}

function handleDragLeave(e) {
  isDragOver.value = false
}

async function handleDrop(e) {
  isDragOver.value = false
  const files = Array.from(e.dataTransfer?.files || [])
  await processFiles(files)
}

async function processFiles(files) {
  const validFiles = files.filter(f => 
    f.type.startsWith('video/') || f.type.startsWith('audio/')
  )

  for (const file of validFiles) {
    try {
      await store.addMediaFile(file)
    } catch (error) {
      console.error('添加文件失败:', file.name, error)
    }
  }
}

function handleDragStart(e, item) {
  e.dataTransfer.setData('mediaItem', JSON.stringify(item))
  e.dataTransfer.effectAllowed = 'copy'
}

function selectItem(item) {
  selectedId.value = item.id
}

function addToTrack(item) {
  emit('add-to-track', item)
}

function removeItem(id) {
  if (confirm('确定要从媒体库中删除此文件吗？')) {
    store.removeFromMediaLibrary(id)
    if (selectedId.value === id) {
      selectedId.value = null
    }
  }
}
</script>

<style scoped>
.media-library {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.library-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.btn-add {
  padding: 6px 12px;
  background: var(--accent-primary);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-add:hover:not(:disabled) {
  background: #ff5a75;
  transform: translateY(-1px);
}

.btn-add:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.drop-zone {
  border: 2px dashed var(--border-color);
  border-radius: var(--radius);
  padding: 24px 16px;
  text-align: center;
  margin-bottom: 16px;
  transition: all 0.2s;
  background: var(--bg-tertiary);
}

.drop-zone.drag-over {
  border-color: var(--accent-primary);
  background: rgba(233, 69, 96, 0.1);
}

.drop-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.drop-text {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.drop-hint {
  font-size: 11px;
  color: var(--text-muted);
}

.media-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.media-item {
  display: flex;
  gap: 10px;
  padding: 8px;
  background: var(--bg-track);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  cursor: pointer;
  transition: all 0.2s;
}

.media-item:hover {
  border-color: var(--accent-secondary);
  transform: translateX(2px);
}

.media-item.selected {
  border-color: var(--accent-primary);
  background: rgba(233, 69, 96, 0.1);
}

.media-thumbnail {
  position: relative;
  width: 80px;
  height: 45px;
  border-radius: 4px;
  overflow: hidden;
  background: var(--bg-tertiary);
  flex-shrink: 0;
}

.media-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thumbnail-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.audio-thumb {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.media-duration {
  position: absolute;
  bottom: 2px;
  right: 2px;
  background: rgba(0, 0, 0, 0.8);
  padding: 1px 4px;
  border-radius: 2px;
  font-size: 10px;
}

.media-info {
  flex: 1;
  min-width: 0;
}

.media-name {
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 2px;
}

.media-meta {
  font-size: 10px;
  color: var(--text-muted);
}

.media-actions {
  display: flex;
  flex-direction: column;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.media-item:hover .media-actions {
  opacity: 1;
}

.action-btn {
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 4px;
  background: var(--bg-clip);
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.action-btn:hover {
  background: var(--accent-secondary);
}

.action-btn.delete:hover {
  background: var(--accent-primary);
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-muted);
}

.empty-state span {
  font-size: 40px;
  display: block;
  margin-bottom: 8px;
}

.empty-state p {
  font-size: 13px;
}
</style>

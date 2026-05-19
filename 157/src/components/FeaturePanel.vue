<template>
  <div class="feature-panel" :class="{ expanded: isExpanded }">
    <button class="toggle-btn" @click="isExpanded = !isExpanded">
      {{ isExpanded ? '收起功能' : '⚙️ 更多功能' }}
    </button>

    <div v-if="isExpanded" class="panel-content">
    <div class="feature-section">
      <h4>⚡ WebCodecs 解码状态</h4>
      <div class="decode-status">
        <div class="status-item">
          <span class="status-label">WebCodecs支持:</span>
          <span class="status-value" :class="{ success: decodeStats.webCodecs, error: !decodeStats.webCodecs }">
            {{ decodeStats.webCodecs ? '✓ 已启用' : '✗ 不支持' }}
          </span>
        </div>
        <div class="status-item">
          <span class="status-label">AVIF格式:</span>
          <span class="status-value" :class="{ success: decodeStats.avif, error: !decodeStats.avif }">
            {{ decodeStats.avif ? '✓ 支持' : '✗ 不支持' }}
          </span>
        </div>
        <div class="status-item">
          <span class="status-label">Worker线程:</span>
          <span class="status-value">{{ decodeStats.workers || 0 }} 个</span>
        </div>
        <div class="status-item">
          <span class="status-label">解码队列:</span>
          <span class="status-value">{{ decodeStats.pending || 0 }} 等待, {{ decodeStats.active || 0 }} 进行中</span>
        </div>
        <div class="status-item">
          <span class="status-label">总解码:</span>
          <span class="status-value">{{ decodeStats.totalDecoded || 0 }} 页 (平均 {{ Math.round(decodeStats.avgTime || 0) }}ms/页)</span>
        </div>
        <div class="status-item">
          <span class="status-label">硬件加速:</span>
          <span class="status-value" :class="{ success: decodeStats.hardwareAccelerated > 0, info: decodeStats.hardwareAccelerated === 0 }">
            {{ decodeStats.hardwareAccelerated || 0 }} 页
          </span>
        </div>
        <div class="status-item">
          <span class="status-label">缓存状态:</span>
          <span class="status-value">{{ decodeStats.cacheSize || 0 }} / {{ decodeStats.maxCacheSize || 20 }} 页</span>
        </div>
      </div>
    </div>

    <div class="feature-section">
      <h4>💬 弹幕设置</h4>
        <div class="danmaku-controls">
          <label class="toggle-label">
            <input type="checkbox" v-model="danmakuEnabled" @change="toggleDanmaku" />
            显示弹幕
          </label>
          <div class="danmaku-input">
            <input 
              type="text" 
              v-model="danmakuText" 
              placeholder="发送弹幕..." 
              @keyup.enter="sendDanmaku"
              maxlength="30"
            />
            <button @click="sendDanmaku" :disabled="!danmakuText.trim()">发送</button>
          </div>
          <div class="color-picker">
            <span>颜色:</span>
            <button 
              v-for="color in colors" 
              :key="color"
              class="color-btn"
              :style="{ background: color }"
              :class="{ active: selectedColor === color }"
              @click="selectedColor = color"
            ></button>
          </div>
        </div>
      </div>

      <div class="feature-section">
        <h4>✂️ 图片裁剪</h4>
        <div class="crop-controls">
          <label class="toggle-label">
            <input type="checkbox" v-model="autoCrop" @change="toggleCrop" />
            自动去白边
          </label>
          <div class="threshold-control">
            <span>灵敏度:</span>
            <input 
              type="range" 
              v-model.number="cropThreshold" 
              min="200" 
              max="250" 
              @change="updateCropThreshold"
            />
            <span class="threshold-value">{{ cropThreshold }}</span>
          </div>
        </div>
      </div>

      <div class="feature-section">
        <h4>📥 批量下载</h4>
        <div class="download-controls">
          <div class="page-range">
            <input 
              type="number" 
              v-model.number="downloadStart" 
              min="1" 
              :max="totalPages"
              placeholder="起始页"
            />
            <span>~</span>
            <input 
              type="number" 
              v-model.number="downloadEnd" 
              :min="downloadStart"
              :max="totalPages"
              placeholder="结束页"
            />
          </div>
          <label class="toggle-label">
            <input type="checkbox" v-model="downloadWithCrop" />
            下载时裁剪白边
          </label>
          <button 
            class="download-btn" 
            @click="startDownload"
            :disabled="isDownloading"
          >
            {{ isDownloading ? `下载中 ${downloadProgress}%` : '开始下载ZIP' }}
          </button>
          <div v-if="isDownloading" class="progress-bar">
            <div class="progress-fill" :style="{ width: downloadProgress + '%' }"></div>
          </div>
        </div>
      </div>

      <div class="feature-section">
        <h4>📊 阅读统计</h4>
        <div class="stats-display">
          <div class="stat-item">
            <span class="stat-value">{{ stats.totalPages }}</span>
            <span class="stat-label">总页数</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ stats.totalTime }}</span>
            <span class="stat-label">分钟</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ stats.daysRead }}</span>
            <span class="stat-label">阅读天数</span>
          </div>
          <div class="stat-item streak">
            <span class="stat-value">{{ stats.currentStreak }}</span>
            <span class="stat-label">连续签到</span>
          </div>
        </div>

        <div class="checkin-section">
          <button 
            class="checkin-btn" 
            :class="{ checked: stats.checkedInToday }"
            @click="doCheckIn"
            :disabled="stats.checkedInToday"
          >
            {{ stats.checkedInToday ? '今日已签到' : '📅 立即签到' }}
          </button>
          
          <div v-if="nextReward" class="next-reward">
            再读 {{ nextReward.daysLeft }} 天获得: {{ nextReward.reward }}
          </div>
        </div>

        <div class="weekly-calendar">
          <div 
            v-for="day in weeklyData" 
            :key="day.date"
            class="day-cell"
            :class="{ read: day.read, 'check-in': day.checkedIn }"
            :title="day.checkedIn ? '已签到' : day.read ? '已阅读' : '未阅读'"
          >
            <span class="weekday">{{ day.weekday }}</span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showToast" class="toast-message">
      {{ toastMessage }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { danmakuService } from '../services/danmakuService'
import { downloadService } from '../services/downloadService'
import { readingStatsService } from '../services/readingStats'
import { imageCropper } from '../utils/imageCrop'
import { usePreload } from '../composables/usePreload'

const props = defineProps({
  totalPages: Number,
  currentPage: Number,
  imageUrls: Array
})

const emit = defineEmits([
  'toggleDanmaku',
  'toggleCrop',
  'cropThresholdChange'
])

const isExpanded = ref(false)
const danmakuEnabled = ref(true)
const danmakuText = ref('')
const selectedColor = ref('#ffffff')
const colors = ['#ffffff', '#ff6b6b', '#4ecdc4', '#ffe66d', '#f38181', '#aa96da']

const autoCrop = ref(false)
const cropThreshold = ref(240)

const downloadStart = ref(1)
const downloadEnd = ref(1)
const downloadWithCrop = ref(false)
const isDownloading = ref(false)
const downloadProgress = ref(0)

const stats = ref({})
const weeklyData = ref([])
const nextReward = ref(null)

const showToast = ref(false)
const toastMessage = ref('')
const decodeStats = ref({})

let statsRefreshInterval = null

onMounted(async () => {
  danmakuService.init()
  await downloadService.init()
  stats.value = readingStatsService.init()
  weeklyData.value = readingStatsService.getWeeklyProgress()
  nextReward.value = readingStatsService.getNextReward()
  
  downloadEnd.value = props.totalPages
  
  refreshDecodeStats()
  statsRefreshInterval = setInterval(refreshDecodeStats, 1000)
})

onUnmounted(() => {
  if (statsRefreshInterval) {
    clearInterval(statsRefreshInterval)
  }
})

async function refreshDecodeStats() {
  const { getCacheStats } = usePreload()
  decodeStats.value = getCacheStats()
}

function toggleDanmaku() {
  emit('toggleDanmaku', danmakuEnabled.value)
}

function sendDanmaku() {
  if (!danmakuText.value.trim()) return
  
  danmakuService.sendDanmaku(danmakuText.value.trim(), props.currentPage, {
    color: selectedColor.value
  })
  
  showToastMessage('弹幕发送成功!')
  danmakuText.value = ''
}

function toggleCrop() {
  emit('toggleCrop', autoCrop.value)
}

function updateCropThreshold() {
  imageCropper.setThreshold(cropThreshold.value)
  emit('cropThresholdChange', cropThreshold.value)
}

async function startDownload() {
  if (isDownloading.value) return
  
  const start = Math.max(1, downloadStart.value)
  const end = Math.min(props.totalPages, downloadEnd.value)
  
  if (start > end) {
    showToastMessage('请选择有效的页码范围')
    return
  }

  const urlsToDownload = props.imageUrls.slice(start - 1, end)
  
  if (urlsToDownload.length === 0) {
    showToastMessage('没有可下载的图片')
    return
  }

  isDownloading.value = true
  downloadProgress.value = 0

  await downloadService.downloadBatch(urlsToDownload, {
    startPage: start,
    cropImages: downloadWithCrop.value,
    onProgress: (progress, current, total) => {
      downloadProgress.value = Math.round(progress)
    }
  })

  isDownloading.value = false
  showToastMessage('下载完成!')
}

function doCheckIn() {
  const result = readingStatsService.checkIn()
  
  if (result.success) {
    stats.value = readingStatsService.getStats()
    weeklyData.value = readingStatsService.getWeeklyProgress()
    nextReward.value = readingStatsService.getNextReward()
    showToastMessage(result.message)
  } else {
    showToastMessage(result.message)
  }
}

function showToastMessage(msg) {
  toastMessage.value = msg
  showToast.value = true
  setTimeout(() => {
    showToast.value = false
  }, 2000)
}
</script>

<style scoped>
.feature-panel {
  position: absolute;
  top: 20px;
  right: 20px;
  z-index: 80;
}

.toggle-btn {
  background: rgba(0, 0, 0, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: #fff;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.toggle-btn:hover {
  background: rgba(0, 0, 0, 0.85);
}

.panel-content {
  margin-top: 10px;
  background: rgba(0, 0, 0, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  padding: 20px;
  max-width: 350px;
  max-height: 70vh;
  overflow-y: auto;
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.feature-section {
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.feature-section:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.feature-section h4 {
  color: #fff;
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 500;
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #ccc;
  font-size: 13px;
  cursor: pointer;
  margin-bottom: 10px;
}

.danmaku-input {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}

.danmaku-input input {
  flex: 1;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #fff;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
}

.danmaku-input input:focus {
  outline: none;
  border-color: #007aff;
}

.danmaku-input button {
  background: #007aff;
  border: none;
  color: #fff;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}

.danmaku-input button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.color-picker {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #ccc;
  font-size: 13px;
}

.color-btn {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 2px solid transparent;
  cursor: pointer;
  transition: all 0.2s;
}

.color-btn.active {
  border-color: #fff;
  transform: scale(1.1);
}

.threshold-control {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #ccc;
  font-size: 13px;
}

.threshold-control input[type="range"] {
  flex: 1;
  cursor: pointer;
}

.threshold-value {
  min-width: 30px;
  text-align: center;
}

.page-range {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.page-range input {
  width: 70px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #fff;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 13px;
  text-align: center;
}

.page-range span {
  color: #888;
}

.download-btn {
  width: 100%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  color: #fff;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s;
}

.download-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.download-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.progress-bar {
  margin-top: 10px;
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2);
  border-radius: 3px;
  transition: width 0.3s;
}

.stats-display {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 15px;
}

.stat-item {
  text-align: center;
  padding: 10px 5px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
}

.stat-item.streak {
  background: rgba(255, 193, 7, 0.15);
}

.stat-value {
  display: block;
  font-size: 20px;
  font-weight: bold;
  color: #fff;
}

.stat-label {
  display: block;
  font-size: 11px;
  color: #888;
  margin-top: 4px;
}

.checkin-section {
  text-align: center;
  margin-bottom: 15px;
}

.checkin-btn {
  width: 100%;
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  border: none;
  color: #fff;
  padding: 12px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s;
}

.checkin-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(245, 87, 108, 0.4);
}

.checkin-btn:disabled,
.checkin-btn.checked {
  opacity: 0.6;
  cursor: not-allowed;
  background: #666;
}

.next-reward {
  margin-top: 10px;
  font-size: 12px;
  color: #ffd700;
}

.weekly-calendar {
  display: flex;
  justify-content: space-between;
  gap: 6px;
}

.day-cell {
  flex: 1;
  text-align: center;
  padding: 8px 4px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  font-size: 11px;
  color: #666;
  transition: all 0.3s;
}

.day-cell.read {
  background: rgba(102, 126, 234, 0.2);
  color: #667eea;
}

.day-cell.check-in {
  background: rgba(245, 87, 108, 0.3);
  color: #f5576c;
}

.weekday {
  display: block;
}

.toast-message {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(0, 0, 0, 0.9);
  color: #fff;
  padding: 15px 30px;
  border-radius: 8px;
  font-size: 14px;
  z-index: 200;
  animation: fadeIn 0.3s ease;
}

.decode-status {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  padding: 12px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.status-item:last-child {
  border-bottom: none;
}

.status-label {
  color: #aaa;
  font-size: 13px;
}

.status-value {
  font-size: 13px;
  font-weight: 500;
  color: #fff;
}

.status-value.success {
  color: #4ade80;
}

.status-value.error {
  color: #f87171;
}

.status-value.info {
  color: #60a5fa;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>

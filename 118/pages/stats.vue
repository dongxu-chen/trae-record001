<template>
  <div class="stats-page">
    <header class="stats-header">
      <button class="back-btn" @click="navigateTo('/')">← 返回</button>
      <h1>📊 阅读统计</h1>
    </header>

    <div class="stats-content">
      <div class="stats-overview">
        <div class="stat-card">
          <div class="stat-icon">⏱️</div>
          <div class="stat-info">
            <h3>总阅读时长</h3>
            <p class="stat-value">{{ formatTime(totalStats?.totalReadTime || 0) }}</p>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-icon">📚</div>
          <div class="stat-info">
            <h3>已读书籍</h3>
            <p class="stat-value">{{ totalStats?.booksCompleted || 0 }} / {{ totalStats?.totalBooks || 0 }}</p>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-icon">📖</div>
          <div class="stat-info">
            <h3>我的书库</h3>
            <p class="stat-value">{{ totalStats?.totalBooks || 0 }} 本</p>
          </div>
        </div>
      </div>

      <div class="chart-section">
        <h2>📈 最近30天阅读趋势</h2>
        <div class="chart-container">
          <div v-for="stat in dailyStats" :key="stat.date" class="chart-bar-wrapper">
            <div 
              class="chart-bar" 
              :style="{ height: getBarHeight(stat.totalReadTime) }"
            ></div>
            <span class="chart-label">{{ formatDate(stat.date) }}</span>
          </div>
        </div>
      </div>

      <div class="books-section">
        <h2>📕 阅读时长排行</h2>
        <div class="books-list">
          <div v-for="book in books" :key="book.id" class="book-stat-item">
            <div class="book-icon">📚</div>
            <div class="book-info">
              <h4>{{ book.title }}</h4>
              <p class="book-time">{{ formatTime(book.totalReadTime) }}</p>
              <span v-if="book.isCompleted" class="completed-badge">✓ 已读完</span>
            </div>
            <button class="read-btn" @click="navigateTo(`/reader/${book.id}`)">
              继续阅读
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const { data: statsData } = await useFetch('/api/reading/stats')

const dailyStats = computed(() => statsData.value?.daily || [])
const books = computed(() => statsData.value?.books || [])
const totalStats = computed(() => statsData.value?.total || {})

const formatTime = (seconds: number): string => {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  
  if (hours > 0) {
    return `${hours}小时 ${minutes}分钟`
  }
  return `${minutes}分钟`
}

const formatDate = (date: string): string => {
  const d = new Date(date)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

const maxDailyTime = computed(() => {
  return Math.max(...dailyStats.value.map(s => s.totalReadTime), 1)
})

const getBarHeight = (time: number): string => {
  const percentage = (time / maxDailyTime.value) * 100
  return `${Math.max(percentage, 2)}%`
}
</script>

<style scoped>
.stats-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding-bottom: 40px;
}

.stats-header {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 20px;
  color: white;
}

.back-btn {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 16px;
}

.stats-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.stats-overview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
  margin-bottom: 40px;
}

.stat-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 20px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.stat-icon {
  font-size: 48px;
}

.stat-info h3 {
  font-size: 16px;
  color: #666;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #333;
  margin: 0;
}

.chart-section,
.books-section {
  background: white;
  border-radius: 16px;
  padding: 30px;
  margin-bottom: 30px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.chart-section h2,
.books-section h2 {
  margin-bottom: 24px;
  color: #333;
  font-size: 20px;
}

.chart-container {
  display: flex;
  align-items: end;
  justify-content: space-between;
  height: 200px;
  gap: 8px;
  padding: 0 10px;
}

.chart-bar-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
}

.chart-bar {
  width: 100%;
  background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
  border-radius: 4px 4px 0 0;
  min-height: 4px;
  transition: height 0.3s ease;
}

.chart-label {
  font-size: 12px;
  color: #999;
  margin-top: 8px;
}

.books-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.book-stat-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 12px;
}

.book-icon {
  font-size: 36px;
}

.book-info {
  flex: 1;
}

.book-info h4 {
  font-size: 16px;
  color: #333;
  margin-bottom: 4px;
}

.book-time {
  font-size: 14px;
  color: #667eea;
  font-weight: 600;
  margin: 0;
}

.completed-badge {
  font-size: 12px;
  color: #27ae60;
  background: #d4edda;
  padding: 2px 8px;
  border-radius: 4px;
}

.read-btn {
  background: #667eea;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}
</style>

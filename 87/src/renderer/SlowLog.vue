<template>
  <div class="slowlog">
    <div class="slowlog-header">
      <div class="header-left">
        <h3>慢查询日志</h3>
        <span class="log-count" v-if="logLength !== null">共 {{ logLength }} 条记录</span>
      </div>
      <div class="header-right">
        <select v-model="limit" class="limit-select">
          <option :value="50">显示 50 条</option>
          <option :value="100">显示 100 条</option>
          <option :value="256">显示 256 条</option>
          <option :value="500">显示 500 条</option>
        </select>
        <button @click="loadLogs" class="btn-refresh">刷新</button>
        <button @click="resetLogs" class="btn-reset">清空日志</button>
      </div>
    </div>

    <div class="slowlog-stats" v-if="logs.length > 0">
      <div class="stat-item">
        <span class="stat-label">最快</span>
        <span class="stat-value">{{ formatDuration(minDuration) }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">平均</span>
        <span class="stat-value">{{ formatDuration(avgDuration) }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">最慢</span>
        <span class="stat-value danger">{{ formatDuration(maxDuration) }}</span>
      </div>
    </div>

    <div class="slowlog-table-wrap">
      <div v-if="loading" class="loading">加载中...</div>

      <div v-else-if="logs.length === 0" class="empty-logs">
        暂无慢查询日志
      </div>

      <table v-else class="slowlog-table">
        <thead>
          <tr>
            <th class="col-id">ID</th>
            <th class="col-time">执行时间</th>
            <th class="col-duration">耗时</th>
            <th class="col-cmd">命令</th>
            <th class="col-client">客户端</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="log in logs"
            :key="log.id"
            class="log-row"
            :class="{ slow: log.durationUs > 10000 }"
          >
            <td class="col-id">{{ log.id }}</td>
            <td class="col-time">{{ formatTime(log.timestamp) }}</td>
            <td class="col-duration">
              <span :class="getDurationClass(log.durationUs)">
                {{ formatDuration(log.durationUs) }}
              </span>
            </td>
            <td class="col-cmd">
              <code>{{ log.command }}</code>
            </td>
            <td class="col-client">
              <div v-if="log.clientName">{{ log.clientName }}</div>
              <div v-if="log.client" class="client-ip">{{ log.client }}</div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { redisClient } from './RedisClient.js'

const props = defineProps({
  connectionId: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['error'])

const logs = ref([])
const logLength = ref(null)
const limit = ref(100)
const loading = ref(false)

const minDuration = computed(() => {
  if (logs.value.length === 0) return 0
  return Math.min(...logs.value.map(l => l.durationUs))
})

const maxDuration = computed(() => {
  if (logs.value.length === 0) return 0
  return Math.max(...logs.value.map(l => l.durationUs))
})

const avgDuration = computed(() => {
  if (logs.value.length === 0) return 0
  const sum = logs.value.reduce((acc, l) => acc + l.durationUs, 0)
  return Math.round(sum / logs.value.length)
})

function formatDuration(us) {
  if (us === 0) return '-'
  if (us < 1000) return `${us}µs`
  if (us < 1000000) return `${(us / 1000).toFixed(2)}ms`
  return `${(us / 1000000).toFixed(2)}s`
}

function formatTime(ts) {
  const d = new Date(ts * 1000)
  const pad = (n) => n.toString().padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function getDurationClass(us) {
  if (us > 100000) return 'danger'
  if (us > 10000) return 'warning'
  return 'normal'
}

async function loadLogs() {
  if (!props.connectionId) return

  loading.value = true
  try {
    logs.value = await redisClient.slowlog(props.connectionId, limit.value)
    try {
      logLength.value = await redisClient.slowlogLen(props.connectionId)
    } catch {
      logLength.value = logs.value.length
    }
  } catch (error) {
    emit('error', error.message)
  } finally {
    loading.value = false
  }
}

async function resetLogs() {
  if (!confirm('确定要清空所有慢查询日志吗?')) return

  try {
    await redisClient.slowlogReset(props.connectionId)
    logs.value = []
    logLength.value = 0
  } catch (error) {
    emit('error', error.message)
  }
}

watch(() => props.connectionId, () => {
  logs.value = []
  logLength.value = null
  loadLogs()
})

watch(limit, () => {
  loadLogs()
})

onMounted(() => {
  loadLogs()
})
</script>

<style scoped>
.slowlog {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: white;
}

.slowlog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #e0e0e0;
  background: #fafafa;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-left h3 {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.log-count {
  font-size: 12px;
  color: #999;
}

.header-right {
  display: flex;
  gap: 8px;
  align-items: center;
}

.limit-select {
  padding: 6px 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 12px;
  background: white;
}

.btn-refresh,
.btn-reset {
  padding: 6px 14px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  border: none;
}

.btn-refresh {
  background: #3498db;
  color: white;
}

.btn-refresh:hover {
  background: #2980b9;
}

.btn-reset {
  background: #e74c3c;
  color: white;
}

.btn-reset:hover {
  background: #c0392b;
}

.slowlog-stats {
  display: flex;
  gap: 24px;
  padding: 12px 16px;
  border-bottom: 1px solid #e0e0e0;
  background: #fff;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-label {
  font-size: 11px;
  color: #999;
}

.stat-value {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.stat-value.danger {
  color: #e74c3c;
}

.slowlog-table-wrap {
  flex: 1;
  overflow: auto;
}

.loading,
.empty-logs {
  padding: 40px 20px;
  text-align: center;
  color: #999;
  font-size: 13px;
}

.slowlog-table {
  width: 100%;
  border-collapse: collapse;
}

.slowlog-table th {
  background: #f5f5f5;
  padding: 10px 12px;
  text-align: left;
  font-size: 12px;
  font-weight: 500;
  color: #666;
  border-bottom: 1px solid #e0e0e0;
  position: sticky;
  top: 0;
}

.slowlog-table td {
  padding: 10px 12px;
  font-size: 13px;
  border-bottom: 1px solid #f0f0f0;
  vertical-align: top;
}

.log-row:hover td {
  background: #fafafa;
}

.log-row.slow td {
  background: #fef5f5;
}

.col-id {
  width: 60px;
  color: #999;
}

.col-time {
  width: 150px;
  color: #666;
}

.col-duration {
  width: 100px;
}

.col-duration .normal {
  color: #27ae60;
}

.col-duration .warning {
  color: #f39c12;
}

.col-duration .danger {
  color: #e74c3c;
  font-weight: 600;
}

.col-cmd {
  max-width: 400px;
}

.col-cmd code {
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 12px;
  word-break: break-all;
}

.col-client {
  width: 160px;
  color: #666;
}

.client-ip {
  font-size: 11px;
  color: #999;
}
</style>

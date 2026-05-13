<template>
  <div class="app-container">
    <header class="header">
      <h1>Redis Client</h1>
    </header>

    <div class="main-content">
      <aside class="sidebar">
        <div class="connections-header">
          <h2>连接</h2>
          <button @click="showAddDialog = true" class="btn-add">+ 新建连接</button>
        </div>

        <div class="connections-list">
          <div
            v-for="conn in connections"
            :key="conn.id"
            class="connection-item"
            :class="{ active: currentConnection?.id === conn.id }"
            @click="selectConnection(conn)"
          >
            <span class="conn-name">{{ conn.name }}</span>
            <button @click.stop="removeConnection(conn.id)" class="btn-delete">×</button>
          </div>

          <div v-if="connections.length === 0" class="empty-state">
            暂无连接
          </div>
        </div>
      </aside>

      <main class="content">
        <KeyBrowser
          v-if="currentConnection"
          :connection-id="currentConnection.id"
          @error="handleError"
        />
        <div v-else class="no-connection">
          <p>请从左侧选择或创建一个 Redis 连接</p>
        </div>
      </main>
    </div>

    <div v-if="showAddDialog" class="dialog-overlay" @click.self="showAddDialog = false">
      <div class="dialog">
        <h3>新建 Redis 连接</h3>

        <div class="form-group">
          <label>连接名称</label>
          <input v-model="newConnection.name" placeholder="My Redis" />
        </div>

        <div class="form-group">
          <label>Host</label>
          <input v-model="newConnection.host" placeholder="127.0.0.1" />
        </div>

        <div class="form-group">
          <label>Port</label>
          <input v-model.number="newConnection.port" type="number" placeholder="6379" />
        </div>

        <div class="form-group">
          <label>密码 (可选)</label>
          <input v-model="newConnection.password" type="password" placeholder="password" />
        </div>

        <div class="form-group">
          <label>数据库</label>
          <input v-model.number="newConnection.db" type="number" placeholder="0" />
        </div>

        <div class="form-actions">
          <button @click="showAddDialog = false" class="btn-cancel">取消</button>
          <button @click="addConnection" class="btn-confirm" :disabled="isConnecting">
            {{ isConnecting ? '连接中...' : '连接' }}
          </button>
        </div>

        <div v-if="errorMessage" class="error-msg">{{ errorMessage }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import KeyBrowser from './renderer/KeyBrowser.vue'
import { redisClient } from './renderer/RedisClient.js'

const showAddDialog = ref(false)
const isConnecting = ref(false)
const errorMessage = ref('')
const connections = ref([])
const currentConnection = ref(null)

const newConnection = ref({
  name: '',
  host: '127.0.0.1',
  port: 6379,
  password: '',
  db: 0
})

const addConnection = async () => {
  isConnecting.value = true
  errorMessage.value = ''

  try {
    const config = { ...newConnection.value }
    const id = await redisClient.connect(config)
    connections.value = redisClient.getConnections()
    currentConnection.value = connections.value.find(c => c.id === id)
    showAddDialog.value = false
    resetForm()
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isConnecting.value = false
  }
}

const removeConnection = async (id) => {
  try {
    await redisClient.disconnect(id)
    connections.value = redisClient.getConnections()
    if (currentConnection.value?.id === id) {
      currentConnection.value = null
    }
  } catch (error) {
    handleError(error.message)
  }
}

const selectConnection = (conn) => {
  currentConnection.value = conn
}

const handleError = (msg) => {
  errorMessage.value = msg
  setTimeout(() => {
    errorMessage.value = ''
  }, 5000)
}

const resetForm = () => {
  newConnection.value = {
    name: '',
    host: '127.0.0.1',
    port: 6379,
    password: '',
    db: 0
  }
  errorMessage.value = ''
}

onMounted(() => {
  connections.value = redisClient.getConnections()
})
</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
}

.header {
  background: #2c3e50;
  color: white;
  padding: 12px 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.header h1 {
  font-size: 18px;
  font-weight: 500;
}

.main-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.sidebar {
  width: 280px;
  background: white;
  border-right: 1px solid #e0e0e0;
  display: flex;
  flex-direction: column;
}

.connections-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #e0e0e0;
}

.connections-header h2 {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.btn-add {
  background: #3498db;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.btn-add:hover {
  background: #2980b9;
}

.connections-list {
  flex: 1;
  overflow-y: auto;
}

.connection-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
}

.connection-item:hover {
  background: #f8f9fa;
}

.connection-item.active {
  background: #e8f4fc;
  border-left: 3px solid #3498db;
}

.conn-name {
  font-size: 14px;
  color: #333;
}

.btn-delete {
  background: transparent;
  border: none;
  color: #999;
  cursor: pointer;
  font-size: 16px;
  padding: 2px 6px;
}

.btn-delete:hover {
  color: #e74c3c;
}

.empty-state {
  padding: 40px 20px;
  text-align: center;
  color: #999;
  font-size: 13px;
}

.content {
  flex: 1;
  overflow: hidden;
  background: #fafafa;
}

.no-connection {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #999;
  font-size: 14px;
}

.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog {
  background: white;
  border-radius: 8px;
  padding: 24px;
  width: 400px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.dialog h3 {
  margin-bottom: 20px;
  font-size: 16px;
  color: #333;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  color: #666;
}

.form-group input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.form-group input:focus {
  outline: none;
  border-color: #3498db;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
}

.btn-cancel {
  padding: 8px 16px;
  border: 1px solid #ddd;
  background: white;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.btn-confirm {
  padding: 8px 16px;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.btn-confirm:hover:not(:disabled) {
  background: #2980b9;
}

.btn-confirm:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
}

.error-msg {
  margin-top: 12px;
  padding: 10px;
  background: #fdecea;
  color: #e74c3c;
  border-radius: 4px;
  font-size: 13px;
}
</style>

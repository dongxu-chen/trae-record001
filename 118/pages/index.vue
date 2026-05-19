<template>
  <div class="container">
    <div v-if="isInstallPromptAvailable" class="install-banner">
      <span>📱 安装到桌面，获得更好的阅读体验</span>
      <button @click="handleInstall" class="install-btn">立即安装</button>
    </div>

    <header class="header">
      <div class="header-left">
        <h1>电子书阅读器</h1>
        <span class="online-status" :class="{ offline: !isOnline }">
          {{ isOnline ? '🟢 在线' : '🔴 离线' }}
        </span>
      </div>
      <div class="header-buttons">
        <button @click="navigateTo('/stats')" class="stats-btn">📊 阅读统计</button>
        <label class="upload-btn">
          <span>上传 EPUB</span>
          <input type="file" accept=".epub" @change="handleUpload" hidden>
        </label>
      </div>
    </header>

    <div v-if="isDownloading" class="download-progress">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: downloadProgress + '%' }"></div>
      </div>
      <span>正在下载: {{ currentDownload }} ({{ downloadProgress }}%)</span>
    </div>

    <div class="books-grid" v-if="books.length > 0">
      <div 
        v-for="book in books" 
        :key="book.id" 
        class="book-card" 
        @click="handleBookClick(book)"
      >
        <div class="book-cover">
          <span class="book-icon">
            {{ isBookEncrypted(book) ? '🔒' : (isBookOffline(book) ? '📚' : '🌐') }}
          </span>
          <button 
            v-if="!isBookOffline(book) && isOnline" 
            class="download-btn"
            @click.stop="downloadBookForOffline(book)"
          >
            ⬇️ 离线
          </button>
        </div>
        <div class="book-info">
          <h3>{{ book.title }}</h3>
          <p v-if="book.author">{{ book.author }}</p>
          <div class="book-meta">
            <span v-if="isBookEncrypted(book)" class="encrypted-badge">已加密</span>
            <span v-if="isBookOffline(book)" class="offline-badge">已离线</span>
            <span v-if="book.totalReadTime > 0" class="time-badge">
              ⏱️ {{ formatReadTime(book.totalReadTime) }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showPasswordModal" class="password-modal" @click.self="showPasswordModal = false">
      <div class="password-content">
        <h3>此电子书已加密</h3>
        <p>请输入密码以继续阅读</p>
        <input 
          type="password" 
          v-model="passwordInput" 
          @keyup.enter="decryptBook"
          placeholder="请输入密码"
          class="password-input"
        >
        <div class="password-actions">
          <button @click="showPasswordModal = false" class="cancel-btn">取消</button>
          <button @click="decryptBook" class="confirm-btn">解密</button>
        </div>
        <p v-if="decryptError" class="error-message">{{ decryptError }}</p>
      </div>
    </div>

    <div v-else class="empty-state">
      <span class="empty-icon">📖</span>
      <p>还没有电子书，上传一本开始阅读吧！</p>
      <p v-if="!isOnline" class="offline-hint">离线模式下仅能查看已下载的书籍</p>
    </div>
  </div>
</template>

<script setup lang="ts">
const { data: books, refresh } = await useFetch('/api/books')
const { isOnline, installPWA, isInstallPromptAvailable, downloadBook, isDownloading, downloadProgress, currentDownload } = usePWA()

const showPasswordModal = ref(false)
const passwordInput = ref('')
const decryptError = ref('')
const selectedBookId = ref<number | null>(null)

const offlineBooks = ref<any[]>([])

const loadOfflineBooks = async () => {
  const { db } = useIndexedDB()
  offlineBooks.value = await db.getAllBooks()
}

const isBookOffline = (book: any): boolean => {
  return offlineBooks.value.some((b: any) => b.id === book.id && b.downloadedAt)
}

const isBookEncrypted = (book: any) => {
  if (!book.description) return false
  try {
    const desc = JSON.parse(book.description)
    return desc.encrypted === true
  } catch {
    return false
  }
}

const handleBookClick = (book: any) => {
  if (isBookEncrypted(book)) {
    selectedBookId.value = book.id
    passwordInput.value = ''
    decryptError.value = ''
    showPasswordModal.value = true
  } else {
    navigateTo(`/reader/${book.id}`)
  }
}

const decryptBook = async () => {
  if (!selectedBookId.value || !passwordInput.value) return

  try {
    await $fetch('/api/decrypt', {
      method: 'POST',
      body: {
        bookId: selectedBookId.value,
        password: passwordInput.value
      }
    })
    showPasswordModal.value = false
    await refresh()
    navigateTo(`/reader/${selectedBookId.value}`)
  } catch (e: any) {
    decryptError.value = e.data?.message || '解密失败'
  }
}

const handleUpload = async (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return

  const formData = new FormData()
  formData.append('file', file)

  const result: any = await $fetch('/api/upload', {
    method: 'POST',
    body: formData
  })

  await refresh()

  if (result.encryption?.isEncrypted) {
    selectedBookId.value = result.book.id
    showPasswordModal.value = true
  }
}

const downloadBookForOffline = async (book: any) => {
  const bookUrl = `/api/books/file/${book.filePath}`
  const success = await downloadBook(book.id, bookUrl, book.filePath)

  if (success) {
    const { db } = useIndexedDB()
    await db.addBook({
      id: book.id,
      title: book.title,
      author: book.author,
      description: book.description,
      filePath: book.filePath,
      fileSize: 0,
      isCompleted: false,
      totalReadTime: 0,
      downloadedAt: Date.now(),
      syncStatus: 'synced',
      createdAt: Date.now(),
      updatedAt: Date.now()
    })
    await loadOfflineBooks()
  }
}

const handleInstall = async () => {
  const success = await installPWA()
  if (success) {
    console.log('PWA installed successfully')
  }
}

const formatReadTime = (seconds: number): string => {
  const hours = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  if (hours > 0) return `${hours}小时${mins}分`
  return `${mins}分钟`
}

onMounted(() => {
  loadOfflineBooks()
})
</script>

<style scoped>
.container {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.install-banner {
  max-width: 1200px;
  margin: 0 auto 20px;
  background: rgba(255, 255, 255, 0.95);
  padding: 15px 20px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.install-btn {
  background: #667eea;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
}

.header {
  max-width: 1200px;
  margin: 0 auto 30px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: white;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.online-status {
  font-size: 14px;
  padding: 4px 12px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 20px;
}

.online-status.offline {
  background: rgba(255, 100, 100, 0.3);
}

.header-buttons {
  display: flex;
  gap: 10px;
  align-items: center;
}

.stats-btn {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: none;
  padding: 12px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: background 0.2s;
}

.stats-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.upload-btn {
  background: white;
  color: #667eea;
  padding: 12px 24px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: transform 0.2s;
}

.upload-btn:hover {
  transform: scale(1.05);
}

.download-progress {
  max-width: 1200px;
  margin: 0 auto 20px;
  background: rgba(255, 255, 255, 0.95);
  padding: 15px 20px;
  border-radius: 12px;
}

.download-progress .progress-bar {
  height: 8px;
  background: #e0e0e0;
  border-radius: 4px;
  margin-bottom: 8px;
  overflow: hidden;
}

.download-progress .progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2);
  transition: width 0.3s;
}

.download-progress span {
  font-size: 14px;
  color: #333;
}

.books-grid {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 20px;
}

.book-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  position: relative;
}

.book-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
}

.book-cover {
  height: 150px;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 15px;
  position: relative;
}

.book-icon {
  font-size: 48px;
}

.download-btn {
  position: absolute;
  bottom: 10px;
  right: 10px;
  background: rgba(102, 126, 234, 0.9);
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.2s;
}

.download-btn:hover {
  background: #667eea;
}

.book-info h3 {
  font-size: 16px;
  color: #333;
  margin-bottom: 5px;
}

.book-info p {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.book-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.encrypted-badge,
.offline-badge,
.time-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  display: inline-block;
}

.encrypted-badge {
  color: #e74c3c;
  background: #fee;
}

.offline-badge {
  color: #27ae60;
  background: #e8f8f5;
}

.time-badge {
  color: #667eea;
  background: #f0f3ff;
}

.empty-state {
  text-align: center;
  padding: 100px 20px;
  color: white;
}

.empty-icon {
  font-size: 80px;
  display: block;
  margin-bottom: 20px;
}

.offline-hint {
  font-size: 14px;
  opacity: 0.8;
  margin-top: 10px;
}

.password-modal {
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

.password-content {
  background: white;
  padding: 30px;
  border-radius: 12px;
  width: 90%;
  max-width: 400px;
}

.password-content h3 {
  margin-bottom: 10px;
  color: #333;
}

.password-content p {
  color: #666;
  margin-bottom: 20px;
}

.password-input {
  width: 100%;
  padding: 12px;
  border: 2px solid #ddd;
  border-radius: 8px;
  font-size: 16px;
  margin-bottom: 20px;
  box-sizing: border-box;
}

.password-input:focus {
  outline: none;
  border-color: #667eea;
}

.password-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.cancel-btn, .confirm-btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.cancel-btn {
  background: #eee;
  color: #666;
}

.confirm-btn {
  background: #667eea;
  color: white;
}

.error-message {
  color: #e74c3c;
  font-size: 14px;
  margin-top: 10px;
  margin-bottom: 0;
}
</style>

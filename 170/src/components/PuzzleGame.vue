<template>
  <div class="puzzle-game">
    <div class="header">
      <h1 class="title">拼图游戏</h1>
      
      <div class="difficulty-selector">
        <button 
          v-for="diff in difficulties" 
          :key="diff.size"
          class="diff-btn"
          :class="{ active: gridSize === diff.size }"
          @click="changeDifficulty(diff.size)"
        >
          {{ diff.label }}
        </button>
      </div>

      <div class="stats">
        <div class="stat-item">
          <span class="stat-label">步数</span>
          <span class="stat-value">{{ moves }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">用时</span>
          <span class="stat-value">{{ formatTime(time) }}</span>
        </div>
      </div>
    </div>

    <div class="image-selector">
      <button 
        v-for="(img, idx) in displayImages" 
        :key="idx"
        class="image-btn"
        :class="{ active: currentImageIndex === idx && !customImage }"
        @click="selectImage(idx)"
      >
        <img :src="img" alt="图片预览" />
      </button>
      <label class="image-btn upload-btn" :class="{ active: customImage }">
        <input type="file" accept="image/*" @change="handleImageUpload" hidden />
        <span class="upload-icon">📷</span>
      </label>
    </div>

    <div class="puzzle-container" ref="puzzleContainer">
      <div 
        v-for="(tile, index) in tiles" 
        :key="tile.id"
        class="tile"
        :class="{ 
          'empty': tile.isEmpty,
          'correct': showHint && isCorrect(index),
          'dragging': draggedTile && draggedTile.id === tile.id,
          'selected': selectedTile && selectedTile.id === tile.id
        }"
        :style="getTileStyle(tile)"
        :ref="el => setTileRef(el, index)"
        @click="handleClick(index)"
      >
        <div v-if="!tile.isEmpty" class="tile-inner">
          <div class="tile-image" :style="getTileImageStyle(tile)"></div>
          <span v-if="gridSize <= 4" class="tile-number">{{ tile.id + 1 }}</span>
        </div>
      </div>
    </div>

    <div class="controls">
      <button class="btn btn-primary" @click="resetGame">
        <span class="btn-icon">🔄</span>
        重新开始
      </button>
      <button class="btn btn-secondary" @click="toggleHint" :class="{ active: showHint }">
        <span class="btn-icon">💡</span>
        {{ showHint ? '提示中...' : '显示提示' }}
      </button>
      <button class="btn btn-secondary" @click="showLeaderboard = true">
        <span class="btn-icon">🏆</span>
        排行榜
      </button>
    </div>

    <div class="original-preview">
      <span class="preview-label">原图</span>
      <img :src="currentImage" alt="原图" class="preview-image" />
    </div>

    <div v-if="isComplete" class="modal-overlay" @click="closeCompleteModal">
      <div class="modal-content" @click.stop>
        <div class="modal-icon">🎉</div>
        <h2 class="modal-title">恭喜完成！</h2>
        <p class="modal-text">难度: {{ currentDifficultyLabel }}</p>
        <p class="modal-text">用时: {{ formatTime(time) }}</p>
        <p class="modal-text">步数: {{ moves }}</p>
        
        <div v-if="isNewRecord" class="new-record">
          <span class="record-badge">🏆 新纪录！</span>
          <div class="name-input">
            <input 
              v-model="playerName" 
              type="text" 
              placeholder="输入你的名字"
              maxlength="10"
              @keyup.enter="saveRecord"
            />
            <button class="btn btn-primary" @click="saveRecord">保存</button>
          </div>
        </div>
        
        <button class="btn btn-primary btn-large" @click="resetGame">再玩一次</button>
      </div>
    </div>

    <div v-if="showLeaderboard" class="modal-overlay" @click="showLeaderboard = false">
      <div class="modal-content leaderboard-modal" @click.stop>
        <div class="modal-header">
          <h2 class="modal-title">🏆 排行榜</h2>
          <button class="close-btn" @click="showLeaderboard = false">✕</button>
        </div>
        
        <div class="leaderboard-tabs">
          <button 
            v-for="diff in difficulties" 
            :key="diff.size"
            class="tab-btn"
            :class="{ active: leaderboardTab === diff.size }"
            @click="leaderboardTab = diff.size"
          >
            {{ diff.label }}
          </button>
        </div>
        
        <div class="leaderboard-list">
          <div v-if="currentLeaderboard.length === 0" class="empty-state">
            <p>暂无记录</p>
            <p class="empty-hint">快来挑战第一名吧！</p>
          </div>
          <div 
            v-for="(record, idx) in currentLeaderboard" 
            :key="idx"
            class="leaderboard-item"
            :class="{ 'top-three': idx < 3 }"
          >
            <span class="rank" :class="`rank-${idx + 1}`">
              {{ idx < 3 ? ['🥇', '🥈', '🥉'][idx] : idx + 1 }}
            </span>
            <span class="player-name">{{ record.name }}</span>
            <span class="record-time">{{ formatTime(record.time) }}</span>
            <span class="record-moves">{{ record.moves }}步</span>
          </div>
        </div>
        
        <button v-if="currentLeaderboard.length > 0" class="btn btn-secondary" @click="clearLeaderboard">
          清除记录
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import Hammer from 'hammerjs'

const defaultImages = [
  'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=600&h=600&fit=crop',
  'https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=600&h=600&fit=crop',
  'https://images.unsplash.com/photo-1426604966848-d7adac402bff?w=600&h=600&fit=crop',
  'https://images.unsplash.com/photo-1472214103451-9374bd1c798e?w=600&h=600&fit=crop'
]

const difficulties = [
  { size: 3, label: '简单 3×3', shuffleMoves: 100 },
  { size: 4, label: '中等 4×4', shuffleMoves: 200 },
  { size: 5, label: '困难 5×5', shuffleMoves: 300 }
]

const HINT_DURATION = 3000
const LEADERBOARD_KEY = 'puzzle_leaderboard'
const MAX_RECORDS = 10

const puzzleContainer = ref(null)
const tileRefs = ref([])
const gridSize = ref(3)
const currentImageIndex = ref(0)
const customImage = ref(null)
const tiles = ref([])
const moves = ref(0)
const time = ref(0)
const isPlaying = ref(false)
const isComplete = ref(false)
const showHint = ref(false)
const selectedTile = ref(null)
const draggedTile = ref(null)
const timer = ref(null)
const hintTimer = ref(null)
const hammerManager = ref(null)
const containerSize = ref(300)
const showLeaderboard = ref(false)
const leaderboardTab = ref(3)
const playerName = ref('')
const isNewRecord = ref(false)
const leaderboard = ref({})

const displayImages = computed(() => defaultImages)

const currentImage = computed(() => customImage.value || defaultImages[currentImageIndex.value])

const currentDifficulty = computed(() => difficulties.find(d => d.size === gridSize.value))

const currentDifficultyLabel = computed(() => currentDifficulty.value?.label || '')

const tileSize = computed(() => containerSize.value / gridSize.value)

const currentLeaderboard = computed(() => {
  const key = String(gridSize.value)
  return leaderboard.value[key] || []
})

function setTileRef(el, index) {
  if (el) {
    tileRefs.value[index] = el
  }
}

function formatTime(seconds) {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

function initTiles() {
  const newTiles = []
  const total = gridSize.value * gridSize.value
  for (let i = 0; i < total; i++) {
    newTiles.push({
      id: i,
      correctIndex: i,
      currentIndex: i,
      isEmpty: i === total - 1
    })
  }
  return newTiles
}

function getEmptyIndex(tilesArray = tiles.value) {
  return tilesArray.findIndex(t => t.isEmpty)
}

function getAdjacentIndices(index) {
  const row = Math.floor(index / gridSize.value)
  const col = index % gridSize.value
  const adjacent = []
  
  if (row > 0) adjacent.push(index - gridSize.value)
  if (row < gridSize.value - 1) adjacent.push(index + gridSize.value)
  if (col > 0) adjacent.push(index - 1)
  if (col < gridSize.value - 1) adjacent.push(index + 1)
  
  return adjacent
}

function shuffleTilesByMoves() {
  const newTiles = initTiles()
  let lastMovedIndex = -1
  const shuffleMoves = currentDifficulty.value?.shuffleMoves || 100
  
  for (let i = 0; i < shuffleMoves; i++) {
    const emptyIndex = getEmptyIndex(newTiles)
    const adjacentIndices = getAdjacentIndices(emptyIndex)
    
    const validMoves = adjacentIndices.filter(idx => idx !== lastMovedIndex)
    const moveIndex = validMoves[Math.floor(Math.random() * validMoves.length)]
    
    const temp = newTiles[emptyIndex].currentIndex
    newTiles[emptyIndex].currentIndex = newTiles[moveIndex].currentIndex
    newTiles[moveIndex].currentIndex = temp
    
    ;[newTiles[emptyIndex], newTiles[moveIndex]] = [newTiles[moveIndex], newTiles[emptyIndex]]
    
    lastMovedIndex = emptyIndex
  }
  
  return newTiles
}

function checkComplete(tilesArray = tiles.value) {
  return tilesArray.every(tile => tile.id === tile.currentIndex)
}

function isAdjacentToEmpty(index) {
  const emptyIndex = getEmptyIndex()
  return getAdjacentIndices(index).includes(emptyIndex)
}

function swapTiles(index1, index2) {
  const temp = tiles.value[index1].currentIndex
  tiles.value[index1].currentIndex = tiles.value[index2].currentIndex
  tiles.value[index2].currentIndex = temp
  
  ;[tiles.value[index1], tiles.value[index2]] = [tiles.value[index2], tiles.value[index1]]
  
  moves.value++
  
  if (checkComplete()) {
    gameComplete()
  }
}

function handleClick(index) {
  const tile = tiles.value[index]
  if (tile.isEmpty || isComplete.value) return
  
  if (isAdjacentToEmpty(index)) {
    if (!isPlaying.value) {
      startTimer()
    }
    swapTiles(index, getEmptyIndex())
    selectedTile.value = null
  } else {
    if (selectedTile.value && selectedTile.value.currentIndex === index) {
      selectedTile.value = null
    } else if (selectedTile.value) {
      if (getAdjacentIndices(selectedTile.value.currentIndex).includes(index)) {
        if (!isPlaying.value) {
          startTimer()
        }
        swapTiles(selectedTile.value.currentIndex, index)
      }
      selectedTile.value = null
    } else {
      selectedTile.value = tile
    }
  }
}

function getTileStyle(tile) {
  const row = Math.floor(tile.currentIndex / gridSize.value)
  const col = tile.currentIndex % gridSize.value
  const size = tileSize.value
  
  let style = {
    width: `${size}px`,
    height: `${size}px`,
    transform: `translate(${col * size}px, ${row * size}px)`
  }
  
  if (draggedTile.value && draggedTile.value.id === tile.id) {
    style.zIndex = 100
  }
  
  return style
}

function getTileImageStyle(tile) {
  const originalRow = Math.floor(tile.id / gridSize.value)
  const originalCol = tile.id % gridSize.value
  
  return {
    backgroundImage: `url(${currentImage.value})`,
    backgroundSize: `${containerSize.value}px ${containerSize.value}px`,
    backgroundPosition: `-${originalCol * tileSize.value}px -${originalRow * tileSize.value}px`
  }
}

function isCorrect(index) {
  return tiles.value[index].id === index
}

function startTimer() {
  isPlaying.value = true
  timer.value = setInterval(() => {
    time.value++
  }, 1000)
}

function stopTimer() {
  isPlaying.value = false
  if (timer.value) {
    clearInterval(timer.value)
    timer.value = null
  }
}

function gameComplete() {
  stopTimer()
  isComplete.value = true
  isNewRecord.value = checkIsNewRecord()
}

function checkIsNewRecord() {
  const key = String(gridSize.value)
  const records = leaderboard.value[key] || []
  
  if (records.length < MAX_RECORDS) return true
  
  const worstRecord = records[records.length - 1]
  return time.value < worstRecord.time || 
         (time.value === worstRecord.time && moves.value < worstRecord.moves)
}

function saveRecord() {
  const name = playerName.value.trim() || '匿名玩家'
  const key = String(gridSize.value)
  
  if (!leaderboard.value[key]) {
    leaderboard.value[key] = []
  }
  
  leaderboard.value[key].push({
    name,
    time: time.value,
    moves: moves.value,
    date: new Date().toISOString()
  })
  
  leaderboard.value[key].sort((a, b) => {
    if (a.time !== b.time) return a.time - b.time
    return a.moves - b.moves
  })
  
  leaderboard.value[key] = leaderboard.value[key].slice(0, MAX_RECORDS)
  
  saveLeaderboardToStorage()
  isNewRecord.value = false
  playerName.value = ''
}

function clearLeaderboard() {
  if (confirm('确定要清除该难度的所有记录吗？')) {
    const key = String(gridSize.value)
    leaderboard.value[key] = []
    saveLeaderboardToStorage()
  }
}

function loadLeaderboardFromStorage() {
  try {
    const saved = localStorage.getItem(LEADERBOARD_KEY)
    if (saved) {
      leaderboard.value = JSON.parse(saved)
    }
  } catch (e) {
    console.error('加载排行榜失败', e)
  }
}

function saveLeaderboardToStorage() {
  try {
    localStorage.setItem(LEADERBOARD_KEY, JSON.stringify(leaderboard.value))
  } catch (e) {
    console.error('保存排行榜失败', e)
  }
}

function resetGame() {
  stopTimer()
  moves.value = 0
  time.value = 0
  isComplete.value = false
  showHint.value = false
  selectedTile.value = null
  draggedTile.value = null
  isNewRecord.value = false
  playerName.value = ''
  if (hintTimer.value) {
    clearTimeout(hintTimer.value)
    hintTimer.value = null
  }
  tiles.value = shuffleTilesByMoves()
}

function toggleHint() {
  if (showHint.value) {
    showHint.value = false
    if (hintTimer.value) {
      clearTimeout(hintTimer.value)
      hintTimer.value = null
    }
  } else {
    showHint.value = true
    if (hintTimer.value) {
      clearTimeout(hintTimer.value)
    }
    hintTimer.value = setTimeout(() => {
      showHint.value = false
      hintTimer.value = null
    }, HINT_DURATION)
  }
}

function selectImage(idx) {
  currentImageIndex.value = idx
  customImage.value = null
  resetGame()
}

function handleImageUpload(event) {
  const file = event.target.files[0]
  if (!file) return
  
  if (!file.type.startsWith('image/')) {
    alert('请选择图片文件')
    return
  }
  
  const reader = new FileReader()
  reader.onload = (e) => {
    const img = new Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      const size = 600
      canvas.width = size
      canvas.height = size
      const ctx = canvas.getContext('2d')
      
      const scale = Math.max(size / img.width, size / img.height)
      const x = (size - img.width * scale) / 2
      const y = (size - img.height * scale) / 2
      
      ctx.drawImage(img, x, y, img.width * scale, img.height * scale)
      
      customImage.value = canvas.toDataURL('image/jpeg', 0.9)
      resetGame()
    }
    img.src = e.target.result
  }
  reader.readAsDataURL(file)
  event.target.value = ''
}

function changeDifficulty(size) {
  if (gridSize.value === size) return
  gridSize.value = size
  leaderboardTab.value = size
  resetGame()
}

function closeCompleteModal() {
  isComplete.value = false
  isNewRecord.value = false
  playerName.value = ''
}

function initHammer() {
  if (!puzzleContainer.value) return
  
  if (hammerManager.value) {
    hammerManager.value.destroy()
  }
  
  hammerManager.value = new Hammer(puzzleContainer.value, {
    touchAction: 'auto',
    recognizers: [
      [Hammer.Pan, { direction: Hammer.DIRECTION_ALL, threshold: 5 }]
    ]
  })
  
  let panStartIndex = -1
  let isDragging = false
  
  hammerManager.value.on('panstart', (e) => {
    const target = e.target.closest('.tile')
    if (!target) return
    
    const index = Array.from(target.parentNode.children).indexOf(target)
    if (index < 0 || tiles.value[index].isEmpty) return
    
    panStartIndex = index
    draggedTile.value = tiles.value[index]
    isDragging = false
    
    const tileEl = tileRefs.value[panStartIndex]
    if (tileEl) {
      tileEl.style.transition = 'none'
    }
  })
  
  hammerManager.value.on('panmove', (e) => {
    if (panStartIndex < 0 || !draggedTile.value) return
    
    isDragging = true
    const tileEl = tileRefs.value[panStartIndex]
    if (!tileEl) return
    
    const emptyIndex = getEmptyIndex()
    const emptyRow = Math.floor(emptyIndex / gridSize.value)
    const emptyCol = emptyIndex % gridSize.value
    const tileRow = Math.floor(draggedTile.value.currentIndex / gridSize.value)
    const tileCol = draggedTile.value.currentIndex % gridSize.value
    
    const size = tileSize.value
    let translateX = tileCol * size
    let translateY = tileRow * size
    
    const isHorizontal = emptyRow === tileRow
    const isVertical = emptyCol === tileCol
    
    if (isHorizontal) {
      translateX = Math.max(
        Math.min(tileCol * size + e.deltaX, Math.max(tileCol, emptyCol) * size),
        Math.min(tileCol, emptyCol) * size
      )
    } else if (isVertical) {
      translateY = Math.max(
        Math.min(tileRow * size + e.deltaY, Math.max(tileRow, emptyRow) * size),
        Math.min(tileRow, emptyRow) * size
      )
    } else {
      translateX += e.deltaX * 0.3
      translateY += e.deltaY * 0.3
    }
    
    tileEl.style.transform = `translate(${translateX}px, ${translateY}px)`
    tileEl.style.zIndex = 100
  })
  
  hammerManager.value.on('panend', (e) => {
    if (panStartIndex < 0 || !draggedTile.value) return
    
    const tileEl = tileRefs.value[panStartIndex]
    if (tileEl) {
      tileEl.style.transition = ''
      tileEl.style.zIndex = ''
      tileEl.style.transform = ''
    }
    
    if (isDragging) {
      const threshold = tileSize.value / 3
      const emptyIndex = getEmptyIndex()
      
      if (Math.abs(e.deltaX) > threshold || Math.abs(e.deltaY) > threshold) {
        const emptyRow = Math.floor(emptyIndex / gridSize.value)
        const emptyCol = emptyIndex % gridSize.value
        const tileRow = Math.floor(draggedTile.value.currentIndex / gridSize.value)
        const tileCol = draggedTile.value.currentIndex % gridSize.value
        
        const isHorizontal = Math.abs(e.deltaX) > Math.abs(e.deltaY)
        
        let canMove = false
        if (isHorizontal) {
          if (e.deltaX > 0 && emptyRow === tileRow && emptyCol === tileCol + 1) {
            canMove = true
          } else if (e.deltaX < 0 && emptyRow === tileRow && emptyCol === tileCol - 1) {
            canMove = true
          }
        } else {
          if (e.deltaY > 0 && emptyCol === tileCol && emptyRow === tileRow + 1) {
            canMove = true
          } else if (e.deltaY < 0 && emptyCol === tileCol && emptyRow === tileRow - 1) {
            canMove = true
          }
        }
        
        if (canMove) {
          if (!isPlaying.value) {
            startTimer()
          }
          swapTiles(draggedTile.value.currentIndex, emptyIndex)
        }
      }
    }
    
    panStartIndex = -1
    draggedTile.value = null
    isDragging = false
  })
}

function updateContainerSize() {
  const width = Math.min(window.innerWidth - 40, 400)
  containerSize.value = width
}

watch(gridSize, () => {
  nextTick(() => {
    initHammer()
  })
})

onMounted(() => {
  loadLeaderboardFromStorage()
  updateContainerSize()
  window.addEventListener('resize', updateContainerSize)
  
  nextTick(() => {
    tiles.value = shuffleTilesByMoves()
    initHammer()
  })
})

onUnmounted(() => {
  stopTimer()
  window.removeEventListener('resize', updateContainerSize)
  if (hintTimer.value) {
    clearTimeout(hintTimer.value)
  }
  if (hammerManager.value) {
    hammerManager.value.destroy()
  }
})
</script>

<style scoped>
.puzzle-game {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
  color: #fff;
  min-height: 100vh;
}

.header {
  text-align: center;
  margin-bottom: 15px;
  width: 100%;
}

.title {
  font-size: 28px;
  font-weight: bold;
  margin-bottom: 15px;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
}

.difficulty-selector {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-bottom: 15px;
  flex-wrap: wrap;
}

.diff-btn {
  padding: 8px 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  backdrop-filter: blur(10px);
}

.diff-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

.diff-btn.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: transparent;
  transform: scale(1.05);
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}

.stats {
  display: flex;
  justify-content: center;
  gap: 30px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  background: rgba(255, 255, 255, 0.2);
  padding: 8px 16px;
  border-radius: 12px;
  backdrop-filter: blur(10px);
  min-width: 80px;
}

.stat-label {
  font-size: 11px;
  opacity: 0.8;
  margin-bottom: 2px;
}

.stat-value {
  font-size: 20px;
  font-weight: bold;
  font-family: 'Courier New', monospace;
}

.image-selector {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
  overflow-x: auto;
  padding: 5px;
  width: 100%;
  justify-content: center;
}

.image-btn {
  width: 50px;
  height: 50px;
  border-radius: 8px;
  overflow: hidden;
  border: 3px solid transparent;
  cursor: pointer;
  padding: 0;
  background: rgba(255, 255, 255, 0.1);
  flex-shrink: 0;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-btn:hover {
  transform: scale(1.1);
}

.image-btn.active {
  border-color: #fff;
  transform: scale(1.1);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
}

.image-btn img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.upload-btn {
  background: rgba(255, 255, 255, 0.2);
  border: 2px dashed rgba(255, 255, 255, 0.5);
}

.upload-btn.active {
  border-style: solid;
  border-color: #ffd700;
}

.upload-icon {
  font-size: 24px;
}

.puzzle-container {
  position: relative;
  width: v-bind('containerSize + "px"');
  height: v-bind('containerSize + "px"');
  background: rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
  touch-action: none;
}

.tile {
  position: absolute;
  width: v-bind('tileSize + "px"');
  height: v-bind('tileSize + "px"');
  transition: transform 0.15s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.2s ease;
  cursor: pointer;
  z-index: 1;
  will-change: transform;
}

.tile.empty {
  background: rgba(0, 0, 0, 0.2);
  cursor: default;
}

.tile:not(.empty):hover {
  z-index: 10;
}

.tile.dragging {
  transition: none;
}

.tile.selected {
  box-shadow: 0 0 0 3px #ffd700, 0 0 20px rgba(255, 215, 0, 0.5);
  z-index: 20;
}

.tile.correct:not(.empty) {
  box-shadow: inset 0 0 0 3px rgba(76, 175, 80, 0.8), 0 0 15px rgba(76, 175, 80, 0.4);
  animation: hintPulse 1s ease-in-out infinite;
}

@keyframes hintPulse {
  0%, 100% {
    box-shadow: inset 0 0 0 3px rgba(76, 175, 80, 0.8), 0 0 15px rgba(76, 175, 80, 0.4);
  }
  50% {
    box-shadow: inset 0 0 0 3px rgba(76, 175, 80, 1), 0 0 25px rgba(76, 175, 80, 0.6);
  }
}

.tile.correct:not(.empty) .tile-inner::after {
  content: '✓';
  position: absolute;
  top: 4px;
  right: 4px;
  font-size: 14px;
  color: #4caf50;
  font-weight: bold;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
}

.tile-inner {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.tile-image {
  width: 100%;
  height: 100%;
  background-repeat: no-repeat;
}

.tile-number {
  position: absolute;
  bottom: 3px;
  left: 3px;
  font-size: 12px;
  font-weight: bold;
  color: #fff;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.8);
  background: rgba(0, 0, 0, 0.3);
  padding: 1px 4px;
  border-radius: 3px;
}

.controls {
  display: flex;
  gap: 10px;
  margin-top: 20px;
  width: 100%;
  justify-content: center;
  flex-wrap: wrap;
}

.btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 18px;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  color: #fff;
}

.btn:active {
  transform: scale(0.95);
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(10px);
  border: 2px solid rgba(255, 255, 255, 0.3);
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.3);
}

.btn-secondary.active {
  background: rgba(255, 215, 0, 0.3);
  border-color: #ffd700;
  animation: hintBtnPulse 1s ease-in-out infinite;
}

@keyframes hintBtnPulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(255, 215, 0, 0.4);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(255, 215, 0, 0);
  }
}

.btn-large {
  padding: 14px 40px;
  font-size: 16px;
}

.btn-icon {
  font-size: 18px;
}

.original-preview {
  margin-top: 15px;
  text-align: center;
}

.preview-label {
  display: block;
  font-size: 11px;
  opacity: 0.8;
  margin-bottom: 6px;
}

.preview-image {
  width: 70px;
  height: 70px;
  border-radius: 8px;
  object-fit: cover;
  border: 2px solid rgba(255, 255, 255, 0.3);
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  backdrop-filter: blur(5px);
  padding: 20px;
}

.modal-content {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 30px;
  border-radius: 24px;
  text-align: center;
  max-width: 340px;
  width: 100%;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  animation: modalIn 0.3s ease;
  max-height: 80vh;
  overflow-y: auto;
}

@keyframes modalIn {
  from {
    transform: scale(0.8);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.close-btn {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: #fff;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.3s ease;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.modal-icon {
  font-size: 56px;
  margin-bottom: 12px;
  animation: bounce 0.5s ease infinite alternate;
}

@keyframes bounce {
  from {
    transform: translateY(0);
  }
  to {
    transform: translateY(-10px);
  }
}

.modal-title {
  font-size: 22px;
  margin-bottom: 12px;
}

.modal-text {
  font-size: 16px;
  margin-bottom: 6px;
  opacity: 0.9;
}

.new-record {
  margin: 20px 0;
  padding: 15px;
  background: rgba(255, 215, 0, 0.2);
  border-radius: 12px;
  border: 2px solid #ffd700;
}

.record-badge {
  display: inline-block;
  font-size: 18px;
  font-weight: bold;
  color: #ffd700;
  margin-bottom: 12px;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.3);
}

.name-input {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}

.name-input input {
  flex: 1;
  padding: 10px 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: #fff;
  font-size: 14px;
  outline: none;
  transition: border-color 0.3s ease;
}

.name-input input::placeholder {
  color: rgba(255, 255, 255, 0.5);
}

.name-input input:focus {
  border-color: #ffd700;
}

.name-input .btn {
  padding: 10px 20px;
}

.leaderboard-modal {
  max-width: 380px;
}

.leaderboard-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  justify-content: center;
}

.tab-btn {
  padding: 8px 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.tab-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

.tab-btn.active {
  background: rgba(255, 255, 255, 0.3);
  border-color: transparent;
}

.leaderboard-list {
  margin-bottom: 20px;
  max-height: 300px;
  overflow-y: auto;
}

.leaderboard-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  margin-bottom: 8px;
  transition: all 0.3s ease;
}

.leaderboard-item:hover {
  background: rgba(255, 255, 255, 0.15);
}

.leaderboard-item.top-three {
  background: rgba(255, 215, 0, 0.15);
  border: 1px solid rgba(255, 215, 0, 0.3);
}

.rank {
  width: 30px;
  font-size: 18px;
  font-weight: bold;
  text-align: center;
}

.rank-1, .rank-2, .rank-3 {
  font-size: 22px;
}

.player-name {
  flex: 1;
  font-size: 14px;
  font-weight: 600;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.record-time {
  font-family: 'Courier New', monospace;
  font-size: 14px;
  font-weight: bold;
  color: #ffd700;
}

.record-moves {
  font-size: 12px;
  opacity: 0.7;
  min-width: 45px;
  text-align: right;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  opacity: 0.7;
}

.empty-state p {
  margin-bottom: 5px;
}

.empty-hint {
  font-size: 13px;
  opacity: 0.8;
}

.modal-content .btn {
  margin-top: 15px;
  width: 100%;
  justify-content: center;
  background: rgba(255, 255, 255, 0.2);
}

@media (max-width: 360px) {
  .title {
    font-size: 24px;
  }
  
  .diff-btn {
    padding: 6px 12px;
    font-size: 12px;
  }
  
  .stats {
    gap: 15px;
  }
  
  .stat-item {
    padding: 6px 12px;
    min-width: 70px;
  }
  
  .stat-value {
    font-size: 18px;
  }
  
  .btn {
    padding: 8px 14px;
    font-size: 13px;
  }
  
  .preview-image {
    width: 60px;
    height: 60px;
  }
  
  .modal-content {
    padding: 24px 20px;
  }
}
</style>

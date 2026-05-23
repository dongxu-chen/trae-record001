<template>
  <div class="sticker-library">
    <div class="panel-section">
      <h3>🎨 贴纸库</h3>
      
      <div class="tab-buttons">
        <button
          v-for="category in stickerCategories"
          :key="category.id"
          class="tab-btn"
          :class="{ active: activeTab === category.id }"
          @click="activeTab = category.id"
        >
          {{ category.icon }}
        </button>
      </div>

      <div class="search-box">
        <input
          type="text"
          v-model="searchQuery"
          placeholder="搜索贴纸..."
          @input="handleSearch"
        />
      </div>

      <div class="sticker-grid">
        <div
          v-for="sticker in displayedStickers"
          :key="sticker.id"
          class="sticker-item"
          :title="sticker.name"
          @click="addSticker(sticker)"
        >
          <span v-if="sticker.type === 'text'" class="emoji-sticker">
            {{ sticker.emoji }}
          </span>
          <div
            v-else-if="sticker.type === 'shape'"
            class="shape-sticker"
            :style="{ backgroundColor: sticker.color }"
          >
            <span class="shape-text">{{ getShapeIcon(sticker.shape) }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="panel-section">
      <h3>✍️ 艺术字库</h3>
      
      <div class="tab-buttons">
        <button
          v-for="category in artTextCategories"
          :key="category.id"
          class="tab-btn"
          :class="{ active: activeArtTab === category.id }"
          @click="activeArtTab = category.id"
        >
          {{ category.name }}
        </button>
      </div>

      <div class="art-text-list">
        <div
          v-for="artText in displayedArtTexts"
          :key="artText.id"
          class="art-text-item"
          :title="artText.name"
          @click="addArtText(artText)"
        >
          <span
            class="art-text-preview"
            :style="getArtTextStyle(artText.style)"
          >
            {{ artText.text }}
          </span>
          <span class="art-text-name">{{ artText.name }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const props = defineProps({
  canvas: Object
})

const emit = defineEmits(['add'])

const activeTab = ref('emoji')
const activeArtTab = ref('classic')
const searchQuery = ref('')

const stickerCategories = ref([])
const artTextCategories = ref([])

const displayedStickers = computed(() => {
  const category = stickerCategories.value.find(c => c.id === activeTab.value)
  if (!category) return []
  return category.items
})

const displayedArtTexts = computed(() => {
  const category = artTextCategories.value.find(c => c.id === activeArtTab.value)
  if (!category) return []
  return category.items
})

onMounted(async () => {
  const { assetLibrary } = await import('../utils/AssetLibrary.js')
  stickerCategories.value = assetLibrary.getAllStickerCategories()
  artTextCategories.value = assetLibrary.getAllArtTextCategories()
})

function getShapeIcon(shape) {
  const icons = {
    circle: '●',
    rect: '■',
    triangle: '▲',
    diamond: '◆',
    pentagon: '⬠',
    hexagon: '⬡'
  }
  return icons[shape] || '●'
}

function getArtTextStyle(style) {
  const cssStyle = {
    fontSize: (style.fontSize / 2) + 'px',
    fontWeight: style.fontWeight || 'normal',
    color: style.fill || '#000',
    fontFamily: style.fontFamily || 'Arial'
  }
  if (style.stroke) {
    cssStyle.textShadow = `2px 2px 0 ${style.stroke}, -2px -2px 0 ${style.stroke}, 2px -2px 0 ${style.stroke}, -2px 2px 0 ${style.stroke}`
  }
  return cssStyle
}

async function addSticker(sticker) {
  if (!props.canvas) return

  const { assetLibrary } = await import('../utils/AssetLibrary.js')
  const fabric = await import('fabric')
  
  if (sticker.type === 'text') {
    const text = new fabric.default.IText(sticker.emoji, {
      left: props.canvas.width / 2,
      top: props.canvas.height / 2,
      fontSize: 64,
      originX: 'center',
      originY: 'center'
    })
    text.layerId = 'sticker_' + Date.now()
    props.canvas.add(text)
    props.canvas.setActiveObject(text)
    props.canvas.renderAll()
    emit('add', text)
  } else if (sticker.type === 'shape') {
    const imageUrl = await assetLibrary.getStickerImage(sticker)
    fabric.default.Image.fromURL(imageUrl, (img) => {
      img.scale(0.8)
      img.center()
      img.layerId = 'sticker_' + Date.now()
      props.canvas.add(img)
      props.canvas.setActiveObject(img)
      props.canvas.renderAll()
      emit('add', img)
      
      if (imageUrl.startsWith('blob:')) {
        URL.revokeObjectURL(imageUrl)
      }
    })
  }
}

async function addArtText(artText) {
  if (!props.canvas) return

  const fabric = await import('fabric')
  
  const text = new fabric.default.IText(artText.text, {
    left: props.canvas.width / 2,
    top: props.canvas.height / 2,
    originX: 'center',
    originY: 'center',
    ...artText.style
  })
  
  text.layerId = 'arttext_' + Date.now()
  props.canvas.add(text)
  props.canvas.setActiveObject(text)
  props.canvas.renderAll()
  emit('add', text)
}

function handleSearch() {
  if (!searchQuery.value) return
  // 搜索功能可以在这里扩展
}
</script>

<style scoped>
.sticker-library {
  margin-bottom: 24px;
}

.tab-buttons {
  display: flex;
  gap: 4px;
  margin-bottom: 12px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.tab-btn {
  padding: 6px 10px;
  background: #0f3460;
  border: none;
  border-radius: 4px;
  color: #fff;
  cursor: pointer;
  font-size: 12px;
  white-space: nowrap;
  transition: all 0.2s;
}

.tab-btn:hover {
  background: #533483;
}

.tab-btn.active {
  background: #e94560;
}

.search-box {
  margin-bottom: 12px;
}

.search-box input {
  width: 100%;
  padding: 8px 12px;
  background: #0f3460;
  border: 1px solid #1a1a2e;
  border-radius: 6px;
  color: #fff;
  font-size: 13px;
}

.search-box input::placeholder {
  color: #666;
}

.sticker-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  max-height: 200px;
  overflow-y: auto;
  padding: 4px;
}

.sticker-item {
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0f3460;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.sticker-item:hover {
  background: #533483;
  transform: scale(1.1);
}

.emoji-sticker {
  font-size: 28px;
}

.shape-sticker {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.shape-text {
  color: #fff;
  font-size: 20px;
}

.art-text-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 200px;
  overflow-y: auto;
}

.art-text-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: #0f3460;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.art-text-item:hover {
  background: #533483;
}

.art-text-preview {
  flex: 1;
  text-align: center;
}

.art-text-name {
  font-size: 11px;
  color: #888;
  margin-left: 10px;
}
</style>

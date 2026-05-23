const stickerCategories = {
  emoji: {
    name: '表情符号',
    icon: '😊',
    items: [
      { id: 'emoji_1', name: '笑脸', emoji: '😊', type: 'text' },
      { id: 'emoji_2', name: '爱心', emoji: '❤️', type: 'text' },
      { id: 'emoji_3', name: '点赞', emoji: '👍', type: 'text' },
      { id: 'emoji_4', name: '星星', emoji: '⭐', type: 'text' },
      { id: 'emoji_5', name: '火焰', emoji: '🔥', type: 'text' },
      { id: 'emoji_6', name: '彩虹', emoji: '🌈', type: 'text' },
      { id: 'emoji_7', name: '太阳', emoji: '☀️', type: 'text' },
      { id: 'emoji_8', name: '月亮', emoji: '🌙', type: 'text' },
      { id: 'emoji_9', name: '花朵', emoji: '🌸', type: 'text' },
      { id: 'emoji_10', name: '蝴蝶', emoji: '🦋', type: 'text' },
      { id: 'emoji_11', name: '皇冠', emoji: '👑', type: 'text' },
      { id: 'emoji_12', name: '钻石', emoji: '💎', type: 'text' },
      { id: 'emoji_13', name: '气球', emoji: '🎈', type: 'text' },
      { id: 'emoji_14', name: '礼物', emoji: '🎁', type: 'text' },
      { id: 'emoji_15', name: '蛋糕', emoji: '🎂', type: 'text' },
      { id: 'emoji_16', name: '音乐', emoji: '🎵', type: 'text' }
    ]
  },
  shapes: {
    name: '几何形状',
    icon: '🔷',
    items: [
      { id: 'shape_1', name: '圆形', type: 'shape', shape: 'circle', color: '#e94560' },
      { id: 'shape_2', name: '方形', type: 'shape', shape: 'rect', color: '#4ade80' },
      { id: 'shape_3', name: '三角形', type: 'shape', shape: 'triangle', color: '#60a5fa' },
      { id: 'shape_4', name: '菱形', type: 'shape', shape: 'diamond', color: '#fbbf24' },
      { id: 'shape_5', name: '五边形', type: 'shape', shape: 'pentagon', color: '#a78bfa' },
      { id: 'shape_6', name: '六边形', type: 'shape', shape: 'hexagon', color: '#f472b6' }
    ]
  },
  decorations: {
    name: '装饰元素',
    icon: '✨',
    items: [
      { id: 'deco_1', name: '边框', type: 'svg', svg: 'border' },
      { id: 'deco_2', name: '箭头', emoji: '➡️', type: 'text' },
      { id: 'deco_3', name: '对勾', emoji: '✅', type: 'text' },
      { id: 'deco_4', name: '叉号', emoji: '❌', type: 'text' },
      { id: 'deco_5', name: '问号', emoji: '❓', type: 'text' },
      { id: 'deco_6', name: '感叹号', emoji: '❗', type: 'text' },
      { id: 'deco_7', name: '引号', emoji: '💬', type: 'text' },
      { id: 'deco_8', name: '思考', emoji: '💭', type: 'text' }
    ]
  },
  nature: {
    name: '自然元素',
    icon: '🌿',
    items: [
      { id: 'nature_1', name: '树叶', emoji: '🍃', type: 'text' },
      { id: 'nature_2', name: '雨滴', emoji: '💧', type: 'text' },
      { id: 'nature_3', name: '雪花', emoji: '❄️', type: 'text' },
      { id: 'nature_4', name: '闪电', emoji: '⚡', type: 'text' },
      { id: 'nature_5', name: '云朵', emoji: '☁️', type: 'text' },
      { id: 'nature_6', name: '彩虹', emoji: '🌈', type: 'text' },
      { id: 'nature_7', name: '棕榈树', emoji: '🌴', type: 'text' },
      { id: 'nature_8', name: '山脉', emoji: '🏔️', type: 'text' }
    ]
  },
  food: {
    name: '美食',
    icon: '🍕',
    items: [
      { id: 'food_1', name: '披萨', emoji: '🍕', type: 'text' },
      { id: 'food_2', name: '汉堡', emoji: '🍔', type: 'text' },
      { id: 'food_3', name: '咖啡', emoji: '☕', type: 'text' },
      { id: 'food_4', name: '冰淇淋', emoji: '🍦', type: 'text' },
      { id: 'food_5', name: '苹果', emoji: '🍎', type: 'text' },
      { id: 'food_6', name: '葡萄', emoji: '🍇', type: 'text' },
      { id: 'food_7', name: '西瓜', emoji: '🍉', type: 'text' },
      { id: 'food_8', name: '啤酒', emoji: '🍺', type: 'text' }
    ]
  }
}

const artTextTemplates = {
  classic: {
    name: '经典风格',
    items: [
      {
        id: 'art_1',
        name: '标题大字',
        text: '标题文字',
        style: {
          fontSize: 72,
          fontWeight: 'bold',
          fill: '#ffffff',
          stroke: '#000000',
          strokeWidth: 3,
          fontFamily: 'Arial Black'
        }
      },
      {
        id: 'art_2',
        name: '渐变文字',
        text: '渐变效果',
        style: {
          fontSize: 56,
          fontWeight: 'bold',
          fill: '#e94560',
          fontFamily: 'Arial'
        }
      },
      {
        id: 'art_3',
        name: '描边文字',
        text: '描边效果',
        style: {
          fontSize: 64,
          fontWeight: 'bold',
          fill: '#ffffff',
          stroke: '#e94560',
          strokeWidth: 4,
          fontFamily: 'Impact'
        }
      }
    ]
  },
  modern: {
    name: '现代风格',
    items: [
      {
        id: 'art_4',
        name: '阴影文字',
        text: '阴影效果',
        style: {
          fontSize: 56,
          fontWeight: 'normal',
          fill: '#333333',
          fontFamily: 'Helvetica Neue',
          shadow: { color: 'rgba(0,0,0,0.3)', blur: 10, offsetX: 5, offsetY: 5 }
        }
      },
      {
        id: 'art_5',
        name: '霓虹文字',
        text: '霓虹发光',
        style: {
          fontSize: 64,
          fontWeight: 'bold',
          fill: '#00ffff',
          stroke: '#00ffff',
          strokeWidth: 1,
          fontFamily: 'Arial Black',
          shadow: { color: '#00ffff', blur: 20, offsetX: 0, offsetY: 0 }
        }
      },
      {
        id: 'art_6',
        name: '科技感',
        text: 'TECH',
        style: {
          fontSize: 72,
          fontWeight: 'bold',
          fill: '#4ade80',
          fontFamily: 'Courier New',
          charSpacing: 20
        }
      }
    ]
  },
  playful: {
    name: '活泼风格',
    items: [
      {
        id: 'art_7',
        name: '卡通文字',
        text: '可爱卡通',
        style: {
          fontSize: 56,
          fontWeight: 'bold',
          fill: '#ff6b6b',
          stroke: '#ffffff',
          strokeWidth: 3,
          fontFamily: 'Comic Sans MS'
        }
      },
      {
        id: 'art_8',
        name: '复古文字',
        text: '复古风格',
        style: {
          fontSize: 48,
          fontWeight: 'bold',
          fill: '#fbbf24',
          stroke: '#92400e',
          strokeWidth: 2,
          fontFamily: 'Georgia'
        }
      },
      {
        id: 'art_9',
        name: '趣味文字',
        text: 'Fun!',
        style: {
          fontSize: 80,
          fontWeight: 'bold',
          fill: '#ff00ff',
          stroke: '#ffff00',
          strokeWidth: 3,
          fontFamily: 'Arial Black'
        }
      }
    ]
  },
  elegant: {
    name: '优雅风格',
    items: [
      {
        id: 'art_10',
        name: '书法文字',
        text: '书法艺术',
        style: {
          fontSize: 64,
          fontWeight: 'normal',
          fill: '#1a1a2e',
          fontFamily: 'Times New Roman',
          fontStyle: 'italic'
        }
      },
      {
        id: 'art_11',
        name: '纤细文字',
        text: 'Elegant',
        style: {
          fontSize: 56,
          fontWeight: 'lighter',
          fill: '#666666',
          fontFamily: 'Helvetica Neue Light',
          charSpacing: 10
        }
      },
      {
        id: 'art_12',
        name: '手写风格',
        text: 'Handwritten',
        style: {
          fontSize: 52,
          fontWeight: 'normal',
          fill: '#333333',
          fontFamily: 'Brush Script MT',
          fontStyle: 'italic'
        }
      }
    ]
  }
}

function createShapeSVG(shape, color, size = 100) {
  const svgMap = {
    circle: `<svg width="${size}" height="${size}" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
      <circle cx="50" cy="50" r="45" fill="${color}"/>
    </svg>`,
    rect: `<svg width="${size}" height="${size}" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
      <rect x="10" y="10" width="80" height="80" fill="${color}"/>
    </svg>`,
    triangle: `<svg width="${size}" height="${size}" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
      <polygon points="50,10 90,90 10,90" fill="${color}"/>
    </svg>`,
    diamond: `<svg width="${size}" height="${size}" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
      <polygon points="50,5 95,50 50,95 5,50" fill="${color}"/>
    </svg>`,
    pentagon: `<svg width="${size}" height="${size}" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
      <polygon points="50,5 95,38 77,90 23,90 5,38" fill="${color}"/>
    </svg>`,
    hexagon: `<svg width="${size}" height="${size}" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
      <polygon points="50,5 90,27.5 90,72.5 50,95 10,72.5 10,27.5" fill="${color}"/>
    </svg>`
  }
  return svgMap[shape] || svgMap.circle
}

function stickerToDataURL(sticker) {
  return new Promise((resolve) => {
    if (sticker.type === 'text') {
      const canvas = document.createElement('canvas')
      canvas.width = 120
      canvas.height = 120
      const ctx = canvas.getContext('2d')
      ctx.font = '80px Arial'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(sticker.emoji, 60, 60)
      resolve(canvas.toDataURL())
    } else if (sticker.type === 'shape') {
      const svg = createShapeSVG(sticker.shape, sticker.color, 120)
      const blob = new Blob([svg], { type: 'image/svg+xml' })
      const url = URL.createObjectURL(blob)
      resolve(url)
    } else {
      resolve(null)
    }
  })
}

class AssetLibrary {
  constructor() {
    this.stickerCategories = stickerCategories
    this.artTextTemplates = artTextTemplates
  }

  getAllStickerCategories() {
    return Object.entries(this.stickerCategories).map(([key, value]) => ({
      id: key,
      ...value
    }))
  }

  getStickersByCategory(categoryId) {
    return this.stickerCategories[categoryId]?.items || []
  }

  searchStickers(query) {
    const results = []
    const lowerQuery = query.toLowerCase()
    
    Object.values(this.stickerCategories).forEach(category => {
      category.items.forEach(item => {
        if (item.name.toLowerCase().includes(lowerQuery) || 
            (item.emoji && item.emoji.includes(query))) {
          results.push(item)
        }
      })
    })
    
    return results
  }

  getAllArtTextCategories() {
    return Object.entries(this.artTextTemplates).map(([key, value]) => ({
      id: key,
      ...value
    }))
  }

  getArtTextsByCategory(categoryId) {
    return this.artTextTemplates[categoryId]?.items || []
  }

  async getStickerImage(sticker) {
    return await stickerToDataURL(sticker)
  }
}

export const assetLibrary = new AssetLibrary()
export default AssetLibrary
export { stickerCategories, artTextTemplates }

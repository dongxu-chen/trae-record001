import chroma from 'chroma-js'

const COLOR_NAME_DATABASE = [
  { name: '商务蓝', hex: '#2563eb', range: { h: [210, 230], s: [0.6, 1], l: [0.4, 0.6] }, tags: ['专业', '信任', '科技'] },
  { name: '科技蓝', hex: '#3b82f6', range: { h: [200, 225], s: [0.7, 1], l: [0.5, 0.7] }, tags: ['科技', '创新', '未来'] },
  { name: '深邃蓝', hex: '#1e3a8a', range: { h: [210, 230], s: [0.6, 1], l: [0.2, 0.4] }, tags: ['稳重', '高端', '权威'] },
  { name: '天空蓝', hex: '#60a5fa', range: { h: [200, 220], s: [0.5, 0.9], l: [0.6, 0.8] }, tags: ['开阔', '自由', '清新'] },
  { name: '活力橙', hex: '#f97316', range: { h: [20, 40], s: [0.8, 1], l: [0.4, 0.6] }, tags: ['活力', '热情', '创意'] },
  { name: '暖阳橙', hex: '#fb923c', range: { h: [25, 45], s: [0.7, 1], l: [0.5, 0.7] }, tags: ['温暖', '亲切', '友好'] },
  { name: '警示红', hex: '#ef4444', range: { h: [0, 15], s: [0.7, 1], l: [0.4, 0.6] }, tags: ['警示', '紧急', '热情'] },
  { name: '中国红', hex: '#dc2626', range: { h: [0, 10], s: [0.7, 1], l: [0.3, 0.5] }, tags: ['喜庆', '传统', '力量'] },
  { name: '玫红色', hex: '#ec4899', range: { h: [320, 350], s: [0.7, 1], l: [0.4, 0.6] }, tags: ['时尚', '优雅', '浪漫'] },
  { name: '活力绿', hex: '#22c55e', range: { h: [120, 150], s: [0.6, 1], l: [0.4, 0.6] }, tags: ['活力', '成长', '健康'] },
  { name: '自然绿', hex: '#16a34a', range: { h: [120, 145], s: [0.5, 0.9], l: [0.3, 0.5] }, tags: ['自然', '环保', '安全'] },
  { name: '薄荷绿', hex: '#4ade80', range: { h: [130, 160], s: [0.5, 0.8], l: [0.5, 0.7] }, tags: ['清新', '健康', '舒缓'] },
  { name: '典雅紫', hex: '#8b5cf6', range: { h: [250, 280], s: [0.6, 1], l: [0.5, 0.7] }, tags: ['典雅', '神秘', '创意'] },
  { name: '高贵紫', hex: '#7c3aed', range: { h: [250, 280], s: [0.6, 1], l: [0.4, 0.6] }, tags: ['高贵', '奢华', '神秘'] },
  { name: '明黄色', hex: '#eab308', range: { h: [40, 60], s: [0.7, 1], l: [0.4, 0.6] }, tags: ['明亮', '快乐', '智慧'] },
  { name: '金秋黄', hex: '#ca8a04', range: { h: [35, 55], s: [0.6, 0.9], l: [0.3, 0.5] }, tags: ['丰收', '温暖', '品质'] },
  { name: '柠檬黄', hex: '#facc15', range: { h: [45, 65], s: [0.7, 1], l: [0.5, 0.7] }, tags: ['活泼', '年轻', '醒目'] },
  { name: '青绿色', hex: '#14b8a6', range: { h: [170, 190], s: [0.6, 1], l: [0.3, 0.5] }, tags: ['清新', '专业', '冷静'] },
  { name: '水青色', hex: '#2dd4bf', range: { h: [170, 190], s: [0.5, 0.9], l: [0.4, 0.6] }, tags: ['清澈', '透明', '现代'] },
  { name: '玫瑰红', hex: '#f43f5e', range: { h: [340, 360], s: [0.7, 1], l: [0.4, 0.6] }, tags: ['浪漫', '优雅', '温柔'] },
  { name: '珊瑚红', hex: '#f87171', range: { h: [0, 20], s: [0.6, 0.9], l: [0.5, 0.7] }, tags: ['温暖', '亲切', '活力'] },
  { name: '海军蓝', hex: '#1e40af', range: { h: [210, 235], s: [0.7, 1], l: [0.25, 0.45] }, tags: ['专业', '可靠', '稳重'] },
  { name: '靛蓝色', hex: '#4f46e5', range: { h: [230, 250], s: [0.6, 1], l: [0.4, 0.6] }, tags: ['智慧', '专注', '创新'] },
  { name: '深灰色', hex: '#374151', range: { h: [210, 230], s: [0.1, 0.3], l: [0.2, 0.35] }, tags: ['专业', '简约', '现代'] },
  { name: '石墨灰', hex: '#4b5563', range: { h: [210, 225], s: [0.1, 0.25], l: [0.25, 0.45] }, tags: ['稳重', '商务', '低调'] },
  { name: '象牙白', hex: '#f9fafb', range: { h: [0, 60], s: [0, 0.1], l: [0.9, 1] }, tags: ['纯净', '简约', '优雅'] },
  { name: '香槟金', hex: '#fbbf24', range: { h: [35, 55], s: [0.5, 0.9], l: [0.55, 0.75] }, tags: ['奢华', '品质', '尊贵'] },
  { name: '古铜色', hex: '#d97706', range: { h: [25, 45], s: [0.5, 0.8], l: [0.35, 0.55] }, tags: ['复古', '品质', '稳重'] },
  { name: '粉色系', hex: '#f472b6', range: { h: [320, 350], s: [0.5, 0.8], l: [0.6, 0.8] }, tags: ['温柔', '浪漫', '甜美'] },
  { name: '橄榄绿', hex: '#65a30d', range: { h: [70, 90], s: [0.5, 0.8], l: [0.25, 0.45] }, tags: ['自然', '军旅', '朴实'] },
  { name: '天青色', hex: '#0ea5e9', range: { h: [190, 210], s: [0.7, 1], l: [0.4, 0.6] }, tags: ['清新', '文艺', '古典'] },
  { name: '藏青色', hex: '#0369a1', range: { h: [195, 215], s: [0.8, 1], l: [0.25, 0.45] }, tags: ['沉稳', '专业', '传统'] },
]

const COLOR_EMOTION_MAP = {
  red: {
    emotions: ['热情', '活力', '警示', '力量', '爱'],
    scenes: ['促销活动', '紧急通知', '节日庆典', '运动品牌'],
    intensity: 8
  },
  orange: {
    emotions: ['温暖', '友好', '创意', '活力', '快乐'],
    scenes: ['餐饮美食', '儿童产品', '创意设计', '社交平台'],
    intensity: 7
  },
  yellow: {
    emotions: ['阳光', '乐观', '智慧', '年轻', '活力'],
    scenes: ['教育培训', '快餐品牌', '创意产业', '生活方式'],
    intensity: 6
  },
  green: {
    emotions: ['自然', '健康', '安全', '成长', '环保'],
    scenes: ['医疗健康', '环保公益', '有机食品', '金融安全'],
    intensity: 4
  },
  blue: {
    emotions: ['信任', '专业', '稳重', '科技', '冷静'],
    scenes: ['金融科技', '企业官网', '医疗健康', '科技公司'],
    intensity: 3
  },
  purple: {
    emotions: ['高贵', '神秘', '创意', '优雅', '奢华'],
    scenes: ['奢侈品', '美妆护肤', '艺术设计', '娱乐产业'],
    intensity: 5
  },
  pink: {
    emotions: ['温柔', '浪漫', '甜美', '优雅', '亲切'],
    scenes: ['美妆护肤', '婚庆服务', '母婴产品', '时尚品牌'],
    intensity: 4
  },
  brown: {
    emotions: ['稳重', '自然', '品质', '传统', '可靠'],
    scenes: ['咖啡品牌', '传统工艺', '地产建筑', '家具家居'],
    intensity: 2
  },
  gray: {
    emotions: ['专业', '简约', '现代', '中性', '商务'],
    scenes: ['企业品牌', '高端产品', '科技公司', '媒体平台'],
    intensity: 1
  },
  black: {
    emotions: ['高端', '神秘', '力量', '简约', '权威'],
    scenes: ['奢侈品', '高端时尚', '科技产品', '艺术画廊'],
    intensity: 2
  }
}

const BUSINESS_SCENES = [
  { id: 'tech', name: '科技公司', colors: ['blue', 'purple', 'cyan'], description: '专业、创新、未来感' },
  { id: 'finance', name: '金融银行', colors: ['blue', 'green', 'navy'], description: '信任、安全、稳重' },
  { id: 'retail', name: '零售电商', colors: ['red', 'orange', 'pink'], description: '活力、促销、亲和力' },
  { id: 'food', name: '餐饮美食', colors: ['orange', 'red', 'yellow'], description: '美味、温暖、诱人' },
  { id: 'health', name: '医疗健康', colors: ['green', 'blue', 'teal'], description: '健康、安全、专业' },
  { id: 'education', name: '教育培训', colors: ['blue', 'yellow', 'green'], description: '智慧、成长、活力' },
  { id: 'luxury', name: '奢侈品牌', colors: ['purple', 'gold', 'black'], description: '高贵、品质、奢华' },
  { id: 'eco', name: '环保公益', colors: ['green', 'teal', 'brown'], description: '自然、环保、可持续' },
  { id: 'fashion', name: '时尚美妆', colors: ['pink', 'purple', 'red'], description: '美丽、个性、潮流' },
  { id: 'realty', name: '地产生态', colors: ['brown', 'green', 'blue'], description: '稳重、自然、家园' },
  { id: 'media', name: '媒体娱乐', colors: ['purple', 'red', 'orange'], description: '创意、活力、多元' },
  { id: 'sports', name: '运动户外', colors: ['red', 'orange', 'green'], description: '活力、力量、激情' }
]

function getColorFamily(hue) {
  if (hue >= 0 && hue < 15) return 'red'
  if (hue >= 15 && hue < 45) return 'orange'
  if (hue >= 45 && hue < 70) return 'yellow'
  if (hue >= 70 && hue < 150) return 'green'
  if (hue >= 150 && hue < 190) return 'cyan'
  if (hue >= 190 && hue < 250) return 'blue'
  if (hue >= 250 && hue < 310) return 'purple'
  if (hue >= 310 && hue < 350) return 'pink'
  if (hue >= 350 && hue <= 360) return 'red'
  return 'gray'
}

export function getColorName(color) {
  try {
    const c = chroma(color)
    const [h, s, l] = c.hsl()

    if (s < 0.15) {
      if (l > 0.9) return { name: '象牙白', family: 'white', tags: ['纯净', '简约'] }
      if (l > 0.6) return { name: '浅灰色', family: 'gray', tags: ['中性', '柔和'] }
      if (l > 0.4) return { name: '中灰色', family: 'gray', tags: ['商务', '稳重'] }
      if (l > 0.2) return { name: '深灰色', family: 'gray', tags: ['专业', '高端'] }
      return { name: '炭黑色', family: 'black', tags: ['高端', '神秘'] }
    }

    let bestMatch = null
    let bestScore = Infinity

    COLOR_NAME_DATABASE.forEach(entry => {
      const range = entry.range
      if (h >= range.h[0] && h <= range.h[1] &&
          s >= range.s[0] && s <= range.s[1] &&
          l >= range.l[0] && l <= range.l[1]) {
        const refColor = chroma(entry.hex)
        const deltaE = chroma.deltaE(c, refColor)
        if (deltaE < bestScore) {
          bestScore = deltaE
          bestMatch = entry
        }
      }
    })

    if (bestMatch) {
      return {
        name: bestMatch.name,
        family: getColorFamily(h),
        tags: bestMatch.tags
      }
    }

    const family = getColorFamily(h)
    const prefixes = {
      low: '深',
      mid: '标准',
      high: '浅'
    }
    const lightnessPrefix = l < 0.4 ? '深' : l < 0.6 ? '' : '浅'
    const familyNames = {
      red: '红色',
      orange: '橙色',
      yellow: '黄色',
      green: '绿色',
      cyan: '青色',
      blue: '蓝色',
      purple: '紫色',
      pink: '粉色',
      brown: '棕色',
      gray: '灰色'
    }

    return {
      name: lightnessPrefix + (familyNames[family] || '彩色'),
      family,
      tags: ['自定义']
    }
  } catch (e) {
    return { name: '未知色', family: 'unknown', tags: [] }
  }
}

export function getColorEmotion(color) {
  try {
    const c = chroma(color)
    const [h, s, l] = c.hsl()
    const family = getColorFamily(h)
    const emotionData = COLOR_EMOTION_MAP[family] || COLOR_EMOTION_MAP.gray

    const saturationFactor = s
    const lightnessFactor = l > 0.3 && l < 0.7 ? 1 : 0.7
    const intensity = Math.round(emotionData.intensity * saturationFactor * lightnessFactor)

    return {
      ...emotionData,
      family,
      intensity,
      primaryEmotion: emotionData.emotions[0],
      isVibrant: s > 0.6 && l > 0.3 && l < 0.7,
      isLight: l > 0.6,
      isDark: l < 0.4
    }
  } catch (e) {
    return { emotions: [], scenes: [], intensity: 0, family: 'unknown' }
  }
}

export function getSceneRecommendations(sceneId) {
  const scene = BUSINESS_SCENES.find(s => s.id === sceneId)
  if (!scene) return null

  const schemePreferences = {
    tech: ['Blues', 'Purples', 'YlGnBu', 'Set2'],
    finance: ['Blues', 'Greens', 'BuPu', 'Set1'],
    retail: ['Reds', 'OrRd', 'Set1', 'Paired'],
    food: ['OrRd', 'YlOrBr', 'YlOrRd', 'Set2'],
    health: ['Greens', 'BuGn', 'YlGn', 'Paired'],
    education: ['Blues', 'YlOrBr', 'Greens', 'Set3'],
    luxury: ['Purples', 'RdPu', 'Greys', 'Set1'],
    eco: ['Greens', 'YlGn', 'BrBG', 'Set2'],
    fashion: ['RdPu', 'Purples', 'Reds', 'Set1'],
    realty: ['BrBG', 'YlOrBr', 'Greens', 'Set2'],
    media: ['RdBu', 'Spectral', 'Set1', 'Paired'],
    sports: ['Reds', 'Oranges', 'Greens', 'Set1']
  }

  return {
    ...scene,
    preferredSchemes: schemePreferences[sceneId] || [],
    colorFamilies: scene.colors
  }
}

export function extractBrandColors(imageElement, count = 5) {
  return new Promise((resolve, reject) => {
    try {
      const canvas = document.createElement('canvas')
      const ctx = canvas.getContext('2d')
      const img = imageElement

      canvas.width = img.width
      canvas.height = img.height
      ctx.drawImage(img, 0, 0)

      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
      const pixelData = imageData.data

      const colorCounts = {}
      const sampleRate = 10

      for (let i = 0; i < pixelData.length; i += 4 * sampleRate) {
        const r = pixelData[i]
        const g = pixelData[i + 1]
        const b = pixelData[i + 2]
        const a = pixelData[i + 3]

        if (a < 50 || (r > 250 && g > 250 && b > 250)) continue
        if (r < 10 && g < 10 && b < 10) continue

        const colorKey = `${Math.round(r / 20) * 20},${Math.round(g / 20) * 20},${Math.round(b / 20) * 20}`
        colorCounts[colorKey] = (colorCounts[colorKey] || 0) + 1
      }

      const sortedColors = Object.entries(colorCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, count * 3)

      const finalColors = []
      const usedColors = new Set()

      for (const [colorKey] of sortedColors) {
        if (finalColors.length >= count) break
        const [r, g, b] = colorKey.split(',').map(Number)
        const hex = chroma(r, g, b).hex()

        let isSimilar = false
        for (const used of usedColors) {
          if (chroma.deltaE(hex, used) < 15) {
            isSimilar = true
            break
          }
        }

        if (!isSimilar) {
          finalColors.push(hex)
          usedColors.add(hex)
        }
      }

      const primaryColor = finalColors[0]
      const primaryInfo = getColorName(primaryColor)
      const emotionInfo = getColorEmotion(primaryColor)

      resolve({
        colors: finalColors,
        primaryColor,
        primaryName: primaryInfo.name,
        primaryTags: primaryInfo.tags,
        emotions: emotionInfo.emotions,
        suggestedScenes: emotionInfo.scenes,
        luminance: chroma(primaryColor).luminance()
      })
    } catch (error) {
      reject(error)
    }
  })
}

export function generateBrandPalette(primaryColor, count = 6, type = 'professional') {
  const base = chroma(primaryColor)
  const [h, s, l] = base.hsl()

  switch (type) {
    case 'professional':
      return chroma.scale([
        chroma(primaryColor).darken(2),
        chroma(primaryColor).darken(1),
        primaryColor,
        chroma(primaryColor).brighten(1),
        chroma(primaryColor).brighten(2),
        chroma(primaryColor).saturate(-0.5).brighten(1.5)
      ]).mode('lab').colors(count)

    case 'complementary':
      const complement = chroma(primaryColor).set('hsl.h', h + 180)
      return chroma.scale([
        chroma(primaryColor).darken(1.5),
        primaryColor,
        chroma(primaryColor).brighten(1),
        chroma(complement).brighten(1),
        complement,
        chroma(complement).darken(1.5)
      ]).mode('lab').colors(count)

    case 'analogous':
      return chroma.scale([
        chroma(primaryColor).set('hsl.h', h - 30),
        primaryColor,
        chroma(primaryColor).set('hsl.h', h + 30)
      ]).mode('hsl').colors(count)

    case 'gradient':
      return chroma.scale([
        chroma(primaryColor).darken(2).desaturate(0.5),
        primaryColor,
        chroma(primaryColor).brighten(2).desaturate(0.3)
      ]).mode('lab').colors(count)

    default:
      return chroma.scale([
        chroma(primaryColor).darken(1.5),
        primaryColor,
        chroma(primaryColor).brighten(1.5)
      ]).mode('lab').colors(count)
  }
}

export { COLOR_NAME_DATABASE, COLOR_EMOTION_MAP, BUSINESS_SCENES, getColorFamily }

import { ref } from 'vue'
import { AI_PREANNOTATION_CONFIG, ANNOTATION_TYPES, ANNOTATION_CATEGORIES, CONFIDENCE_LEVELS } from '../constants'

class AIPreAnnotator {
  constructor() {
    this.isProcessing = ref(false)
    this.progress = ref(0)
    this.results = ref([])
    this.enabled = ref(AI_PREANNOTATION_CONFIG.ENABLED)
    this.minConfidence = ref(AI_PREANNOTATION_CONFIG.MIN_CONFIDENCE)
    this.autoAcceptThreshold = ref(AI_PREANNOTATION_CONFIG.AUTO_ACCEPT_THRESHOLD)
    this.canvas = document.createElement('canvas')
    this.ctx = this.canvas.getContext('2d')
  }

  async preAnnotate(imageElement, imageInfo) {
    if (!this.enabled.value) return []

    this.isProcessing.value = true
    this.progress.value = 0
    this.results.value = []

    try {
      const detections = await this.detectElements(imageElement, imageInfo)
      
      this.progress.value = 60
      
      const annotations = this.convertToAnnotations(detections, imageInfo)
      
      this.progress.value = 90
      
      const autoAccepted = annotations.filter(
        a => a.confidence >= this.autoAcceptThreshold.value
      )
      
      const needReview = annotations.filter(
        a => a.confidence < this.autoAcceptThreshold.value && 
             a.confidence >= this.minConfidence.value
      )
      
      this.results.value = {
        autoAccepted,
        needReview,
        all: annotations
      }
      
      this.progress.value = 100
      
      return this.results.value
    } catch (error) {
      console.error('AI pre-annotation error:', error)
      throw error
    } finally {
      setTimeout(() => {
        this.isProcessing.value = false
      }, 300)
    }
  }

  async detectElements(imageElement, imageInfo) {
    const { width, height } = imageInfo
    
    this.canvas.width = width
    this.canvas.height = height
    this.ctx.drawImage(imageElement, 0, 0, width, height)
    
    const imageData = this.ctx.getImageData(0, 0, width, height)
    const detections = []

    detections.push(...this.detectTitle(imageData, width, height))
    
    detections.push(...this.detectAxisLabels(imageData, width, height))
    
    detections.push(...this.detectLegend(imageData, width, height))
    
    detections.push(...this.detectDataRegion(imageData, width, height))

    return detections.sort((a, b) => b.confidence - a.confidence)
  }

  detectTitle(imageData, width, height) {
    const detections = []
    const titleHeight = Math.min(height * 0.15, 100)
    
    const textRegion = this.analyzeTextRegion(
      imageData, 0, 0, width, titleHeight
    )

    if (textRegion.hasText) {
      const confidence = 0.75 + textRegion.density * 0.2
      
      detections.push({
        type: 'title',
        bbox: {
          x: textRegion.bbox.x,
          y: textRegion.bbox.y,
          width: textRegion.bbox.width,
          height: textRegion.bbox.height
        },
        confidence: Math.min(0.95, confidence),
        label: this.guessTitle(textRegion)
      })
    }

    return detections
  }

  detectAxisLabels(imageData, width, height) {
    const detections = []
    
    const bottomRegion = this.analyzeTextRegion(
      imageData, 0, height * 0.85, width, height * 0.15
    )
    if (bottomRegion.hasText) {
      detections.push({
        type: 'axis_label',
        bbox: {
          x: bottomRegion.bbox.x || width * 0.1,
          y: bottomRegion.bbox.y || height * 0.88,
          width: bottomRegion.bbox.width || width * 0.8,
          height: bottomRegion.bbox.height || 30
        },
        confidence: 0.72,
        label: 'X轴标签',
        subType: 'x-axis'
      })
    }

    const leftRegion = this.analyzeTextRegion(
      imageData, 0, 0, width * 0.15, height
    )
    if (leftRegion.hasText) {
      detections.push({
        type: 'axis_label',
        bbox: {
          x: leftRegion.bbox.x || 10,
          y: leftRegion.bbox.y || height * 0.3,
          width: leftRegion.bbox.width || 40,
          height: leftRegion.bbox.height || height * 0.4
        },
        confidence: 0.68,
        label: 'Y轴标签',
        subType: 'y-axis'
      })
    }

    return detections
  }

  detectLegend(imageData, width, height) {
    const detections = []
    
    const searchAreas = [
      { x: width * 0.7, y: height * 0.05, w: width * 0.25, h: height * 0.3 },
      { x: width * 0.05, y: height * 0.05, w: width * 0.2, h: height * 0.3 },
      { x: width * 0.7, y: height * 0.6, w: width * 0.25, h: height * 0.35 }
    ]

    for (const area of searchAreas) {
      const legendRegion = this.analyzeLegendRegion(
        imageData, area.x, area.y, area.w, area.h
      )
      
      if (legendRegion.hasLegend) {
        detections.push({
          type: 'legend',
          bbox: {
            x: legendRegion.bbox.x,
            y: legendRegion.bbox.y,
            width: legendRegion.bbox.width,
            height: legendRegion.bbox.height
          },
          confidence: legendRegion.confidence,
          label: '图例',
          items: legendRegion.items || []
        })
        break
      }
    }

    return detections
  }

  detectDataRegion(imageData, width, height) {
    const detections = []
    
    const dataArea = this.findDataPlotArea(imageData, width, height)
    
    if (dataArea.hasData) {
      detections.push({
        type: 'data_region',
        bbox: {
          x: dataArea.bbox.x,
          y: dataArea.bbox.y,
          width: dataArea.bbox.width,
          height: dataArea.bbox.height
        },
        confidence: dataArea.confidence,
        label: '数据区域',
        chartType: dataArea.chartType
      })
    }

    return detections
  }

  analyzeTextRegion(imageData, x, y, w, h) {
    const data = imageData.data
    const startX = Math.max(0, Math.floor(x))
    const startY = Math.max(0, Math.floor(y))
    const endX = Math.min(imageData.width, Math.floor(x + w))
    const endY = Math.min(imageData.height, Math.floor(y + h))
    
    let edgePixels = 0
    let totalPixels = 0
    let minX = endX, maxX = startX, minY = endY, maxY = startY
    
    for (let py = startY; py < endY; py += 2) {
      for (let px = startX; px < endX; px += 2) {
        const idx = (py * imageData.width + px) * 4
        const gray = (data[idx] + data[idx + 1] + data[idx + 2]) / 3
        
        let hasEdge = false
        if (px > startX) {
          const leftIdx = (py * imageData.width + px - 2) * 4
          const leftGray = (data[leftIdx] + data[leftIdx + 1] + data[leftIdx + 2]) / 3
          if (Math.abs(gray - leftGray) > 30) hasEdge = true
        }
        if (py > startY) {
          const topIdx = ((py - 2) * imageData.width + px) * 4
          const topGray = (data[topIdx] + data[topIdx + 1] + data[topIdx + 2]) / 3
          if (Math.abs(gray - topGray) > 30) hasEdge = true
        }
        
        if (hasEdge) {
          edgePixels++
          minX = Math.min(minX, px)
          maxX = Math.max(maxX, px)
          minY = Math.min(minY, py)
          maxY = Math.max(maxY, py)
        }
        totalPixels++
      }
    }
    
    const density = edgePixels / totalPixels
    const hasText = density > 0.05 && density < 0.5
    
    return {
      hasText,
      density,
      bbox: hasText ? {
        x: minX,
        y: minY,
        width: Math.max(50, maxX - minX),
        height: Math.max(20, maxY - minY)
      } : null
    }
  }

  analyzeLegendRegion(imageData, x, y, w, h) {
    const data = imageData.data
    const startX = Math.max(0, Math.floor(x))
    const startY = Math.max(0, Math.floor(y))
    const endX = Math.min(imageData.width, Math.floor(x + w))
    const endY = Math.min(imageData.height, Math.floor(y + h))
    
    const colorClusters = new Map()
    let textPixels = 0
    let totalPixels = 0
    
    for (let py = startY; py < endY; py += 3) {
      for (let px = startX; px < endX; px += 3) {
        const idx = (py * imageData.width + px) * 4
        const r = data[idx], g = data[idx + 1], b = data[idx + 2]
        const a = data[idx + 3]
        
        if (a < 128) continue
        
        const colorKey = `${Math.floor(r / 32)},${Math.floor(g / 32)},${Math.floor(b / 32)}`
        colorClusters.set(colorKey, (colorClusters.get(colorKey) || 0) + 1)
        
        const gray = (r + g + b) / 3
        if (gray < 80) textPixels++
        totalPixels++
      }
    }
    
    const dominantColors = Array.from(colorClusters.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8)
    
    const hasMultipleColors = dominantColors.length >= 3
    const hasText = textPixels / totalPixels > 0.08
    const hasLegend = hasMultipleColors && hasText
    
    let confidence = 0
    if (hasLegend) {
      confidence = 0.5
      if (dominantColors.length >= 4) confidence += 0.15
      if (textPixels / totalPixels > 0.15) confidence += 0.1
    }
    
    const items = dominantColors.slice(1, 6).map(([color, count]) => ({
      color,
      count,
      label: `系列 ${dominantColors.indexOf([color, count])}`
    }))

    return {
      hasLegend,
      confidence,
      items,
      bbox: {
        x: startX + 10,
        y: startY + 10,
        width: endX - startX - 20,
        height: endY - startY - 20
      }
    }
  }

  findDataPlotArea(imageData, width, height) {
    const data = imageData.data
    
    const margin = {
      left: width * 0.12,
      right: width * 0.1,
      top: height * 0.18,
      bottom: height * 0.18
    }
    
    const plotX = margin.left
    const plotY = margin.top
    const plotW = width - margin.left - margin.right
    const plotH = height - margin.top - margin.bottom
    
    let dataPoints = 0
    let gridLines = 0
    let totalPixels = 0
    
    let minX = plotX + plotW, maxX = plotX
    let minY = plotY + plotH, maxY = plotY
    
    for (let py = plotY; py < plotY + plotH; py += 2) {
      for (let px = plotX; px < plotX + plotW; px += 2) {
        const idx = (py * imageData.width + px) * 4
        const r = data[idx], g = data[idx + 1], b = data[idx + 2]
        
        const gray = (r + g + b) / 3
        
        let isLine = false
        const neighbors = [[-2, 0], [2, 0], [0, -2], [0, 2]]
        for (const [dx, dy] of neighbors) {
          const nx = px + dx, ny = py + dy
          if (nx >= plotX && nx < plotX + plotW && ny >= plotY && ny < plotY + plotH) {
            const nidx = (ny * imageData.width + nx) * 4
            const ngray = (data[nidx] + data[nidx + 1] + data[nidx + 2]) / 3
            if (Math.abs(gray - ngray) > 40) {
              isLine = true
              break
            }
          }
        }
        
        if (isLine) {
          dataPoints++
          minX = Math.min(minX, px)
          maxX = Math.max(maxX, px)
          minY = Math.min(minY, py)
          maxY = Math.max(maxY, py)
        }
        
        if (Math.abs(gray - 220) < 20) {
          gridLines++
        }
        
        totalPixels++
      }
    }
    
    const dataDensity = dataPoints / totalPixels
    const hasData = dataDensity > 0.02
    
    let chartType = 'unknown'
    if (hasData) {
      const horizontalLines = this.detectHorizontalLines(data, plotX, plotY, plotW, plotH, imageData.width)
      const verticalLines = this.detectVerticalLines(data, plotX, plotY, plotW, plotH, imageData.width)
      
      if (horizontalLines > verticalLines * 2) {
        chartType = 'bar'
      } else if (Math.abs(horizontalLines - verticalLines) < 10) {
        chartType = 'line'
      } else {
        chartType = 'other'
      }
    }
    
    let confidence = 0.5
    if (hasData) {
      confidence = 0.6
      if (dataDensity > 0.05) confidence += 0.15
      if (gridLines > 10) confidence += 0.1
    }

    return {
      hasData,
      confidence,
      chartType,
      bbox: {
        x: Math.max(plotX, minX - 10),
        y: Math.max(plotY, minY - 10),
        width: Math.min(plotW, maxX - minX + 20),
        height: Math.min(plotH, maxY - minY + 20)
      }
    }
  }

  detectHorizontalLines(data, x, y, w, h, imgWidth) {
    let count = 0
    for (let py = y; py < y + h; py += 4) {
      let linePixels = 0
      for (let px = x; px < x + w; px += 4) {
        const idx = (py * imgWidth + px) * 4
        const gray = (data[idx] + data[idx + 1] + data[idx + 2]) / 3
        if (gray < 100) linePixels++
      }
      if (linePixels / (w / 4) > 0.6) count++
    }
    return count
  }

  detectVerticalLines(data, x, y, w, h, imgWidth) {
    let count = 0
    for (let px = x; px < x + w; px += 4) {
      let linePixels = 0
      for (let py = y; py < y + h; py += 4) {
        const idx = (py * imgWidth + px) * 4
        const gray = (data[idx] + data[idx + 1] + data[idx + 2]) / 3
        if (gray < 100) linePixels++
      }
      if (linePixels / (h / 4) > 0.4) count++
    }
    return count
  }

  guessTitle(textRegion) {
    const commonTitles = [
      '销售统计', '数据分析', '趋势图', '对比图',
      '年度报告', '月度数据', '季度分析'
    ]
    return commonTitles[Math.floor(Math.random() * commonTitles.length)]
  }

  convertToAnnotations(detections, imageInfo) {
    return detections.map((det, index) => {
      const category = ANNOTATION_CATEGORIES.find(c => c.id === det.type)
      return {
        id: `ai_${Date.now()}_${index}`,
        type: ANNOTATION_TYPES.RECTANGLE,
        category: det.type,
        label: det.label,
        confidence: det.confidence,
        isAI: true,
        status: det.confidence >= this.autoAcceptThreshold.value ? 'auto_accepted' : 'pending_review',
        aiMeta: {
          chartType: det.chartType,
          subType: det.subType,
          items: det.items
        },
        imageCoords: {
          x: det.bbox.x,
          y: det.bbox.y,
          width: det.bbox.width,
          height: det.bbox.height
        },
        canvasCoords: {
          left: imageInfo.offsetX + det.bbox.x * imageInfo.scale,
          top: imageInfo.offsetY + det.bbox.y * imageInfo.scale,
          width: det.bbox.width * imageInfo.scale,
          height: det.bbox.height * imageInfo.scale
        },
        color: category ? category.color : '#409eff',
        createdAt: Date.now(),
        updatedAt: Date.now()
      }
    }).filter(a => 
      a.confidence >= this.minConfidence.value &&
      a.imageCoords.width > 20 &&
      a.imageCoords.height > 20
    ).slice(0, AI_PREANNOTATION_CONFIG.MAX_DETECTIONS)
  }

  getConfidenceLevel(confidence) {
    if (confidence >= CONFIDENCE_LEVELS.HIGH.min) return CONFIDENCE_LEVELS.HIGH
    if (confidence >= CONFIDENCE_LEVELS.MEDIUM.min) return CONFIDENCE_LEVELS.MEDIUM
    return CONFIDENCE_LEVELS.LOW
  }

  setMinConfidence(value) {
    this.minConfidence.value = Math.max(0, Math.min(1, value))
  }

  setAutoAcceptThreshold(value) {
    this.autoAcceptThreshold.value = Math.max(0, Math.min(1, value))
  }

  setEnabled(value) {
    this.enabled.value = value
  }
}

const aiPreAnnotator = new AIPreAnnotator()
export default aiPreAnnotator

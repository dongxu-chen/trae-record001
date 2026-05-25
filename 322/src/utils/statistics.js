import { ref, computed } from 'vue'
import { ANNOTATION_CATEGORIES, KAPPA_THRESHOLDS, ANNOTATION_STATUS, ANNOTATION_TYPES } from '../constants'

class AnnotationStatistics {
  constructor() {
    this.annotations = ref([])
    this.images = ref([])
    this.totalTargets = ref(100)
  }

  setData(annotations, images = [], totalTargets = null) {
    this.annotations.value = annotations
    this.images.value = images
    if (totalTargets) this.totalTargets.value = totalTargets
  }

  get overview() {
    return computed(() => {
      const anns = this.annotations.value
      const total = anns.length
      
      const byCategory = {}
      const byType = {}
      const byStatus = {
        auto_accepted: 0,
        pending_review: 0,
        manual: 0
      }
      const byConfidence = { high: 0, medium: 0, low: 0 }
      const aiGenerated = anns.filter(a => a.isAI).length
      
      let avgConfidence = 0
      let aiAnnotations = 0
      
      anns.forEach(ann => {
        byCategory[ann.category] = (byCategory[ann.category] || 0) + 1
        byType[ann.type] = (byType[ann.type] || 0) + 1
        
        if (ann.isAI) {
          aiAnnotations++
          avgConfidence += ann.confidence || 0
          if (ann.status === 'auto_accepted') byStatus.auto_accepted++
          if (ann.status === 'pending_review') byStatus.pending_review++
          
          if (ann.confidence >= 0.8) byConfidence.high++
          else if (ann.confidence >= 0.6) byConfidence.medium++
          else byConfidence.low++
        } else {
          byStatus.manual++
        }
      })
      
      if (aiAnnotations > 0) {
        avgConfidence /= aiAnnotations
      }
      
      const progress = Math.min(100, (total / this.totalTargets.value) * 100)
      
      return {
        total,
        byCategory,
        byType,
        byStatus,
        byConfidence,
        aiGenerated,
        manual: total - aiGenerated,
        avgConfidence,
        progress,
        totalTargets: this.totalTargets.value
      }
    })
  }

  get categoryStats() {
    return computed(() => {
      const anns = this.annotations.value
      
      return ANNOTATION_CATEGORIES.map(cat => {
        const categoryAnns = anns.filter(a => a.category === cat.id)
        const total = categoryAnns.length
        const aiCount = categoryAnns.filter(a => a.isAI).length
        const manualCount = total - aiCount
        
        return {
          ...cat,
          count: total,
          aiCount,
          manualCount,
          percentage: anns.length > 0 ? (total / anns.length * 100).toFixed(1) : 0,
          avgConfidence: aiCount > 0 
            ? categoryAnns.filter(a => a.isAI).reduce((sum, a) => sum + (a.confidence || 0), 0) / aiCount
            : 0
        }
      })
    })
  }

  get typeStats() {
    return computed(() => {
      const anns = this.annotations.value
      
      return [
        { type: ANNOTATION_TYPES.RECTANGLE, name: '矩形框', color: '#409eff' },
        { type: ANNOTATION_TYPES.ARROW, name: '箭头', color: '#67c23a' },
        { type: ANNOTATION_TYPES.TEXT, name: '文本', color: '#e6a23c' }
      ].map(t => {
        const count = anns.filter(a => a.type === t.type).length
        return {
          ...t,
          count,
          percentage: anns.length > 0 ? (count / anns.length * 100).toFixed(1) : 0
        }
      })
    })
  }

  get imageStats() {
    return computed(() => {
      const images = this.images.value
      const anns = this.annotations.value
      
      return images.map(img => {
        const imgAnns = anns.filter(a => a.imageId === img.id)
        const status = imgAnns.length === 0 
          ? ANNOTATION_STATUS.NOT_STARTED
          : imgAnns.length >= 4
            ? ANNOTATION_STATUS.COMPLETED
            : ANNOTATION_STATUS.IN_PROGRESS
        
        return {
          ...img,
          annotationCount: imgAnns.length,
          status,
          hasAI: imgAnns.some(a => a.isAI),
          categories: [...new Set(imgAnns.map(a => a.category))]
        }
      })
    })
  }

  get progressData() {
    return computed(() => {
      const total = this.totalTargets.value
      const completed = this.annotations.value.length
      const remaining = Math.max(0, total - completed)
      const percentage = Math.min(100, (completed / total) * 100)
      
      let status = ANNOTATION_STATUS.NOT_STARTED
      if (percentage >= 100) status = ANNOTATION_STATUS.COMPLETED
      else if (percentage >= 50) status = ANNOTATION_STATUS.IN_PROGRESS
      else if (percentage > 0) status = ANNOTATION_STATUS.IN_PROGRESS
      
      return {
        total,
        completed,
        remaining,
        percentage: percentage.toFixed(1),
        status
      }
    })
  }

  calculateCohenKappa(annotator1Anns, annotator2Anns, categoryId = null) {
    if (annotator1Anns.length === 0 || annotator2Anns.length === 0) {
      return { kappa: 0, level: 'none', agreement: 0 }
    }

    const anns1 = categoryId 
      ? annotator1Anns.filter(a => a.category === categoryId)
      : annotator1Anns
    const anns2 = categoryId
      ? annotator2Anns.filter(a => a.category === categoryId)
      : annotator2Anns

    const matched = this.findMatchingAnnotations(anns1, anns2)
    const n = anns1.length + anns2.length - matched.length
    
    if (n === 0) return { kappa: 1, level: 'perfect', agreement: 100 }

    let observedAgreement = 0
    const categoryCounts1 = {}
    const categoryCounts2 = {}

    matched.forEach(match => {
      if (match.ann1.category === match.ann2.category) {
        observedAgreement++
      }
      categoryCounts1[match.ann1.category] = (categoryCounts1[match.ann1.category] || 0) + 1
      categoryCounts2[match.ann2.category] = (categoryCounts2[match.ann2.category] || 0) + 1
    })

    const po = observedAgreement / matched.length

    let pe = 0
    Object.keys(categoryCounts1).forEach(cat => {
      const p1 = (categoryCounts1[cat] || 0) / matched.length
      const p2 = (categoryCounts2[cat] || 0) / matched.length
      pe += p1 * p2
    })

    const kappa = pe === 1 ? 1 : (po - pe) / (1 - pe)

    return {
      kappa: Math.max(-1, Math.min(1, kappa)),
      level: this.getKappaLevel(kappa),
      agreement: (po * 100).toFixed(1),
      observedAgreement: po,
      chanceAgreement: pe,
      matchedCount: matched.length,
      totalCount: n
    }
  }

  calculateFleissKappa(annotatorsAnnotations, categoryId = null) {
    if (annotatorsAnnotations.length < 2) {
      return { kappa: 0, level: 'none' }
    }

    const annsByAnnotator = categoryId
      ? annotatorsAnnotations.map(anns => anns.filter(a => a.category === categoryId))
      : annotatorsAnnotations

    const allAnnotations = annsByAnnotator.flat()
    const imageIds = [...new Set(allAnnotations.map(a => a.imageId))]
    
    let totalKappa = 0
    let validImages = 0

    imageIds.forEach(imageId => {
      const imageAnns = allAnnotations.filter(a => a.imageId === imageId)
      if (imageAnns.length < 2) return

      const categories = ANNOTATION_CATEGORIES.map(c => c.id)
      const n = annsByAnnotator.length
      const k = categories.length
      
      const nij = categories.map(cat => 
        imageAnns.filter(a => a.category === cat).length
      )
      
      const pi = nij.map(count => count / (n * imageIds.length))
      const pj = nij.map(count => count / n)
      
      let Pmean = 0
      pj.forEach(p => Pmean += (p * (p * n - 1)) / (n - 1))
      Pmean /= imageIds.length
      
      let Pe = 0
      pi.forEach(p => Pe += p * p)
      
      if (Pe !== 1) {
        const kappa = (Pmean - Pe) / (1 - Pe)
        totalKappa += kappa
        validImages++
      }
    })

    const avgKappa = validImages > 0 ? totalKappa / validImages : 0

    return {
      kappa: Math.max(-1, Math.min(1, avgKappa)),
      level: this.getKappaLevel(avgKappa),
      annotatorCount: annotatorsAnnotations.length,
      imageCount: validImages
    }
  }

  findMatchingAnnotations(anns1, anns2, iouThreshold = 0.5) {
    const matches = []
    const used2 = new Set()

    anns1.forEach(ann1 => {
      let bestMatch = null
      let bestIou = 0

      anns2.forEach((ann2, idx) => {
        if (used2.has(idx)) return
        
        const iou = this.calculateIoU(ann1, ann2)
        if (iou > iouThreshold && iou > bestIou) {
          bestIou = iou
          bestMatch = { ann1, ann2, iou, idx }
        }
      })

      if (bestMatch) {
        used2.add(bestMatch.idx)
        matches.push(bestMatch)
      }
    })

    return matches
  }

  calculateIoU(ann1, ann2) {
    const bbox1 = ann1.imageCoords || ann1.canvasCoords
    const bbox2 = ann2.imageCoords || ann2.canvasCoords
    
    if (!bbox1 || !bbox2) return 0

    const x1 = Math.max(bbox1.x || bbox1.left, bbox2.x || bbox2.left)
    const y1 = Math.max(bbox1.y || bbox1.top, bbox2.y || bbox2.top)
    const x2 = Math.min(
      (bbox1.x || bbox1.left) + (bbox1.width || 0),
      (bbox2.x || bbox2.left) + (bbox2.width || 0)
    )
    const y2 = Math.min(
      (bbox1.y || bbox1.top) + (bbox1.height || 0),
      (bbox2.y || bbox2.top) + (bbox2.height || 0)
    )

    const intersection = Math.max(0, x2 - x1) * Math.max(0, y2 - y1)
    const area1 = (bbox1.width || 0) * (bbox1.height || 0)
    const area2 = (bbox2.width || 0) * (bbox2.height || 0)
    const union = area1 + area2 - intersection

    return union > 0 ? intersection / union : 0
  }

  getKappaLevel(kappa) {
    if (kappa >= KAPPA_THRESHOLDS.PERFECT) return { id: 'perfect', label: '几乎完美', color: '#67c23a' }
    if (kappa >= KAPPA_THRESHOLDS.SUBSTANTIAL) return { id: 'substantial', label: '高度一致', color: '#409eff' }
    if (kappa >= KAPPA_THRESHOLDS.MODERATE) return { id: 'moderate', label: '中等一致', color: '#909399' }
    if (kappa >= KAPPA_THRESHOLDS.FAIR) return { id: 'fair', label: '一般一致', color: '#e6a23c' }
    if (kappa >= KAPPA_THRESHOLDS.SLIGHT) return { id: 'slight', label: '轻微一致', color: '#f56c6c' }
    return { id: 'none', label: '不一致', color: '#f56c6c' }
  }

  getConsistencyReport(annotationsByUser) {
    const categories = ANNOTATION_CATEGORIES.map(c => c.id)
    
    const categoryKappas = categories.map(cat => {
      const anns1 = annotationsByUser[0]?.filter(a => a.category === cat) || []
      const anns2 = annotationsByUser[1]?.filter(a => a.category === cat) || []
      const result = this.calculateCohenKappa(anns1, anns2, cat)
      return {
        category: cat,
        ...result
      }
    })

    const overall = this.calculateCohenKappa(
      annotationsByUser[0] || [],
      annotationsByUser[1] || []
    )

    const issues = categoryKappas
      .filter(k => k.kappa < KAPPA_THRESHOLDS.MODERATE)
      .map(k => ({
        category: k.category,
        kappa: k.kappa,
        level: k.level,
        suggestion: this.getConsistencySuggestion(k)
      }))

    return {
      overall,
      byCategory: categoryKappas,
      issues,
      suggestions: this.generateImprovementSuggestions(overall, issues)
    }
  }

  getConsistencySuggestion(kappaResult) {
    const { category, kappa } = kappaResult
    const catInfo = ANNOTATION_CATEGORIES.find(c => c.id === category)
    
    if (kappa < KAPPA_THRESHOLDS.SLIGHT) {
      return `建议重新讨论"${catInfo?.name || category}"的定义和标注范围`
    }
    if (kappa < KAPPA_THRESHOLDS.MODERATE) {
      return `建议提供更多"${catInfo?.name || category}"的标注示例`
    }
    if (kappa < KAPPA_THRESHOLDS.SUBSTANTIAL) {
      return `"${catInfo?.name || category}"一致性较好，可继续优化`
    }
    return `"${catInfo?.name || category}"一致性优秀`
  }

  generateImprovementSuggestions(overall, issues) {
    const suggestions = []
    
    if (overall.kappa < KAPPA_THRESHOLDS.MODERATE) {
      suggestions.push({
        priority: 'high',
        type: 'training',
        message: '整体一致性较低，建议组织标注培训会议'
      })
    }
    
    if (issues.length > 0) {
      suggestions.push({
        priority: 'medium',
        type: 'category',
        message: `有 ${issues.length} 个分类一致性需要关注`
      })
    }
    
    const lowConfidence = this.annotations.value.filter(a => a.isAI && (a.confidence || 0) < 0.7).length
    if (lowConfidence > 0) {
      suggestions.push({
        priority: 'low',
        type: 'review',
        message: `有 ${lowConfidence} 个AI标注置信度较低，建议人工审核`
      })
    }
    
    return suggestions
  }

  getTimeSeriesData(days = 7) {
    const anns = this.annotations.value
    const now = Date.now()
    const dayMs = 24 * 60 * 60 * 1000
    
    const data = []
    for (let i = days - 1; i >= 0; i--) {
      const dayStart = now - i * dayMs
      const dayEnd = dayStart + dayMs
      
      const dayAnns = anns.filter(a => a.createdAt >= dayStart && a.createdAt < dayEnd)
      const aiCount = dayAnns.filter(a => a.isAI).length
      
      data.push({
        date: new Date(dayStart).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }),
        total: dayAnns.length,
        ai: aiCount,
        manual: dayAnns.length - aiCount
      })
    }
    
    return data
  }
}

const statistics = new AnnotationStatistics()
export default statistics

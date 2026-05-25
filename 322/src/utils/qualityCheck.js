import { QUALITY_CHECK_RULES, ANNOTATION_TYPES, ANNOTATION_CATEGORIES } from '../constants'

export const checkAnnotationQuality = (annotations, imageInfo = null) => {
  const issues = []
  const warnings = []
  const passed = []
  let totalScore = 100

  if (annotations.length === 0) {
    return {
      score: 0,
      level: 'error',
      issues: [{ id: 'no_annotations', type: 'error', message: '没有任何标注' }],
      warnings: [],
      passed: [],
      details: createQualityDetails(0, [], [], []),
      reasonableness: null
    }
  }

  const rectAnnotations = annotations.filter(a => a.type === ANNOTATION_TYPES.RECTANGLE)
  
  let reasonablenessChecks = []
  if (imageInfo) {
    reasonablenessChecks = checkReasonableness(annotations, imageInfo)
    reasonablenessChecks.forEach(check => {
      if (check.type === 'error') {
        issues.push(check)
        totalScore -= check.penalty || 8
      } else if (check.type === 'warning') {
        warnings.push(check)
        totalScore -= check.penalty || 4
      } else {
        passed.push(check)
      }
    })
  }

  if (rectAnnotations.length < QUALITY_CHECK_RULES.MIN_ANNOTATIONS) {
    const scorePenalty = (QUALITY_CHECK_RULES.MIN_ANNOTATIONS - rectAnnotations.length) * 15
    totalScore -= scorePenalty
    issues.push({
      id: 'min_annotations',
      type: 'error',
      message: `矩形标注数量不足，当前 ${rectAnnotations.length} 个，至少需要 ${QUALITY_CHECK_RULES.MIN_ANNOTATIONS} 个`,
      current: rectAnnotations.length,
      required: QUALITY_CHECK_RULES.MIN_ANNOTATIONS
    })
  } else {
    passed.push({
      id: 'min_annotations',
      message: `矩形标注数量符合要求 (${rectAnnotations.length} 个)`
    })
  }

  const categoryCounts = {}
  annotations.forEach(ann => {
    categoryCounts[ann.category] = (categoryCounts[ann.category] || 0) + 1
  })

  const missingCategories = []
  QUALITY_CHECK_RULES.REQUIRED_CATEGORIES.forEach(catId => {
    if (!categoryCounts[catId]) {
      const catInfo = ANNOTATION_CATEGORIES.find(c => c.id === catId)
      missingCategories.push(catInfo?.name || catId)
      totalScore -= 15
    }
  })

  if (missingCategories.length > 0) {
    issues.push({
      id: 'missing_categories',
      type: 'error',
      message: `缺少必需的分类标注: ${missingCategories.join(', ')}`,
      missing: missingCategories
    })
  } else {
    passed.push({
      id: 'required_categories',
      message: '所有必需分类都已标注'
    })
  }

  const smallAnnotations = []
  rectAnnotations.forEach(ann => {
    if (ann.imageCoords) {
      const { width, height } = ann.imageCoords
      if (width < QUALITY_CHECK_RULES.MIN_SIZE || height < QUALITY_CHECK_RULES.MIN_SIZE) {
        smallAnnotations.push({
          id: ann.id,
          width,
          height,
          label: ann.label || '未命名'
        })
        totalScore -= 5
      }
    }
  })

  if (smallAnnotations.length > 0) {
    warnings.push({
      id: 'small_annotations',
      type: 'warning',
      message: `${smallAnnotations.length} 个标注尺寸过小（小于 ${QUALITY_CHECK_RULES.MIN_SIZE}px）`,
      annotations: smallAnnotations
    })
  } else {
    passed.push({
      id: 'annotation_size',
      message: '所有标注尺寸符合要求'
    })
  }

  const overlaps = findOverlaps(rectAnnotations)
  if (overlaps.length > 0) {
    totalScore -= overlaps.length * 5
    warnings.push({
      id: 'overlapping_annotations',
      type: 'warning',
      message: `检测到 ${overlaps.length} 处标注重叠`,
      overlaps: overlaps
    })
  } else {
    passed.push({
      id: 'no_overlaps',
      message: '没有检测到标注重叠'
    })
  }

  const emptyLabels = annotations.filter(a => !a.label || a.label.trim() === '')
  if (emptyLabels.length > 0) {
    totalScore -= emptyLabels.length * 3
    warnings.push({
      id: 'empty_labels',
      type: 'warning',
      message: `${emptyLabels.length} 个标注缺少标签说明`,
      count: emptyLabels.length
    })
  } else {
    passed.push({
      id: 'all_labeled',
      message: '所有标注都添加了标签'
    })
  }

  const typeStats = {
    rectangle: rectAnnotations.length,
    arrow: annotations.filter(a => a.type === ANNOTATION_TYPES.ARROW).length,
    text: annotations.filter(a => a.type === ANNOTATION_TYPES.TEXT).length
  }

  if (typeStats.arrow === 0 && typeStats.text === 0) {
    warnings.push({
      id: 'no_arrows_or_text',
      type: 'warning',
      message: '建议添加箭头或文本注释来增强标注说明'
    })
  }

  if (imageInfo) {
    const coverage = calculateCoverage(rectAnnotations, imageInfo)
    if (coverage > 0.8) {
      warnings.push({
        id: 'high_coverage',
        type: 'warning',
        message: `标注覆盖率过高 (${(coverage * 100).toFixed(1)}%)，可能存在过度标注`
      })
    } else if (coverage < 0.1 && rectAnnotations.length > 0) {
      warnings.push({
        id: 'low_coverage',
        type: 'warning',
        message: `标注覆盖率较低 (${(coverage * 100).toFixed(1)}%)，可能存在遗漏`
      })
    } else {
      passed.push({
        id: 'coverage_ok',
        message: `标注覆盖率适中 (${(coverage * 100).toFixed(1)}%)`
      })
    }
  }

  totalScore = Math.max(0, Math.min(100, totalScore))

  let level = 'excellent'
  if (totalScore < 60) level = 'poor'
  else if (totalScore < 80) level = 'fair'
  else if (totalScore < 90) level = 'good'

  return {
    score: totalScore,
    level,
    issues,
    warnings,
    passed,
    details: createQualityDetails(totalScore, issues, warnings, passed),
    reasonableness: reasonablenessChecks,
    stats: {
      total: annotations.length,
      byType: typeStats,
      byCategory: categoryCounts
    }
  }
}

const findOverlaps = (annotations) => {
  const overlaps = []
  const overlapThreshold = QUALITY_CHECK_RULES.OVERLAP_THRESHOLD

  for (let i = 0; i < annotations.length; i++) {
    for (let j = i + 1; j < annotations.length; j++) {
      const ann1 = annotations[i]
      const ann2 = annotations[j]

      if (!ann1.imageCoords || !ann2.imageCoords) continue
      if (ann1.category !== ann2.category) continue

      const iou = calculateIoU(ann1.imageCoords, ann2.imageCoords)
      if (iou > overlapThreshold) {
        overlaps.push({
          annotation1: { id: ann1.id, label: ann1.label || '未命名' },
          annotation2: { id: ann2.id, label: ann2.label || '未命名' },
          iou: iou
        })
      }
    }
  }

  return overlaps
}

const calculateIoU = (box1, box2) => {
  const x1 = Math.max(box1.x, box2.x)
  const y1 = Math.max(box1.y, box2.y)
  const x2 = Math.min(box1.x + box1.width, box2.x + box2.width)
  const y2 = Math.min(box1.y + box1.height, box2.y + box2.height)

  const intersection = Math.max(0, x2 - x1) * Math.max(0, y2 - y1)
  const area1 = box1.width * box1.height
  const area2 = box2.width * box2.height
  const union = area1 + area2 - intersection

  return union > 0 ? intersection / union : 0
}

const calculateCoverage = (annotations, imageInfo) => {
  if (!imageInfo || !imageInfo.width || !imageInfo.height) return 0

  let totalArea = 0
  annotations.forEach(ann => {
    if (ann.imageCoords) {
      totalArea += ann.imageCoords.width * ann.imageCoords.height
    }
  })

  const imageArea = imageInfo.width * imageInfo.height
  return imageArea > 0 ? totalArea / imageArea : 0
}

const createQualityDetails = (score, issues, warnings, passed) => {
  return {
    completeness: {
      score: issues.some(i => i.id === 'min_annotations' || i.id === 'missing_categories') ? 50 : 100,
      description: '标注完整性',
      checks: [
        { name: '最小标注数量', pass: !issues.some(i => i.id === 'min_annotations') },
        { name: '必需分类覆盖', pass: !issues.some(i => i.id === 'missing_categories') }
      ]
    },
    accuracy: {
      score: warnings.some(w => w.id === 'small_annotations' || w.id === 'overlapping_annotations') ? 60 : 100,
      description: '标注准确性',
      checks: [
        { name: '标注尺寸合理', pass: !warnings.some(w => w.id === 'small_annotations') },
        { name: '无严重重叠', pass: !warnings.some(w => w.id === 'overlapping_annotations') }
      ]
    },
    richness: {
      score: warnings.some(w => w.id === 'empty_labels' || w.id === 'no_arrows_or_text') ? 70 : 100,
      description: '标注丰富度',
      checks: [
        { name: '标签完整', pass: !warnings.some(w => w.id === 'empty_labels') },
        { name: '包含辅助标注', pass: !warnings.some(w => w.id === 'no_arrows_or_text') }
      ]
    }
  }
}

export const getQualityLevelColor = (level) => {
  const colors = {
    excellent: '#67c23a',
    good: '#409eff',
    fair: '#e6a23c',
    poor: '#f56c6c'
  }
  return colors[level] || '#909399'
}

export const getQualityLevelText = (level) => {
  const texts = {
    excellent: '优秀',
    good: '良好',
    fair: '一般',
    poor: '较差'
  }
  return texts[level] || '未知'
}

const checkReasonableness = (annotations, imageInfo) => {
  const checks = []
  const { width: imgWidth, height: imgHeight } = imageInfo
  const tolerance = QUALITY_CHECK_RULES.POSITION_TOLERANCE
  const axisTolerance = QUALITY_CHECK_RULES.AXIS_LABEL_POSITION_TOLERANCE

  const titleAnnotations = annotations.filter(a => a.category === 'title' && a.imageCoords)
  const axisLabels = annotations.filter(a => a.category === 'axis_label' && a.imageCoords)
  const dataRegions = annotations.filter(a => a.category === 'data_region' && a.imageCoords)
  const legends = annotations.filter(a => a.category === 'legend' && a.imageCoords)

  titleAnnotations.forEach(title => {
    const { y, height } = title.imageCoords
    const titleBottom = y + height
    const expectedBottom = imgHeight * tolerance
    
    if (titleBottom > expectedBottom) {
      checks.push({
        id: 'title_position',
        type: 'warning',
        category: 'position',
        message: `标题 "${title.label || '未命名'}" 位置可能不合理，建议位于图表顶部区域`,
        annotationId: title.id,
        currentPosition: `y=${y.toFixed(0)}`,
        expectedPosition: `应小于 ${expectedBottom.toFixed(0)}px`,
        penalty: 5
      })
    } else {
      checks.push({
        id: 'title_position_ok',
        type: 'pass',
        message: `标题 "${title.label || '未命名'}" 位置合理（位于顶部）`
      })
    }

    const { TITLE_WIDTH_RATIO } = QUALITY_CHECK_RULES
    const widthRatio = title.imageCoords.width / imgWidth
    if (widthRatio < TITLE_WIDTH_RATIO.MIN || widthRatio > TITLE_WIDTH_RATIO.MAX) {
      checks.push({
        id: 'title_width',
        type: 'warning',
        category: 'size',
        message: `标题 "${title.label || '未命名'}" 宽度比例 ${(widthRatio * 100).toFixed(0)}% 可能不合理`,
        annotationId: title.id,
        currentWidth: `${title.imageCoords.width}px (${(widthRatio * 100).toFixed(0)}%)`,
        expectedRange: `${(TITLE_WIDTH_RATIO.MIN * 100).toFixed(0)}% - ${(TITLE_WIDTH_RATIO.MAX * 100).toFixed(0)}%`,
        penalty: 3
      })
    }
  })

  axisLabels.forEach(label => {
    const { x, y, width, height } = label.imageCoords
    const isAtBottom = y > imgHeight * (1 - axisTolerance)
    const isAtLeft = x < imgWidth * axisTolerance
    const isAtTop = y < imgHeight * axisTolerance
    const isAtRight = x > imgWidth * (1 - axisTolerance)

    if (!isAtBottom && !isAtLeft && !isAtTop && !isAtRight) {
      checks.push({
        id: 'axis_label_position',
        type: 'warning',
        category: 'position',
        message: `轴标签 "${label.label || '未命名'}" 位置可能不合理，轴标签通常位于图表边缘`,
        annotationId: label.id,
        currentPosition: `x=${x.toFixed(0)}, y=${y.toFixed(0)}`,
        expectedPosition: '应靠近图表左、右、上、下边缘',
        penalty: 4
      })
    } else {
      const position = isAtBottom ? '底部' : isAtLeft ? '左侧' : isAtTop ? '顶部' : '右侧'
      checks.push({
        id: 'axis_label_position_ok',
        type: 'pass',
        message: `轴标签 "${label.label || '未命名'}" 位置合理（位于${position}边缘）`
      })
    }
  })

  if (legends.length > 0 && dataRegions.length > 0) {
    legends.forEach(legend => {
      const legendCenter = {
        x: legend.imageCoords.x + legend.imageCoords.width / 2,
        y: legend.imageCoords.y + legend.imageCoords.height / 2
      }

      let minDistance = Infinity
      dataRegions.forEach(data => {
        const dataCenter = {
          x: data.imageCoords.x + data.imageCoords.width / 2,
          y: data.imageCoords.y + data.imageCoords.height / 2
        }
        const distance = Math.sqrt(
          Math.pow(legendCenter.x - dataCenter.x, 2) + 
          Math.pow(legendCenter.y - dataCenter.y, 2)
        )
        minDistance = Math.min(minDistance, distance)
      })

      const maxExpectedDistance = Math.sqrt(imgWidth * imgWidth + imgHeight * imgHeight) * 0.6
      if (minDistance > maxExpectedDistance) {
        checks.push({
          id: 'legend_distance',
          type: 'warning',
          category: 'position',
          message: `图例 "${legend.label || '未命名'}" 距离数据区域较远，建议靠近数据区域`,
          annotationId: legend.id,
          currentDistance: `${minDistance.toFixed(0)}px`,
          expectedDistance: `< ${maxExpectedDistance.toFixed(0)}px`,
          penalty: 3
        })
      } else {
        checks.push({
          id: 'legend_distance_ok',
          type: 'pass',
          message: `图例 "${legend.label || '未命名'}" 位置合理（靠近数据区域）`
        })
      }
    })
  }

  if (dataRegions.length > 0) {
    const dataArea = dataRegions.reduce((sum, d) => sum + d.imageCoords.width * d.imageCoords.height, 0)
    const otherArea = annotations
      .filter(a => a.type === ANNOTATION_TYPES.RECTANGLE && a.category !== 'data_region' && a.imageCoords)
      .reduce((sum, a) => sum + a.imageCoords.width * a.imageCoords.height, 0)
    
    if (dataArea < otherArea && dataRegions.length > 0) {
      checks.push({
        id: 'data_region_size',
        type: 'warning',
        category: 'size',
        message: '数据区域标注总面积小于其他分类，建议检查数据区域是否完整',
        currentRatio: `${(dataArea / (dataArea + otherArea) * 100).toFixed(0)}%`,
        expected: '数据区域通常应占据最大标注面积',
        penalty: 6
      })
    } else {
      checks.push({
        id: 'data_region_size_ok',
        type: 'pass',
        message: '数据区域标注面积比例合理'
      })
    }

    dataRegions.forEach(data => {
      const { x, y, width, height } = data.imageCoords
      const centerY = y + height / 2
      const imgCenterY = imgHeight / 2
      
      if (Math.abs(centerY - imgCenterY) > imgHeight * tolerance) {
        checks.push({
          id: 'data_region_centering',
          type: 'warning',
          category: 'position',
          message: `数据区域 "${data.label || '未命名'}" 可能未位于图表中心区域`,
          annotationId: data.id,
          currentCenter: `y=${centerY.toFixed(0)}`,
          expectedRange: `${(imgCenterY - imgHeight * tolerance).toFixed(0)} - ${(imgCenterY + imgHeight * tolerance).toFixed(0)}`,
          penalty: 3
        })
      }
    })
  }

  const allRects = annotations.filter(a => a.type === ANNOTATION_TYPES.RECTANGLE && a.imageCoords)
  for (let i = 0; i < allRects.length; i++) {
    for (let j = i + 1; j < allRects.length; j++) {
      const r1 = allRects[i]
      const r2 = allRects[j]
      
      if (r1.category === r2.category) continue
      
      const contains = (outer, inner) => {
        return inner.imageCoords.x >= outer.imageCoords.x &&
               inner.imageCoords.y >= outer.imageCoords.y &&
               inner.imageCoords.x + inner.imageCoords.width <= outer.imageCoords.x + outer.imageCoords.width &&
               inner.imageCoords.y + inner.imageCoords.height <= outer.imageCoords.y + outer.imageCoords.height
      }

      if (contains(r1, r2) || contains(r2, r1)) {
        const outer = contains(r1, r2) ? r1 : r2
        const inner = contains(r1, r2) ? r2 : r1
        
        if (outer.category === 'data_region' && 
            (inner.category === 'axis_label' || inner.category === 'legend')) {
          checks.push({
            id: 'unexpected_containment',
            type: 'warning',
            category: 'relation',
            message: `${getCategoryName(inner.category)} "${inner.label || '未命名'}" 位于数据区域内部，可能标注错误`,
            annotationIds: [inner.id, outer.id],
            penalty: 5
          })
        }
        
        if (outer.category === 'title' && inner.category !== 'title') {
          checks.push({
            id: 'title_contains_other',
            type: 'warning',
            category: 'relation',
            message: `标题区域包含了 ${getCategoryName(inner.category)} 标注，可能标注范围过大`,
            annotationIds: [inner.id, outer.id],
            penalty: 4
          })
        }
      }
    }
  }

  if (checks.length === 0 || checks.every(c => c.type === 'pass')) {
    checks.push({
      id: 'all_reasonable',
      type: 'pass',
      message: '所有标注位置和尺寸关系合理'
    })
  }

  return checks
}

const getCategoryName = (categoryId) => {
  const cat = ANNOTATION_CATEGORIES.find(c => c.id === categoryId)
  return cat ? cat.name : categoryId
}

export default {
  checkAnnotationQuality,
  getQualityLevelColor,
  getQualityLevelText,
  checkReasonableness
}

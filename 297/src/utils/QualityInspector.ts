import { Annotation, LabelType } from '@/types'

export interface QualityIssue {
  id: string
  annotationId: string
  type: 'missing' | 'wrong_label' | 'overlapping' | 'incomplete' | 'small'
  severity: 'low' | 'medium' | 'high'
  message: string
  suggestedFix?: string
}

export interface InspectionResult {
  checked: number
  passed: number
  issues: QualityIssue[]
  passRate: number
  qualityScore: number
}

export interface SamplingResult {
  sampleSize: number
  totalAnnotations: number
  sampledIds: string[]
  inspection: InspectionResult
  timestamp: string
}

export class QualityInspector {
  private annotations: Annotation[] = []

  setAnnotations(annotations: Annotation[]) {
    this.annotations = annotations
  }

  randomSample(sampleSize: number): Annotation[] {
    const total = this.annotations.length
    if (total === 0) return []
    
    const actualSize = Math.min(sampleSize, total)
    const sampled: Annotation[] = []
    const sampledIndices = new Set<number>()

    while (sampledIndices.size < actualSize) {
      const idx = Math.floor(Math.random() * total)
      if (!sampledIndices.has(idx)) {
        sampledIndices.add(idx)
        sampled.push(this.annotations[idx])
      }
    }

    return sampled
  }

  stratifiedSample(sampleSize: number): Annotation[] {
    const byLabel: Record<LabelType, Annotation[]> = {
      ground: [],
      vehicle: [],
      pedestrian: [],
    }

    this.annotations.forEach(a => {
      if (byLabel[a.label]) {
        byLabel[a.label].push(a)
      }
    })

    const sampled: Annotation[] = []
    const totalLabels = Object.keys(byLabel).filter(l => byLabel[l as LabelType].length > 0).length
    const perLabelSize = Math.ceil(sampleSize / totalLabels)

    Object.values(byLabel).forEach(annots => {
      const actualSize = Math.min(perLabelSize, annots.length)
      const indices = new Set<number>()
      
      while (indices.size < actualSize && indices.size < annots.length) {
        const idx = Math.floor(Math.random() * annots.length)
        if (!indices.has(idx)) {
          indices.add(idx)
          sampled.push(annots[idx])
        }
      }
    })

    return sampled.slice(0, sampleSize)
  }

  checkAnnotation(annotation: Annotation): QualityIssue[] {
    const issues: QualityIssue[] = []

    const geo = annotation.geometry as any
    const size = geo.size || { x: 0, y: 0, z: 0 }
    const volume = size.x * size.y * size.z

    if (annotation.label === 'ground') {
      if (size.x < 3 || size.z < 3) {
        issues.push({
          id: `issue_${Date.now()}_small`,
          annotationId: annotation.id,
          type: 'small',
          severity: 'medium',
          message: '地面标注区域过小，建议检查是否完整',
        })
      }
    }

    if (annotation.label === 'vehicle') {
      if (volume < 2) {
        issues.push({
          id: `issue_${Date.now()}_small`,
          annotationId: annotation.id,
          type: 'small',
          severity: 'low',
          message: '车辆标注体积过小，可能标注不准确',
        })
      }
      if (volume > 40) {
        issues.push({
          id: `issue_${Date.now()}_large`,
          annotationId: annotation.id,
          type: 'incomplete',
          severity: 'medium',
          message: '车辆标注体积过大，可能包含多余区域',
        })
      }
      if (size.y < 0.8 || size.y > 3) {
        issues.push({
          id: `issue_${Date.now()}_height`,
          annotationId: annotation.id,
          type: 'wrong_label',
          severity: 'medium',
          message: `车辆高度异常 (${size.y.toFixed(1)}m)，请检查标签是否正确`,
        })
      }
    }

    if (annotation.label === 'pedestrian') {
      if (size.y < 1 || size.y > 2.5) {
        issues.push({
          id: `issue_${Date.now()}_height`,
          annotationId: annotation.id,
          type: 'wrong_label',
          severity: 'high',
          message: `行人高度异常 (${size.y.toFixed(1)}m)，建议检查标签`,
          suggestedFix: '可能是车辆或其他物体',
        })
      }
      if (size.x > 1.5 || size.z > 1.5) {
        issues.push({
          id: `issue_${Date.now()}_size`,
          annotationId: annotation.id,
          type: 'incomplete',
          severity: 'medium',
          message: '行人标注范围过大，请检查',
        })
      }
    }

    if (annotation.pointIndices.length < 5) {
      issues.push({
        id: `issue_${Date.now()}_points`,
        annotationId: annotation.id,
        type: 'incomplete',
        severity: 'low',
        message: '标注包含点数过少，建议补充',
      })
    }

    return issues
  }

  checkOverlaps(): QualityIssue[] {
    const issues: QualityIssue[] = []
    
    for (let i = 0; i < this.annotations.length; i++) {
      for (let j = i + 1; j < this.annotations.length; j++) {
        const a1 = this.annotations[i]
        const a2 = this.annotations[j]
        
        if (this.checkBoxOverlap(a1, a2)) {
          issues.push({
            id: `issue_${Date.now()}_overlap_${i}_${j}`,
            annotationId: a1.id,
            type: 'overlapping',
            severity: 'medium',
            message: `与 ${a2.label} 标注存在重叠`,
            suggestedFix: '调整标注范围或删除重复标注',
          })
        }
      }
    }

    return issues
  }

  private checkBoxOverlap(a1: Annotation, a2: Annotation): boolean {
    const g1 = a1.geometry as any
    const g2 = a2.geometry as any

    if (!g1.center || !g2.center || !g1.size || !g2.size) return false

    const overlapX = Math.abs(g1.center.x - g2.center.x) < (g1.size.x + g2.size.x) / 2 * 0.8
    const overlapY = Math.abs(g1.center.y - g2.center.y) < (g1.size.y + g2.size.y) / 2 * 0.8
    const overlapZ = Math.abs(g1.center.z - g2.center.z) < (g1.size.z + g2.size.z) / 2 * 0.8

    return overlapX && overlapY && overlapZ
  }

  inspectSample(sampleSize: number = 20): SamplingResult {
    const sampled = this.stratifiedSample(sampleSize)
    const allIssues: QualityIssue[] = []

    sampled.forEach(annotation => {
      const issues = this.checkAnnotation(annotation)
      allIssues.push(...issues)
    })

    allIssues.push(...this.checkOverlaps())

    const highIssues = allIssues.filter(i => i.severity === 'high').length
    const mediumIssues = allIssues.filter(i => i.severity === 'medium').length
    const lowIssues = allIssues.filter(i => i.severity === 'low').length

    const qualityScore = Math.max(0, 100 - highIssues * 15 - mediumIssues * 5 - lowIssues * 2)
    const passed = Math.max(0, sampled.length - allIssues.filter(i => i.severity !== 'low').length / 2)

    return {
      sampleSize: sampled.length,
      totalAnnotations: this.annotations.length,
      sampledIds: sampled.map(a => a.id),
      inspection: {
        checked: sampled.length,
        passed: Math.round(passed),
        issues: allIssues,
        passRate: sampled.length > 0 ? (passed / sampled.length) * 100 : 100,
        qualityScore,
      },
      timestamp: new Date().toISOString(),
    }
  }

  getStatistics() {
    const byLabel: Record<LabelType, number> = {
      ground: 0,
      vehicle: 0,
      pedestrian: 0,
    }

    this.annotations.forEach(a => {
      byLabel[a.label]++
    })

    const avgBoxSize = {
      ground: { x: 0, y: 0, z: 0 },
      vehicle: { x: 0, y: 0, z: 0 },
      pedestrian: { x: 0, y: 0, z: 0 },
    }

    const countByLabel: Record<LabelType, number> = {
      ground: 0,
      vehicle: 0,
      pedestrian: 0,
    }

    this.annotations.forEach(a => {
      const geo = a.geometry as any
      if (geo.size) {
        avgBoxSize[a.label].x += geo.size.x
        avgBoxSize[a.label].y += geo.size.y
        avgBoxSize[a.label].z += geo.size.z
        countByLabel[a.label]++
      }
    })

    ;(['ground', 'vehicle', 'pedestrian'] as LabelType[]).forEach(label => {
      if (countByLabel[label] > 0) {
        avgBoxSize[label].x /= countByLabel[label]
        avgBoxSize[label].y /= countByLabel[label]
        avgBoxSize[label].z /= countByLabel[label]
      }
    })

    return {
      total: this.annotations.length,
      byLabel,
      avgBoxSize,
    }
  }
}

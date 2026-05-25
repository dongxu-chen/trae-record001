import { useState } from 'react'
import { Sparkles, Check, X, Play, Loader2, Layers } from 'lucide-react'
import { useAnnotationStore } from '@/store/annotationStore'
import { useToolsStore } from '@/store/toolsStore'
import { AIPreAnnotator, PointData } from '@/utils/AIPreAnnotator'
import * as THREE from 'three'

interface AIPanelProps {
  pointCloudData?: PointData[]
  onAddAnnotations?: (annotations: any[]) => void
}

export default function AIPanel({ pointCloudData, onAddAnnotations }: AIPanelProps) {
  const [isProcessing, setIsProcessing] = useState(false)
  const [progress, setProgress] = useState(0)
  const { aiAnnotations, setAiAnnotations, clearAiAnnotations } = useToolsStore()
  const { addAnnotation } = useAnnotationStore()

  const runPreAnnotation = async () => {
    setIsProcessing(true)
    setProgress(0)
    clearAiAnnotations()

    const mockPoints: PointData[] = []
    for (let i = 0; i < 10000; i++) {
      const x = (Math.random() - 0.5) * 100
      const z = (Math.random() - 0.5) * 100
      const y = Math.random() * 5 - Math.abs(x) * 0.05 - Math.abs(z) * 0.05

      mockPoints.push({
        position: new THREE.Vector3(x, Math.max(y, -2), z),
        color: new THREE.Color(0x888888),
      })
    }

    const progressInterval = setInterval(() => {
      setProgress((prev) => Math.min(prev + 10, 90))
    }, 200)

    const annotator = new AIPreAnnotator()
    annotator.setPoints(mockPoints)
    const annotations = await annotator.preAnnotate()

    clearInterval(progressInterval)
    setProgress(100)
    setAiAnnotations(annotations)
    setIsProcessing(false)
  }

  const acceptAnnotation = (annotation: any) => {
    addAnnotation({
      ...annotation,
      id: `ann_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    })
    setAiAnnotations(aiAnnotations.filter(a => a.id !== annotation.id))
  }

  const rejectAnnotation = (annotation: any) => {
    setAiAnnotations(aiAnnotations.filter(a => a.id !== annotation.id))
  }

  const acceptAll = () => {
    aiAnnotations.forEach(ann => {
      addAnnotation({
        ...ann,
        id: `ann_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      })
    })
    clearAiAnnotations()
  }

  const getLabelColor = (label: string) => {
    switch (label) {
      case 'ground': return 'bg-green-500/20 text-green-400 border-green-500/50'
      case 'vehicle': return 'bg-red-500/20 text-red-400 border-red-500/50'
      case 'pedestrian': return 'bg-orange-500/20 text-orange-400 border-orange-500/50'
      default: return 'bg-zinc-500/20 text-zinc-400 border-zinc-500/50'
    }
  }

  const getLabelName = (label: string) => {
    switch (label) {
      case 'ground': return '地面'
      case 'vehicle': return '车辆'
      case 'pedestrian': return '行人'
      default: return label
    }
  }

  return (
    <div className="glass-panel rounded-xl p-4 w-72">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-purple-400" />
          <h3 className="text-sm font-semibold text-white">AI预标注</h3>
        </div>
      </div>

      {isProcessing ? (
        <div className="space-y-4">
          <div className="flex flex-col items-center py-6">
            <div className="relative">
              <div className="w-16 h-16 border-4 border-zinc-700 rounded-full" />
              <div 
                className="absolute inset-0 border-4 border-purple-500 rounded-full border-t-transparent animate-spin"
              />
              <span className="absolute inset-0 flex items-center justify-center text-sm text-white font-medium">
                {progress}%
              </span>
            </div>
            <p className="text-sm text-zinc-400 mt-4">AI正在分析点云...</p>
            <p className="text-xs text-zinc-500 mt-1">检测地面、车辆、行人</p>
          </div>
        </div>
      ) : aiAnnotations.length > 0 ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-purple-400" />
              <span className="text-sm text-white">
                发现 {aiAnnotations.length} 个目标
              </span>
            </div>
            <button
              onClick={acceptAll}
              className="text-xs text-purple-400 hover:text-purple-300 transition-colors"
            >
              全部接受
            </button>
          </div>

          <div className="space-y-2 max-h-64 overflow-y-auto scrollbar-thin">
            {aiAnnotations.map((ann, idx) => (
              <div
                key={ann.id}
                className="bg-zinc-800/50 rounded-lg p-2 flex items-center justify-between"
              >
                <div className="flex items-center gap-2">
                  <span className="text-xs text-zinc-500">#{idx + 1}</span>
                  <span className={`text-xs px-2 py-0.5 rounded border ${getLabelColor(ann.label)}`}>
                    {getLabelName(ann.label)}
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => acceptAnnotation(ann)}
                    className="p-1 hover:bg-green-500/20 rounded transition-colors"
                  >
                    <Check className="w-4 h-4 text-green-400" />
                  </button>
                  <button
                    onClick={() => rejectAnnotation(ann)}
                    className="p-1 hover:bg-red-500/20 rounded transition-colors"
                  >
                    <X className="w-4 h-4 text-red-400" />
                  </button>
                </div>
              </div>
            ))}
          </div>

          <button
            onClick={runPreAnnotation}
            disabled={isProcessing}
            className="w-full btn-secondary text-sm"
          >
            重新检测
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="text-center py-6">
            <div className="w-16 h-16 mx-auto mb-3 bg-purple-500/10 rounded-xl flex items-center justify-center">
              <Sparkles className="w-8 h-8 text-purple-400" />
            </div>
            <p className="text-sm text-zinc-400 mb-1">自动识别常见物体</p>
            <p className="text-xs text-zinc-500">支持地面、车辆、行人检测</p>
          </div>
          
          <button
            onClick={runPreAnnotation}
            disabled={isProcessing}
            className="w-full flex items-center justify-center gap-2 bg-purple-500 hover:bg-purple-600 text-white font-medium py-2 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Play className="w-4 h-4" />
            开始检测
          </button>

          <div className="space-y-2">
            <p className="text-xs text-zinc-500 font-medium">检测算法:</p>
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs text-zinc-400">
                <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
                RANSAC 地面检测
              </div>
              <div className="flex items-center gap-2 text-xs text-zinc-400">
                <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
                DBSCAN 聚类分析
              </div>
              <div className="flex items-center gap-2 text-xs text-zinc-400">
                <div className="w-1.5 h-1.5 rounded-full bg-orange-500" />
                几何特征分类
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

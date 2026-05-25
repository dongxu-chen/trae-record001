import { useState } from 'react'
import { useEditorStore } from '@/lib/store'
import { downloadLottie, getExportStats } from '@/lib/lottieExporter'
import { ExportOptions } from '@/types'

export function ExportModal({ onClose }: { onClose: () => void }) {
  const { project } = useEditorStore()
  const [options, setOptions] = useState<ExportOptions>({
    compress: false,
    keyframeTolerance: 0.01,
    optimizePaths: true,
    minify: false,
  })
  const [stats, setStats] = useState<any>(null)

  if (!project) return null

  const handlePreview = () => {
    const result = getExportStats(project, options)
    setStats(result)
  }

  const handleExport = () => {
    downloadLottie(project, options)
    onClose()
  }

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.7)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: '#16213e',
          padding: '24px',
          borderRadius: '12px',
          width: '450px',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 style={{ marginBottom: '20px', color: '#e94560' }}>导出 Lottie</h2>

        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px' }}>
          <input
            type="checkbox"
            checked={options.compress}
            onChange={(e) => setOptions({ ...options, compress: e.target.checked })}
          />
          启用压缩
        </label>
        <p style={{ fontSize: '12px', color: '#888', marginLeft: '24px', marginTop: '4px' }}>
          合并相似关键帧，减少文件体积
        </p>
        </div>

        {options.compress && (
          <div style={{ marginLeft: '24px', marginBottom: '16px' }}>
            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px' }}>
                关键帧容差: {(options.keyframeTolerance * 100).toFixed(0)}%
              </label>
              <input
                type="range"
                min="0.001"
                max="0.1"
                step="0.005"
                value={options.keyframeTolerance}
                onChange={(e) => setOptions({ ...options, keyframeTolerance: parseFloat(e.target.value) })}
                style={{ width: '100%' }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#888' }}>
                <span>高精度</span>
                <span>高压缩</span>
              </div>
            </div>

            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px' }}>
              <input
                type="checkbox"
                checked={options.optimizePaths}
                onChange={(e) => setOptions({ ...options, optimizePaths: e.target.checked })}
              />
              优化路径数据
            </label>
          </div>
        )}

        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px' }}>
            <input
              type="checkbox"
              checked={options.minify}
              onChange={(e) => setOptions({ ...options, minify: e.target.checked })}
            />
            压缩 JSON (去除空格)
          </label>
        </div>

        <button
          className="btn btn-secondary"
          style={{ width: '100%', marginBottom: '12px' }}
          onClick={handlePreview}
        >
          预览压缩效果
        </button>

        {stats && (
          <div
            style={{
              padding: '12px',
              background: '#0f3460',
              borderRadius: '6px',
              marginBottom: '16px',
              fontSize: '13px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
              <span>原始大小:</span>
              <span>{(stats.originalSize / 1024).toFixed(2)} KB</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
              <span>压缩后:</span>
              <span>{(stats.compressedSize / 1024).toFixed(2)} KB</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
              <span>压缩率:</span>
              <span style={{ color: stats.compressionRatio > 0 ? '#4ade80' : '#fff' }}>
                {(stats.compressionRatio * 100).toFixed(1)}%
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>减少关键帧:</span>
              <span style={{ color: stats.keyframesReduced > 0 ? '#4ade80' : '#fff' }}>
                {stats.keyframesReduced} 个
              </span>
            </div>
          </div>
        )}

        <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
          <button className="btn btn-secondary" onClick={onClose}>
            取消
          </button>
          <button className="btn btn-primary" onClick={handleExport}>
            导出
          </button>
        </div>
      </div>
    </div>
  )
}

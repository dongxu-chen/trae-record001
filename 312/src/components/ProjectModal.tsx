import { useState } from 'react'
import { useEditorStore } from '@/lib/store'
import { parseSvg } from '@/lib/svgParser'

export function ProjectModal({ onClose }: { onClose: () => void }) {
  const [name, setName] = useState('')
  const [svgContent, setSvgContent] = useState('')
  const { createProject } = useEditorStore()

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      const reader = new FileReader()
      reader.onload = (event) => {
        setSvgContent(event.target?.result as string)
      }
      reader.readAsText(file)
    }
  }

  const handleCreate = async () => {
    if (!name || !svgContent) return

    const { elements, layers, viewBox } = parseSvg(svgContent)

    const project = {
      id: '',
      name,
      createdAt: 0,
      updatedAt: 0,
      duration: 3000,
      framerate: 60,
      width: viewBox.width,
      height: viewBox.height,
      svgContent,
      elements,
      layers,
      versions: [],
    }

    await createProject(name, svgContent)
    
    const { project: newProject } = useEditorStore.getState()
    if (newProject) {
      newProject.elements = elements
      newProject.layers = layers
      newProject.width = viewBox.width
      newProject.height = viewBox.height
      await useEditorStore.getState().saveProject()
    }

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
          width: '500px',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 style={{ marginBottom: '20px', color: '#e94560' }}>创建新项目</h2>

        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px' }}>项目名称</label>
          <input
            type="text"
            className="property-input"
            style={{ width: '100%' }}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="输入项目名称"
          />
        </div>

        <div style={{ marginBottom: '24px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px' }}>导入 SVG</label>
          <input
            type="file"
            accept=".svg"
            onChange={handleFileUpload}
            style={{ color: 'white', marginBottom: '12px' }}
          />
          {svgContent && (
            <div style={{ padding: '10px', background: '#0f3460', borderRadius: '6px', fontSize: '12px' }}>
              ✓ SVG 已加载 ({svgContent.length} 字符)
            </div>
          )}
        </div>

        <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
          <button className="btn btn-secondary" onClick={onClose}>
            取消
          </button>
          <button className="btn btn-primary" onClick={handleCreate} disabled={!name || !svgContent}>
            创建
          </button>
        </div>
      </div>
    </div>
  )
}

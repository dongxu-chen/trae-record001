'use client'

import { useEffect, useRef, useState } from 'react'
import ForceGraph from 'force-graph'
import { Note } from '@/types'
import { buildKnowledgeGraph } from '@/lib/wikiLinks'
import { X, Maximize2, Minimize2, Info } from 'lucide-react'

interface KnowledgeGraphProps {
  notes: Note[]
  currentNoteId?: string
  onSelectNote: (noteId: string) => void
  onClose: () => void
}

export default function KnowledgeGraph({
  notes,
  currentNoteId,
  onSelectNote,
  onClose,
}: KnowledgeGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const graphRef = useRef<any>(null)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [hoveredNode, setHoveredNode] = useState<any>(null)

  useEffect(() => {
    if (!containerRef.current || notes.length === 0) return

    const { nodes, links } = buildKnowledgeGraph(notes)

    const graph = ForceGraph()(containerRef.current)
      .graphData({ nodes, links })
      .nodeLabel('name')
      .nodeColor((node: any) => {
        if (node.id === currentNoteId) return '#3b82f6'
        if (links.some(l => l.source === node.id || l.target === node.id)) return '#10b981'
        return '#9ca3af'
      })
      .nodeVal((node: any) => {
        const connectionCount = links.filter(
          l => l.source === node.id || l.target === node.id
        ).length
        return Math.max(4, connectionCount * 2 + 4)
      })
      .linkColor(() => '#d1d5db')
      .linkWidth(1)
      .onNodeClick((node: any) => {
        onSelectNote(node.id)
      })
      .onNodeHover((node: any) => {
        setHoveredNode(node)
      })
      .d3Force('charge', -200)
      .d3Force('link', { distance: 100 })

    graphRef.current = graph

    return () => {
      if (graphRef.current) {
        graphRef.current._destructor()
      }
    }
  }, [notes, currentNoteId, onSelectNote])

  useEffect(() => {
    if (!graphRef.current) return

    graphRef.current
      .nodeColor((node: any) => {
        if (node.id === currentNoteId) return '#3b82f6'
        if (hoveredNode && (
          hoveredNode.id === node.id ||
          graphRef.current.graphData().links.some(
            (l: any) => 
              (l.source.id === hoveredNode.id && l.target.id === node.id) ||
              (l.target.id === hoveredNode.id && l.source.id === node.id)
          )
        )) return '#f59e0b'
        if (graphRef.current.graphData().links.some(
          (l: any) => l.source.id === node.id || l.target.id === node.id
        )) return '#10b981'
        return '#9ca3af'
      })
  }, [currentNoteId, hoveredNode])

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen)
    setTimeout(() => {
      if (graphRef.current) {
        graphRef.current.refresh()
      }
    }, 100)
  }

  const stats = {
    totalNotes: notes.length,
    linkedNotes: notes.filter(n => 
      buildKnowledgeGraph(notes).links.some(
        l => l.source === n._id || l.target === n._id
      )
    ).length,
    totalLinks: buildKnowledgeGraph(notes).links.length,
  }

  return (
    <div
      className={`fixed bg-white shadow-xl z-40 rounded-lg overflow-hidden transition-all duration-300 ${
        isFullscreen
          ? 'inset-4'
          : 'bottom-4 right-4 w-96 h-80'
      }`}
    >
      <div className="flex items-center justify-between px-4 py-2 bg-gray-100 border-b">
        <div className="flex items-center gap-2">
          <span className="font-medium text-gray-700">知识图谱</span>
          <div className="flex gap-2 text-xs text-gray-500">
            <span>{stats.totalNotes} 笔记</span>
            <span>{stats.linkedNotes} 已关联</span>
            <span>{stats.totalLinks} 链接</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={toggleFullscreen}
            className="p-1 hover:bg-gray-200 rounded"
            title={isFullscreen ? '退出全屏' : '全屏'}
          >
            {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
          </button>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-200 rounded"
            title="关闭"
          >
            <X size={16} />
          </button>
        </div>
      </div>

      <div ref={containerRef} className="w-full h-[calc(100%-40px)]" />

      {hoveredNode && (
        <div className="absolute bottom-4 left-4 bg-white border rounded-lg shadow-lg px-3 py-2 max-w-xs">
          <div className="font-medium text-gray-800">{hoveredNode.name}</div>
          <div className="text-xs text-gray-500 mt-1">
            {hoveredNode.id === currentNoteId && (
              <span className="inline-block bg-blue-100 text-blue-700 px-2 py-0.5 rounded mr-2">
                当前笔记
              </span>
            )}
            点击跳转
          </div>
        </div>
      )}

      <div className="absolute bottom-4 right-4 bg-white/90 backdrop-blur border rounded-lg px-3 py-2 text-xs">
        <div className="flex items-center gap-2 mb-1">
          <span className="w-3 h-3 rounded-full bg-blue-500"></span>
          <span className="text-gray-600">当前笔记</span>
        </div>
        <div className="flex items-center gap-2 mb-1">
          <span className="w-3 h-3 rounded-full bg-green-500"></span>
          <span className="text-gray-600">已关联笔记</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-gray-400"></span>
          <span className="text-gray-600">孤立笔记</span>
        </div>
      </div>
    </div>
  )
}

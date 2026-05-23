'use client'

import { useState, useEffect } from 'react'
import { Search, Download, Share2, History, Clock, Eye, Edit3, X, Check, Copy, GitCompare } from 'lucide-react'
import { Note, Version, Tag as TagType } from '@/types'
import VersionDiff from './VersionDiff'

interface ToolbarProps {
  note: Note | null
  versions: Version[]
  tags: TagType[]
  onSearch: (query: string) => void
  onExport: (format: 'md' | 'html' | 'pdf') => void
  onShare: () => void
  onRestoreVersion: (version: Version) => void
  onUpdateNote: (updates: Partial<Note>) => void
  shareToken?: string
}

export default function Toolbar({
  note,
  versions,
  tags,
  onSearch,
  onExport,
  onShare,
  onRestoreVersion,
  onUpdateNote,
  shareToken,
}: ToolbarProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [showVersions, setShowVersions] = useState(false)
  const [showExport, setShowExport] = useState(false)
  const [showShare, setShowShare] = useState(false)
  const [showTagSelector, setShowTagSelector] = useState(false)
  const [compareMode, setCompareMode] = useState(false)
  const [selectedVersions, setSelectedVersions] = useState<number[]>([])
  const [diffData, setDiffData] = useState<any>(null)
  const [showDiff, setShowDiff] = useState(false)

  const handleSearch = () => {
    if (searchQuery.trim()) {
      onSearch(searchQuery.trim())
    }
  }

  const copyShareLink = () => {
    if (shareToken) {
      const link = `${window.location.origin}/share/${shareToken}`
      navigator.clipboard.writeText(link)
    }
  }

  const toggleTag = (tagId: string) => {
    if (!note) return
    const currentTags = note.tags || []
    const newTags = currentTags.includes(tagId)
      ? currentTags.filter(t => t !== tagId)
      : [...currentTags, tagId]
    onUpdateNote({ tags: newTags as any })
  }

  const toggleVersionSelection = (versionNumber: number) => {
    setSelectedVersions(prev => {
      if (prev.includes(versionNumber)) {
        return prev.filter(v => v !== versionNumber)
      }
      if (prev.length >= 2) {
        return [prev[1], versionNumber]
      }
      return [...prev, versionNumber]
    })
  }

  const loadVersionDiff = async () => {
    if (selectedVersions.length !== 2 || !note) return
    
    const [v1, v2] = selectedVersions.sort((a, b) => a - b)
    
    try {
      const res = await fetch(`/api/notes/${note._id}/versions?compare=${v1},${v2}`)
      const data = await res.json()
      setDiffData({ ...data, version1: v1, version2: v2 })
      setShowDiff(true)
      setCompareMode(false)
      setSelectedVersions([])
      setShowVersions(false)
    } catch (error) {
      console.error('Failed to load version diff:', error)
    }
  }

  const handleRestoreFromDiff = () => {
    if (!diffData || !note) return
    const version = versions.find(v => v.versionNumber === diffData.version2)
    if (version) {
      onRestoreVersion(version)
    }
    setShowDiff(false)
  }

  return (
    <div className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-4">
      <div className="flex items-center gap-4 flex-1">
        <div className="relative w-64">
          <input
            type="text"
            placeholder="搜索笔记..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={16} />
        </div>

        {note && (
          <div className="relative">
            <button
              onClick={() => setShowTagSelector(!showTagSelector)}
              className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg"
            >
              <Edit3 size={16} />
              标签
            </button>
            {showTagSelector && (
              <div className="absolute top-full left-0 mt-2 w-48 bg-white border border-gray-200 rounded-lg shadow-lg z-10">
                <div className="p-2">
                  {tags.map(tag => (
                    <label
                      key={tag._id}
                      className="flex items-center gap-2 px-2 py-1.5 hover:bg-gray-100 rounded cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={note.tags?.includes(tag._id)}
                        onChange={() => toggleTag(tag._id)}
                        className="rounded"
                      />
                      <span className="text-sm" style={{ color: tag.color }}>
                        {tag.name}
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {note && (
        <div className="flex items-center gap-2">
          <div className="relative">
            <button
              onClick={() => setShowVersions(!showVersions)}
              className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg"
            >
              <History size={16} />
              <Clock size={14} />
              历史版本
            </button>
            {showVersions && (
              <div className="absolute top-full right-0 mt-2 w-80 bg-white border border-gray-200 rounded-lg shadow-lg z-10 max-h-96 overflow-y-auto">
                <div className="p-3 border-b border-gray-200">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-medium text-gray-800">历史版本</h3>
                    <button
                      onClick={() => {
                        setCompareMode(!compareMode)
                        setSelectedVersions([])
                      }}
                      className={`flex items-center gap-1 px-2 py-1 text-xs rounded ${
                        compareMode
                          ? 'bg-blue-100 text-blue-700'
                          : 'text-gray-600 hover:bg-gray-100'
                      }`}
                    >
                      <GitCompare size={12} />
                      对比
                    </button>
                  </div>
                  {compareMode && (
                    <div className="text-xs text-gray-500">
                      选择两个版本进行对比 (已选 {selectedVersions.length}/2)
                      {selectedVersions.length === 2 && (
                        <button
                          onClick={loadVersionDiff}
                          className="ml-2 text-blue-600 hover:underline"
                        >
                          查看差异
                        </button>
                      )}
                    </div>
                  )}
                </div>
                <div className="p-2">
                  {versions.length === 0 ? (
                    <p className="text-sm text-gray-500 p-2">暂无历史版本</p>
                  ) : (
                    versions.map(version => (
                      <div
                        key={version._id}
                        className={`flex items-center justify-between p-2 rounded cursor-pointer ${
                          selectedVersions.includes(version.versionNumber)
                            ? 'bg-blue-50 border border-blue-200'
                            : 'hover:bg-gray-100'
                        }`}
                        onClick={() => compareMode && toggleVersionSelection(version.versionNumber)}
                      >
                        <div className="flex items-center gap-2">
                          {compareMode && (
                            <input
                              type="checkbox"
                              checked={selectedVersions.includes(version.versionNumber)}
                              onChange={() => {}}
                              className="rounded"
                            />
                          )}
                          <div>
                            <p className="text-sm font-medium">
                              v{version.versionNumber}
                              {(version as any).isDelta && (
                                <span className="ml-1 text-xs text-gray-400">Δ</span>
                              )}
                            </p>
                            <p className="text-xs text-gray-500">
                              {new Date(version.createdAt).toLocaleString()}
                            </p>
                          </div>
                        </div>
                        {!compareMode && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              onRestoreVersion(version)
                              setShowVersions(false)
                            }}
                            className="text-xs text-blue-600 hover:underline"
                          >
                            恢复
                          </button>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>

          <div className="relative">
            <button
              onClick={() => setShowExport(!showExport)}
              className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg"
            >
              <Download size={16} />
              导出
            </button>
            {showExport && (
              <div className="absolute top-full right-0 mt-2 w-40 bg-white border border-gray-200 rounded-lg shadow-lg z-10">
                <button
                  onClick={() => {
                    onExport('md')
                    setShowExport(false)
                  }}
                  className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100"
                >
                  Markdown (.md)
                </button>
                <button
                  onClick={() => {
                    onExport('html')
                    setShowExport(false)
                  }}
                  className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100"
                >
                  HTML (.html)
                </button>
                <button
                  onClick={() => {
                    onExport('pdf')
                    setShowExport(false)
                  }}
                  className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100"
                >
                  PDF (.pdf)
                </button>
              </div>
            )}
          </div>

          <div className="relative">
            <button
              onClick={() => {
                onShare()
                setShowShare(!showShare)
              }}
              className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg ${
                note.isPublic
                  ? 'bg-green-100 text-green-700'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <Share2 size={16} />
              {note.isPublic ? '已分享' : '分享'}
            </button>
            {showShare && note.isPublic && shareToken && (
              <div className="absolute top-full right-0 mt-2 w-72 bg-white border border-gray-200 rounded-lg shadow-lg z-10 p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-medium text-gray-800">分享链接</h3>
                  <button
                    onClick={() => setShowShare(false)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    <X size={16} />
                  </button>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    readOnly
                    value={`${window.location.origin}/share/${shareToken}`}
                    className="flex-1 px-2 py-1 text-sm border border-gray-300 rounded"
                  />
                  <button
                    onClick={copyShareLink}
                    className="p-1.5 bg-blue-600 text-white rounded hover:bg-blue-700"
                  >
                    <Copy size={14} />
                  </button>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  任何人都可以通过此链接查看笔记
                </p>
              </div>
            )}
          </div>

          <div className="text-xs text-gray-500 ml-2">
            {note.isPublic ? (
              <span className="flex items-center gap-1">
                <Eye size={12} /> 公开
              </span>
            ) : (
              <span className="flex items-center gap-1">
                <Check size={12} /> 私密
              </span>
            )}
          </div>
        </div>
      )}

      {showDiff && diffData && (
        <VersionDiff
          version1={diffData.version1}
          version2={diffData.version2}
          titleDiff={diffData.titleDiff}
          contentDiff={diffData.contentDiff}
          onClose={() => setShowDiff(false)}
          onRestore={handleRestoreFromDiff}
        />
      )}
    </div>
  )
}

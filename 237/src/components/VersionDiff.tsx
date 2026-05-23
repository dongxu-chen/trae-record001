'use client'

import { useState } from 'react'
import { diff_match_patch } from 'diff-match-patch'
import { X, ChevronLeft, ChevronRight } from 'lucide-react'

interface VersionDiffProps {
  version1: number
  version2: number
  titleDiff: any[]
  contentDiff: any[]
  onClose: () => void
  onRestore: () => void
}

export default function VersionDiff({
  version1,
  version2,
  titleDiff,
  contentDiff,
  onClose,
  onRestore,
}: VersionDiffProps) {
  const [viewMode, setViewMode] = useState<'split' | 'unified'>('unified')

  const renderDiff = (diffs: any[], isTitle: boolean = false) => {
    return diffs.map((diff: any, index: number) => {
      const [operation, text] = diff
      let className = ''
      
      if (operation === diff_match_patch.DIFF_INSERT) {
        className = 'bg-green-200 text-green-800'
      } else if (operation === diff_match_patch.DIFF_DELETE) {
        className = 'bg-red-200 text-red-800 line-through'
      }

      return (
        <span
          key={index}
          className={className}
          style={{
            padding: isTitle ? '2px 4px' : '1px 2px',
            borderRadius: '2px',
          }}
        >
          {text}
        </span>
      )
    })
  }

  const renderSplitView = () => {
    const oldText = contentDiff
      .filter((d: any) => d[0] !== diff_match_patch.DIFF_INSERT)
      .map((d: any) => d[1])
      .join('')
    
    const newText = contentDiff
      .filter((d: any) => d[0] !== diff_match_patch.DIFF_DELETE)
      .map((d: any) => d[1])
      .join('')

    return (
      <div className="grid grid-cols-2 gap-4">
        <div>
          <h4 className="text-sm font-medium text-gray-500 mb-2">
            版本 v{version1}（旧）
          </h4>
          <div className="bg-gray-50 p-4 rounded border font-mono text-sm whitespace-pre-wrap">
            {oldText}
          </div>
        </div>
        <div>
          <h4 className="text-sm font-medium text-gray-500 mb-2">
            版本 v{version2}（新）
          </h4>
          <div className="bg-gray-50 p-4 rounded border font-mono text-sm whitespace-pre-wrap">
            {newText}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-5xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-4">
            <h3 className="text-lg font-semibold">
              版本对比: v{version1} → v{version2}
            </h3>
            <div className="flex gap-2">
              <button
                onClick={() => setViewMode('unified')}
                className={`px-3 py-1 text-sm rounded ${
                  viewMode === 'unified'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                统一视图
              </button>
              <button
                onClick={() => setViewMode('split')}
                className={`px-3 py-1 text-sm rounded ${
                  viewMode === 'split'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                分栏视图
              </button>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded"
          >
            <X size={20} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          <div className="mb-6">
            <h4 className="text-sm font-medium text-gray-500 mb-2">标题变更</h4>
            <div className="bg-gray-50 p-3 rounded border font-medium">
              {renderDiff(titleDiff, true)}
            </div>
          </div>

          <div>
            <h4 className="text-sm font-medium text-gray-500 mb-2">内容变更</h4>
            {viewMode === 'unified' ? (
              <div className="bg-gray-50 p-4 rounded border font-mono text-sm whitespace-pre-wrap">
                {renderDiff(contentDiff)}
              </div>
            ) : (
              renderSplitView()
            )}
          </div>
        </div>

        <div className="flex items-center justify-between p-4 border-t bg-gray-50">
          <div className="flex items-center gap-4 text-sm text-gray-500">
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 bg-green-200 rounded"></span>
              新增
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 bg-red-200 rounded"></span>
              删除
            </span>
          </div>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:bg-gray-200 rounded"
            >
              关闭
            </button>
            <button
              onClick={onRestore}
              className="px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 rounded"
            >
              恢复到此版本
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

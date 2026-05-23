'use client'

import { SearchResult } from '@/types'
import { FileText, X } from 'lucide-react'

interface SearchResultsProps {
  results: SearchResult[]
  onSelectNote: (noteId: string) => void
  onClose: () => void
}

export default function SearchResults({ results, onSelectNote, onClose }: SearchResultsProps) {
  if (results.length === 0) {
    return null
  }

  return (
    <div className="absolute top-16 left-4 right-4 bg-white border border-gray-200 rounded-lg shadow-lg z-20 max-h-96 overflow-y-auto">
      <div className="sticky top-0 bg-white border-b border-gray-200 p-3 flex items-center justify-between">
        <h3 className="font-medium text-gray-800">
          搜索结果 ({results.length})
        </h3>
        <button
          onClick={onClose}
          className="p-1 hover:bg-gray-100 rounded"
        >
          <X size={16} />
        </button>
      </div>
      <div className="p-2">
        {results.map(result => (
          <div
            key={result._id}
            className="p-3 hover:bg-gray-50 rounded cursor-pointer border border-gray-100 mb-2"
            onClick={() => onSelectNote(result._id)}
          >
            <div className="flex items-start gap-3">
              <FileText size={16} className="text-blue-500 mt-1" />
              <div className="flex-1 min-w-0">
                <h4 className="font-medium text-gray-800 truncate">
                  {result.highlight?.title ? (
                    <span dangerouslySetInnerHTML={{ __html: result.highlight.title[0] }} />
                  ) : (
                    result.title
                  )}
                </h4>
                <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                  {result.highlight?.content ? (
                    <span dangerouslySetInnerHTML={{ __html: result.highlight.content.join('...') }} />
                  ) : (
                    result.content.substring(0, 200) + '...'
                  )}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

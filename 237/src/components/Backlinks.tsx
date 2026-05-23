'use client'

import { useState } from 'react'
import { Note } from '@/types'
import { getBacklinks } from '@/lib/wikiLinks'
import { Link2, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react'

interface BacklinksProps {
  noteId: string
  notes: Note[]
  onSelectNote: (noteId: string) => void
}

export default function Backlinks({ noteId, notes, onSelectNote }: BacklinksProps) {
  const [isExpanded, setIsExpanded] = useState(true)
  
  const backlinks = getBacklinks(noteId, notes)

  if (backlinks.length === 0) {
    return null
  }

  return (
    <div className="border-t border-gray-200">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-4 py-2 hover:bg-gray-50"
      >
        <div className="flex items-center gap-2">
          <Link2 size={16} className="text-gray-500" />
          <span className="text-sm font-medium text-gray-700">
            反向链接 ({backlinks.length})
          </span>
        </div>
        {isExpanded ? (
          <ChevronUp size={16} className="text-gray-400" />
        ) : (
          <ChevronDown size={16} className="text-gray-400" />
        )}
      </button>
      
      {isExpanded && (
        <div className="px-4 pb-3 space-y-2">
          {backlinks.map(link => (
            <button
              key={link.noteId}
              onClick={() => onSelectNote(link.noteId)}
              className="w-full text-left p-2 rounded-lg hover:bg-gray-50 group"
            >
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-blue-600 group-hover:underline">
                  {link.title}
                </span>
                <ExternalLink size={12} className="text-gray-400 opacity-0 group-hover:opacity-100" />
              </div>
              <p className="text-xs text-gray-500 mt-1 line-clamp-2">
                {link.snippet}
              </p>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

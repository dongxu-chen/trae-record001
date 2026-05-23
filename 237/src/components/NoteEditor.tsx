'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { useDebounce } from '@/hooks/useDebounce'
import { setNoteCache, getNoteCache, clearNoteCache } from '@/hooks/useLocalStorage'
import MarkdownEditor from './MarkdownEditor'
import { Note } from '@/types'
import { Save, Eye, Edit2, Folder, HardDrive, Cloud, Network } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { resolveWikiLinks, extractLinkTitles, parseWikiLinks } from '@/lib/wikiLinks'
import Backlinks from './Backlinks'
import KnowledgeGraph from './KnowledgeGraph'

interface NoteEditorProps {
  note: Note | null
  notes: Note[]
  folders: any[]
  onUpdateNote: (noteId: string, updates: Partial<Note>) => void
  onSelectNote: (noteId: string) => void
  isSaving: boolean
}

const AUTO_SAVE_DEBOUNCE_MS = 5000

export default function NoteEditor({ note, notes, folders, onUpdateNote, onSelectNote, isSaving }: NoteEditorProps) {
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [showPreview, setShowPreview] = useState(false)
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null)
  const [hasLocalCache, setHasLocalCache] = useState(false)
  const [cacheInfo, setCacheInfo] = useState<{ timestamp: number } | null>(null)
  const [showGraph, setShowGraph] = useState(false)

  const debouncedTitle = useDebounce(title, AUTO_SAVE_DEBOUNCE_MS)
  const debouncedContent = useDebounce(content, AUTO_SAVE_DEBOUNCE_MS)

  const wikiLinkInfo = useMemo(() => {
    if (!note) return { outLinks: [], inLinks: [] }
    const outLinks = extractLinkTitles(content)
    return { outLinks }
  }, [content, note])

  const resolvedContent = useMemo(() => {
    if (!showPreview) return content
    const { content: resolved } = resolveWikiLinks(content, notes)
    return resolved
  }, [content, showPreview, notes])

  useEffect(() => {
    if (note) {
      const cache = getNoteCache(note._id)
      if (cache) {
        const cacheTime = new Date(cache.timestamp)
        const noteTime = new Date(note.updatedAt)
        
        if (cacheTime > noteTime) {
          setTitle(cache.title)
          setContent(cache.content)
          setHasLocalCache(true)
          setCacheInfo({ timestamp: cache.timestamp })
        } else {
          setTitle(note.title)
          setContent(note.content)
          setHasLocalCache(false)
          setCacheInfo(null)
        }
      } else {
        setTitle(note.title)
        setContent(note.content)
        setHasLocalCache(false)
        setCacheInfo(null)
      }
      setSelectedFolderId(note.folderId || null)
    }
  }, [note?._id])

  useEffect(() => {
    if (note && (title !== note.title || content !== note.content) {
      setNoteCache(note._id, title, content)
      setHasLocalCache(true)
      setCacheInfo({ timestamp: Date.now() })
    }
  }, [title, content])

  const handleUpdate = useCallback(() => {
    if (!note) return

    const updates: Partial<Note> = {}
    if (title !== note.title) updates.title = title
    if (content !== note.content) updates.content = content
    if (selectedFolderId !== note.folderId) updates.folderId = selectedFolderId

    if (Object.keys(updates).length > 0) {
      onUpdateNote(note._id, updates)
      clearNoteCache(note._id)
      setHasLocalCache(false)
      setCacheInfo(null)
    }
  }, [note, debouncedTitle, debouncedContent, selectedFolderId])

  useEffect(() => {
    if (note) {
      handleUpdate()
    }
  }, [debouncedTitle, debouncedContent, selectedFolderId])

  if (!note) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50">
        <div className="text-center text-gray-500">
          <Edit2 size={48} className="mx-auto mb-4 opacity-50" />
          <p className="text-lg">选择一个笔记或创建新笔记</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col bg-white overflow-hidden">
      <div className="border-b border-gray-200 p-4">
        <div className="flex items-center justify-between mb-4">
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="text-2xl font-bold text-gray-800 focus:outline-none focus:ring-0 border-none w-full bg-transparent"
            placeholder="笔记标题"
          />
          <div className="flex items-center gap-3">
            {hasLocalCache && (
              <div className="flex items-center gap-1 text-sm text-amber-600" title={`本地缓存: ${cacheInfo ? new Date(cacheInfo.timestamp).toLocaleTimeString() : ''}`}>
                <HardDrive size={14} />
                本地缓存
              </div>
            )}
            {isSaving && (
              <div className="flex items-center gap-1 text-sm text-gray-500">
                <Cloud size={14} className="animate-pulse" />
                保存中...
              </div>
            )}
            {!isSaving && !hasLocalCache && (
              <div className="flex items-center gap-1 text-sm text-green-600">
                <Cloud size={14} />
                已同步
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Folder size={16} className="text-gray-400" />
            <select
              value={selectedFolderId || ''}
              onChange={(e) => setSelectedFolderId(e.target.value || null)}
              className="text-sm text-gray-600 border-none bg-transparent focus:outline-none cursor-pointer"
            >
              <option value="">无文件夹</option>
              {folders.map(folder => (
                <option key={folder._id} value={folder._id}>
                  {folder.name}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowPreview(false)}
              className={`flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg ${
                !showPreview
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <Edit2 size={14} />
              编辑
            </button>
            <button
              onClick={() => setShowPreview(true)}
              className={`flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg ${
                showPreview
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <Eye size={14} />
              预览
            </button>
            <button
              onClick={() => setShowGraph(!showGraph)}
              className={`flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg ${
                showGraph
                  ? 'bg-green-100 text-green-700'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
              title="知识图谱"
            >
              <Network size={14} />
              图谱
            </button>
          </div>

          {wikiLinkInfo.outLinks.length > 0 && (
            <div className="flex items-center gap-2 ml-4">
              <span className="text-xs text-gray-500">出链:</span>
              <div className="flex gap-1">
                {wikiLinkInfo.outLinks.slice(0, 3).map(linkTitle => (
                  <span
                    key={linkTitle}
                    className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded"
                  >
                    {linkTitle}
                  </span>
                ))}
                {wikiLinkInfo.outLinks.length > 3 && (
                  <span className="text-xs text-gray-400">
                    +{wikiLinkInfo.outLinks.length - 3}
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-hidden flex flex-col">
        {showPreview ? (
          <div className="markdown-preview flex-1 overflow-y-auto p-6">
            <ReactMarkdown 
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[]}
            >
              {resolvedContent}
            </ReactMarkdown>
          </div>
        ) : (
          <div className="flex-1">
            <MarkdownEditor value={content} onChange={setContent} />
          </div>
        )}

        {note && (
          <Backlinks
            noteId={note._id}
            notes={notes}
            onSelectNote={onSelectNote}
          />
        )}
      </div>

      {showGraph && note && (
        <KnowledgeGraph
          notes={notes}
          currentNoteId={note._id}
          onSelectNote={onSelectNote}
          onClose={() => setShowGraph(false)}
        />
      )}
    </div>
  )
}

'use client'

import { useState } from 'react'
import { Plus, Folder, FileText, Tag, ChevronDown, ChevronRight, Trash2, Edit2, X, Check } from 'lucide-react'
import { Note, Folder as FolderType, Tag as TagType } from '@/types'

interface SidebarProps {
  notes: Note[]
  folders: FolderType[]
  tags: TagType[]
  selectedNote: Note | null
  selectedFolder: string | null
  selectedTag: string | null
  onSelectNote: (note: Note) => void
  onSelectFolder: (folderId: string | null) => void
  onSelectTag: (tagId: string | null) => void
  onCreateNote: () => void
  onCreateFolder: () => void
  onCreateTag: () => void
  onDeleteNote: (noteId: string) => void
  onDeleteFolder: (folderId: string) => void
  onDeleteTag: (tagId: string) => void
  onRenameFolder: (folderId: string, name: string) => void
  onRenameTag: (tagId: string, name: string) => void
}

export default function Sidebar({
  notes,
  folders,
  tags,
  selectedNote,
  selectedFolder,
  selectedTag,
  onSelectNote,
  onSelectFolder,
  onSelectTag,
  onCreateNote,
  onCreateFolder,
  onCreateTag,
  onDeleteNote,
  onDeleteFolder,
  onDeleteTag,
  onRenameFolder,
  onRenameTag,
}: SidebarProps) {
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set())
  const [editingFolder, setEditingFolder] = useState<string | null>(null)
  const [editingTag, setEditingTag] = useState<string | null>(null)
  const [editingName, setEditingName] = useState('')

  const toggleFolder = (folderId: string) => {
    setExpandedFolders(prev => {
      const newSet = new Set(prev)
      if (newSet.has(folderId)) {
        newSet.delete(folderId)
      } else {
        newSet.add(folderId)
      }
      return newSet
    })
  }

  const startEditingFolder = (folder: FolderType) => {
    setEditingFolder(folder._id)
    setEditingName(folder.name)
  }

  const startEditingTag = (tag: TagType) => {
    setEditingTag(tag._id)
    setEditingName(tag.name)
  }

  const saveFolderName = (folderId: string) => {
    if (editingName.trim()) {
      onRenameFolder(folderId, editingName.trim())
    }
    setEditingFolder(null)
    setEditingName('')
  }

  const saveTagName = (tagId: string) => {
    if (editingName.trim()) {
      onRenameTag(tagId, editingName.trim())
    }
    setEditingTag(null)
    setEditingName('')
  }

  const filteredNotes = notes.filter(note => {
    if (selectedFolder) {
      return note.folderId === selectedFolder
    }
    if (selectedTag) {
      return note.tags.includes(selectedTag)
    }
    return true
  })

  const notesByFolder = filteredNotes.reduce((acc, note) => {
    const folderId = note.folderId || 'root'
    if (!acc[folderId]) {
      acc[folderId] = []
    }
    acc[folderId].push(note)
    return acc
  }, {} as Record<string, Note[]>)

  return (
    <div className="w-64 bg-gray-50 border-r border-gray-200 h-screen overflow-y-auto flex flex-col">
      <div className="p-4 border-b border-gray-200">
        <h1 className="text-xl font-bold text-gray-800 mb-4">Markdown 笔记</h1>
        <button
          onClick={onCreateNote}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus size={18} />
          新建笔记
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="p-2">
          <div className="flex items-center justify-between px-2 py-1">
            <h2 className="text-sm font-semibold text-gray-600">文件夹</h2>
            <button
              onClick={onCreateFolder}
              className="p-1 hover:bg-gray-200 rounded"
            >
              <Plus size={14} />
            </button>
          </div>
          
          <div className="mt-1">
            {folders.map(folder => (
              <div key={folder._id}>
                <div
                  className={`flex items-center gap-1 px-2 py-1.5 rounded cursor-pointer hover:bg-gray-200 ${
                    selectedFolder === folder._id ? 'bg-blue-100 text-blue-700' : ''
                  }`}
                >
                  <button
                    onClick={() => toggleFolder(folder._id)}
                    className="p-0.5 hover:bg-gray-300 rounded"
                  >
                    {expandedFolders.has(folder._id) ? (
                      <ChevronDown size={14} />
                    ) : (
                      <ChevronRight size={14} />
                    )}
                  </button>
                  <Folder size={16} className="text-yellow-500" />
                  {editingFolder === folder._id ? (
                    <input
                      type="text"
                      value={editingName}
                      onChange={(e) => setEditingName(e.target.value)}
                      className="flex-1 px-1 py-0.5 text-sm border rounded"
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') saveFolderName(folder._id)
                        if (e.key === 'Escape') {
                          setEditingFolder(null)
                          setEditingName('')
                        }
                      }}
                    />
                  ) : (
                    <span
                      className="flex-1 text-sm truncate"
                      onClick={() => onSelectFolder(folder._id)}
                    >
                      {folder.name}
                    </span>
                  )}
                  <div className="flex items-center gap-1">
                    {editingFolder === folder._id ? (
                      <>
                        <button
                          onClick={() => saveFolderName(folder._id)}
                          className="p-0.5 hover:bg-green-200 rounded"
                        >
                          <Check size={12} />
                        </button>
                        <button
                          onClick={() => {
                            setEditingFolder(null)
                            setEditingName('')
                          }}
                          className="p-0.5 hover:bg-red-200 rounded"
                        >
                          <X size={12} />
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          onClick={() => startEditingFolder(folder)}
                          className="p-0.5 hover:bg-gray-300 rounded opacity-0 group-hover:opacity-100"
                        >
                          <Edit2 size={12} />
                        </button>
                        <button
                          onClick={() => onDeleteFolder(folder._id)}
                          className="p-0.5 hover:bg-red-200 rounded opacity-0 group-hover:opacity-100"
                        >
                          <Trash2 size={12} />
                        </button>
                      </>
                    )}
                  </div>
                </div>
                {expandedFolders.has(folder._id) && (
                  <div className="ml-6">
                    {(notesByFolder[folder._id] || []).map(note => (
                      <div
                        key={note._id}
                        className={`flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer hover:bg-gray-200 ${
                          selectedNote?._id === note._id ? 'bg-blue-100 text-blue-700' : ''
                        }`}
                        onClick={() => onSelectNote(note)}
                      >
                        <FileText size={14} />
                        <span className="text-sm truncate flex-1">{note.title}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="p-2 mt-4">
          <div className="flex items-center justify-between px-2 py-1">
            <h2 className="text-sm font-semibold text-gray-600">标签</h2>
            <button
              onClick={onCreateTag}
              className="p-1 hover:bg-gray-200 rounded"
            >
              <Plus size={14} />
            </button>
          </div>
          
          <div className="mt-1">
            {tags.map(tag => (
              <div
                key={tag._id}
                className={`flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer hover:bg-gray-200 ${
                  selectedTag === tag._id ? 'bg-blue-100' : ''
                }`}
              >
                <Tag size={14} style={{ color: tag.color }} />
                {editingTag === tag._id ? (
                  <input
                    type="text"
                    value={editingName}
                    onChange={(e) => setEditingName(e.target.value)}
                    className="flex-1 px-1 py-0.5 text-sm border rounded"
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') saveTagName(tag._id)
                      if (e.key === 'Escape') {
                        setEditingTag(null)
                        setEditingName('')
                      }
                    }}
                  />
                ) : (
                  <span
                    className="flex-1 text-sm truncate"
                    onClick={() => onSelectTag(tag._id)}
                  >
                    {tag.name}
                  </span>
                )}
                <div className="flex items-center gap-1">
                  {editingTag === tag._id ? (
                    <>
                      <button
                        onClick={() => saveTagName(tag._id)}
                        className="p-0.5 hover:bg-green-200 rounded"
                      >
                        <Check size={12} />
                      </button>
                      <button
                        onClick={() => {
                          setEditingTag(null)
                          setEditingName('')
                        }}
                        className="p-0.5 hover:bg-red-200 rounded"
                      >
                        <X size={12} />
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={() => startEditingTag(tag)}
                        className="p-0.5 hover:bg-gray-300 rounded"
                      >
                        <Edit2 size={12} />
                      </button>
                      <button
                        onClick={() => onDeleteTag(tag._id)}
                        className="p-0.5 hover:bg-red-200 rounded"
                      >
                        <Trash2 size={12} />
                      </button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="p-2 mt-4">
          <div className="flex items-center justify-between px-2 py-1">
            <h2 className="text-sm font-semibold text-gray-600">
              {selectedFolder || selectedTag ? '筛选笔记' : '所有笔记'}
            </h2>
            {(selectedFolder || selectedTag) && (
              <button
                onClick={() => {
                  onSelectFolder(null)
                  onSelectTag(null)
                }}
                className="text-xs text-blue-600 hover:underline"
              >
                清除筛选
              </button>
            )}
          </div>
          
          <div className="mt-1">
            {(notesByFolder['root'] || []).map(note => (
              <div
                key={note._id}
                className={`flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer hover:bg-gray-200 ${
                  selectedNote?._id === note._id ? 'bg-blue-100 text-blue-700' : ''
                }`}
                onClick={() => onSelectNote(note)}
              >
                <FileText size={14} />
                <span className="text-sm truncate flex-1">{note.title}</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onDeleteNote(note._id)
                  }}
                  className="p-0.5 hover:bg-red-200 rounded opacity-0 group-hover:opacity-100"
                >
                  <Trash2 size={12} />
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

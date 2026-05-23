'use client'

import { useState, useEffect } from 'react'
import Sidebar from '@/components/Sidebar'
import Toolbar from '@/components/Toolbar'
import NoteEditor from '@/components/NoteEditor'
import SearchResults from '@/components/SearchResults'
import { Note, Folder, Tag, Version, SearchResult } from '@/types'

export default function Home() {
  const [notes, setNotes] = useState<Note[]>([])
  const [folders, setFolders] = useState<Folder[]>([])
  const [tags, setTags] = useState<Tag[]>([])
  const [selectedNote, setSelectedNote] = useState<Note | null>(null)
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null)
  const [selectedTag, setSelectedTag] = useState<string | null>(null)
  const [versions, setVersions] = useState<Version[]>([])
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [shareToken, setShareToken] = useState<string>('')
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    fetchNotes()
    fetchFolders()
    fetchTags()
  }, [])

  useEffect(() => {
    if (selectedNote) {
      fetchVersions(selectedNote._id)
      fetchShareInfo(selectedNote._id)
    }
  }, [selectedNote?._id])

  const fetchNotes = async () => {
    try {
      const res = await fetch('/api/notes')
      const data = await res.json()
      setNotes(data)
    } catch (error) {
      console.error('Failed to fetch notes:', error)
    }
  }

  const fetchFolders = async () => {
    try {
      const res = await fetch('/api/folders')
      const data = await res.json()
      setFolders(data)
    } catch (error) {
      console.error('Failed to fetch folders:', error)
    }
  }

  const fetchTags = async () => {
    try {
      const res = await fetch('/api/tags')
      const data = await res.json()
      setTags(data)
    } catch (error) {
      console.error('Failed to fetch tags:', error)
    }
  }

  const fetchVersions = async (noteId: string) => {
    try {
      const res = await fetch(`/api/notes/${noteId}/versions`)
      const data = await res.json()
      setVersions(data)
    } catch (error) {
      console.error('Failed to fetch versions:', error)
    }
  }

  const fetchShareInfo = async (noteId: string) => {
    try {
      const res = await fetch(`/api/notes/${noteId}/share`)
      const data = await res.json()
      if (data?.shareToken) {
        setShareToken(data.shareToken)
      } else {
        setShareToken('')
      }
    } catch (error) {
      console.error('Failed to fetch share info:', error)
      setShareToken('')
    }
  }

  const createNote = async () => {
    try {
      const res = await fetch('/api/notes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: '新建笔记',
          content: '',
          folderId: selectedFolder,
        }),
      })
      const newNote = await res.json()
      setNotes([newNote, ...notes])
      setSelectedNote(newNote)
    } catch (error) {
      console.error('Failed to create note:', error)
    }
  }

  const createFolder = async () => {
    const name = prompt('输入文件夹名称:')
    if (!name) return

    try {
      const res = await fetch('/api/folders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      })
      const newFolder = await res.json()
      setFolders([...folders, newFolder])
    } catch (error) {
      console.error('Failed to create folder:', error)
    }
  }

  const createTag = async () => {
    const name = prompt('输入标签名称:')
    if (!name) return

    const colors = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6', '#8b5cf6', '#ec4899']
    const color = colors[Math.floor(Math.random() * colors.length)]

    try {
      const res = await fetch('/api/tags', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, color }),
      })
      const newTag = await res.json()
      setTags([...tags, newTag])
    } catch (error) {
      console.error('Failed to create tag:', error)
    }
  }

  const updateNote = async (noteId: string, updates: Partial<Note>) => {
    setIsSaving(true)
    try {
      const res = await fetch(`/api/notes/${noteId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      })
      const updatedNote = await res.json()
      
      setNotes(notes.map(n => n._id === noteId ? updatedNote : n))
      if (selectedNote?._id === noteId) {
        setSelectedNote(updatedNote)
      }
    } catch (error) {
      console.error('Failed to update note:', error)
    } finally {
      setTimeout(() => setIsSaving(false), 500)
    }
  }

  const deleteNote = async (noteId: string) => {
    if (!confirm('确定要删除此笔记吗？')) return

    try {
      await fetch(`/api/notes/${noteId}`, { method: 'DELETE' })
      setNotes(notes.filter(n => n._id !== noteId))
      if (selectedNote?._id === noteId) {
        setSelectedNote(null)
      }
    } catch (error) {
      console.error('Failed to delete note:', error)
    }
  }

  const deleteFolder = async (folderId: string) => {
    if (!confirm('确定要删除此文件夹吗？文件夹内的笔记将移至根目录。')) return

    try {
      await fetch(`/api/folders/${folderId}`, { method: 'DELETE' })
      setFolders(folders.filter(f => f._id !== folderId))
      if (selectedFolder === folderId) {
        setSelectedFolder(null)
      }
    } catch (error) {
      console.error('Failed to delete folder:', error)
    }
  }

  const deleteTag = async (tagId: string) => {
    if (!confirm('确定要删除此标签吗？')) return

    try {
      await fetch(`/api/tags/${tagId}`, { method: 'DELETE' })
      setTags(tags.filter(t => t._id !== tagId))
      if (selectedTag === tagId) {
        setSelectedTag(null)
      }
    } catch (error) {
      console.error('Failed to delete tag:', error)
    }
  }

  const renameFolder = async (folderId: string, name: string) => {
    try {
      const res = await fetch(`/api/folders/${folderId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      })
      const updatedFolder = await res.json()
      setFolders(folders.map(f => f._id === folderId ? updatedFolder : f))
    } catch (error) {
      console.error('Failed to rename folder:', error)
    }
  }

  const renameTag = async (tagId: string, name: string) => {
    try {
      const res = await fetch(`/api/tags/${tagId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      })
      const updatedTag = await res.json()
      setTags(tags.map(t => t._id === tagId ? updatedTag : t))
    } catch (error) {
      console.error('Failed to rename tag:', error)
    }
  }

  const handleSearch = async (query: string) => {
    try {
      const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`)
      const data = await res.json()
      setSearchResults(data)
    } catch (error) {
      console.error('Failed to search notes:', error)
      setSearchResults([])
    }
  }

  const handleExport = (format: 'md' | 'html' | 'pdf') => {
    if (!selectedNote) return
    window.open(`/api/notes/${selectedNote._id}/export?format=${format}`, '_blank')
  }

  const handleShare = async () => {
    if (!selectedNote) return
    try {
      const res = await fetch(`/api/notes/${selectedNote._id}/share`, {
        method: 'POST',
      })
      const share = await res.json()
      setShareToken(share.shareToken)
      
      setNotes(notes.map(n => 
        n._id === selectedNote._id 
          ? { ...n, isPublic: share.isActive } 
          : n
      ))
      setSelectedNote({ ...selectedNote, isPublic: share.isActive })
    } catch (error) {
      console.error('Failed to toggle share:', error)
    }
  }

  const handleRestoreVersion = (version: Version) => {
    if (!selectedNote) return
    if (!confirm(`确定要恢复到版本 v${version.versionNumber} 吗？`)) return

    updateNote(selectedNote._id, {
      title: version.title,
      content: version.content,
    })
  }

  const handleSelectNoteFromSearch = (noteId: string) => {
    const note = notes.find(n => n._id === noteId)
    if (note) {
      setSelectedNote(note)
      setSearchResults([])
    }
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        notes={notes}
        folders={folders}
        tags={tags}
        selectedNote={selectedNote}
        selectedFolder={selectedFolder}
        selectedTag={selectedTag}
        onSelectNote={setSelectedNote}
        onSelectFolder={setSelectedFolder}
        onSelectTag={setSelectedTag}
        onCreateNote={createNote}
        onCreateFolder={createFolder}
        onCreateTag={createTag}
        onDeleteNote={deleteNote}
        onDeleteFolder={deleteFolder}
        onDeleteTag={deleteTag}
        onRenameFolder={renameFolder}
        onRenameTag={renameTag}
      />

      <div className="flex-1 flex flex-col relative">
        <Toolbar
          note={selectedNote}
          versions={versions}
          tags={tags}
          onSearch={handleSearch}
          onExport={handleExport}
          onShare={handleShare}
          onRestoreVersion={handleRestoreVersion}
          onUpdateNote={(updates) => {
            if (selectedNote) {
              updateNote(selectedNote._id, updates)
            }
          }}
          shareToken={shareToken}
        />

        <SearchResults
          results={searchResults}
          onSelectNote={handleSelectNoteFromSearch}
          onClose={() => setSearchResults([])}
        />

        <NoteEditor
          note={selectedNote}
          folders={folders}
          onUpdateNote={updateNote}
          isSaving={isSaving}
        />
      </div>
    </div>
  )
}

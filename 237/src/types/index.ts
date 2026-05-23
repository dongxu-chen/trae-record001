export interface Note {
  _id: string
  title: string
  content: string
  ocrText?: string
  folderId?: string
  tags: string[]
  isPublic: boolean
  createdAt: string
  updatedAt: string
}

export interface Folder {
  _id: string
  name: string
  parentId?: string
  createdAt: string
  updatedAt: string
}

export interface Tag {
  _id: string
  name: string
  color: string
  createdAt: string
  updatedAt: string
}

export interface Version {
  _id: string
  noteId: string
  title: string
  content: string
  versionNumber: number
  createdAt: string
}

export interface Share {
  _id: string
  noteId: string
  shareToken: string
  isActive: boolean
  expiresAt?: string
  createdAt: string
}

export interface SearchResult {
  _id: string
  title: string
  content: string
  highlight?: {
    title?: string[]
    content?: string[]
  }
}

export interface FileTreeNode {
  name: string
  path: string
  type: 'file' | 'directory'
  children?: FileTreeNode[]
}

export interface DiffTreeNode extends FileTreeNode {
  status: 'added' | 'deleted' | 'modified' | 'unchanged'
  children?: DiffTreeNode[]
}

export interface Hunk {
  oldStart: number
  oldLines: number
  newStart: number
  newLines: number
  changes: Change[]
}

export interface Change {
  type: 'add' | 'delete' | 'normal'
  oldLineNumber?: number
  newLineNumber?: number
  content: string
}

export interface DiffStats {
  additions: number
  deletions: number
  changes: number
}

export type CompareMode = 'code' | 'directory'
export type DiffEditorLayout = 'side-by-side' | 'inline'

export interface ReviewComment {
  id: string
  filePath: string
  lineNumber: number
  side: 'old' | 'new'
  author: string
  avatar: string
  content: string
  timestamp: number
  resolved: boolean
  replies: ReviewReply[]
}

export interface ReviewReply {
  id: string
  author: string
  avatar: string
  content: string
  timestamp: number
}

export interface ConflictRegion {
  startLine: number
  endLine: number
  currentContent: string
  incomingContent: string
  currentLabel: string
  incomingLabel: string
  resolved: boolean
  resolution: 'current' | 'incoming' | 'both' | null
}

export interface CodeVersion {
  id: string
  label: string
  code: string
  timestamp: number
  description: string
}

export type PlaybackState = 'idle' | 'playing' | 'paused'


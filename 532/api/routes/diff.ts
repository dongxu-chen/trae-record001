import { Router, type Request, type Response } from 'express'
import * as Diff from 'diff'
import multer from 'multer'

const router = Router()

const upload = multer({ storage: multer.memoryStorage() })

interface ChangeItem {
  type: 'add' | 'delete' | 'normal'
  oldLineNumber?: number
  newLineNumber?: number
  content: string
}

interface Hunk {
  oldStart: number
  oldLines: number
  newStart: number
  newLines: number
  changes: ChangeItem[]
}

interface FileTreeNode {
  name: string
  path: string
  type: 'file' | 'directory'
  children?: FileTreeNode[]
}

interface DiffTreeNode extends FileTreeNode {
  status: 'added' | 'deleted' | 'modified' | 'unchanged'
}

router.post('/text', (req: Request, res: Response): void => {
  const { oldText, newText } = req.body

  if (typeof oldText !== 'string' || typeof newText !== 'string') {
    res.status(400).json({ success: false, error: 'oldText and newText are required strings' })
    return
  }

  const changes = Diff.diffLines(oldText, newText)
  const hunks: Hunk[] = []
  let oldLine = 1
  let newLine = 1
  let additions = 0
  let deletions = 0
  let currentHunk: Hunk | null = null
  let inHunk = false

  for (const change of changes) {
    const lines = change.value.replace(/\n$/, '').split('\n')

    if (!change.added && !change.removed) {
      if (inHunk && currentHunk) {
        const contextLines = lines.slice(0, 3)
        for (const line of contextLines) {
          currentHunk.changes.push({
            type: 'normal',
            oldLineNumber: oldLine,
            newLineNumber: newLine,
            content: line,
          })
          oldLine++
          newLine++
          currentHunk.oldLines++
          currentHunk.newLines++
        }
        hunks.push(currentHunk)
        currentHunk = null
        inHunk = false

        oldLine += lines.length - contextLines.length
        newLine += lines.length - contextLines.length
      } else {
        oldLine += lines.length
        newLine += lines.length
      }
    } else {
      if (!inHunk) {
        currentHunk = {
          oldStart: oldLine,
          oldLines: 0,
          newStart: newLine,
          newLines: 0,
          changes: [],
        }
        inHunk = true
      }

      for (const line of lines) {
        if (change.removed) {
          currentHunk!.changes.push({
            type: 'delete',
            oldLineNumber: oldLine,
            content: line,
          })
          oldLine++
          currentHunk!.oldLines++
          deletions++
        } else if (change.added) {
          currentHunk!.changes.push({
            type: 'add',
            newLineNumber: newLine,
            content: line,
          })
          newLine++
          currentHunk!.newLines++
          additions++
        }
      }
    }
  }

  if (inHunk && currentHunk) {
    hunks.push(currentHunk)
  }

  res.json({
    success: true,
    data: {
      hunks,
      stats: { additions, deletions, changes: additions + deletions },
    },
  })
})

router.post('/upload', upload.array('files', 200), (req: Request, res: Response): void => {
  const files = req.files as Express.Multer.File[]
  const basePath = req.body.basePath || ''

  if (!files || files.length === 0) {
    res.status(400).json({ success: false, error: 'No files uploaded' })
    return
  }

  const tree: FileTreeNode[] = []
  const fileContents: Record<string, string> = {}

  for (const file of files) {
    const relativePath = basePath
      ? file.originalname.replace(new RegExp(`^${basePath.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}[/\\\\]`), '')
      : file.originalname

    const parts = relativePath.split(/[/\\]/)
    let currentLevel = tree

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i]
      const isFile = i === parts.length - 1
      const currentPath = parts.slice(0, i + 1).join('/')

      if (isFile) {
        currentLevel.push({
          name: part,
          path: currentPath,
          type: 'file',
        })
        fileContents[currentPath] = file.buffer.toString('utf-8')
      } else {
        let existing = currentLevel.find((n) => n.name === part && n.type === 'directory')
        if (!existing) {
          existing = {
            name: part,
            path: currentPath,
            type: 'directory',
            children: [],
          }
          currentLevel.push(existing)
        }
        currentLevel = existing.children!
      }
    }
  }

  const sortTree = (nodes: FileTreeNode[]): FileTreeNode[] => {
    return nodes.sort((a, b) => {
      if (a.type !== b.type) return a.type === 'directory' ? -1 : 1
      return a.name.localeCompare(b.name)
    }).map((node) => ({
      ...node,
      children: node.children ? sortTree(node.children) : undefined,
    }))
  }

  res.json({
    success: true,
    data: {
      tree: sortTree(tree),
      files: fileContents,
    },
  })
})

router.post('/directory', (req: Request, res: Response): void => {
  const { oldFiles, newFiles } = req.body as {
    oldFiles: Record<string, string>
    newFiles: Record<string, string>
  }

  if (!oldFiles || !newFiles) {
    res.status(400).json({ success: false, error: 'oldFiles and newFiles are required' })
    return
  }

  const allPaths = new Set([...Object.keys(oldFiles), ...Object.keys(newFiles)])
  const diffResults: Record<string, 'added' | 'deleted' | 'modified' | 'unchanged'> = {}
  const changedFiles: string[] = []

  for (const filePath of allPaths) {
    const inOld = filePath in oldFiles
    const inNew = filePath in newFiles

    if (inOld && !inNew) {
      diffResults[filePath] = 'deleted'
      changedFiles.push(filePath)
    } else if (!inOld && inNew) {
      diffResults[filePath] = 'added'
      changedFiles.push(filePath)
    } else {
      const changes = Diff.diffLines(oldFiles[filePath], newFiles[filePath])
      const hasChanges = changes.some((c) => c.added || c.removed)
      diffResults[filePath] = hasChanges ? 'modified' : 'unchanged'
      if (hasChanges) changedFiles.push(filePath)
    }
  }

  const combineStatuses = (
    statuses: Array<'added' | 'deleted' | 'modified' | 'unchanged'>
  ): 'added' | 'deleted' | 'modified' | 'unchanged' => {
    if (statuses.length === 0) return 'unchanged'

    const unique = [...new Set(statuses)]
    if (unique.length === 1) return unique[0]

    const hasAdded = unique.includes('added')
    const hasDeleted = unique.includes('deleted')
    const hasModified = unique.includes('modified')

    if (hasModified) return 'modified'
    if (hasAdded && hasDeleted) return 'modified'
    if (hasAdded) return 'added'
    if (hasDeleted) return 'deleted'

    return 'unchanged'
  }

  const propagateDirStatusRecursive = (nodes: DiffTreeNode[]): DiffTreeNode[] => {
    return nodes.map((node) => {
      if (node.type === 'file') return node

      if (!node.children || node.children.length === 0) {
        return { ...node, status: 'unchanged' }
      }

      const processedChildren = propagateDirStatusRecursive(node.children as DiffTreeNode[])
      const childStatuses = processedChildren.map((c) => c.status)
      const combinedStatus = combineStatuses(childStatuses)

      return {
        ...node,
        status: combinedStatus,
        children: processedChildren,
      }
    })
  }

  const buildDiffTree = (paths: Iterable<string>, statuses: Record<string, 'added' | 'deleted' | 'modified' | 'unchanged'>): DiffTreeNode[] => {
    const root: DiffTreeNode[] = []

    for (const filePath of paths) {
      const parts = filePath.split(/[/\\]/)
      let currentLevel = root

      for (let i = 0; i < parts.length; i++) {
        const part = parts[i]
        const isFile = i === parts.length - 1
        const currentPath = parts.slice(0, i + 1).join('/')

        if (isFile) {
          currentLevel.push({
            name: part,
            path: currentPath,
            type: 'file',
            status: statuses[filePath] || 'unchanged',
          })
        } else {
          let existing = currentLevel.find((n) => n.name === part && n.type === 'directory')
          if (!existing) {
            existing = {
              name: part,
              path: currentPath,
              type: 'directory',
              status: 'unchanged',
              children: [],
            }
            currentLevel.push(existing)
          }
          currentLevel = (existing as DiffTreeNode).children! as DiffTreeNode[]
        }
      }
    }

    const sortTree = (nodes: DiffTreeNode[]): DiffTreeNode[] => {
      return nodes.sort((a, b) => {
        if (a.type !== b.type) return a.type === 'directory' ? -1 : 1
        return a.name.localeCompare(b.name)
      }).map((node) => {
        if (node.type === 'directory' && node.children) {
          return { ...node, children: sortTree(node.children as DiffTreeNode[]) }
        }
        return node
      })
    }

    const sorted = sortTree(root)
    return propagateDirStatusRecursive(sorted)
  }

  function getAllStatuses(nodes: DiffTreeNode[]): string[] {
    const statuses: string[] = []
    for (const node of nodes) {
      statuses.push(node.status)
      if (node.children) statuses.push(...getAllStatuses(node.children as DiffTreeNode[]))
    }
    return statuses
  }

  const diffTree = buildDiffTree(allPaths, diffResults)

  res.json({
    success: true,
    data: {
      diffTree,
      changedFiles,
      diffResults,
    },
  })
})

router.post('/resolve-conflicts', (req: Request, res: Response): void => {
  const { code, resolutions } = req.body as {
    code: string
    resolutions: Array<{ startLine: number; endLine: number; resolution: 'current' | 'incoming' | 'both' }>
  }

  if (!code || !resolutions) {
    res.status(400).json({ success: false, error: 'code and resolutions are required' })
    return
  }

  const lines = code.split('\n')
  const result: string[] = []
  let i = 0
  let resolutionIndex = 0

  while (i < lines.length) {
    if (lines[i].startsWith('<<<<<<<')) {
      const resolution = resolutions[resolutionIndex]
      resolutionIndex++

      const currentContent: string[] = []
      const incomingContent: string[] = []
      let inCurrent = true
      i++

      while (i < lines.length && !lines[i].startsWith('>>>>>>>')) {
        if (lines[i].startsWith('=======')) {
          inCurrent = false
          i++
          continue
        }
        if (inCurrent) {
          currentContent.push(lines[i])
        } else {
          incomingContent.push(lines[i])
        }
        i++
      }

      if (i < lines.length) i++

      if (resolution) {
        if (resolution.resolution === 'current') {
          result.push(...currentContent)
        } else if (resolution.resolution === 'incoming') {
          result.push(...incomingContent)
        } else if (resolution.resolution === 'both') {
          result.push(...currentContent)
          result.push(...incomingContent)
        }
      }
    } else {
      result.push(lines[i])
      i++
    }
  }

  res.json({
    success: true,
    data: { resolvedCode: result.join('\n') },
  })
})

export default router

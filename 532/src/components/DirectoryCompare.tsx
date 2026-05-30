import { useCallback, useState } from 'react'
import { DiffEditor } from '@monaco-editor/react'
import { useDiffStore } from '@/store/diffStore'
import FileTree from '@/components/FileTree'
import { getLanguageFromPath } from '@/utils/languages'
import { Upload, FolderArchive } from 'lucide-react'
import type { DiffTreeNode } from '@/types'

type StatusPriority = Record<string, number>

const STATUS_PRIORITY: StatusPriority = {
  unchanged: 0,
  added: 1,
  deleted: 2,
  modified: 3,
}

function combineStatuses(
  statuses: Array<'added' | 'deleted' | 'modified' | 'unchanged'>
): 'added' | 'deleted' | 'modified' | 'unchanged' {
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

function propagateDirStatusRecursive(nodes: DiffTreeNode[]): DiffTreeNode[] {
  return nodes.map((node) => {
    if (node.type === 'file') return node

    if (!node.children || node.children.length === 0) {
      return { ...node, status: 'unchanged' }
    }

    const processedChildren = propagateDirStatusRecursive(node.children)
    const childStatuses = processedChildren.map((c) => c.status)
    const combinedStatus = combineStatuses(childStatuses)

    return {
      ...node,
      status: combinedStatus,
      children: processedChildren,
    }
  })
}

function convertToDiffTree(
  oldFiles: Record<string, string>,
  newFiles: Record<string, string>
): DiffTreeNode[] {
  const allPaths = new Set([...Object.keys(oldFiles), ...Object.keys(newFiles)])
  const nodes: DiffTreeNode[] = []

  const fileStatusCache: Record<string, 'added' | 'deleted' | 'modified' | 'unchanged'> = {}

  for (const filePath of allPaths) {
    const inOld = filePath in oldFiles
    const inNew = filePath in newFiles
    let status: 'added' | 'deleted' | 'modified' | 'unchanged' = 'unchanged'

    if (inOld && !inNew) status = 'deleted'
    else if (!inOld && inNew) status = 'added'
    else if (oldFiles[filePath] !== newFiles[filePath]) status = 'modified'

    fileStatusCache[filePath] = status

    const parts = filePath.split(/[/\\]/)
    let currentLevel = nodes

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i]
      const isFile = i === parts.length - 1
      const currentPath = parts.slice(0, i + 1).join('/')

      if (isFile) {
        currentLevel.push({ name: part, path: currentPath, type: 'file', status })
      } else {
        let existing = currentLevel.find((n) => n.name === part && n.type === 'directory')
        if (!existing) {
          existing = { name: part, path: currentPath, type: 'directory', status: 'unchanged', children: [] }
          currentLevel.push(existing)
        }
        currentLevel = existing.children as DiffTreeNode[]
      }
    }
  }

  const sortNodes = (ns: DiffTreeNode[]): DiffTreeNode[] => {
    return ns.sort((a, b) => {
      if (a.type !== b.type) return a.type === 'directory' ? -1 : 1
      return a.name.localeCompare(b.name)
    }).map((n) => ({ ...n, children: n.children ? sortNodes(n.children) : undefined }))
  }

  const sorted = sortNodes(nodes)
  return propagateDirStatusRecursive(sorted)
}

export default function DirectoryCompare() {
  const {
    oldFiles,
    newFiles,
    diffTree,
    setDiffTree,
    setOldFiles,
    setNewFiles,
    selectedFile,
    setSelectedFile,
    setLanguage,
    setOldCode,
    setNewCode,
    setIsComparing,
  } = useDiffStore()

  const [isDragOver, setIsDragOver] = useState<'old' | 'new' | null>(null)

  const handleDirectorySelect = useCallback(
    async (side: 'old' | 'new') => {
      const input = document.createElement('input')
      input.type = 'file'
      input.webkitdirectory = true
      input.multiple = true
      input.onchange = async () => {
        const files = input.files
        if (!files) return

        const fileContents: Record<string, string> = {}
        const processFiles = Array.from(files).map(async (file) => {
          const text = await file.text()
          fileContents[file.webkitRelativePath || file.name] = text
        })
        await Promise.all(processFiles)

        if (side === 'old') {
          setOldFiles(fileContents)
        } else {
          setNewFiles(fileContents)
        }

        const currentOld = side === 'old' ? fileContents : oldFiles
        const currentNew = side === 'new' ? fileContents : newFiles

        if (Object.keys(currentOld).length > 0 && Object.keys(currentNew).length > 0) {
          const tree = convertToDiffTree(currentOld, currentNew)
          setDiffTree(tree)
        }
      }
      input.click()
    },
    [oldFiles, newFiles, setOldFiles, setNewFiles, setDiffTree]
  )

  const handleFileSelect = useCallback(
    (path: string) => {
      setSelectedFile(path)
      const oldContent = oldFiles[path] ?? ''
      const newContent = newFiles[path] ?? ''
      setOldCode(oldContent)
      setNewCode(newContent)
      setLanguage(getLanguageFromPath(path))
      setIsComparing(true)
    },
    [oldFiles, newFiles, setSelectedFile, setOldCode, setNewCode, setLanguage, setIsComparing]
  )

  const treeNodes = diffTree ? diffTree : convertToDiffTree(oldFiles, newFiles)
  const hasFiles = Object.keys(oldFiles).length > 0 || Object.keys(newFiles).length > 0

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {!hasFiles ? (
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="flex gap-8">
            <div
              className={`w-72 h-48 rounded-2xl border-2 border-dashed flex flex-col items-center justify-center gap-4 cursor-pointer transition-all duration-300 ${
                isDragOver === 'old'
                  ? 'border-red-400 bg-red-500/10 scale-105'
                  : 'border-[#2a2a4a] bg-[#0d0d1a] hover:border-red-400/50 hover:bg-red-500/5'
              }`}
              onClick={() => handleDirectorySelect('old')}
              onDragOver={(e) => { e.preventDefault(); setIsDragOver('old') }}
              onDragLeave={() => setIsDragOver(null)}
              onDrop={(e) => { e.preventDefault(); setIsDragOver(null) }}
            >
              <div className="w-12 h-12 rounded-xl bg-red-500/10 flex items-center justify-center">
                <FolderArchive size={24} className="text-red-400" />
              </div>
              <div className="text-center">
                <p className="text-sm font-semibold text-zinc-300">旧版本目录</p>
                <p className="text-xs text-zinc-500 mt-1">点击选择或拖拽上传</p>
              </div>
            </div>

            <div
              className={`w-72 h-48 rounded-2xl border-2 border-dashed flex flex-col items-center justify-center gap-4 cursor-pointer transition-all duration-300 ${
                isDragOver === 'new'
                  ? 'border-emerald-400 bg-emerald-500/10 scale-105'
                  : 'border-[#2a2a4a] bg-[#0d0d1a] hover:border-emerald-400/50 hover:bg-emerald-500/5'
              }`}
              onClick={() => handleDirectorySelect('new')}
              onDragOver={(e) => { e.preventDefault(); setIsDragOver('new') }}
              onDragLeave={() => setIsDragOver(null)}
              onDrop={(e) => { e.preventDefault(); setIsDragOver(null) }}
            >
              <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center">
                <Upload size={24} className="text-emerald-400" />
              </div>
              <div className="text-center">
                <p className="text-sm font-semibold text-zinc-300">新版本目录</p>
                <p className="text-xs text-zinc-500 mt-1">点击选择或拖拽上传</p>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex overflow-hidden">
          <div className="w-72 border-r border-[#2a2a4a] bg-[#0d0d1a] flex flex-col shrink-0">
            <div className="px-3 py-2 border-b border-[#2a2a4a] flex items-center justify-between">
              <span className="text-xs font-semibold text-zinc-400">文件差异</span>
              <div className="flex items-center gap-1.5 text-[10px]">
                <span className="text-emerald-400">+新增</span>
                <span className="text-red-400">-删除</span>
                <span className="text-amber-400">~修改</span>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto custom-scrollbar">
              <FileTree
                nodes={treeNodes}
                selectedFile={selectedFile}
                onSelectFile={handleFileSelect}
                showStatus={true}
              />
            </div>
          </div>

          <div className="flex-1 flex flex-col">
            {selectedFile ? (
              <div className="flex-1" id="directory-diff-editor">
                <DirectoryDiffEditor />
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center">
                  <FolderArchive size={40} className="text-zinc-700 mx-auto mb-3" />
                  <p className="text-sm text-zinc-500">从左侧文件树选择文件查看差异</p>
                  <p className="text-xs text-zinc-600 mt-1">差异文件已用颜色标记</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function DirectoryDiffEditor() {
  const { oldCode, newCode, language, editorLayout } = useDiffStore()

  return (
    <DiffEditorWrapper
      oldCode={oldCode}
      newCode={newCode}
      language={language}
      editorLayout={editorLayout}
    />
  )
}

function DiffEditorWrapper({
  oldCode,
  newCode,
  language,
  editorLayout,
}: {
  oldCode: string
  newCode: string
  language: string
  editorLayout: 'side-by-side' | 'inline'
}) {
  return (
    <DiffEditor
      height="100%"
      language={language}
      original={oldCode}
      modified={newCode}
      theme="vs-dark"
      options={{
        readOnly: true,
        renderSideBySide: editorLayout === 'side-by-side',
        scrollBeyondLastLine: false,
        fontSize: 13,
        fontFamily: "'JetBrains Mono', monospace",
        minimap: { enabled: true },
        folding: true,
        foldingStrategy: 'indentation',
        showFoldingControls: 'mouseover',
        automaticLayout: true,
        diffAlgorithm: 'advanced',
      }}
    />
  )
}

import { useState } from 'react'
import type { DiffTreeNode, FileTreeNode } from '@/types'
import {
  ChevronRight,
  ChevronDown,
  File,
  Folder,
  FolderOpen,
  Plus,
  Minus,
  PenLine,
} from 'lucide-react'

interface FileTreeProps {
  nodes: DiffTreeNode[]
  selectedFile: string | null
  onSelectFile: (path: string) => void
  showStatus?: boolean
  side?: 'old' | 'new'
}

const statusConfig = {
  added: { icon: Plus, color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', label: 'A' },
  deleted: { icon: Minus, color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/30', label: 'D' },
  modified: { icon: PenLine, color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/30', label: 'M' },
  unchanged: { icon: null, color: 'text-zinc-500', bg: '', border: '', label: '' },
}

function TreeNode({
  node,
  depth,
  selectedFile,
  onSelectFile,
  showStatus,
  side,
}: {
  node: DiffTreeNode
  depth: number
  selectedFile: string | null
  onSelectFile: (path: string) => void
  showStatus?: boolean
  side?: 'old' | 'new'
}) {
  const [expanded, setExpanded] = useState(depth < 2)
  const isDir = node.type === 'directory'
  const isSelected = node.path === selectedFile
  const status = node.status || 'unchanged'
  const config = statusConfig[status]

  const shouldHide =
    side === 'old' && status === 'added'
      ? true
      : side === 'new' && status === 'deleted'
        ? true
        : false

  if (shouldHide) return null

  return (
    <div>
      <div
        className={`flex items-center gap-1 py-0.5 px-2 cursor-pointer text-xs transition-all duration-150 group ${
          isSelected
            ? 'bg-violet-500/15 text-violet-300'
            : 'text-zinc-400 hover:bg-[#1a1a2e] hover:text-zinc-200'
        }`}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
        onClick={() => {
          if (isDir) setExpanded(!expanded)
          else onSelectFile(node.path)
        }}
      >
        {isDir ? (
          <>
            {expanded ? (
              <ChevronDown size={10} className="text-zinc-500 shrink-0" />
            ) : (
              <ChevronRight size={10} className="text-zinc-500 shrink-0" />
            )}
            {expanded ? (
              <FolderOpen size={13} className="text-amber-400/80 shrink-0" />
            ) : (
              <Folder size={13} className="text-amber-400/80 shrink-0" />
            )}
          </>
        ) : (
          <>
            <span className="w-[10px] shrink-0" />
            <File size={13} className="text-zinc-500 shrink-0" />
          </>
        )}

        <span className="truncate font-['JetBrains_Mono'] text-[11px]">{node.name}</span>

        {showStatus && config.label && (
          <span
            className={`ml-auto text-[9px] font-bold px-1 py-0.5 rounded ${config.color} ${config.bg} border ${config.border} shrink-0`}
          >
            {config.label}
          </span>
        )}
      </div>

      {isDir && expanded && node.children && (
        <div>
          {node.children.map((child) => (
            <TreeNode
              key={child.path}
              node={child}
              depth={depth + 1}
              selectedFile={selectedFile}
              onSelectFile={onSelectFile}
              showStatus={showStatus}
              side={side}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default function FileTree({
  nodes,
  selectedFile,
  onSelectFile,
  showStatus = true,
  side,
}: FileTreeProps) {
  if (nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-xs text-zinc-600">
        暂无文件
      </div>
    )
  }

  return (
    <div className="py-1">
      {nodes.map((node) => (
        <TreeNode
          key={node.path}
          node={node}
          depth={0}
          selectedFile={selectedFile}
          onSelectFile={onSelectFile}
          showStatus={showStatus}
          side={side}
        />
      ))}
    </div>
  )
}

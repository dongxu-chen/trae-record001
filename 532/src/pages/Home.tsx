import { useDiffStore } from '@/store/diffStore'
import { useConflictStore } from '@/store/conflictPlaybackStore'
import { usePlaybackStore } from '@/store/conflictPlaybackStore'
import Toolbar from '@/components/Toolbar'
import CodeInput from '@/components/CodeInput'
import DiffViewer from '@/components/DiffViewer'
import DiffNavigator from '@/components/DiffNavigator'
import DirectoryCompare from '@/components/DirectoryCompare'
import CommentPanel from '@/components/CommentPanel'
import ConflictView from '@/components/ConflictView'
import PlaybackControls from '@/components/PlaybackControls'

export default function Home() {
  const { mode, isComparing } = useDiffStore()
  const { hasConflicts } = useConflictStore()
  const { versions } = usePlaybackStore()

  const showConflictBar = hasConflicts && isComparing
  const showPlaybackBar = versions.length > 0 && isComparing

  return (
    <div className="h-screen flex flex-col bg-[#1e1e2e] text-zinc-200 overflow-hidden">
      <Toolbar />

      <div className="flex-1 flex flex-col overflow-hidden relative">
        {showConflictBar && <ConflictView />}
        {showPlaybackBar && <PlaybackControls />}

        <div className="flex-1 flex overflow-hidden">
          <div className="flex-1 flex flex-col overflow-hidden relative">
            {mode === 'code' ? (
              isComparing ? (
                <>
                  <DiffViewer />
                  <DiffNavigator />
                </>
              ) : (
                <CodeInput />
              )
            ) : (
              <DirectoryCompare />
            )}
          </div>

          <CommentPanel />
        </div>
      </div>

      <div className="h-6 bg-[#0d0d1a] border-t border-[#2a2a4a] flex items-center px-3 gap-4 shrink-0">
        <span className="text-[10px] text-zinc-600 font-['JetBrains_Mono']">
          CodeDiff Viewer
        </span>
        <div className="flex-1" />
        <span className="text-[10px] text-zinc-600">
          F7/F8 跳转差异 · 点击行号旁标记添加评论
        </span>
      </div>
    </div>
  )
}

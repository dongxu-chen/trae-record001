import { useState, useCallback } from 'react'
import { useDiffStore } from '@/store/diffStore'
import { SAMPLE_OLD_CODE, SAMPLE_NEW_CODE } from '@/utils/languages'
import { FileUp, Sparkles } from 'lucide-react'

export default function CodeInput() {
  const { oldCode, newCode, setOldCode, setNewCode, setIsComparing } = useDiffStore()
  const [dragOver, setDragOver] = useState<'old' | 'new' | null>(null)

  const handleLoadSample = useCallback(() => {
    setOldCode(SAMPLE_OLD_CODE)
    setNewCode(SAMPLE_NEW_CODE)
  }, [setOldCode, setNewCode])

  const handleFileDrop = useCallback(
    (side: 'old' | 'new', e: React.DragEvent) => {
      e.preventDefault()
      setDragOver(null)
      const file = e.dataTransfer.files[0]
      if (file) {
        const reader = new FileReader()
        reader.onload = (ev) => {
          const text = ev.target?.result as string
          if (side === 'old') setOldCode(text)
          else setNewCode(text)
        }
        reader.readAsText(file)
      }
    },
    [setOldCode, setNewCode]
  )

  return (
    <div className="flex-1 flex flex-col gap-3 p-4 overflow-hidden">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-zinc-300 font-['IBM_Plex_Sans']">
          输入代码版本
        </h2>
        <button
          onClick={handleLoadSample}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs text-violet-400 hover:text-violet-300 hover:bg-violet-500/10 transition-all duration-200"
        >
          <Sparkles size={12} />
          加载示例
        </button>
      </div>

      <div className="flex-1 flex gap-3 min-h-0">
        <div
          className={`flex-1 flex flex-col rounded-xl border transition-all duration-200 ${
            dragOver === 'old'
              ? 'border-red-500/60 bg-red-500/5'
              : 'border-[#2a2a4a] bg-[#0d0d1a]'
          }`}
          onDragOver={(e) => {
            e.preventDefault()
            setDragOver('old')
          }}
          onDragLeave={() => setDragOver(null)}
          onDrop={(e) => handleFileDrop('old', e)}
        >
          <div className="flex items-center gap-2 px-3 py-2 border-b border-[#2a2a4a]">
            <span className="w-2 h-2 rounded-full bg-red-400" />
            <span className="text-xs font-medium text-zinc-400">旧版本</span>
            <FileUp size={11} className="text-zinc-600 ml-auto" />
          </div>
          <textarea
            value={oldCode}
            onChange={(e) => setOldCode(e.target.value)}
            placeholder="粘贴旧版本代码，或拖拽文件到此处..."
            className="flex-1 bg-transparent text-zinc-200 text-sm font-['JetBrains_Mono'] p-3 resize-none outline-none placeholder:text-zinc-600"
            spellCheck={false}
          />
        </div>

        <div
          className={`flex-1 flex flex-col rounded-xl border transition-all duration-200 ${
            dragOver === 'new'
              ? 'border-emerald-500/60 bg-emerald-500/5'
              : 'border-[#2a2a4a] bg-[#0d0d1a]'
          }`}
          onDragOver={(e) => {
            e.preventDefault()
            setDragOver('new')
          }}
          onDragLeave={() => setDragOver(null)}
          onDrop={(e) => handleFileDrop('new', e)}
        >
          <div className="flex items-center gap-2 px-3 py-2 border-b border-[#2a2a4a]">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span className="text-xs font-medium text-zinc-400">新版本</span>
            <FileUp size={11} className="text-zinc-600 ml-auto" />
          </div>
          <textarea
            value={newCode}
            onChange={(e) => setNewCode(e.target.value)}
            placeholder="粘贴新版本代码，或拖拽文件到此处..."
            className="flex-1 bg-transparent text-zinc-200 text-sm font-['JetBrains_Mono'] p-3 resize-none outline-none placeholder:text-zinc-600"
            spellCheck={false}
          />
        </div>
      </div>

      <div className="flex justify-center">
        <button
          onClick={() => setIsComparing(true)}
          disabled={!oldCode && !newCode}
          className="flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-semibold bg-gradient-to-r from-violet-600 to-indigo-600 text-white hover:from-violet-500 hover:to-indigo-500 shadow-lg shadow-violet-600/30 transition-all duration-300 disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none"
        >
          开始对比
        </button>
      </div>
    </div>
  )
}

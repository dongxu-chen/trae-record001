import { useCallback, useMemo } from 'react'
import { usePlaybackStore } from '@/store/conflictPlaybackStore'
import { useDiffStore } from '@/store/diffStore'
import {
  Play,
  Pause,
  Square,
  SkipBack,
  SkipForward,
  ChevronLeft,
  ChevronRight,
  Clock,
  Gauge,
  Plus,
  X,
  GitCommitHorizontal,
} from 'lucide-react'

export default function PlaybackControls() {
  const {
    versions,
    currentIndex,
    playbackState,
    playbackSpeed,
    setCurrentIndex,
    play,
    pause,
    stop,
    nextStep,
    prevStep,
    setPlaybackSpeed,
    addVersion,
    removeVersion,
  } = usePlaybackStore()

  const { setOldCode, setNewCode, setIsComparing } = useDiffStore()

  const currentVersion = versions[currentIndex]
  const previousVersion = currentIndex > 0 ? versions[currentIndex - 1] : null

  const handleStepChange = useCallback(
    (index: number) => {
      setCurrentIndex(index)
      const version = usePlaybackStore.getState().versions[index]
      if (version) {
        const prevVersion = index > 0 ? usePlaybackStore.getState().versions[index - 1] : null
        setOldCode(prevVersion ? prevVersion.code : '')
        setNewCode(version.code)
        setIsComparing(true)
      }
    },
    [setCurrentIndex, setOldCode, setNewCode, setIsComparing]
  )

  const handleAddVersion = useCallback(() => {
    const code = useDiffStore.getState().newCode || ''
    const label = `V${versions.length + 1}`
    const description = `版本 ${versions.length + 1} 的代码快照`
    addVersion({ label, code, timestamp: Date.now(), description })
  }, [versions.length, addVersion])

  const handlePlay = useCallback(() => {
    if (versions.length <= 1) return
    if (playbackState === 'playing') {
      pause()
    } else {
      play()
    }
  }, [versions.length, playbackState, play, pause])

  const speedLabels: Record<number, string> = {
    4000: '0.5x',
    2000: '1x',
    1000: '2x',
    500: '4x',
  }

  return (
    <div className="border-b border-[#2a2a4a] bg-[#1a1a2e]">
      <div className="px-4 py-2 flex items-center gap-3">
        <div className="flex items-center gap-1.5">
          <GitCommitHorizontal size={14} className="text-cyan-400" />
          <span className="text-xs font-semibold text-cyan-300">演变回放</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300">
            {versions.length} 版本
          </span>
        </div>

        <div className="h-4 w-px bg-[#2a2a4a]" />

        <div className="flex items-center gap-1">
          <button
            onClick={stop}
            disabled={playbackState === 'idle'}
            className="p-1 rounded text-zinc-400 hover:text-white hover:bg-[#2a2a4a] disabled:opacity-30 transition-colors"
            title="停止"
          >
            <Square size={12} />
          </button>
          <button
            onClick={() => handleStepChange(0)}
            disabled={currentIndex === 0 || versions.length === 0}
            className="p-1 rounded text-zinc-400 hover:text-white hover:bg-[#2a2a4a] disabled:opacity-30 transition-colors"
            title="回到开始"
          >
            <SkipBack size={12} />
          </button>
          <button
            onClick={prevStep}
            disabled={currentIndex === 0}
            className="p-1 rounded text-zinc-400 hover:text-white hover:bg-[#2a2a4a] disabled:opacity-30 transition-colors"
            title="上一步"
          >
            <ChevronLeft size={14} />
          </button>
          <button
            onClick={handlePlay}
            disabled={versions.length <= 1}
            className={`p-1.5 rounded-lg transition-all ${
              playbackState === 'playing'
                ? 'bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30'
                : 'bg-[#0d0d1a] text-zinc-300 hover:text-white hover:bg-[#2a2a4a] disabled:opacity-30'
            }`}
            title={playbackState === 'playing' ? '暂停' : '播放'}
          >
            {playbackState === 'playing' ? <Pause size={14} /> : <Play size={14} />}
          </button>
          <button
            onClick={nextStep}
            disabled={currentIndex >= versions.length - 1}
            className="p-1 rounded text-zinc-400 hover:text-white hover:bg-[#2a2a4a] disabled:opacity-30 transition-colors"
            title="下一步"
          >
            <ChevronRight size={14} />
          </button>
          <button
            onClick={() => handleStepChange(versions.length - 1)}
            disabled={currentIndex >= versions.length - 1 || versions.length === 0}
            className="p-1 rounded text-zinc-400 hover:text-white hover:bg-[#2a2a4a] disabled:opacity-30 transition-colors"
            title="跳到结尾"
          >
            <SkipForward size={12} />
          </button>
        </div>

        <div className="h-4 w-px bg-[#2a2a4a]" />

        <div className="flex items-center gap-1">
          <Gauge size={10} className="text-zinc-500" />
          {Object.entries(speedLabels).map(([ms, label]) => (
            <button
              key={ms}
              onClick={() => setPlaybackSpeed(Number(ms))}
              className={`px-1.5 py-0.5 rounded text-[10px] font-medium transition-all ${
                playbackSpeed === Number(ms)
                  ? 'bg-cyan-500/20 text-cyan-300'
                  : 'text-zinc-500 hover:text-zinc-300'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="flex-1" />

        <span className="text-[10px] text-zinc-500 font-['JetBrains_Mono']">
          {currentIndex + 1}/{versions.length}
        </span>

        <button
          onClick={handleAddVersion}
          className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] text-cyan-400 hover:bg-cyan-500/10 border border-cyan-500/30 transition-colors"
          title="添加当前代码为新版本"
        >
          <Plus size={10} />
          添加版本
        </button>
      </div>

      {versions.length > 0 && (
        <div className="px-4 pb-2">
          <div className="relative flex items-center gap-0.5 h-6">
            <div className="absolute top-1/2 left-0 right-0 h-px bg-[#2a2a4a]" />

            {versions.map((version, index) => (
              <div
                key={version.id}
                className="relative z-10 flex items-center group"
                style={{ flex: 1 }}
              >
                <button
                  onClick={() => handleStepChange(index)}
                  className={`w-3 h-3 rounded-full border-2 transition-all duration-200 ${
                    index === currentIndex
                      ? 'bg-cyan-400 border-cyan-400 scale-125 shadow-lg shadow-cyan-400/40'
                      : index < currentIndex
                        ? 'bg-cyan-600 border-cyan-600'
                        : 'bg-[#0d0d1a] border-zinc-600 hover:border-cyan-400'
                  }`}
                />

                <div className="absolute top-5 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                  <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-2 py-1 shadow-xl whitespace-nowrap">
                    <p className="text-[10px] font-semibold text-zinc-300">{version.label}</p>
                    <p className="text-[9px] text-zinc-500">{version.description}</p>
                    <p className="text-[9px] text-zinc-600">
                      {new Date(version.timestamp).toLocaleTimeString('zh-CN')}
                    </p>
                  </div>
                </div>

                {index < versions.length - 1 && (
                  <div
                    className={`absolute top-1/2 left-3 right-0 h-0.5 -translate-y-1/2 ${
                      index < currentIndex ? 'bg-cyan-600' : 'bg-[#2a2a4a]'
                    }`}
                  />
                )}
              </div>
            ))}
          </div>

          <div className="flex justify-between mt-1">
            <span className="text-[9px] text-zinc-600">{versions[0]?.label}</span>
            {currentVersion && (
              <span className="text-[9px] text-cyan-400/70">
                {currentVersion.label}: {currentVersion.description}
              </span>
            )}
            <span className="text-[9px] text-zinc-600">{versions[versions.length - 1]?.label}</span>
          </div>
        </div>
      )}
    </div>
  )
}

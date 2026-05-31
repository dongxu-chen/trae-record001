import { usePerformance } from '@/hooks/usePerformance'
import { useSimulationStore } from '@/store/useSimulationStore'
import { Activity, Cpu, Monitor } from 'lucide-react'

export function StatusBar() {
  const { fps } = usePerformance()
  const { isPlaying, resolution } = useSimulationStore((state) => state.simulation)

  return (
    <div className="absolute bottom-0 left-0 right-0 z-10">
      <div className="glass-panel mx-4 mb-4 px-4 py-2 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <Activity
              className={`w-4 h-4 ${isPlaying ? 'text-green-400' : 'text-yellow-400'}`}
            />
            <span className="text-xs text-gray-400">
              状态:
              <span className={`ml-1 ${isPlaying ? 'text-green-400' : 'text-yellow-400'}`}>
                {isPlaying ? '运行中' : '已暂停'}
              </span>
            </span>
          </div>

          <div className="flex items-center gap-2">
            <Monitor className="w-4 h-4 text-cyber-cyan" />
            <span className="text-xs text-gray-400">
              FPS: <span className="text-cyber-cyan font-mono ml-1">{fps}</span>
            </span>
          </div>

          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-neon-purple" />
            <span className="text-xs text-gray-400">
              分辨率: <span className="text-neon-purple font-mono ml-1">{resolution}px</span>
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          <span className="text-xs text-gray-500">GPU 加速已启用</span>
        </div>
      </div>
    </div>
  )
}

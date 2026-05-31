import { useState } from 'react'
import { Wind, Waves, Cloud, Settings, ChevronDown, ChevronUp } from 'lucide-react'
import { useSimulationStore } from '@/store/useSimulationStore'
import type { SceneType } from '@/types'
import { SCENE_CONFIGS } from '@/config/scenes'

const sceneIcons: Record<SceneType, typeof Wind> = {
  windTunnel: Wind,
  river: Waves,
  smoke: Cloud,
  custom: Settings,
}

export function SceneSelector() {
  const { currentScene, switchScene } = useSimulationStore((state) => ({
    currentScene: state.simulation.currentScene,
    switchScene: state.switchScene,
  }))

  const [isExpanded, setIsExpanded] = useState(true)

  const scenes: SceneType[] = ['windTunnel', 'river', 'smoke', 'custom']

  return (
    <div className="glass-panel p-3 mb-4">
      <button
        className="w-full flex items-center justify-between mb-3"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="section-title mb-0">场景选择</span>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-gray-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-gray-400" />
        )}
      </button>

      {isExpanded && (
        <div className="grid grid-cols-2 gap-2">
          {scenes.map((sceneType) => {
            const scene = SCENE_CONFIGS[sceneType]
            const Icon = sceneIcons[sceneType]
            const isActive = currentScene === sceneType

            return (
              <button
                key={sceneType}
                className={`p-3 rounded-lg transition-all duration-200 text-left ${
                  isActive
                    ? 'bg-cyber-cyan/20 border border-cyber-cyan/50'
                    : 'bg-white/5 border border-white/10 hover:bg-white/10'
                }`}
                onClick={() => switchScene(sceneType)}
              >
                <div className="flex items-center gap-2 mb-1">
                  <Icon
                    className={`w-4 h-4 ${isActive ? 'text-cyber-cyan' : 'text-gray-400'}`}
                  />
                  <span
                    className={`text-sm font-medium ${isActive ? 'text-cyber-cyan' : 'text-white'}`}
                  >
                    {scene.name}
                  </span>
                </div>
                <p className="text-xs text-gray-500 line-clamp-2">
                  {scene.description}
                </p>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}

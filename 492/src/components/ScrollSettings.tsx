import React from 'react';
import { MoveLeft, MoveRight, MoveUp, MoveDown, Repeat, PlayCircle, Gauge } from 'lucide-react';
import { useLEDStore } from '../store/ledStore';
import { ScrollDirection, ScrollMode } from '../store/types';

const directions: { value: ScrollDirection; label: string; icon: React.ReactNode }[] = [
  { value: 'left', label: '向左', icon: <MoveLeft className="w-4 h-4" /> },
  { value: 'right', label: '向右', icon: <MoveRight className="w-4 h-4" /> },
  { value: 'up', label: '向上', icon: <MoveUp className="w-4 h-4" /> },
  { value: 'down', label: '向下', icon: <MoveDown className="w-4 h-4" /> }
];

const modes: { value: ScrollMode; label: string; icon: React.ReactNode }[] = [
  { value: 'continuous', label: '循环', icon: <Repeat className="w-4 h-4" /> },
  { value: 'once', label: '单次', icon: <PlayCircle className="w-4 h-4" /> }
];

export const ScrollSettings: React.FC = () => {
  const { scroll, setScroll } = useLEDStore();

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
        <Gauge className="w-4 h-4" />
        滚动设置
      </h3>

      <div>
        <label className="text-xs text-gray-400 mb-2 block">滚动方向</label>
        <div className="grid grid-cols-4 gap-2">
          {directions.map((dir) => (
            <button
              key={dir.value}
              onClick={() => setScroll({ direction: dir.value })}
              className={`flex flex-col items-center gap-1 py-2 px-3 rounded-lg border transition-all ${
                scroll.direction === dir.value
                  ? 'bg-cyan-500/20 border-cyan-500 text-cyan-400'
                  : 'bg-gray-800/50 border-gray-700 text-gray-400 hover:border-gray-600'
              }`}
            >
              {dir.icon}
              <span className="text-xs">{dir.label}</span>
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="text-xs text-gray-400 mb-2 block">
          滚动速度: {scroll.speed}x
        </label>
        <input
          type="range"
          min="0.5"
          max="10"
          step="0.5"
          value={scroll.speed}
          onChange={(e) => setScroll({ speed: Number(e.target.value) })}
          className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
        />
        <div className="flex justify-between mt-1">
          <span className="text-xs text-gray-500">慢</span>
          <span className="text-xs text-gray-500">快</span>
        </div>
      </div>

      <div>
        <label className="text-xs text-gray-400 mb-2 block">滚动模式</label>
        <div className="grid grid-cols-2 gap-2">
          {modes.map((mode) => (
            <button
              key={mode.value}
              onClick={() => setScroll({ mode: mode.value })}
              className={`flex items-center justify-center gap-2 py-2.5 rounded-lg border transition-all ${
                scroll.mode === mode.value
                  ? 'bg-cyan-500/20 border-cyan-500 text-cyan-400'
                  : 'bg-gray-800/50 border-gray-700 text-gray-400 hover:border-gray-600'
              }`}
            >
              {mode.icon}
              <span className="text-sm">{mode.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

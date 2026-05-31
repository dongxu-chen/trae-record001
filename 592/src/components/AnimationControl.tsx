import React from 'react';
import { Play, Pause, RotateCcw, SkipForward, SkipBack } from 'lucide-react';
import { AnimationState } from '../types';

interface AnimationControlProps {
  state: AnimationState;
  onTogglePlay: () => void;
  onReset: () => void;
  onSpeedChange: (speed: number) => void;
  onParamChange: (param: AnimationState['animationParam']) => void;
}

const PARAMS: { value: AnimationState['animationParam']; label: string; desc: string }[] = [
  { value: 'phase', label: '相位', desc: 'Phase' },
  { value: 'frequency', label: '频率', desc: 'Frequency' },
  { value: 'amplitude', label: '振幅', desc: 'Amplitude' },
];

const AnimationControl: React.FC<AnimationControlProps> = ({
  state,
  onTogglePlay,
  onReset,
  onSpeedChange,
  onParamChange,
}) => {
  return (
    <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
      <div className="flex items-center gap-2 mb-4">
        <Play className="w-5 h-5 text-green-400" />
        <h3 className="text-lg font-semibold text-white">参数动画</h3>
      </div>

      <div className="flex items-center justify-center gap-3 mb-6">
        <button
          onClick={() => onSpeedChange(Math.max(0.25, state.speed - 0.25))}
          className="p-2 rounded-lg bg-gray-900/50 text-gray-400 hover:text-white hover:bg-gray-700 transition-colors"
          title="减速"
        >
          <SkipBack className="w-5 h-5" />
        </button>
        <button
          onClick={onTogglePlay}
          className={`p-4 rounded-full transition-all ${
            state.isPlaying
              ? 'bg-green-600 hover:bg-green-500 text-white'
              : 'bg-blue-600 hover:bg-blue-500 text-white'
          }`}
        >
          {state.isPlaying ? <Pause className="w-6 h-6" /> : <Play className="w-6 h-6" />}
        </button>
        <button
          onClick={onReset}
          className="p-2 rounded-lg bg-gray-900/50 text-gray-400 hover:text-white hover:bg-gray-700 transition-colors"
          title="重置"
        >
          <RotateCcw className="w-5 h-5" />
        </button>
        <button
          onClick={() => onSpeedChange(Math.min(4, state.speed + 0.25))}
          className="p-2 rounded-lg bg-gray-900/50 text-gray-400 hover:text-white hover:bg-gray-700 transition-colors"
          title="加速"
        >
          <SkipForward className="w-5 h-5" />
        </button>
      </div>

      <div className="space-y-4">
        <div>
          <div className="flex justify-between items-center mb-2">
            <label className="text-sm font-medium text-gray-300">动画速度</label>
            <span className="text-sm font-mono text-green-400">
              {state.speed.toFixed(2)}x
            </span>
          </div>
          <input
            type="range"
            min="0.25"
            max="4"
            step="0.25"
            value={state.speed}
            onChange={(e) => onSpeedChange(parseFloat(e.target.value))}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-green-500"
          />
        </div>

        <div>
          <label className="text-sm font-medium text-gray-300 mb-2 block">动画参数</label>
          <div className="grid grid-cols-3 gap-2">
            {PARAMS.map((param) => (
              <button
                key={param.value}
                onClick={() => onParamChange(param.value)}
                className={`p-2 rounded-lg text-xs transition-all ${
                  state.animationParam === param.value
                    ? 'bg-green-600 text-white'
                    : 'bg-gray-900/50 text-gray-400 hover:bg-gray-700 hover:text-white'
                }`}
              >
                <div className="font-medium">{param.label}</div>
                <div className="text-xs opacity-70">{param.desc}</div>
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-4 p-3 bg-gray-900/50 rounded-lg border border-gray-600">
        <div className="flex justify-between items-center">
          <span className="text-xs text-gray-400">当前时间</span>
          <span className="text-sm font-mono text-white">
            t = {state.currentTime.toFixed(2)}
          </span>
        </div>
        <div className="mt-2 h-1 bg-gray-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-green-500 transition-all duration-100"
            style={{ width: `${(state.currentTime % (2 * Math.PI)) / (2 * Math.PI) * 100}%` }}
          />
        </div>
      </div>
    </div>
  );
};

export default AnimationControl;

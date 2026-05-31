import React from 'react';
import type { AnimationConfig } from '../types';

interface AnimationPanelProps {
  expression: string;
  animationConfig: AnimationConfig;
  setAnimationConfig: React.Dispatch<React.SetStateAction<AnimationConfig>>;
  isPlaying: boolean;
  currentValue: number;
  play: () => void;
  pause: () => void;
  reset: () => void;
  stepForward: () => void;
  stepBackward: () => void;
  setParameterValue: (value: number) => void;
  validation: { valid: boolean; error?: string };
  currentExpression: string;
}

const EXAMPLE_ANIMATIONS = [
  { label: '正弦波振幅', expr: 'a * sin(x)', param: 'a', range: [0.1, 3] },
  { label: '抛物线开口', expr: 'a * x^2', param: 'a', range: [-2, 2] },
  { label: '指数衰减', expr: 'exp(-a * abs(x))', param: 'a', range: [0.1, 3] },
  { label: '正弦叠加', expr: 'sin(x) + sin(a * x) / 2', param: 'a', range: [0.5, 5] },
  { label: '分段移动', expr: 'piecewise(x < a, -1, x < 0, x, 1)', param: 'a', range: [-3, 0] },
];

export const AnimationPanel: React.FC<AnimationPanelProps> = ({
  expression,
  animationConfig,
  setAnimationConfig,
  isPlaying,
  currentValue,
  play,
  pause,
  reset,
  stepForward,
  stepBackward,
  setParameterValue,
  validation,
  currentExpression
}) => {
  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
        <span className="text-xl">🎬</span> 函数动画
      </h3>

      <div className="mb-4">
        <label className="block text-gray-400 text-sm mb-1">参数名称</label>
        <input
          type="text"
          value={animationConfig.parameterName}
          onChange={(e) => setAnimationConfig(prev => ({
            ...prev,
            parameterName: e.target.value || 'a'
          }))}
          className="w-full px-3 py-2 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none text-sm"
          placeholder="参数名"
        />
      </div>

      <div className="grid grid-cols-2 gap-2 mb-4">
        <div>
          <label className="block text-gray-400 text-xs mb-1">起始值</label>
          <input
            type="number"
            value={animationConfig.parameterStart}
            onChange={(e) => setAnimationConfig(prev => ({
              ...prev,
              parameterStart: parseFloat(e.target.value) || 0
            }))}
            className="w-full px-2 py-1 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none text-sm"
            step="0.1"
          />
        </div>
        <div>
          <label className="block text-gray-400 text-xs mb-1">结束值</label>
          <input
            type="number"
            value={animationConfig.parameterEnd}
            onChange={(e) => setAnimationConfig(prev => ({
              ...prev,
              parameterEnd: parseFloat(e.target.value) || 10
            }))}
            className="w-full px-2 py-1 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none text-sm"
            step="0.1"
          />
        </div>
      </div>

      <div className="mb-4">
        <label className="block text-gray-400 text-xs mb-1">
          动画周期: {animationConfig.duration} 秒
        </label>
        <input
          type="range"
          min="1"
          max="20"
          step="0.5"
          value={animationConfig.duration}
          onChange={(e) => setAnimationConfig(prev => ({
            ...prev,
            duration: parseFloat(e.target.value)
          }))}
          className="w-full"
        />
      </div>

      <div className="flex items-center gap-2 mb-4">
        <input
          type="checkbox"
          id="loop"
          checked={animationConfig.loop}
          onChange={(e) => setAnimationConfig(prev => ({
            ...prev,
            loop: e.target.checked
          }))}
          className="rounded"
        />
        <label htmlFor="loop" className="text-gray-400 text-sm cursor-pointer">
          循环播放
        </label>
      </div>

      <div className="mb-4">
        <label className="block text-gray-400 text-xs mb-2">
          当前值: <span className="text-blue-400 font-mono">{currentValue.toFixed(3)}</span>
        </label>
        <input
          type="range"
          min={animationConfig.parameterStart}
          max={animationConfig.parameterEnd}
          step={(animationConfig.parameterEnd - animationConfig.parameterStart) / 1000}
          value={currentValue}
          onChange={(e) => setParameterValue(parseFloat(e.target.value))}
          className="w-full"
          disabled={isPlaying}
        />
      </div>

      <div className="flex gap-2 mb-4">
        <button
          onClick={stepBackward}
          className="flex-1 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded font-medium text-sm transition-colors"
        >
          ⏮
        </button>
        <button
          onClick={isPlaying ? pause : play}
          disabled={!validation.valid}
          className={`flex-1 py-2 rounded font-medium text-sm transition-colors ${
            !validation.valid
              ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
              : isPlaying
              ? 'bg-orange-500 hover:bg-orange-600 text-white'
              : 'bg-green-500 hover:bg-green-600 text-white'
          }`}
        >
          {isPlaying ? '⏸ 暂停' : '▶ 播放'}
        </button>
        <button
          onClick={stepForward}
          className="flex-1 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded font-medium text-sm transition-colors"
        >
          ⏭
        </button>
        <button
          onClick={reset}
          className="flex-1 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded font-medium text-sm transition-colors"
        >
          ↺
        </button>
      </div>

      {!validation.valid && (
        <div className="mb-4 p-2 bg-red-900/30 border border-red-700 rounded">
          <p className="text-red-400 text-xs">{validation.error}</p>
        </div>
      )}

      {validation.valid && animationConfig.enabled && (
        <div className="mb-4 p-2 bg-blue-900/30 border border-blue-700 rounded">
          <p className="text-blue-400 text-xs font-mono break-all">
            f(x) = {currentExpression}
          </p>
        </div>
      )}

      <div className="mb-4">
        <label className="block text-gray-400 text-sm mb-2">示例动画</label>
        <div className="flex flex-wrap gap-1">
          {EXAMPLE_ANIMATIONS.map((ex, idx) => (
            <button
              key={idx}
              onClick={() => {
                setAnimationConfig(prev => ({
                  ...prev,
                  parameterName: ex.param,
                  parameterStart: ex.range[0],
                  parameterEnd: ex.range[1],
                  currentValue: ex.range[0]
                }));
              }}
              className="px-2 py-1 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded text-xs transition-colors"
            >
              {ex.label}
            </button>
          ))}
        </div>
      </div>

      <button
        onClick={() => setAnimationConfig(prev => ({ ...prev, enabled: !prev.enabled }))}
        className={`w-full py-2 rounded font-medium text-sm transition-colors ${
          animationConfig.enabled
            ? 'bg-red-500 hover:bg-red-600 text-white'
            : 'bg-blue-500 hover:bg-blue-600 text-white'
        }`}
      >
        {animationConfig.enabled ? '关闭动画' : '启用动画'}
      </button>
    </div>
  );
};

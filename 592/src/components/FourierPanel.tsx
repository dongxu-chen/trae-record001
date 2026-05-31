import React from 'react';
import { FourierConfig } from '../types';
import { Waves, Layers, Eye, EyeOff } from 'lucide-react';

interface FourierPanelProps {
  config: FourierConfig;
  onUpdateConfig: (updates: Partial<FourierConfig>) => void;
}

const WAVE_TYPES: { type: FourierConfig['type']; name: string; desc: string }[] = [
  { type: 'square', name: '方波', desc: 'Square Wave' },
  { type: 'sawtooth', name: '锯齿波', desc: 'Sawtooth Wave' },
  { type: 'triangle', name: '三角波', desc: 'Triangle Wave' },
];

const FourierPanel: React.FC<FourierPanelProps> = ({ config, onUpdateConfig }) => {
  return (
    <div className="space-y-4">
      <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
        <div className="flex items-center gap-2 mb-4">
          <Waves className="w-5 h-5 text-cyan-400" />
          <h3 className="text-lg font-semibold text-white">傅里叶级数</h3>
        </div>

        <div className="grid grid-cols-3 gap-2 mb-6">
          {WAVE_TYPES.map((wave) => (
            <button
              key={wave.type}
              onClick={() => onUpdateConfig({ type: wave.type })}
              className={`p-3 rounded-lg text-sm transition-all ${
                config.type === wave.type
                  ? 'bg-cyan-600 text-white'
                  : 'bg-gray-900/50 text-gray-400 hover:bg-gray-700 hover:text-white'
              }`}
            >
              <div className="font-medium">{wave.name}</div>
              <div className="text-xs opacity-70">{wave.desc}</div>
            </button>
          ))}
        </div>

        <div className="space-y-4">
          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="text-sm font-medium text-gray-300">谐波次数</label>
              <span className="text-sm font-mono text-cyan-400">
                {config.harmonics}
              </span>
            </div>
            <input
              type="range"
              min="1"
              max="20"
              step="1"
              value={config.harmonics}
              onChange={(e) => onUpdateConfig({ harmonics: parseInt(e.target.value) })}
              className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>1</span>
              <span>20</span>
            </div>
          </div>

          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="text-sm font-medium text-gray-300">频率</label>
              <span className="text-sm font-mono text-purple-400">
                {config.frequency.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min="0.5"
              max="3"
              step="0.1"
              value={config.frequency}
              onChange={(e) => onUpdateConfig({ frequency: parseFloat(e.target.value) })}
              className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-purple-500"
            />
          </div>

          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="text-sm font-medium text-gray-300">振幅</label>
              <span className="text-sm font-mono text-orange-400">
                {config.amplitude.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min="0.5"
              max="2"
              step="0.1"
              value={config.amplitude}
              onChange={(e) => onUpdateConfig({ amplitude: parseFloat(e.target.value) })}
              className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-orange-500"
            />
          </div>
        </div>

        <div className="mt-6 flex gap-4">
          <button
            onClick={() => onUpdateConfig({ showComponents: !config.showComponents })}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm transition-all ${
              config.showComponents
                ? 'bg-gray-600 text-white'
                : 'bg-gray-900/50 text-gray-400 hover:bg-gray-700'
            }`}
          >
            <Layers className="w-4 h-4" />
            显示谐波
          </button>
          <button
            onClick={() => onUpdateConfig({ showSum: !config.showSum })}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm transition-all ${
              config.showSum
                ? 'bg-gray-600 text-white'
                : 'bg-gray-900/50 text-gray-400 hover:bg-gray-700'
            }`}
          >
            <Eye className="w-4 h-4" />
            显示合成
          </button>
        </div>

        <div className="mt-6 p-4 bg-gray-900/50 rounded-lg border border-gray-600">
          <p className="text-xs text-gray-400 mb-2">傅里叶级数公式</p>
          <p className="text-sm font-mono text-white">
            {config.type === 'square' && 'f(x) = (4/π)Σ(1/(2n-1))·sin((2n-1)ωx)'}
            {config.type === 'sawtooth' && 'f(x) = (2/π)Σ((-1)^(n+1)/n)·sin(nωx)'}
            {config.type === 'triangle' && 'f(x) = (8/π²)Σ((-1)^((n-1)/2)/n²)·sin(nωx)'}
          </p>
          <p className="text-xs text-gray-500 mt-2">
            💡 增加谐波次数可以使波形更接近理想形状
          </p>
        </div>
      </div>
    </div>
  );
};

export default FourierPanel;

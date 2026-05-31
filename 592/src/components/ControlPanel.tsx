import React from 'react';
import { FunctionConfig } from '../types';
import { formatNumber } from '../utils/mathEngine';
import { Sliders, RotateCcw } from 'lucide-react';

interface ControlPanelProps {
  selectedFunctionId: string | null;
  functions: FunctionConfig[];
  onUpdateFunction: (id: string, updates: Partial<FunctionConfig>) => void;
  onResetFunction: (id: string) => void;
}

const ControlPanel: React.FC<ControlPanelProps> = ({
  selectedFunctionId,
  functions,
  onUpdateFunction,
  onResetFunction,
}) => {
  const selectedFunction = functions.find((f) => f.id === selectedFunctionId);

  if (!selectedFunction) {
    return (
      <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
        <div className="flex items-center gap-2 mb-4">
          <Sliders className="w-5 h-5 text-blue-400" />
          <h3 className="text-lg font-semibold text-white">参数控制</h3>
        </div>
        <p className="text-gray-400 text-sm">请选择一个函数来调整参数</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Sliders className="w-5 h-5 text-blue-400" />
          <h3 className="text-lg font-semibold text-white">
            {selectedFunction.type.toUpperCase()} 参数
          </h3>
        </div>
        <button
          onClick={() => onResetFunction(selectedFunction.id)}
          className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
        >
          <RotateCcw className="w-4 h-4" />
          重置
        </button>
      </div>

      <div className="space-y-6">
        <div>
          <div className="flex justify-between items-center mb-2">
            <label className="text-sm font-medium text-gray-300">
              频率 (f)
            </label>
            <span className="text-sm font-mono text-blue-400">
              {formatNumber(selectedFunction.frequency, 2)}
            </span>
          </div>
          <input
            type="range"
            min="0.1"
            max="5"
            step="0.1"
            value={selectedFunction.frequency}
            onChange={(e) =>
              onUpdateFunction(selectedFunction.id, {
                frequency: parseFloat(e.target.value),
              })
            }
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>0.1</span>
            <span>5</span>
          </div>
        </div>

        <div>
          <div className="flex justify-between items-center mb-2">
            <label className="text-sm font-medium text-gray-300">
              相位 (φ)
            </label>
            <span className="text-sm font-mono text-cyan-400">
              {(selectedFunction.phase / Math.PI).toFixed(2)}π
            </span>
          </div>
          <input
            type="range"
            min={-Math.PI}
            max={Math.PI}
            step="0.1"
            value={selectedFunction.phase}
            onChange={(e) =>
              onUpdateFunction(selectedFunction.id, {
                phase: parseFloat(e.target.value),
              })
            }
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>-π</span>
            <span>π</span>
          </div>
        </div>

        <div>
          <div className="flex justify-between items-center mb-2">
            <label className="text-sm font-medium text-gray-300">
              振幅 (A)
            </label>
            <span className="text-sm font-mono text-purple-400">
              {formatNumber(selectedFunction.amplitude, 2)}
            </span>
          </div>
          <input
            type="range"
            min="0.1"
            max="3"
            step="0.1"
            value={selectedFunction.amplitude}
            onChange={(e) =>
              onUpdateFunction(selectedFunction.id, {
                amplitude: parseFloat(e.target.value),
              })
            }
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-purple-500"
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>0.1</span>
            <span>3</span>
          </div>
        </div>
      </div>

      <div className="mt-6 p-4 bg-gray-900/50 rounded-lg border border-gray-600">
        <p className="text-xs text-gray-400 mb-2">函数表达式</p>
        <p className="text-sm font-mono text-white">
          y = {selectedFunction.amplitude !== 1 ? `${formatNumber(selectedFunction.amplitude, 2)} · ` : ''}
          {selectedFunction.type}(
          {selectedFunction.frequency !== 1 ? `${formatNumber(selectedFunction.frequency, 2)}x` : 'x'}
          {selectedFunction.phase !== 0 ? ` + ${formatNumber(selectedFunction.phase / Math.PI, 2)}π` : ''}
          )
        </p>
      </div>
    </div>
  );
};

export default ControlPanel;

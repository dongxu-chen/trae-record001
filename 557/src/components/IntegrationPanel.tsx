import React from 'react';
import type { IntegrationConfig } from '../types';

interface IntegrationPanelProps {
  integrationConfig: IntegrationConfig;
  setIntegrationConfig: React.Dispatch<React.SetStateAction<IntegrationConfig>>;
  functions: { id: string; expression: string; color: string }[];
  selectedFunction: { id: string; expression: string } | null;
  integrationResult: number;
  setSelectedFunctionId: (id: string) => void;
  setLowerBound: (value: number) => void;
  setUpperBound: (value: number) => void;
  calculateIntegral: (useAdaptive?: boolean) => number;
  error?: string;
}

const COLOR_OPTIONS = [
  '#60a5fa',
  '#34d399',
  '#fbbf24',
  '#f87171',
  '#a78bfa',
  '#fb7185'
];

export const IntegrationPanel: React.FC<IntegrationPanelProps> = ({
  integrationConfig,
  setIntegrationConfig,
  functions,
  selectedFunction,
  integrationResult,
  setSelectedFunctionId,
  setLowerBound,
  setUpperBound,
  calculateIntegral,
  error
}) => {
  const formatResult = (num: number): string => {
    if (Math.abs(num) < 0.000001 && num !== 0) {
      return num.toExponential(6);
    }
    if (Math.abs(num) >= 1000000) {
      return num.toExponential(6);
    }
    return num.toFixed(8).replace(/\.?0+$/, '');
  };

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
        <span className="text-xl">📐</span> 积分可视化
      </h3>

      <div className="mb-4">
        <label className="block text-gray-400 text-sm mb-2">选择函数</label>
        <div className="space-y-1 max-h-32 overflow-y-auto">
          {functions.map((func) => (
            <button
              key={func.id}
              onClick={() => setSelectedFunctionId(func.id)}
              className={`w-full flex items-center gap-2 p-2 rounded text-left text-sm transition-colors ${
                selectedFunction?.id === func.id
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              <div
                className="w-3 h-3 rounded-full flex-shrink-0"
                style={{ backgroundColor: func.color }}
              />
              <span className="truncate font-mono">{func.expression}</span>
            </button>
          ))}
          {functions.length === 0 && (
            <p className="text-gray-500 text-xs text-center py-2">
              请先添加函数
            </p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 mb-4">
        <div>
          <label className="block text-gray-400 text-xs mb-1">下限 a</label>
          <input
            type="number"
            value={integrationConfig.lowerBound}
            onChange={(e) => setLowerBound(parseFloat(e.target.value) || 0)}
            className="w-full px-2 py-1 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none text-sm"
            step="0.1"
          />
        </div>
        <div>
          <label className="block text-gray-400 text-xs mb-1">上限 b</label>
          <input
            type="number"
            value={integrationConfig.upperBound}
            onChange={(e) => setUpperBound(parseFloat(e.target.value) || 1)}
            className="w-full px-2 py-1 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none text-sm"
            step="0.1"
          />
        </div>
      </div>

      <div className="mb-4">
        <label className="block text-gray-400 text-xs mb-2">填充颜色</label>
        <div className="flex gap-2">
          {COLOR_OPTIONS.map((color) => (
            <button
              key={color}
              onClick={() => setIntegrationConfig(prev => ({ ...prev, fillColor: color }))}
              className={`w-8 h-8 rounded-full transition-transform ${
                integrationConfig.fillColor === color
                  ? 'ring-2 ring-white ring-offset-2 ring-offset-gray-800 scale-110'
                  : 'hover:scale-105'
              }`}
              style={{ backgroundColor: color }}
            />
          ))}
        </div>
      </div>

      <div className="mb-4">
        <label className="block text-gray-400 text-xs mb-1">
          透明度: {Math.round(integrationConfig.fillOpacity * 100)}%
        </label>
        <input
          type="range"
          min="0.1"
          max="0.8"
          step="0.05"
          value={integrationConfig.fillOpacity}
          onChange={(e) => setIntegrationConfig(prev => ({
            ...prev,
            fillOpacity: parseFloat(e.target.value)
          }))}
          className="w-full"
        />
      </div>

      <div className="flex items-center gap-2 mb-4">
        <input
          type="checkbox"
          id="showArea"
          checked={integrationConfig.showArea}
          onChange={(e) => setIntegrationConfig(prev => ({
            ...prev,
            showArea: e.target.checked
          }))}
          className="rounded"
        />
        <label htmlFor="showArea" className="text-gray-400 text-sm cursor-pointer">
          显示积分区域
        </label>
      </div>

      <button
        onClick={() => calculateIntegral(true)}
        disabled={!selectedFunction}
        className={`w-full py-2 rounded font-medium text-sm transition-colors mb-4 ${
          !selectedFunction
            ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
            : 'bg-green-500 hover:bg-green-600 text-white'
        }`}
      >
        🔢 计算积分
      </button>

      {error && (
        <div className="mb-4 p-2 bg-red-900/30 border border-red-700 rounded">
          <p className="text-red-400 text-xs">{error}</p>
        </div>
      )}

      {integrationConfig.enabled && selectedFunction && (
        <div className="p-4 bg-gradient-to-br from-blue-900/50 to-purple-900/50 border border-blue-700 rounded-lg">
          <div className="text-center mb-2">
            <p className="text-gray-400 text-xs mb-1">积分结果</p>
            <p className="text-3xl font-bold text-white font-mono">
              {formatResult(integrationResult)}
            </p>
          </div>
          <div className="text-center">
            <p className="text-gray-400 text-xs">
              ∫<sub>{integrationConfig.lowerBound}</sub><sup>{integrationConfig.upperBound}</sup>{' '}
              <span className="font-mono">{selectedFunction.expression}</span> dx
            </p>
          </div>
        </div>
      )}

      <div className="mt-4">
        <button
          onClick={() => setIntegrationConfig(prev => ({
            ...prev,
            enabled: !prev.enabled
          }))}
          disabled={!selectedFunction}
          className={`w-full py-2 rounded font-medium text-sm transition-colors ${
            !selectedFunction
              ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
              : integrationConfig.enabled
              ? 'bg-red-500 hover:bg-red-600 text-white'
              : 'bg-blue-500 hover:bg-blue-600 text-white'
          }`}
        >
          {integrationConfig.enabled ? '关闭积分' : '启用积分'}
        </button>
      </div>
    </div>
  );
};

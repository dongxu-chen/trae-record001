import React, { useState } from 'react';
import { FunctionConfig, FunctionType, FUNCTION_COLORS } from '../types';
import { Plus, Trash2, Eye, EyeOff, Calculator, TrendingUp, BarChart3 } from 'lucide-react';

interface FunctionSelectorProps {
  functions: FunctionConfig[];
  selectedFunctionId: string | null;
  onSelectFunction: (id: string) => void;
  onAddFunction: (type: FunctionType) => void;
  onRemoveFunction: (id: string) => void;
  onToggleVisibility: (id: string) => void;
  onToggleDerivative: (id: string) => void;
  onToggleIntegral: (id: string) => void;
}

const TRIG_FUNCTIONS: { type: FunctionType; name: string; desc: string }[] = [
  { type: 'sin', name: 'sin', desc: '正弦函数' },
  { type: 'cos', name: 'cos', desc: '余弦函数' },
  { type: 'tan', name: 'tan', desc: '正切函数' },
  { type: 'cot', name: 'cot', desc: '余切函数' },
  { type: 'sec', name: 'sec', desc: '正割函数' },
  { type: 'csc', name: 'csc', desc: '余割函数' },
];

const FunctionSelector: React.FC<FunctionSelectorProps> = ({
  functions,
  selectedFunctionId,
  onSelectFunction,
  onAddFunction,
  onRemoveFunction,
  onToggleVisibility,
  onToggleDerivative,
  onToggleIntegral,
}) => {
  const [showAddMenu, setShowAddMenu] = useState(false);

  return (
    <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Calculator className="w-5 h-5 text-blue-400" />
          <h3 className="text-lg font-semibold text-white">函数列表</h3>
        </div>
        <div className="relative">
          <button
            onClick={() => setShowAddMenu(!showAddMenu)}
            className="flex items-center gap-1 px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            添加
          </button>
          {showAddMenu && (
            <div className="absolute right-0 mt-2 w-48 bg-gray-900 border border-gray-700 rounded-lg shadow-xl z-10">
              {TRIG_FUNCTIONS.map((func) => (
                <button
                  key={func.type}
                  onClick={() => {
                    onAddFunction(func.type);
                    setShowAddMenu(false);
                  }}
                  className="w-full flex items-center gap-2 px-4 py-2 text-sm text-gray-300 hover:bg-gray-800 hover:text-white transition-colors rounded-lg"
                  style={{ borderLeft: `3px solid ${FUNCTION_COLORS[func.type]}` }}
                >
                  <span className="font-mono" style={{ color: FUNCTION_COLORS[func.type] }}>
                    {func.name}
                  </span>
                  <span className="text-gray-500">{func.desc}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="space-y-2 max-h-64 overflow-y-auto">
        {functions.map((func, index) => (
          <div
            key={func.id}
            onClick={() => onSelectFunction(func.id)}
            className={`p-3 rounded-lg border cursor-pointer transition-all ${
              selectedFunctionId === func.id
                ? 'bg-gray-700/50 border-blue-500'
                : 'bg-gray-900/30 border-gray-700 hover:border-gray-600'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: func.color }}
                />
                <span className="font-mono text-white">
                  {func.type.toUpperCase()}
                </span>
                <span className="text-xs text-gray-500">#{index + 1}</span>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onToggleDerivative(func.id);
                  }}
                  className={`p-1.5 rounded transition-colors ${
                    func.showDerivative
                      ? 'bg-cyan-600 text-white'
                      : 'text-gray-500 hover:text-white hover:bg-gray-700'
                  }`}
                  title="显示导数"
                >
                  <TrendingUp className="w-4 h-4" />
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onToggleIntegral(func.id);
                  }}
                  className={`p-1.5 rounded transition-colors ${
                    func.showIntegral
                      ? 'bg-purple-600 text-white'
                      : 'text-gray-500 hover:text-white hover:bg-gray-700'
                  }`}
                  title="显示积分"
                >
                  <BarChart3 className="w-4 h-4" />
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onToggleVisibility(func.id);
                  }}
                  className="p-1.5 rounded text-gray-500 hover:text-white hover:bg-gray-700 transition-colors"
                  title={func.visible ? '隐藏' : '显示'}
                >
                  {func.visible ? (
                    <Eye className="w-4 h-4" />
                  ) : (
                    <EyeOff className="w-4 h-4" />
                  )}
                </button>
                {functions.length > 1 && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onRemoveFunction(func.id);
                    }}
                    className="p-1.5 rounded text-gray-500 hover:text-red-400 hover:bg-gray-700 transition-colors"
                    title="删除"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 pt-4 border-t border-gray-700">
        <div className="flex items-center gap-4 text-xs text-gray-400">
          <div className="flex items-center gap-1">
            <div className="w-4 h-0.5 bg-gray-400 rounded" />
            <span>原函数</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-4 h-0.5 bg-gray-400 rounded border-dashed" style={{ borderStyle: 'dashed' }} />
            <span>导数 (虚线)</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-4 h-0.5 bg-gray-400 rounded" style={{ borderStyle: 'dotted' }} />
            <span>积分 (点线)</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FunctionSelector;

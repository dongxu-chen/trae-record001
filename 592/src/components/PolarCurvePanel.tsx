import React from 'react';
import { PolarCurveConfig, PolarCurveType, POLAR_CURVE_NAMES, POLAR_CURVE_COLORS } from '../types';
import { Plus, Trash2, Eye, EyeOff, Sliders } from 'lucide-react';

interface PolarCurvePanelProps {
  curves: PolarCurveConfig[];
  selectedCurveId: string | null;
  onSelectCurve: (id: string) => void;
  onAddCurve: (type: PolarCurveType) => void;
  onRemoveCurve: (id: string) => void;
  onToggleVisibility: (id: string) => void;
  onUpdateCurve: (id: string, updates: Partial<PolarCurveConfig>) => void;
}

const CURVE_TYPES: { type: PolarCurveType; name: string; formula: string }[] = [
  { type: 'cardioid', name: '心形线', formula: 'r = a(1+cosθ)' },
  { type: 'limacon', name: '蚶线', formula: 'r = a+b·cosθ' },
  { type: 'rose', name: '玫瑰线', formula: 'r = a·cos(nθ)' },
  { type: 'lemniscate', name: '双纽线', formula: 'r² = a²·cos2θ' },
  { type: 'spiral', name: '螺线', formula: 'r = a·θ' },
  { type: 'circle', name: '圆', formula: 'r = a' },
];

const PolarCurvePanel: React.FC<PolarCurvePanelProps> = ({
  curves,
  selectedCurveId,
  onSelectCurve,
  onAddCurve,
  onRemoveCurve,
  onToggleVisibility,
  onUpdateCurve,
}) => {
  const selectedCurve = curves.find((c) => c.id === selectedCurveId);

  return (
    <div className="space-y-4">
      <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Sliders className="w-5 h-5 text-orange-400" />
            <h3 className="text-lg font-semibold text-white">极坐标曲线</h3>
          </div>
          <div className="relative group">
            <button className="flex items-center gap-1 px-3 py-1.5 text-sm bg-orange-600 hover:bg-orange-500 text-white rounded-lg transition-colors">
              <Plus className="w-4 h-4" />
              添加
            </button>
            <div className="absolute right-0 mt-2 w-48 bg-gray-900 border border-gray-700 rounded-lg shadow-xl z-10 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all">
              {CURVE_TYPES.map((curve) => (
                <button
                  key={curve.type}
                  onClick={() => onAddCurve(curve.type)}
                  className="w-full flex flex-col items-start px-4 py-2 text-sm text-gray-300 hover:bg-gray-800 hover:text-white transition-colors"
                  style={{ borderLeft: `3px solid ${POLAR_CURVE_COLORS[curve.type]}` }}
                >
                  <span className="font-mono" style={{ color: POLAR_CURVE_COLORS[curve.type] }}>
                    {curve.name}
                  </span>
                  <span className="text-xs text-gray-500">{curve.formula}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-2 max-h-40 overflow-y-auto">
          {curves.map((curve) => (
            <div
              key={curve.id}
              onClick={() => onSelectCurve(curve.id)}
              className={`p-3 rounded-lg border cursor-pointer transition-all ${
                selectedCurveId === curve.id
                  ? 'bg-gray-700/50 border-orange-500'
                  : 'bg-gray-900/30 border-gray-700 hover:border-gray-600'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: curve.color }}
                  />
                  <span className="font-mono text-white">{POLAR_CURVE_NAMES[curve.type]}</span>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onToggleVisibility(curve.id);
                    }}
                    className="p-1.5 rounded text-gray-500 hover:text-white hover:bg-gray-700 transition-colors"
                  >
                    {curve.visible ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                  </button>
                  {curves.length > 1 && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onRemoveCurve(curve.id);
                      }}
                      className="p-1.5 rounded text-gray-500 hover:text-red-400 hover:bg-gray-700 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {selectedCurve && (
        <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
          <h4 className="text-sm font-semibold text-white mb-4">
            {POLAR_CURVE_NAMES[selectedCurve.type]} 参数
          </h4>

          <div className="space-y-4">
            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="text-sm font-medium text-gray-300">参数 a</label>
                <span className="text-sm font-mono text-orange-400">
                  {selectedCurve.a.toFixed(2)}
                </span>
              </div>
              <input
                type="range"
                min="0.1"
                max="2"
                step="0.1"
                value={selectedCurve.a}
                onChange={(e) => onUpdateCurve(selectedCurve.id, { a: parseFloat(e.target.value) })}
                className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-orange-500"
              />
            </div>

            {(selectedCurve.type === 'limacon' || selectedCurve.type === 'rose') && (
              <div>
                <div className="flex justify-between items-center mb-2">
                  <label className="text-sm font-medium text-gray-300">参数 b</label>
                  <span className="text-sm font-mono text-cyan-400">
                    {selectedCurve.b.toFixed(2)}
                  </span>
                </div>
                <input
                  type="range"
                  min="0.1"
                  max="2"
                  step="0.1"
                  value={selectedCurve.b}
                  onChange={(e) => onUpdateCurve(selectedCurve.id, { b: parseFloat(e.target.value) })}
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                />
              </div>
            )}

            {selectedCurve.type === 'rose' && (
              <div>
                <div className="flex justify-between items-center mb-2">
                  <label className="text-sm font-medium text-gray-300">花瓣数 n</label>
                  <span className="text-sm font-mono text-purple-400">
                    {selectedCurve.n}
                  </span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="12"
                  step="1"
                  value={selectedCurve.n}
                  onChange={(e) => onUpdateCurve(selectedCurve.id, { n: parseInt(e.target.value) })}
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-purple-500"
                />
              </div>
            )}
          </div>

          <div className="mt-4 p-3 bg-gray-900/50 rounded-lg border border-gray-600">
            <p className="text-xs text-gray-400 mb-1">极坐标方程</p>
            <p className="text-sm font-mono text-white">
              {CURVE_TYPES.find((c) => c.type === selectedCurve.type)?.formula}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default PolarCurvePanel;

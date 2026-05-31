import { Eye, EyeOff, Trash2, TrendingUp } from 'lucide-react';
import { useGraphStore } from '../store/useGraphStore';
import { PRESET_COLORS } from '../utils/colors';

export default function FunctionList() {
  const {
    functions,
    removeFunction,
    toggleFunctionVisibility,
    toggleDerivative,
    updateFunctionColor,
  } = useGraphStore();

  if (functions.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center text-gray-500">
        <div className="mb-2 text-4xl">📊</div>
        <p className="text-sm">暂无函数</p>
        <p className="text-xs text-gray-600">在上方输入框添加函数开始绘图</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {functions.map((func) => (
        <div
          key={func.id}
          className="rounded-lg border border-gray-700 bg-gray-800/50 p-3 transition-all hover:border-gray-600"
        >
          <div className="flex items-center gap-3">
            <div className="relative">
              <input
                type="color"
                value={func.color}
                onChange={(e) => updateFunctionColor(func.id, e.target.value)}
                className="h-6 w-6 cursor-pointer rounded border-2 border-gray-600 bg-transparent"
                style={{ WebkitAppearance: 'none' }}
              />
              <div className="absolute -right-1 -top-1 flex gap-0.5 rounded bg-gray-900 p-0.5 opacity-0 transition-opacity hover:opacity-100">
                {PRESET_COLORS.map((color) => (
                  <button
                    key={color}
                    className="h-3 w-3 rounded-full border border-gray-600"
                    style={{ backgroundColor: color }}
                    onClick={() => updateFunctionColor(func.id, color)}
                  />
                ))}
              </div>
            </div>

            <div className="flex-1 min-w-0">
              <p className="truncate font-mono text-sm text-white">
                {func.expression}
              </p>
              {func.showDerivative && func.derivativeExpression && (
                <p className="truncate font-mono text-xs text-gray-500">
                  f&apos;(x) = {func.derivativeExpression}
                </p>
              )}
            </div>

            <div className="flex items-center gap-1">
              <button
                onClick={() => toggleDerivative(func.id)}
                className={`rounded p-1.5 transition-colors ${
                  func.showDerivative
                    ? 'bg-cyan-500/20 text-cyan-400'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
                title="显示导数"
              >
                <TrendingUp size={16} />
              </button>

              <button
                onClick={() => toggleFunctionVisibility(func.id)}
                className="rounded p-1.5 text-gray-400 transition-colors hover:text-gray-200"
                title={func.visible ? '隐藏' : '显示'}
              >
                {func.visible ? <Eye size={16} /> : <EyeOff size={16} />}
              </button>

              <button
                onClick={() => removeFunction(func.id)}
                className="rounded p-1.5 text-gray-400 transition-colors hover:text-red-400"
                title="删除"
              >
                <Trash2 size={16} />
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

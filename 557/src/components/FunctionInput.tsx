import { useCallback } from 'react';
import { Plus, AlertCircle } from 'lucide-react';
import { useFunction } from '../hooks/useFunction';
import { PRESET_COLORS } from '../utils/colors';
import { cn } from '../lib/utils';

const EXAMPLES = [
  'sin(x)',
  'cos(x)',
  'x^2',
  'ln(x)',
  'e^x',
  'tan(x)',
  'sqrt(x)',
  'piecewise(x < 0, -x, x)',
  'piecewise(x < -1, -1, x < 1, x, 1)',
];

export default function FunctionInput() {
  const {
    inputExpression,
    setInputExpression,
    validationError,
    selectedColor,
    setSelectedColor,
    handleAddFunction,
    handleKeyPress,
  } = useFunction();

  const handleExampleClick = useCallback(
    (example: string) => {
      setInputExpression(example);
    },
    [setInputExpression]
  );

  return (
    <div className="space-y-3 p-4 bg-slate-800/50 rounded-lg">
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={inputExpression}
          onChange={(e) => setInputExpression(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="输入函数表达式，如 sin(x)"
          className={cn(
            'flex-1 px-3 py-2 bg-slate-900 border rounded-md font-mono text-sm',
            'focus:outline-none focus:ring-2 focus:ring-cyan-500 transition-all',
            validationError ? 'border-red-500' : 'border-slate-700'
          )}
        />
        <div className="flex gap-1">
          {PRESET_COLORS.map((color) => (
            <button
              key={color}
              onClick={() => setSelectedColor(color)}
              className={cn(
                'w-6 h-6 rounded-full border-2 transition-all hover:scale-110',
                selectedColor === color ? 'border-white scale-110' : 'border-transparent'
              )}
              style={{ backgroundColor: color }}
            />
          ))}
        </div>
        <button
          onClick={handleAddFunction}
          disabled={!inputExpression.trim() || !!validationError}
          className={cn(
            'flex items-center gap-1 px-3 py-2 bg-cyan-600 text-white rounded-md',
            'hover:bg-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all'
          )}
        >
          <Plus className="w-4 h-4" />
          添加
        </button>
      </div>

      {validationError && (
        <div className="flex items-center gap-1 text-red-500 text-sm">
          <AlertCircle className="w-4 h-4" />
          {validationError}
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <span className="text-slate-400 text-sm">示例：</span>
        {EXAMPLES.map((example) => (
          <button
            key={example}
            onClick={() => handleExampleClick(example)}
            className="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded transition-colors font-mono"
          >
            {example}
          </button>
        ))}
      </div>
    </div>
  );
}

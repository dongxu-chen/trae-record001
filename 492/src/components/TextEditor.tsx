import React, { useState } from 'react';
import { Plus, Trash2, ChevronDown, ChevronUp, Edit3 } from 'lucide-react';
import { useLEDStore } from '../store/ledStore';
import { ColorPicker } from './ColorPicker';

export const TextEditor: React.FC = () => {
  const { lines, activeLineIndex, addLine, removeLine, updateLine, setActiveLineIndex } = useLEDStore();
  const [showColorPicker, setShowColorPicker] = useState<number | null>(null);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
          <Edit3 className="w-4 h-4" />
          字幕内容
        </h3>
        <span className="text-xs text-gray-500">{lines.length} 行</span>
      </div>

      <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
        {lines.map((line, index) => (
          <div
            key={line.id}
            className={`relative group rounded-lg border transition-all ${
              activeLineIndex === index
                ? 'border-cyan-500 bg-cyan-500/10'
                : 'border-gray-700 bg-gray-800/50 hover:border-gray-600'
            }`}
            onClick={() => setActiveLineIndex(index)}
          >
            <div className="flex items-center gap-2 p-2">
              <div
                className="w-6 h-6 rounded-md border-2 border-gray-600 cursor-pointer flex-shrink-0 hover:scale-110 transition-transform"
                style={{ backgroundColor: line.color }}
                onClick={(e) => {
                  e.stopPropagation();
                  setShowColorPicker(showColorPicker === index ? null : index);
                }}
              />
              <input
                type="text"
                value={line.text}
                onChange={(e) => updateLine(index, { text: e.target.value })}
                onClick={(e) => e.stopPropagation()}
                className="flex-1 bg-transparent text-sm text-gray-200 outline-none placeholder-gray-500"
                placeholder="输入字幕文字..."
              />
              {lines.length > 1 && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    removeLine(index);
                  }}
                  className="p-1 text-gray-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
                  title="删除行"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
            </div>

            {showColorPicker === index && (
              <div className="absolute z-20 top-full left-0 mt-2 p-3 bg-gray-900 rounded-xl border border-gray-700 shadow-2xl">
                <ColorPicker
                  color={line.color}
                  onChange={(color) => updateLine(index, { color })}
                />
              </div>
            )}
          </div>
        ))}
      </div>

      <button
        onClick={addLine}
        className="w-full flex items-center justify-center gap-2 py-2 text-sm text-cyan-400 bg-cyan-500/10 border border-cyan-500/30 rounded-lg hover:bg-cyan-500/20 transition-all"
      >
        <Plus className="w-4 h-4" />
        添加字幕行
      </button>
    </div>
  );
};

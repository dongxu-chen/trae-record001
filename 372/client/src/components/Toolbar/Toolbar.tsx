import React from 'react';
import {
  MousePointer2,
  PenTool,
  Minus,
  Square,
  Paintbrush,
  Wand2,
  Undo2,
  Redo2,
  Trash2,
} from 'lucide-react';
import type { ToolType } from '@/types/annotation';
import { useAnnotationStore } from '@/store/useAnnotationStore';

const tools: { type: ToolType; icon: React.ReactNode; label: string; shortcut: string }[] = [
  { type: 'select', icon: <MousePointer2 size={20} />, label: '选择', shortcut: 'V' },
  { type: 'polygon', icon: <PenTool size={20} />, label: '多边形', shortcut: 'P' },
  { type: 'point', icon: <Minus size={20} />, label: '点', shortcut: 'O' },
  { type: 'rectangle', icon: <Square size={20} />, label: '矩形', shortcut: 'R' },
  { type: 'brush', icon: <Paintbrush size={20} />, label: '画笔', shortcut: 'B' },
  { type: 'sam', icon: <Wand2 size={20} />, label: 'SAM点击', shortcut: 'S' },
];

export const Toolbar: React.FC = () => {
  const {
    currentTool,
    setCurrentTool,
    undo,
    redo,
    clearAnnotations,
    brushSize,
    setBrushSize,
    currentColor,
    setCurrentColor,
    currentLabel,
    labels,
    setCurrentLabel,
  } = useAnnotationStore();

  return (
    <div className="w-16 bg-slate-800 border-r border-slate-700 flex flex-col items-center py-4 gap-2">
      {tools.map((tool) => (
        <button
          key={tool.type}
          onClick={() => setCurrentTool(tool.type)}
          className={`w-12 h-12 rounded-lg flex items-center justify-center relative group transition-all
            ${currentTool === tool.type
              ? 'bg-cyan-500 text-white shadow-lg shadow-cyan-500/30'
              : 'text-slate-400 hover:bg-slate-700 hover:text-white'
            }`}
          title={`${tool.label} (${tool.shortcut})`}
        >
          {tool.icon}
          <span className="absolute left-full ml-2 px-2 py-1 bg-slate-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-50">
            {tool.label} <kbd className="ml-1 px-1.5 py-0.5 bg-slate-700 rounded text-[10px]">{tool.shortcut}</kbd>
          </span>
        </button>
      ))}

      <div className="w-10 h-px bg-slate-600 my-2" />

      <button
        onClick={undo}
        className="w-12 h-12 rounded-lg flex items-center justify-center text-slate-400 hover:bg-slate-700 hover:text-white relative group"
        title="撤销 (Ctrl+Z)"
      >
        <Undo2 size={20} />
      </button>

      <button
        onClick={redo}
        className="w-12 h-12 rounded-lg flex items-center justify-center text-slate-400 hover:bg-slate-700 hover:text-white relative group"
        title="重做 (Ctrl+Y)"
      >
        <Redo2 size={20} />
      </button>

      <button
        onClick={clearAnnotations}
        className="w-12 h-12 rounded-lg flex items-center justify-center text-slate-400 hover:bg-slate-700 hover:text-red-400 relative group"
        title="清空所有标注"
      >
        <Trash2 size={20} />
      </button>

      <div className="w-10 h-px bg-slate-600 my-2" />

      <div className="w-12 h-12 rounded-lg border-2 border-slate-600 relative group cursor-pointer overflow-hidden">
        <input
          type="color"
          value={currentColor}
          onChange={(e) => setCurrentColor(e.target.value)}
          className="absolute inset-0 w-full h-full cursor-pointer opacity-0"
        />
        <div
          className="absolute inset-1 rounded"
          style={{ backgroundColor: currentColor }}
        />
        <span className="absolute left-full ml-2 px-2 py-1 bg-slate-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-50">
          标注颜色
        </span>
      </div>

      {currentTool === 'brush' && (
        <div className="mt-2 w-full px-2">
          <input
            type="range"
            min="1"
            max="50"
            value={brushSize}
            onChange={(e) => setBrushSize(Number(e.target.value))}
            className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
            title={`画笔大小: ${brushSize}px`}
          />
          <div className="text-center text-xs text-slate-400 mt-1">{brushSize}</div>
        </div>
      )}

      <div className="mt-2 w-full px-2">
        <select
          value={currentLabel}
          onChange={(e) => setCurrentLabel(e.target.value)}
          className="w-full bg-slate-700 text-white text-xs rounded px-2 py-1 border border-slate-600 focus:outline-none focus:border-cyan-500"
        >
          {labels.map((label) => (
            <option key={label.id} value={label.name}>
              {label.name}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
};

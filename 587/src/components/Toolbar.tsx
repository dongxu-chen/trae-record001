import React from 'react';
import { MousePointer2, Type, ArrowUpRight, Highlighter, Download, Share2, LogOut, Sparkles } from 'lucide-react';
import { useStore } from '../store/useStore';
import { ANNOTATION_COLORS } from '../../shared/types';
import { AnnotationType } from '../../shared/types';

type ToolType = 'select' | AnnotationType;

interface ToolbarProps {
  onExportImage: () => void;
  onExportJSON: () => void;
  onShare: () => void;
  onDisconnect: () => void;
  onAIAnalysis?: () => void;
}

const Toolbar: React.FC<ToolbarProps> = ({
  onExportImage,
  onExportJSON,
  onShare,
  onDisconnect,
  onAIAnalysis,
}) => {
  const { activeTool, setActiveTool, selectedColor, setSelectedColor, isConnected, permissions, isAnalyzing } = useStore();
  const isReadOnly = permissions === 'read';

  const tools: { id: ToolType; icon: React.ReactNode; label: string }[] = [
    { id: 'select', icon: <MousePointer2 size={20} />, label: '选择' },
    { id: 'text', icon: <Type size={20} />, label: '文本' },
    { id: 'arrow', icon: <ArrowUpRight size={20} />, label: '箭头' },
    { id: 'highlight', icon: <Highlighter size={20} />, label: '高亮' },
  ];

  return (
    <div className="bg-gray-900 text-white px-4 py-3 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <h1 className="text-xl font-bold mr-6 bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
          ChartAnnotate
        </h1>
        
        <div className="flex items-center gap-1 bg-gray-800 rounded-lg p-1">
          {tools.map((tool) => {
            const isEditTool = tool.id !== 'select';
            const disabled = isReadOnly && isEditTool;
            
            return (
              <button
                key={tool.id}
                onClick={() => !disabled && setActiveTool(tool.id)}
                className={`p-2 rounded-md transition-all duration-200 ${
                  activeTool === tool.id
                    ? 'bg-blue-600 text-white shadow-lg'
                    : disabled
                    ? 'text-gray-600 cursor-not-allowed'
                    : 'text-gray-400 hover:text-white hover:bg-gray-700'
                }`}
                title={disabled ? `${tool.label} (只读模式)` : tool.label}
                disabled={disabled}
              >
                {tool.icon}
              </button>
            );
          })}
        </div>

        <div className="flex items-center gap-1 ml-4 bg-gray-800 rounded-lg p-1.5">
          {ANNOTATION_COLORS.slice(0, 8).map((color) => (
            <button
              key={color}
              onClick={() => !isReadOnly && setSelectedColor(color)}
              className={`w-6 h-6 rounded-full transition-transform ${
                isReadOnly ? 'opacity-50 cursor-not-allowed' : 'hover:scale-110'
              } ${
                selectedColor === color ? 'ring-2 ring-white ring-offset-2 ring-offset-gray-800 scale-110' : ''
              }`}
              style={{ backgroundColor: color }}
              disabled={isReadOnly}
            />
          ))}
        </div>
      </div>

      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1 mr-4">
          <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
          <span className="text-sm text-gray-400">{isConnected ? '已连接' : '未连接'}</span>
        </div>

        <div className="relative group">
          <button
            className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
          >
            <Download size={18} />
            <span className="text-sm">导出</span>
          </button>
          <div className="absolute right-0 top-full mt-1 bg-gray-800 rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50 min-w-[140px]">
            <button
              onClick={onExportImage}
              className="w-full px-4 py-2 text-left text-sm hover:bg-gray-700 rounded-t-lg transition-colors"
            >
              导出图片
            </button>
            <button
              onClick={onExportJSON}
              className="w-full px-4 py-2 text-left text-sm hover:bg-gray-700 rounded-b-lg transition-colors"
            >
              导出JSON
            </button>
          </div>
        </div>

        <button
          onClick={onAIAnalysis}
          disabled={isAnalyzing}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
            isAnalyzing
              ? 'bg-purple-800 text-purple-300 cursor-not-allowed'
              : 'bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700'
          }`}
        >
          <Sparkles size={18} className={isAnalyzing ? 'animate-spin' : ''} />
          <span className="text-sm">{isAnalyzing ? '分析中...' : 'AI推荐'}</span>
        </button>

        <button
          onClick={onShare}
          className="flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
        >
          <Share2 size={18} />
          <span className="text-sm">分享</span>
        </button>

        <button
          onClick={onDisconnect}
          className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-red-600 rounded-lg transition-colors"
          title="断开连接"
        >
          <LogOut size={18} />
        </button>
      </div>
    </div>
  );
};

export default Toolbar;

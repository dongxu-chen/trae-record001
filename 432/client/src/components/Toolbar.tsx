import React, { useState } from 'react';
import {
  MousePointer2,
  Highlighter,
  Underline,
  Strikethrough,
  MessageSquare,
  Square,
  Circle,
  ArrowRight,
  Undo2,
  Redo2,
  Search,
  List,
  Download,
  ZoomIn,
  ZoomOut,
  Eye,
  Bookmark,
  Users,
} from 'lucide-react';
import { usePdfContext } from '../contexts/PdfContext';
import { AnnotationType } from '../types';
import OcrPanel from './OcrPanel';
import TemplatePanel from './TemplatePanel';
import ReviewPanel from './ReviewPanel';

interface ToolItem {
  type: AnnotationType;
  icon: React.ReactNode;
  label: string;
}

const ANNOTATION_COLORS = [
  '#FFEB3B',
  '#FF9800',
  '#F44336',
  '#4CAF50',
  '#2196F3',
  '#9C27B0',
  '#00BCD4',
];

const tools: ToolItem[] = [
  { type: 'select', icon: <MousePointer2 size={20} />, label: '选择' },
  { type: 'highlight', icon: <Highlighter size={20} />, label: '高亮' },
  { type: 'underline', icon: <Underline size={20} />, label: '下划线' },
  { type: 'strikeout', icon: <Strikethrough size={20} />, label: '删除线' },
  { type: 'comment', icon: <MessageSquare size={20} />, label: '批注' },
  { type: 'rectangle', icon: <Square size={20} />, label: '矩形' },
  { type: 'circle', icon: <Circle size={20} />, label: '圆形' },
  { type: 'arrow', icon: <ArrowRight size={20} />, label: '箭头' },
];

const Toolbar: React.FC = () => {
  const { state, dispatch, undo, redo, canUndo, canRedo } = usePdfContext();
  const [showColorPicker, setShowColorPicker] = useState(false);
  const [showOcrPanel, setShowOcrPanel] = useState(false);
  const [showTemplatePanel, setShowTemplatePanel] = useState(false);
  const [showReviewPanel, setShowReviewPanel] = useState(false);

  const { currentTool, currentColor } = state.tool;
  const { zoom, sidebarOpen, sidebarTab } = state.viewer;
  const reviewSession = state.reviewSession;

  const handleToolChange = (tool: AnnotationType) => {
    dispatch({ type: 'SET_CURRENT_TOOL', payload: tool });
  };

  const handleColorChange = (color: string) => {
    dispatch({ type: 'SET_CURRENT_COLOR', payload: color });
    setShowColorPicker(false);
  };

  const handleZoomIn = () => {
    dispatch({ type: 'SET_ZOOM', payload: Math.min(zoom + 0.25, 3) });
  };

  const handleZoomOut = () => {
    dispatch({ type: 'SET_ZOOM', payload: Math.max(zoom - 0.25, 0.25) });
  };

  const handleExport = async () => {
    if (!state.document) return;

    try {
      const formData = new FormData();
      formData.append('file', state.document.file);
      formData.append('annotations', JSON.stringify(state.document.annotations));

      const response = await fetch('/api/pdf/export/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          fileName: state.document.name,
          annotations: state.document.annotations,
        }),
      });

      const { taskId } = await response.json();

      const checkStatus = async () => {
        const statusRes = await fetch(`/api/pdf/export/${taskId}/status`);
        const statusData = await statusRes.json();

        if (statusData.status === 'completed' && statusData.downloadUrl) {
          window.open(statusData.downloadUrl, '_blank');
        } else if (statusData.status === 'failed') {
          alert('导出失败');
        } else if (statusData.status === 'processing') {
          setTimeout(checkStatus, 500);
        }
      };

      checkStatus();
    } catch (error) {
      console.error('Export failed:', error);
      alert('导出失败，请重试');
    }
  };

  return (
    <div className="h-14 bg-white border-b border-gray-200 flex items-center px-4 gap-2 shadow-sm">
      <div className="flex items-center gap-1 border-r border-gray-200 pr-3">
        {tools.slice(0, 4).map((tool) => (
          <button
            key={tool.type}
            className={`toolbar-btn ${currentTool === tool.type ? 'active' : ''}`}
            onClick={() => handleToolChange(tool.type)}
            title={tool.label}
          >
            {tool.icon}
          </button>
        ))}
      </div>

      <div className="flex items-center gap-1 border-r border-gray-200 pr-3">
        {tools.slice(4).map((tool) => (
          <button
            key={tool.type}
            className={`toolbar-btn ${currentTool === tool.type ? 'active' : ''}`}
            onClick={() => handleToolChange(tool.type)}
            title={tool.label}
          >
            {tool.icon}
          </button>
        ))}
      </div>

      <div className="flex items-center gap-1 border-r border-gray-200 pr-3">
        <div className="relative">
          <button
            className="toolbar-btn flex items-center gap-1"
            onClick={() => setShowColorPicker(!showColorPicker)}
            title="选择颜色"
          >
            <div
              className="w-5 h-5 rounded-full border-2 border-gray-300"
              style={{ backgroundColor: currentColor }}
            />
          </button>
          {showColorPicker && (
            <div className="absolute top-full left-0 mt-2 p-2 bg-white rounded-lg shadow-lg border border-gray-200 flex gap-1 z-50">
              {ANNOTATION_COLORS.map((color) => (
                <button
                  key={color}
                  className={`color-swatch ${currentColor === color ? 'active' : ''}`}
                  style={{ backgroundColor: color }}
                  onClick={() => handleColorChange(color)}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-1 border-r border-gray-200 pr-3">
        <button
          className="toolbar-btn disabled:opacity-50 disabled:cursor-not-allowed"
          onClick={undo}
          disabled={!canUndo}
          title="撤销"
        >
          <Undo2 size={20} />
        </button>
        <button
          className="toolbar-btn disabled:opacity-50 disabled:cursor-not-allowed"
          onClick={redo}
          disabled={!canRedo}
          title="重做"
        >
          <Redo2 size={20} />
        </button>
      </div>

      <div className="flex items-center gap-1 border-r border-gray-200 pr-3">
        <button
          className="toolbar-btn"
          onClick={handleZoomOut}
          title="缩小"
        >
          <ZoomOut size={20} />
        </button>
        <span className="text-sm font-medium w-16 text-center">
          {Math.round(zoom * 100)}%
        </span>
        <button
          className="toolbar-btn"
          onClick={handleZoomIn}
          title="放大"
        >
          <ZoomIn size={20} />
        </button>
      </div>

      <div className="flex items-center gap-1 border-r border-gray-200 pr-3">
        <button
          className={`toolbar-btn ${sidebarOpen && sidebarTab === 'search' ? 'active' : ''}`}
          onClick={() => {
            dispatch({ type: 'SET_SIDEBAR_TAB', payload: 'search' });
            if (!sidebarOpen) dispatch({ type: 'TOGGLE_SIDEBAR' });
          }}
          title="搜索"
        >
          <Search size={20} />
        </button>
        <button
          className={`toolbar-btn ${sidebarOpen && sidebarTab === 'outline' ? 'active' : ''}`}
          onClick={() => {
            dispatch({ type: 'SET_SIDEBAR_TAB', payload: 'outline' });
            if (!sidebarOpen) dispatch({ type: 'TOGGLE_SIDEBAR' });
          }}
          title="目录"
        >
          <List size={20} />
        </button>
      </div>

      <div className="flex items-center gap-1 border-r border-gray-200 pr-3">
        <button
          className="toolbar-btn"
          onClick={() => setShowOcrPanel(true)}
          title="OCR文字识别"
        >
          <Eye size={20} />
        </button>
        <button
          className="toolbar-btn"
          onClick={() => setShowTemplatePanel(true)}
          title="标注模板"
        >
          <Bookmark size={20} />
        </button>
        <button
          className={`toolbar-btn ${reviewSession ? 'active' : ''}`}
          onClick={() => setShowReviewPanel(true)}
          title="多人审阅"
        >
          <Users size={20} />
        </button>
      </div>

      <div className="flex-1" />

      <button
        className="toolbar-btn flex items-center gap-2 px-4 bg-primary-600 text-white hover:bg-primary-700 hover:no-underline"
        onClick={handleExport}
        title="导出PDF"
      >
        <Download size={18} />
        <span className="text-sm font-medium">导出</span>
      </button>

      <OcrPanel isOpen={showOcrPanel} onClose={() => setShowOcrPanel(false)} />
      <TemplatePanel isOpen={showTemplatePanel} onClose={() => setShowTemplatePanel(false)} />
      <ReviewPanel isOpen={showReviewPanel} onClose={() => setShowReviewPanel(false)} />
    </div>
  );
};

export default Toolbar;

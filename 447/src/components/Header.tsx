import { PenTool, Save, Download, BookOpen, Settings, Pen, Mic, LayoutTemplate } from 'lucide-react';
import { useEditorStore } from '@/store/useEditorStore';

export default function Header() {
  const {
    editorMode,
    setEditorMode,
    toggleFormulaLibrary,
    toggleExportModal,
    toggleVoiceInputModal,
    toggleTemplateMarketplace,
    toggleSettingsModal,
  } = useEditorStore();

  return (
    <header className="h-14 bg-bg-secondary border-b border-border-custom flex items-center justify-between px-6">
      <div className="flex items-center gap-2">
        <span className="text-accent text-xl">∫</span>
        <span className="font-mono font-bold text-accent text-lg">MathForge</span>
      </div>

      <div className="flex items-center gap-1 bg-bg-tertiary rounded-lg p-1">
        <button
          onClick={() => setEditorMode('visual')}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg transition-colors ${
            editorMode === 'visual'
              ? 'bg-accent text-bg-primary font-medium'
              : 'text-text-secondary hover:text-text-primary'
          }`}
        >
          <PenTool size={14} />
          Visual
        </button>
        <button
          onClick={() => { setEditorMode('handwriting'); toggleVoiceInputModal(); }}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg transition-colors ${
            editorMode === 'handwriting'
              ? 'bg-accent text-bg-primary font-medium'
              : 'text-text-secondary hover:text-text-primary'
          }`}
        >
          <Pen size={14} />
          手写
        </button>
        <button
          onClick={() => { setEditorMode('voice'); toggleVoiceInputModal(); }}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg transition-colors ${
            editorMode === 'voice'
              ? 'bg-accent text-bg-primary font-medium'
              : 'text-text-secondary hover:text-text-primary'
          }`}
        >
          <Mic size={14} />
          语音
        </button>
      </div>

      <div className="flex items-center gap-1">
        <button
          onClick={toggleTemplateMarketplace}
          title="模板市场"
          className="p-2 text-text-secondary hover:bg-bg-tertiary hover:text-text-primary rounded-lg transition-colors"
        >
          <LayoutTemplate size={18} />
        </button>
        <button
          onClick={toggleFormulaLibrary}
          title="保存到公式库"
          className="p-2 text-text-secondary hover:bg-bg-tertiary hover:text-text-primary rounded-lg transition-colors"
        >
          <Save size={18} />
        </button>
        <button
          onClick={toggleExportModal}
          title="导出"
          className="p-2 text-text-secondary hover:bg-bg-tertiary hover:text-text-primary rounded-lg transition-colors"
        >
          <Download size={18} />
        </button>
        <button
          onClick={toggleFormulaLibrary}
          title="公式库"
          className="p-2 text-text-secondary hover:bg-bg-tertiary hover:text-text-primary rounded-lg transition-colors"
        >
          <BookOpen size={18} />
        </button>
        <button
          onClick={toggleSettingsModal}
          title="设置"
          className="p-2 text-text-secondary hover:bg-bg-tertiary hover:text-text-primary rounded-lg transition-colors"
        >
          <Settings size={18} />
        </button>
      </div>
    </header>
  );
}

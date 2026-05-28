import { useEffect } from 'react';
import Header from '@/components/Header';
import Toolbar from '@/components/Toolbar';
import MathQuillEditor from '@/components/MathQuillEditor';
import LatexCodePanel from '@/components/LatexCodePanel';
import KatexPreview from '@/components/KatexPreview';
import HandwritingModal from '@/components/HandwritingModal';
import VoiceInputModal from '@/components/VoiceInputModal';
import FormulaLibrary from '@/components/FormulaLibrary';
import TemplateMarketplace from '@/components/TemplateMarketplace';
import ExportModal from '@/components/ExportModal';
import SettingsModal from '@/components/SettingsModal';
import { useEditorStore } from '@/store/useEditorStore';

export default function Home() {
  const { editorMode, toggleHandwritingModal, toggleVoiceInputModal } = useEditorStore();

  useEffect(() => {
    if (editorMode === 'handwriting') {
      toggleHandwritingModal();
    } else if (editorMode === 'voice') {
      toggleVoiceInputModal();
    }
  }, [editorMode, toggleHandwritingModal, toggleVoiceInputModal]);

  return (
    <div className="flex flex-col h-full bg-bg-primary">
      <Header />

      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 flex flex-col min-w-0">
          <div className="flex-1 flex min-h-0">
            <div className="flex-1 flex flex-col min-w-0 border-r border-border-custom">
              <div className="flex-1 overflow-auto p-5 flex flex-col gap-4">
                <div className="space-y-1.5">
                  <span className="text-xs text-text-muted font-medium tracking-wide uppercase px-1">
                    公式编辑
                  </span>
                  <MathQuillEditor />
                </div>
                <LatexCodePanel />
              </div>
            </div>

            <div className="w-[45%] flex flex-col min-w-[320px]">
              <div className="flex-1 p-5 overflow-auto">
                <div className="space-y-1.5 h-full flex flex-col">
                  <span className="text-xs text-text-muted font-medium tracking-wide uppercase px-1">
                    实时预览
                  </span>
                  <div className="flex-1 min-h-[200px]">
                    <KatexPreview />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <Toolbar />
        </div>

        <FormulaLibrary />
      </div>

      <HandwritingModal />
      <VoiceInputModal />
      <TemplateMarketplace />
      <ExportModal />
      <SettingsModal />
    </div>
  );
}

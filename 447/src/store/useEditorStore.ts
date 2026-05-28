import { create } from 'zustand';

interface EditorState {
  latex: string;
  editorMode: 'visual' | 'handwriting' | 'voice';
  showFormulaLibrary: boolean;
  showExportModal: boolean;
  showHandwritingModal: boolean;
  showVoiceInputModal: boolean;
  showTemplateMarketplace: boolean;
  showSettingsModal: boolean;
  isLibraryLoading: boolean;

  setLatex: (latex: string) => void;
  setEditorMode: (mode: 'visual' | 'handwriting' | 'voice') => void;
  toggleFormulaLibrary: () => void;
  toggleExportModal: () => void;
  toggleHandwritingModal: () => void;
  toggleVoiceInputModal: () => void;
  toggleTemplateMarketplace: () => void;
  toggleSettingsModal: () => void;
  setLibraryLoading: (loading: boolean) => void;
}

export const useEditorStore = create<EditorState>((set) => ({
  latex: '',
  editorMode: 'visual',
  showFormulaLibrary: false,
  showExportModal: false,
  showHandwritingModal: false,
  showVoiceInputModal: false,
  showTemplateMarketplace: false,
  showSettingsModal: false,
  isLibraryLoading: false,

  setLatex: (latex) => set({ latex }),
  setEditorMode: (mode) => set({ editorMode: mode }),
  toggleFormulaLibrary: () => set((s) => ({ showFormulaLibrary: !s.showFormulaLibrary })),
  toggleExportModal: () => set((s) => ({ showExportModal: !s.showExportModal })),
  toggleHandwritingModal: () => set((s) => ({ showHandwritingModal: !s.showHandwritingModal })),
  toggleVoiceInputModal: () => set((s) => ({ showVoiceInputModal: !s.showVoiceInputModal })),
  toggleTemplateMarketplace: () => set((s) => ({ showTemplateMarketplace: !s.showTemplateMarketplace })),
  toggleSettingsModal: () => set((s) => ({ showSettingsModal: !s.showSettingsModal })),
  setLibraryLoading: (loading) => set({ isLibraryLoading: loading }),
}));

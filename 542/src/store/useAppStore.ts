import { create } from 'zustand';
import type { ColorblindType, RGB, ContrastIssue, WcagReport } from '@/types';

interface AppState {
  originalImage: ImageData | null;
  simulatedImage: ImageData | null;
  selectedType: ColorblindType;
  pickedColor: RGB | null;
  simulatedPickedColor: RGB | null;
  contrastIssues: ContrastIssue[];
  wcagReport: WcagReport | null;
  isAnalyzing: boolean;
  showCompare: boolean;
  comparePosition: number;

  setOriginalImage: (image: ImageData | null) => void;
  setSimulatedImage: (image: ImageData | null) => void;
  setSelectedType: (type: ColorblindType) => void;
  setPickedColor: (color: RGB | null) => void;
  setSimulatedPickedColor: (color: RGB | null) => void;
  setContrastIssues: (issues: ContrastIssue[]) => void;
  setWcagReport: (report: WcagReport | null) => void;
  setIsAnalyzing: (analyzing: boolean) => void;
  setShowCompare: (show: boolean) => void;
  setComparePosition: (position: number) => void;
  reset: () => void;
}

const initialState = {
  originalImage: null,
  simulatedImage: null,
  selectedType: 'protanopia' as ColorblindType,
  pickedColor: null,
  simulatedPickedColor: null,
  contrastIssues: [],
  wcagReport: null,
  isAnalyzing: false,
  showCompare: true,
  comparePosition: 50,
};

export const useAppStore = create<AppState>((set) => ({
  ...initialState,

  setOriginalImage: (image) => set({ originalImage: image }),
  setSimulatedImage: (image) => set({ simulatedImage: image }),
  setSelectedType: (type) => set({ selectedType: type }),
  setPickedColor: (color) => set({ pickedColor: color }),
  setSimulatedPickedColor: (color) => set({ simulatedPickedColor: color }),
  setContrastIssues: (issues) => set({ contrastIssues: issues }),
  setWcagReport: (report) => set({ wcagReport: report }),
  setIsAnalyzing: (analyzing) => set({ isAnalyzing: analyzing }),
  setShowCompare: (show) => set({ showCompare: show }),
  setComparePosition: (position) => set({ comparePosition: position }),
  reset: () => set(initialState),
}));

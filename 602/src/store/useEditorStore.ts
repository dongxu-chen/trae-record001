import { create } from 'zustand';
import type { EditorState } from '@/types';

interface EditorStore extends EditorState {
  setSelectedElementId: (id: string | null) => void;
  setSelectedTrackId: (id: string | null) => void;
  setSelectedKeyframeId: (id: string | null) => void;
  setCurrentTime: (time: number) => void;
  setIsPlaying: (playing: boolean) => void;
  setIsLooping: (looping: boolean) => void;
  setZoom: (zoom: number) => void;
  setPan: (pan: { x: number; y: number }) => void;
  setShowGrid: (show: boolean) => void;
  setSnapToGrid: (snap: boolean) => void;
  setGridSize: (size: number) => void;
  setActiveModal: (modal: EditorState['activeModal']) => void;
  resetEditor: () => void;
}

const defaultState: EditorState = {
  selectedElementId: null,
  selectedTrackId: null,
  selectedKeyframeId: null,
  currentTime: 0,
  isPlaying: false,
  isLooping: false,
  zoom: 1,
  pan: { x: 0, y: 0 },
  showGrid: true,
  snapToGrid: false,
  gridSize: 20,
  activeModal: 'none',
};

export const useEditorStore = create<EditorStore>((set) => ({
  ...defaultState,
  
  setSelectedElementId: (id) => set({ selectedElementId: id }),
  setSelectedTrackId: (id) => set({ selectedTrackId: id }),
  setSelectedKeyframeId: (id) => set({ selectedKeyframeId: id }),
  setCurrentTime: (time) => set({ currentTime: Math.max(0, time) }),
  setIsPlaying: (isPlaying) => set({ isPlaying }),
  setIsLooping: (isLooping) => set({ isLooping }),
  setZoom: (zoom) => set({ zoom: Math.max(0.1, Math.min(5, zoom)) }),
  setPan: (pan) => set({ pan }),
  setShowGrid: (showGrid) => set({ showGrid }),
  setSnapToGrid: (snapToGrid) => set({ snapToGrid }),
  setGridSize: (gridSize) => set({ gridSize: Math.max(5, Math.min(100, gridSize)) }),
  setActiveModal: (activeModal) => set({ activeModal }),
  
  resetEditor: () => set(defaultState),
}));

import { create } from 'zustand';
import type { Annotation, ToolType, ImageInfo, Label, CanvasState } from '@/types/annotation';
import { PRESET_COLORS } from '@/types/annotation';
import { generateId } from '@/utils/geometry';
import { calculatePixelArea } from '@/utils/pixelCalc';

interface AnnotationStore {
  annotations: Annotation[];
  selectedAnnotationId: string | null;
  currentTool: ToolType;
  currentLabel: string;
  currentColor: string;
  images: ImageInfo[];
  currentImageId: string | null;
  labels: Label[];
  canvasState: CanvasState;
  history: Annotation[][];
  historyIndex: number;
  brushSize: number;
  samLoading: boolean;
  samPreviewMask: number[] | null;
  samStats: any;
  
  addAnnotation: (annotation: Omit<Annotation, 'id' | 'createdAt' | 'label' | 'color' | 'visible'> & Partial<Annotation>) => void;
  updateAnnotation: (id: string, updates: Partial<Annotation>) => void;
  deleteAnnotation: (id: string) => void;
  selectAnnotation: (id: string | null) => void;
  setCurrentTool: (tool: ToolType) => void;
  setCurrentLabel: (label: string) => void;
  setCurrentColor: (color: string) => void;
  setBrushSize: (size: number) => void;
  addImage: (image: Omit<ImageInfo, 'id' | 'uploadedAt'>) => ImageInfo;
  setCurrentImage: (id: string | null) => void;
  deleteImage: (id: string) => void;
  addLabel: (name: string, color?: string) => void;
  deleteLabel: (id: string) => void;
  setCanvasState: (state: Partial<CanvasState>) => void;
  undo: () => void;
  redo: () => void;
  clearAnnotations: () => void;
  setSamLoading: (loading: boolean) => void;
  setSamPreviewMask: (mask: number[] | null) => void;
  setSamStats: (stats: any) => void;
  updateAnnotationLabel: (id: string, label: string) => void;
  saveToHistory: () => void;
}

const initialCanvasState: CanvasState = {
  scale: 1,
  offsetX: 0,
  offsetY: 0,
  imageWidth: 0,
  imageHeight: 0,
};

const defaultLabels: Label[] = [
  { id: '1', name: '前景', color: PRESET_COLORS[0] },
  { id: '2', name: '背景', color: PRESET_COLORS[1] },
  { id: '3', name: '物体', color: PRESET_COLORS[2] },
];

export const useAnnotationStore = create<AnnotationStore>((set, get) => ({
  annotations: [],
  selectedAnnotationId: null,
  currentTool: 'select',
  currentLabel: '前景',
  currentColor: PRESET_COLORS[0],
  images: [],
  currentImageId: null,
  labels: defaultLabels,
  canvasState: initialCanvasState,
  history: [],
  historyIndex: -1,
  brushSize: 5,
  samLoading: false,
  samPreviewMask: null,
  samStats: null,

  addAnnotation: (annotationData) => {
    const state = get();
    const newAnnotation: Annotation = {
      id: generateId(),
      createdAt: Date.now(),
      label: state.currentLabel,
      color: state.currentColor,
      visible: true,
      ...annotationData,
    } as Annotation;

    const currentImage = state.images.find(img => img.id === state.currentImageId);
    if (currentImage) {
      const { area, percentage } = calculatePixelArea(
        newAnnotation,
        currentImage.width,
        currentImage.height
      );
      (newAnnotation as Annotation).pixelArea = area;
      (newAnnotation as Annotation).pixelPercentage = percentage;
    }

    set((state) => {
      const newAnnotations = [...state.annotations, newAnnotation];
      return {
        annotations: newAnnotations,
        selectedAnnotationId: newAnnotation.id,
        history: [...state.history.slice(0, state.historyIndex + 1), newAnnotations],
        historyIndex: state.historyIndex + 1,
      };
    });
  },

  updateAnnotation: (id, updates) => {
    const state = get();
    const currentImage = state.images.find(img => img.id === state.currentImageId);
    
    set((state) => ({
      annotations: state.annotations.map((ann) => {
        if (ann.id === id) {
          const updated = { ...ann, ...updates } as Annotation;
          if (currentImage) {
            const { area, percentage } = calculatePixelArea(
              updated,
              currentImage.width,
              currentImage.height
            );
            updated.pixelArea = area;
            updated.pixelPercentage = percentage;
          }
          return updated;
        }
        return ann;
      }),
    }));
    get().saveToHistory();
  },

  deleteAnnotation: (id) => {
    set((state) => ({
      annotations: state.annotations.filter((ann) => ann.id !== id),
      selectedAnnotationId: state.selectedAnnotationId === id ? null : state.selectedAnnotationId,
    }));
    get().saveToHistory();
  },

  selectAnnotation: (id) => set({ selectedAnnotationId: id }),
  setCurrentTool: (tool) => set({ currentTool: tool }),
  setCurrentLabel: (label) => set({ currentLabel: label }),
  setCurrentColor: (color) => set({ currentColor: color }),
  setBrushSize: (size) => set({ brushSize: size }),

  addImage: (imageData) => {
    const newImage: ImageInfo = {
      ...imageData,
      id: generateId(),
      uploadedAt: Date.now(),
    };
    set((state) => ({
      images: [...state.images, newImage],
      currentImageId: newImage.id,
      annotations: [],
      history: [],
      historyIndex: -1,
      canvasState: {
        ...initialCanvasState,
        imageWidth: newImage.width,
        imageHeight: newImage.height,
      },
    }));
    return newImage;
  },

  setCurrentImage: (id) => {
    const state = get();
    const image = state.images.find(img => img.id === id);
    set({
      currentImageId: id,
      annotations: [],
      history: [],
      historyIndex: -1,
      canvasState: image ? {
        ...initialCanvasState,
        imageWidth: image.width,
        imageHeight: image.height,
      } : initialCanvasState,
    });
  },

  deleteImage: (id) => {
    set((state) => ({
      images: state.images.filter((img) => img.id !== id),
      currentImageId: state.currentImageId === id ? null : state.currentImageId,
      annotations: state.currentImageId === id ? [] : state.annotations,
    }));
  },

  addLabel: (name, color) => {
    const newLabel: Label = {
      id: generateId(),
      name,
      color: color || PRESET_COLORS[get().labels.length % PRESET_COLORS.length],
    };
    set((state) => ({ labels: [...state.labels, newLabel] }));
  },

  deleteLabel: (id) => {
    set((state) => ({
      labels: state.labels.filter((label) => label.id !== id),
    }));
  },

  setCanvasState: (newState) => {
    set((state) => ({
      canvasState: { ...state.canvasState, ...newState },
    }));
  },

  undo: () => {
    const state = get();
    if (state.historyIndex > 0) {
      const newIndex = state.historyIndex - 1;
      set({
        annotations: state.history[newIndex],
        historyIndex: newIndex,
      });
    }
  },

  redo: () => {
    const state = get();
    if (state.historyIndex < state.history.length - 1) {
      const newIndex = state.historyIndex + 1;
      set({
        annotations: state.history[newIndex],
        historyIndex: newIndex,
      });
    }
  },

  clearAnnotations: () => {
    set({ annotations: [], selectedAnnotationId: null });
    get().saveToHistory();
  },

  setSamLoading: (loading) => set({ samLoading: loading }),
  setSamPreviewMask: (mask) => set({ samPreviewMask: mask }),
  setSamStats: (stats) => set({ samStats: stats }),
  updateAnnotationLabel: (id, label) => {
    set((state) => ({
      annotations: state.annotations.map((ann) =>
        ann.id === id ? { ...ann, label } : ann
      ),
    }));
    get().saveToHistory();
  },

  saveToHistory: () => {
    const state = get();
    set({
      history: [...state.history.slice(0, state.historyIndex + 1), [...state.annotations]],
      historyIndex: state.historyIndex + 1,
    });
  },
}));

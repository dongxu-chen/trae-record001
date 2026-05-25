import { create } from 'zustand'
import { Annotation, LabelType, ToolType, Point3D } from '@/types'

interface AnnotationState {
  annotations: Annotation[]
  selectedAnnotationId: string | null
  currentTool: ToolType
  currentLabel: LabelType
  isDrawing: boolean
  drawingPoints: Point3D[]
  setAnnotations: (annotations: Annotation[]) => void
  addAnnotation: (annotation: Annotation) => void
  updateAnnotation: (id: string, updates: Partial<Annotation>) => void
  deleteAnnotation: (id: string) => void
  setSelectedAnnotationId: (id: string | null) => void
  setCurrentTool: (tool: ToolType) => void
  setCurrentLabel: (label: LabelType) => void
  setIsDrawing: (drawing: boolean) => void
  addDrawingPoint: (point: Point3D) => void
  clearDrawingPoints: () => void
  clearAll: () => void
}

export const useAnnotationStore = create<AnnotationState>((set) => ({
  annotations: [],
  selectedAnnotationId: null,
  currentTool: 'none',
  currentLabel: 'vehicle',
  isDrawing: false,
  drawingPoints: [],
  setAnnotations: (annotations) => set({ annotations }),
  addAnnotation: (annotation) =>
    set((state) => ({
      ({ annotations: [...state.annotations, annotation] }),
    ),
  updateAnnotation: (id, updates) =>
    set((state) => ({
      annotations: state.annotations.map((a) =>
        a.id === id ? { ...a, ...updates } : a,
      ),
    })),
  deleteAnnotation: (id) =>
    set((state) => ({
      annotations: state.annotations.filter((a) => a.id !== id),
      selectedAnnotationId: state.selectedAnnotationId === id ? null : state.selectedAnnotationId,
    })),
  setSelectedAnnotationId: (id) => set({ selectedAnnotationId: id }),
  setCurrentTool: (tool) => set({ currentTool: tool, isDrawing: false, drawingPoints: [] }),
  setCurrentLabel: (label) => set({ currentLabel: label }),
  setIsDrawing: (drawing) => set({ isDrawing: drawing }),
  addDrawingPoint: (point) =>
    set((state) => ({ drawingPoints: [...state.drawingPoints, point] })),
  clearDrawingPoints: () => set({ drawingPoints: [], isDrawing: false }),
  clearAll: () =>
    set({
      annotations: [],
      selectedAnnotationId: null,
      drawingPoints: [],
      isDrawing: false,
    }),
}))

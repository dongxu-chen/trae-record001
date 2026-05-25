import { create } from 'zustand'
import { Annotation } from '@/types'
import { Measurement, MeasurementType } from '@/utils/MeasurementTool'
import { SamplingResult, QualityIssue } from '@/utils/QualityInspector'

interface ToolsState {
  activeTool: 'annotate' | 'measure' | 'inspect' | 'ai'
  measurementType: MeasurementType
  measurements: Measurement[]
  isMeasuring: boolean
  measurementPoints: { x: number; y: number; z: number }[]
  
  inspectionResult: SamplingResult | null
  qualityIssues: QualityIssue[]
  isInspecting: boolean
  
  isAiProcessing: boolean
  aiProgress: number
  aiAnnotations: Annotation[]
  
  setActiveTool: (tool: 'annotate' | 'measure' | 'inspect' | 'ai') => void
  setMeasurementType: (type: MeasurementType) => void
  addMeasurement: (measurement: Measurement) => void
  removeMeasurement: (id: string) => void
  clearMeasurements: () => void
  setIsMeasuring: (measuring: boolean) => void
  addMeasurementPoint: (point: { x: number; y: number; z: number }) => void
  clearMeasurementPoints: () => void
  
  setInspectionResult: (result: SamplingResult | null) => void
  setQualityIssues: (issues: QualityIssue[]) => void
  setIsInspecting: (inspecting: boolean) => void
  
  setIsAiProcessing: (processing: boolean) => void
  setAiProgress: (progress: number) => void
  setAiAnnotations: (annotations: Annotation[]) => void
  clearAiAnnotations: () => void
}

export const useToolsStore = create<ToolsState>((set) => ({
  activeTool: 'annotate',
  measurementType: 'distance',
  measurements: [],
  isMeasuring: false,
  measurementPoints: [],
  
  inspectionResult: null,
  qualityIssues: [],
  isInspecting: false,
  
  isAiProcessing: false,
  aiProgress: 0,
  aiAnnotations: [],
  
  setActiveTool: (tool) => set({ activeTool: tool }),
  setMeasurementType: (type) => set({ measurementType: type, measurementPoints: [], isMeasuring: false }),
  addMeasurement: (measurement) =>
    set((state) => ({
      measurements: [...state.measurements, measurement],
    })),
  removeMeasurement: (id) =>
    set((state) => ({
      measurements: state.measurements.filter((m) => m.id !== id),
    })),
  clearMeasurements: () => set({ measurements: [], measurementPoints: [], isMeasuring: false }),
  setIsMeasuring: (measuring) => set({ isMeasuring: measuring }),
  addMeasurementPoint: (point) =>
    set((state) => ({
      measurementPoints: [...state.measurementPoints, point],
    })),
  clearMeasurementPoints: () => set({ measurementPoints: [], isMeasuring: false }),
  
  setInspectionResult: (result) => set({ inspectionResult: result }),
  setQualityIssues: (issues) => set({ qualityIssues: issues }),
  setIsInspecting: (inspecting) => set({ isInspecting: inspecting }),
  
  setIsAiProcessing: (processing) => set({ isAiProcessing: processing }),
  setAiProgress: (progress) => set({ aiProgress: progress }),
  setAiAnnotations: (annotations) => set({ aiAnnotations: annotations }),
  clearAiAnnotations: () => set({ aiAnnotations: [] }),
}))

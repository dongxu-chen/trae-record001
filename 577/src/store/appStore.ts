import { create } from 'zustand'
import { v4 as uuidv4 } from 'uuid'

export interface ColumnMeta {
  name: string
  type: 'string' | 'number' | 'boolean' | 'date'
}

export interface FileMeta {
  fileId: string
  fileName: string
  format: 'csv' | 'json' | 'parquet'
  totalRows: number
  columns: ColumnMeta[]
  fileSize: number
  uploadedAt: string
}

export type SampleMethod = 'random' | 'stratified' | 'systematic'

export interface SampleConfig {
  method: SampleMethod
  ratio: number
  stratifyColumn: string
  stepSize: number
}

export interface SampleStats {
  sampleSize: number
  totalSize: number
  ratio: number
  distribution?: Record<string, number>
}

export interface StratifyIndex {
  column: string
  groups: Record<string, number[]>
}

export type AnalysisGoal = 'descriptive' | 'inferential' | 'exploratory' | 'classification' | 'regression'

export interface SampleRecommendation {
  recommendedMethod: SampleMethod
  confidence: number
  reasons: string[]
  alternatives: Array<{ method: SampleMethod; reason: string }>
}

export interface DistributionComparison {
  column: string
  overall: Array<{ bin: string; count: number; ratio: number }>
  sample: Array<{ bin: string; count: number; ratio: number }>
  ksStatistic: number
  wassersteinDistance: number
}

export interface AuditRecord {
  id: string
  timestamp: string
  fileId: string
  fileName: string
  config: SampleConfig
  stats: SampleStats
  recommendation?: SampleRecommendation
  comparison?: DistributionComparison
  totalRows: number
  columnNames: string[]
}

interface AppState {
  fileMeta: FileMeta | null
  isUploading: boolean
  uploadProgress: number
  rawData: Record<string, unknown>[]
  rawPage: number
  rawPageSize: number
  allDataCache: Record<string, unknown>[]
  sampleConfig: SampleConfig
  sampleResult: Record<string, unknown>[] | null
  sampleIndices: number[]
  sampleStats: SampleStats | null
  isSampling: boolean
  columnStats: Array<{ value: string; count: number }> | null
  stratifyIndex: StratifyIndex | null
  analysisGoal: AnalysisGoal
  recommendation: SampleRecommendation | null
  distributionComparison: DistributionComparison | null
  auditHistory: AuditRecord[]
  activeAuditId: string | null

  setFileMeta: (meta: FileMeta | null) => void
  setIsUploading: (v: boolean) => void
  setUploadProgress: (v: number) => void
  setRawData: (data: Record<string, unknown>[]) => void
  setRawPage: (page: number) => void
  setRawPageSize: (size: number) => void
  setAllDataCache: (data: Record<string, unknown>[]) => void
  setSampleConfig: (config: Partial<SampleConfig>) => void
  setSampleResult: (data: Record<string, unknown>[], indices: number[], stats: SampleStats) => void
  setIsSampling: (v: boolean) => void
  setColumnStats: (stats: Array<{ value: string; count: number }>) => void
  setStratifyIndex: (index: StratifyIndex | null) => void
  setAnalysisGoal: (goal: AnalysisGoal) => void
  setRecommendation: (rec: SampleRecommendation | null) => void
  setDistributionComparison: (comp: DistributionComparison | null) => void
  addAuditRecord: (record: Omit<AuditRecord, 'id' | 'timestamp'>) => void
  setActiveAuditId: (id: string | null) => void
  applyAuditRecord: (record: AuditRecord) => void
  reset: () => void
}

const defaultSampleConfig: SampleConfig = {
  method: 'random',
  ratio: 0.1,
  stratifyColumn: '',
  stepSize: 10,
}

export const useAppStore = create<AppState>((set, get) => ({
  fileMeta: null,
  isUploading: false,
  uploadProgress: 0,
  rawData: [],
  rawPage: 1,
  rawPageSize: 50,
  allDataCache: [],
  sampleConfig: { ...defaultSampleConfig },
  sampleResult: null,
  sampleIndices: [],
  sampleStats: null,
  isSampling: false,
  columnStats: null,
  stratifyIndex: null,
  analysisGoal: 'descriptive',
  recommendation: null,
  distributionComparison: null,
  auditHistory: [],
  activeAuditId: null,

  setFileMeta: (meta) => set({ fileMeta: meta }),
  setIsUploading: (v) => set({ isUploading: v }),
  setUploadProgress: (v) => set({ uploadProgress: v }),
  setRawData: (data) => set({ rawData: data }),
  setRawPage: (page) => set({ rawPage: page }),
  setRawPageSize: (size) => set({ rawPageSize: size }),
  setAllDataCache: (data) => set({ allDataCache: data }),
  setSampleConfig: (config) =>
    set((state) => ({
      sampleConfig: { ...state.sampleConfig, ...config },
    })),
  setSampleResult: (data, indices, stats) =>
    set({ sampleResult: data, sampleIndices: indices, sampleStats: stats }),
  setIsSampling: (v) => set({ isSampling: v }),
  setColumnStats: (stats) => set({ columnStats: stats }),
  setStratifyIndex: (index) => set({ stratifyIndex: index }),
  setAnalysisGoal: (goal) => set({ analysisGoal: goal }),
  setRecommendation: (rec) => set({ recommendation: rec }),
  setDistributionComparison: (comp) => set({ distributionComparison: comp }),
  addAuditRecord: (record) =>
    set((state) => ({
      auditHistory: [
        { ...record, id: uuidv4(), timestamp: new Date().toISOString() },
        ...state.auditHistory,
      ].slice(0, 50),
    })),
  setActiveAuditId: (id) => set({ activeAuditId: id }),
  applyAuditRecord: (record) => {
    const state = get()
    if (state.fileMeta?.fileId !== record.fileId) {
      console.warn('Audit record is for different file')
      return
    }
    set({
      sampleConfig: { ...record.config },
      analysisGoal: 'descriptive',
      activeAuditId: record.id,
    })
  },
  reset: () =>
    set({
      fileMeta: null,
      isUploading: false,
      uploadProgress: 0,
      rawData: [],
      rawPage: 1,
      allDataCache: [],
      sampleConfig: { ...defaultSampleConfig },
      sampleResult: null,
      sampleIndices: [],
      sampleStats: null,
      isSampling: false,
      columnStats: null,
      stratifyIndex: null,
      analysisGoal: 'descriptive',
      recommendation: null,
      distributionComparison: null,
      activeAuditId: null,
    }),
}))

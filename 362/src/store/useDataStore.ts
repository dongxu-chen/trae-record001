import { create } from 'zustand';
import type {
  CleaningRules,
  UploadedData,
  CleaningResult,
  DatasetStats,
  WorkerResponse,
  DatasetQualityReport,
  RuleRecommendation,
  CleaningWorkflow,
  WorkflowStep,
} from '../types';
import { evaluateDatasetQuality } from '../utils/qualityEvaluator';
import { generateRecommendations } from '../utils/recommendationEngine';

interface DataState {
  uploadedData: UploadedData | null;
  cleaningRules: CleaningRules;
  cleaningResult: CleaningResult | null;
  isCleaning: boolean;
  cleaningProgress: number;
  currentStep: string;
  worker: Worker | null;
  error: string | null;
  activeTab: 'data' | 'stats' | 'charts';
  selectedColumns: string[];
  qualityReport: DatasetQualityReport | null;
  recommendations: RuleRecommendation[];
  currentWorkflow: CleaningWorkflow | null;
  isEvaluatingQuality: boolean;
  isGeneratingRecommendations: boolean;

  setUploadedData: (data: UploadedData | null) => void;
  setCleaningRules: (rules: Partial<CleaningRules>) => void;
  resetCleaningRules: () => void;
  setCleaningResult: (result: CleaningResult | null) => void;
  setIsCleaning: (isCleaning: boolean) => void;
  setCleaningProgress: (progress: number) => void;
  setCurrentStep: (step: string) => void;
  setWorker: (worker: Worker | null) => void;
  setError: (error: string | null) => void;
  setActiveTab: (tab: 'data' | 'stats' | 'charts') => void;
  setSelectedColumns: (columns: string[]) => void;
  toggleColumnSelection: (column: string) => void;
  handleWorkerMessage: (message: WorkerResponse) => void;
  startCleaning: () => void;
  cancelCleaning: () => void;
  resetAll: () => void;
  evaluateQuality: () => void;
  generateRecommendations: () => void;
  applyRecommendation: (recommendationId: string) => void;
  applyAllRecommendations: () => void;
  setCurrentWorkflow: (workflow: CleaningWorkflow | null) => void;
  updateWorkflowStep: (stepId: string, updates: Partial<WorkflowStep>) => void;
  reorderWorkflowSteps: (fromIndex: number, toIndex: number) => void;
  addWorkflowStep: (step: Omit<WorkflowStep, 'id'>) => void;
  removeWorkflowStep: (stepId: string) => void;
  executeWorkflow: () => void;
}

const defaultCleaningRules: CleaningRules = {
  removeDuplicates: {
    enabled: true,
    keep: 'first',
  },
  handleMissing: {
    enabled: true,
    columns: {},
    defaultMethod: 'mean',
  },
  detectOutliers: {
    enabled: true,
    columns: {},
    defaultMethod: 'zscore',
    defaultThreshold: 3,
  },
  normalize: {
    enabled: false,
    columns: {},
    defaultMethod: 'minmax',
  },
};

export const useDataStore = create<DataState>((set, get) => ({
  uploadedData: null,
  cleaningRules: defaultCleaningRules,
  cleaningResult: null,
  isCleaning: false,
  cleaningProgress: 0,
  currentStep: '',
  worker: null,
  error: null,
  activeTab: 'data',
  selectedColumns: [],
  qualityReport: null,
  recommendations: [],
  currentWorkflow: null,
  isEvaluatingQuality: false,
  isGeneratingRecommendations: false,

  setUploadedData: (data) => set({ uploadedData: data, cleaningResult: null }),

  setCleaningRules: (rules) =>
    set((state) => ({
      cleaningRules: { ...state.cleaningRules, ...rules },
    })),

  resetCleaningRules: () => set({ cleaningRules: defaultCleaningRules }),

  setCleaningResult: (result) => set({ cleaningResult: result }),

  setIsCleaning: (isCleaning) => set({ isCleaning }),

  setCleaningProgress: (progress) => set({ cleaningProgress: progress }),

  setCurrentStep: (step) => set({ currentStep: step }),

  setWorker: (worker) => set({ worker }),

  setError: (error) => set({ error }),

  setActiveTab: (tab) => set({ activeTab: tab }),

  setSelectedColumns: (columns) => set({ selectedColumns: columns }),

  toggleColumnSelection: (column) =>
    set((state) => ({
      selectedColumns: state.selectedColumns.includes(column)
        ? state.selectedColumns.filter((c) => c !== column)
        : [...state.selectedColumns, column],
    })),

  handleWorkerMessage: (message: WorkerResponse) => {
    switch (message.type) {
      case 'PROGRESS':
        set({
          cleaningProgress: message.payload.progress,
          currentStep: message.payload.step,
        });
        break;
      case 'STATS':
        if (get().uploadedData) {
          set((state) => ({
            uploadedData: {
              ...state.uploadedData!,
              stats: message.payload as DatasetStats,
            },
          }));
        }
        break;
      case 'COMPLETE':
        set({
          cleaningResult: message.payload,
          isCleaning: false,
          cleaningProgress: 100,
          currentStep: '完成',
        });
        break;
      case 'ERROR':
        set({
          error: message.payload,
          isCleaning: false,
          cleaningProgress: 0,
        });
        break;
    }
  },

  startCleaning: () => {
    const { uploadedData, cleaningRules, worker, handleWorkerMessage } = get();
    if (!uploadedData || !worker) return;

    set({ isCleaning: true, cleaningProgress: 0, error: null, cleaningResult: null });

    worker.postMessage({
      type: 'CLEAN',
      payload: { rules: cleaningRules },
    });

    worker.onmessage = (e: MessageEvent<WorkerResponse>) => {
      handleWorkerMessage(e.data);
    };

    worker.onerror = (e: ErrorEvent) => {
      set({ error: e.message, isCleaning: false, cleaningProgress: 0 });
    };
  },

  cancelCleaning: () => {
    const { worker } = get();
    if (worker) {
      worker.postMessage({ type: 'CANCEL' });
    }
    set({ isCleaning: false, cleaningProgress: 0, currentStep: '' });
  },

  resetAll: () => {
    const { worker } = get();
    if (worker) {
      worker.terminate();
    }
    set({
      uploadedData: null,
      cleaningRules: defaultCleaningRules,
      cleaningResult: null,
      isCleaning: false,
      cleaningProgress: 0,
      currentStep: '',
      worker: null,
      error: null,
      selectedColumns: [],
      qualityReport: null,
      recommendations: [],
      currentWorkflow: null,
    });
  },

  evaluateQuality: () => {
    const { uploadedData } = get();
    if (!uploadedData) return;

    set({ isEvaluatingQuality: true });
    try {
      const report = evaluateDatasetQuality(
        uploadedData.stats,
        uploadedData.data,
        uploadedData.columns
      );
      set({ qualityReport: report });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : '质量评估失败' });
    } finally {
      set({ isEvaluatingQuality: false });
    }
  },

  generateRecommendations: () => {
    const { uploadedData, qualityReport } = get();
    if (!uploadedData) return;

    set({ isGeneratingRecommendations: true });
    try {
      let report = qualityReport;
      if (!report) {
        report = evaluateDatasetQuality(
          uploadedData.stats,
          uploadedData.data,
          uploadedData.columns
        );
        set({ qualityReport: report });
      }
      const recs = generateRecommendations(report, uploadedData.stats, uploadedData.data);
      set({ recommendations: recs });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : '生成推荐失败' });
    } finally {
      set({ isGeneratingRecommendations: false });
    }
  },

  applyRecommendation: (recommendationId: string) => {
    const { recommendations, cleaningRules } = get();
    const rec = recommendations.find((r) => r.id === recommendationId);
    if (!rec) return;

    let newRules = { ...cleaningRules };

    switch (rec.action) {
      case 'remove_duplicates':
        newRules.removeDuplicates = {
          ...newRules.removeDuplicates,
          enabled: true,
          ...rec.suggestedConfig,
        };
        break;
      case 'fill_missing':
        newRules.handleMissing = {
          ...newRules.handleMissing,
          enabled: true,
          columns: {
            ...newRules.handleMissing.columns,
            [rec.columnName]: {
              method: rec.suggestedConfig?.method || 'mean',
              value: rec.suggestedConfig?.value,
            },
          },
        };
        break;
      case 'remove_outliers':
      case 'cap_outliers':
        newRules.detectOutliers = {
          ...newRules.detectOutliers,
          enabled: true,
          columns: {
            ...newRules.detectOutliers.columns,
            [rec.columnName]: {
              method: rec.suggestedConfig?.method || 'zscore',
              threshold: rec.suggestedConfig?.threshold || 3,
              action: rec.suggestedConfig?.action || 'remove',
            },
          },
        };
        break;
      case 'normalize':
        newRules.normalize = {
          ...newRules.normalize,
          enabled: true,
          columns: {
            ...newRules.normalize.columns,
            [rec.columnName]: {
              method: rec.suggestedConfig?.method || 'minmax',
            },
          },
        };
        break;
    }

    set({
      cleaningRules: newRules,
      recommendations: recommendations.map((r) =>
        r.id === recommendationId ? { ...r, applied: true } : r
      ),
    });
  },

  applyAllRecommendations: () => {
    const { recommendations } = get();
    recommendations.forEach((rec) => {
      if (!rec.applied) {
        get().applyRecommendation(rec.id);
      }
    });
  },

  setCurrentWorkflow: (workflow) => set({ currentWorkflow: workflow }),

  updateWorkflowStep: (stepId, updates) => {
    const { currentWorkflow } = get();
    if (!currentWorkflow) return;
    set({
      currentWorkflow: {
        ...currentWorkflow,
        steps: currentWorkflow.steps.map((s) =>
          s.id === stepId ? { ...s, ...updates } : s
        ),
        updatedAt: new Date(),
      },
    });
  },

  reorderWorkflowSteps: (fromIndex, toIndex) => {
    const { currentWorkflow } = get();
    if (!currentWorkflow) return;
    const newSteps = [...currentWorkflow.steps];
    const [removed] = newSteps.splice(fromIndex, 1);
    newSteps.splice(toIndex, 0, removed);
    const reorderedSteps = newSteps.map((s, i) => ({ ...s, order: i }));
    set({
      currentWorkflow: {
        ...currentWorkflow,
        steps: reorderedSteps,
        updatedAt: new Date(),
      },
    });
  },

  addWorkflowStep: (step) => {
    const { currentWorkflow } = get();
    const newStep = { ...step, id: `step_${Date.now()}` };
    if (!currentWorkflow) {
      set({
        currentWorkflow: {
          id: `workflow_${Date.now()}`,
          name: '自定义工作流',
          description: '自定义数据清洗流程',
          steps: [newStep],
          createdAt: new Date(),
          updatedAt: new Date(),
        },
      });
    } else {
      set({
        currentWorkflow: {
          ...currentWorkflow,
          steps: [...currentWorkflow.steps, newStep].map((s, i) => ({
            ...s,
            order: i,
          })),
          updatedAt: new Date(),
        },
      });
    }
  },

  removeWorkflowStep: (stepId) => {
    const { currentWorkflow } = get();
    if (!currentWorkflow) return;
    set({
      currentWorkflow: {
        ...currentWorkflow,
        steps: currentWorkflow.steps
          .filter((s) => s.id !== stepId)
          .map((s, i) => ({ ...s, order: i })),
        updatedAt: new Date(),
      },
    });
  },

  executeWorkflow: () => {
    const { currentWorkflow, cleaningRules, startCleaning } = get();
    if (!currentWorkflow) return;

    let newRules = { ...cleaningRules };
    currentWorkflow.steps
      .filter((s) => s.enabled)
      .sort((a, b) => a.order - b.order)
      .forEach((step) => {
        switch (step.type) {
          case 'duplicates':
            newRules.removeDuplicates = {
              ...newRules.removeDuplicates,
              enabled: true,
              ...step.config,
            };
            if (step.targetColumns) {
              newRules.removeDuplicates.columns = step.targetColumns;
            }
            break;
          case 'missing':
            newRules.handleMissing = {
              ...newRules.handleMissing,
              enabled: true,
              ...step.config,
            };
            break;
          case 'outliers':
            newRules.detectOutliers = {
              ...newRules.detectOutliers,
              enabled: true,
              ...step.config,
            };
            break;
          case 'normalize':
            newRules.normalize = {
              ...newRules.normalize,
              enabled: true,
              ...step.config,
            };
            break;
        }
      });

    set({ cleaningRules: newRules });
    startCleaning();
  },
}));

import { create } from 'zustand';
import { debounce } from 'lodash-es';
import type { 
  AppState, 
  SourceField, 
  DataRow, 
  TargetField, 
  Mapping, 
  TransformFunction,
  MappingTemplate,
  MappingStep,
  QualityReport,
  QualityIssue,
  PipelineResult
} from '@/types';
import { indexedDBService } from '@/utils/indexedDB';
import { applyTransforms, convertToType } from '@/utils/transforms';

export const useAppStore = create<AppState>((set, get) => ({
  projectId: null,
  sourceFileName: null,
  sourceFields: [],
  sourceData: [],
  targetFields: [],
  mappings: [],
  selectedMapping: null,
  previewPage: 1,
  previewPageSize: 10,
  dataPreviewPage: 1,
  dataPageSize: 1000,
  isLoading: false,
  lastSaved: null,
  templates: [],
  mappingSteps: [],
  currentStepId: null,
  qualityReport: null,
  showQualityPanel: false,
  pipelineResults: [],

  setProjectId: (id: number | null) => set({ projectId: id }),

  setSourceData: (fileName: string, fields: SourceField[], data: DataRow[]) => {
    set({ sourceFileName: fileName, sourceFields: fields, sourceData: data, dataPreviewPage: 1 });
    get().autoSave();
    get().evaluateQuality();
  },

  setTargetFields: (fields: TargetField[]) => {
    set({ targetFields: fields });
    get().autoSave();
    get().evaluateQuality();
  },

  addMapping: (mapping: Mapping) => {
    set((state) => ({ mappings: [...state.mappings, mapping] }));
    get().autoSave();
    get().evaluateQuality();
  },

  updateMapping: (id: string, updates: Partial<Mapping>) => {
    set((state) => ({
      mappings: state.mappings.map((m) =>
        m.id === id ? { ...m, ...updates } : m
      ),
    }));
    get().autoSave();
    get().evaluateQuality();
  },

  removeMapping: (id: string) => {
    set((state) => ({
      mappings: state.mappings.filter((m) => m.id !== id),
      selectedMapping: state.selectedMapping === id ? null : state.selectedMapping,
    }));
    get().autoSave();
    get().evaluateQuality();
  },

  setSelectedMapping: (id: string | null) => set({ selectedMapping: id }),

  setPreviewPage: (page: number) => set({ previewPage: page }),

  setDataPreviewPage: (page: number) => set({ dataPreviewPage: page }),

  addTransform: (mappingId: string, transform: TransformFunction) => {
    set((state) => ({
      mappings: state.mappings.map((m) =>
        m.id === mappingId
          ? { ...m, transforms: [...m.transforms, transform] }
          : m
      ),
    }));
    get().autoSave();
    get().evaluateQuality();
  },

  updateTransform: (mappingId: string, transformId: string, updates: Partial<TransformFunction>) => {
    set((state) => ({
      mappings: state.mappings.map((m) =>
        m.id === mappingId
          ? {
              ...m,
              transforms: m.transforms.map((t) =>
                t.id === transformId ? { ...t, ...updates } : t
              ) as TransformFunction[],
            }
          : m
      ),
    }));
    get().autoSave();
    get().evaluateQuality();
  },

  removeTransform: (mappingId: string, transformId: string) => {
    set((state) => ({
      mappings: state.mappings.map((m) =>
        m.id === mappingId
          ? { ...m, transforms: m.transforms.filter((t) => t.id !== transformId) }
          : m
      ),
    }));
    get().autoSave();
    get().evaluateQuality();
  },

  setLoading: (loading: boolean) => set({ isLoading: loading }),

  setLastSaved: (timestamp: number | null) => set({ lastSaved: timestamp }),

  restoreProject: (data: Partial<AppState>) => {
    set({
      projectId: data.projectId ?? null,
      sourceFileName: data.sourceFileName ?? null,
      sourceFields: data.sourceFields ?? [],
      sourceData: data.sourceData ?? [],
      targetFields: data.targetFields ?? [],
      mappings: data.mappings ?? [],
      previewPage: 1,
      dataPreviewPage: 1,
    });
    get().evaluateQuality();
  },

  autoSave: debounce(async () => {
    const state = get();
    if (state.sourceFields.length === 0 && state.targetFields.length === 0) {
      return;
    }

    try {
      const projectData = {
        id: state.projectId ?? undefined,
        name: state.sourceFileName || '未命名项目',
        sourceFileName: state.sourceFileName,
        sourceFields: state.sourceFields,
        targetFields: state.targetFields,
        mappings: state.mappings,
      };

      const newId = await indexedDBService.saveProject(projectData);
      set({ projectId: newId, lastSaved: Date.now() });
    } catch (error) {
      console.error('自动保存失败:', error);
    }
  }, 1000),

  saveAsTemplate: async (name: string, description: string, category: string): Promise<number> => {
    const state = get();
    const fieldMappings = state.mappings
      .filter(m => m.sourceFieldId)
      .map(m => {
        const sourceField = state.sourceFields.find(f => f.id === m.sourceFieldId);
        const targetField = state.targetFields.find(f => f.id === m.targetFieldId);
        return {
          sourceFieldName: sourceField?.name || '',
          targetFieldName: targetField?.name || '',
          outputType: m.outputType,
          transforms: m.transforms,
        };
      });

    const templateData = {
      name,
      description,
      category,
      targetFields: state.targetFields,
      fieldMappings,
    };

    const templateId = await indexedDBService.saveTemplate(templateData);
    await get().refreshTemplates();
    return templateId;
  },

  loadTemplate: (templateId: number) => {
    const state = get();
    const template = state.templates.find(t => t.id === templateId);
    if (!template) return;

    const newMappings: Mapping[] = template.fieldMappings.map((fm, index) => {
      const sourceField = state.sourceFields.find(f => f.name === fm.sourceFieldName);
      const targetField = template.targetFields.find(f => f.name === fm.targetFieldName);
      
      return {
        id: `mapping-${Date.now()}-${index}`,
        sourceFieldId: sourceField?.id || null,
        targetFieldId: targetField?.id || `target-${index}`,
        outputType: fm.outputType,
        transforms: fm.transforms,
      };
    });

    set({
      targetFields: template.targetFields,
      mappings: newMappings,
    });
    get().autoSave();
    get().evaluateQuality();
  },

  deleteTemplate: async (templateId: number): Promise<void> => {
    await indexedDBService.deleteTemplate(templateId);
    await get().refreshTemplates();
  },

  refreshTemplates: async (): Promise<void> => {
    const templates = await indexedDBService.getAllTemplates();
    set({ templates });
  },

  addMappingStep: (name: string, description: string) => {
    const state = get();
    const newStep: MappingStep = {
      id: `step-${Date.now()}`,
      name,
      description,
      stepNumber: state.mappingSteps.length + 1,
      mappings: [],
      targetFields: [],
      enabled: true,
    };
    set((state) => ({
      mappingSteps: [...state.mappingSteps, newStep],
      currentStepId: state.currentStepId || newStep.id,
    }));
    get().autoSave();
  },

  updateMappingStep: (stepId: string, updates: Partial<MappingStep>) => {
    set((state) => ({
      mappingSteps: state.mappingSteps.map(s =>
        s.id === stepId ? { ...s, ...updates } : s
      ),
    }));
    get().autoSave();
  },

  removeMappingStep: (stepId: string) => {
    set((state) => ({
      mappingSteps: state.mappingSteps
        .filter(s => s.id !== stepId)
        .map((s, idx) => ({ ...s, stepNumber: idx + 1 })),
      currentStepId: state.currentStepId === stepId ? null : state.currentStepId,
    }));
    get().autoSave();
  },

  setCurrentStepId: (stepId: string | null) => set({ currentStepId: stepId }),

  reorderMappingSteps: (stepIds: string[]) => {
    set((state) => ({
      mappingSteps: stepIds
        .map(id => state.mappingSteps.find(s => s.id === id))
        .filter(Boolean)
        .map((s, idx) => ({ ...s!, stepNumber: idx + 1 })),
    }));
    get().autoSave();
  },

  runPipeline: async (): Promise<PipelineResult[]> => {
    const state = get();
    const results: PipelineResult[] = [];
    let currentData = [...state.sourceData];

    const enabledSteps = state.mappingSteps.filter(s => s.enabled);
    const allSteps = enabledSteps.length > 0 ? enabledSteps : [
      {
        id: 'default',
        name: '默认映射',
        stepNumber: 1,
        description: '单步映射',
        mappings: state.mappings,
        targetFields: state.targetFields,
        enabled: true,
      }
    ];

    for (const step of allSteps) {
      const startTime = Date.now();
      
      const stepData = currentData.map((row) => {
        const result: DataRow = {};
        step.targetFields.forEach((targetField) => {
          const mapping = step.mappings.find((m) => m.targetFieldId === targetField.id);
          if (mapping && mapping.sourceFieldId) {
            const sourceField = state.sourceFields.find((f) => f.id === mapping.sourceFieldId);
            if (sourceField) {
              const value = row[sourceField.name];
              let transformedValue = applyTransforms(value, mapping.transforms, row);
              if (mapping.outputType) {
                transformedValue = convertToType(transformedValue, mapping.outputType);
              }
              result[targetField.name] = transformedValue;
            }
          } else {
            result[targetField.name] = '';
          }
        });
        return result;
      });

      results.push({
        stepId: step.id,
        stepName: step.name,
        data: stepData,
        duration: Date.now() - startTime,
      });

      currentData = stepData;
    }

    set({ pipelineResults: results });
    return results;
  },

  evaluateQuality: (): QualityReport => {
    const state = get();
    const issues: QualityIssue[] = [];

    const requiredFields = state.targetFields.filter(f => f.required);
    const mappedTargetIds = state.mappings
      .filter(m => m.sourceFieldId)
      .map(m => m.targetFieldId);

    requiredFields.forEach(field => {
      if (!mappedTargetIds.includes(field.id)) {
        issues.push({
          id: `missing-${field.id}`,
          type: 'missing_mapping',
          severity: 'error',
          message: `必填字段 "${field.name}" 未配置映射`,
          targetFieldId: field.id,
        });
      }
    });

    state.mappings.forEach(mapping => {
      if (!mapping.sourceFieldId) {
        const targetField = state.targetFields.find(f => f.id === mapping.targetFieldId);
        issues.push({
          id: `empty-${mapping.id}`,
          type: 'empty_mapping',
          severity: 'warning',
          message: `字段 "${targetField?.name || mapping.targetFieldId}" 的映射未关联源字段`,
          targetFieldId: mapping.targetFieldId,
          mappingId: mapping.id,
        });
      }
    });

    state.mappings.forEach(mapping => {
      if (!mapping.sourceFieldId) return;
      
      const sourceField = state.sourceFields.find(f => f.id === mapping.sourceFieldId);
      const targetField = state.targetFields.find(f => f.id === mapping.targetFieldId);
      
      if (sourceField && targetField && mapping.outputType) {
        if (sourceField.type !== mapping.outputType) {
          const hasTransforms = mapping.transforms.length > 0;
          if (!hasTransforms) {
            issues.push({
              id: `type-${mapping.id}`,
              type: 'type_mismatch',
              severity: 'warning',
              message: `字段类型不匹配: 源 "${sourceField.name}"(${sourceField.type}) → 目标 "${targetField.name}"(${mapping.outputType})`,
              sourceFieldId: mapping.sourceFieldId,
              targetFieldId: mapping.targetFieldId,
              mappingId: mapping.id,
            });
          }
        }
      }
    });

    const totalFields = state.targetFields.length;
    const mappedFields = mappedTargetIds.length;
    const missingFields = requiredFields.filter(f => !mappedTargetIds.includes(f.id)).length;
    const typeWarnings = issues.filter(i => i.type === 'type_mismatch').length;

    let score = 100;
    score -= missingFields * 20;
    score -= typeWarnings * 5;
    score = Math.max(0, Math.min(100, score));

    const report: QualityReport = {
      issues,
      score,
      totalFields,
      mappedFields,
      missingFields,
      typeWarnings,
    };

    set({ qualityReport: report });
    return report;
  },

  setShowQualityPanel: (show: boolean) => set({ showQualityPanel: show }),

  clearAll: () => {
    set({
      projectId: null,
      sourceFileName: null,
      sourceFields: [],
      sourceData: [],
      targetFields: [],
      mappings: [],
      selectedMapping: null,
      previewPage: 1,
      dataPreviewPage: 1,
      lastSaved: null,
      qualityReport: null,
      pipelineResults: [],
      mappingSteps: [],
      currentStepId: null,
    });
  },
}));

export const loadLastProject = async (): Promise<void> => {
  try {
    const store = useAppStore.getState();
    store.setLoading(true);

    const [project, templates] = await Promise.all([
      indexedDBService.getLatestProject(),
      indexedDBService.getAllTemplates(),
    ]);

    set({ templates });

    if (project) {
      store.restoreProject({
        projectId: project.id ?? null,
        sourceFileName: project.sourceFileName,
        sourceFields: project.sourceFields,
        targetFields: project.targetFields,
        mappings: project.mappings,
      });
    }
  } catch (error) {
    console.error('加载项目失败:', error);
  } finally {
    useAppStore.getState().setLoading(false);
  }
};

export const loadTemplates = async (): Promise<void> => {
  try {
    const templates = await indexedDBService.getAllTemplates();
    set({ templates });
  } catch (error) {
    console.error('加载模板失败:', error);
  }
};

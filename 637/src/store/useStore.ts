import { create } from 'zustand';
import type {
  NamingStyle,
  UserSettings,
  HistoryItem,
  Recommendation,
  NamingResponse,
  TypeInferenceResult,
  TeamNamingConfig,
  TeamNamingRule,
  BatchRenameItem,
  BatchRenameResult,
  ConflictDetectionResult
} from '../../shared/types';

interface NamingStore {
  input: string;
  inputType: 'description' | 'code';
  context: string;
  targetStyle: NamingStyle;
  recommendations: Recommendation[];
  isLoading: boolean;
  error: string | null;
  detectedLanguage: string;
  detectedType: string;
  typeInference: TypeInferenceResult | null;
  processingTime: number;
  history: HistoryItem[];
  settings: UserSettings;
  copiedId: string | null;
  
  teamConfig: TeamNamingConfig | null;
  batchRenameCode: string;
  batchRenameItems: BatchRenameItem[];
  batchRenameResult: BatchRenameResult | null;
  conflictCheckResult: ConflictDetectionResult | null;
  
  setInput: (input: string) => void;
  setInputType: (type: 'description' | 'code') => void;
  setContext: (context: string) => void;
  setTargetStyle: (style: NamingStyle) => void;
  getRecommendations: () => Promise<void>;
  copyToClipboard: (id: string, name: string) => void;
  recordSelection: (input: string, selectedName: string, style: NamingStyle) => Promise<void>;
  fetchHistory: () => Promise<void>;
  toggleFavorite: (id: string) => Promise<void>;
  deleteHistoryItem: (id: string) => Promise<void>;
  clearHistory: () => Promise<void>;
  submitFeedback: (id: string, feedback: 'like' | 'dislike') => Promise<void>;
  updateSettings: (settings: Partial<UserSettings>) => void;
  loadSettings: () => void;
  
  fetchTeamConfig: () => Promise<void>;
  updateTeamConfig: (config: TeamNamingConfig) => Promise<void>;
  addTeamRule: (rule: Omit<TeamNamingRule, 'id' | 'createdAt'>) => Promise<TeamNamingRule | null>;
  deleteTeamRule: (id: string) => Promise<void>;
  setBatchRenameCode: (code: string) => void;
  detectVariablesInCode: (code: string) => Promise<void>;
  performBatchRename: (items: BatchRenameItem[]) => Promise<void>;
  addBatchRenameItem: (item: BatchRenameItem) => void;
  updateBatchRenameItem: (id: string, updates: Partial<BatchRenameItem>) => void;
  removeBatchRenameItem: (id: string) => void;
  clearBatchRename: () => void;
  checkNameConflicts: (name: string, code: string) => Promise<void>;
  clearConflictResult: () => void;
}

const DEFAULT_SETTINGS: UserSettings = {
  defaultStyle: 'camelCase',
  preferredLanguage: 'zh',
  autoDetectLanguage: true,
  showConfidence: true,
  maxRecommendations: 8
};

const STORAGE_KEYS = {
  SETTINGS: 'naming_settings',
  HISTORY: 'naming_history'
};

export const useStore = create<NamingStore>((set, get) => ({
  input: '',
  inputType: 'description',
  context: '',
  targetStyle: 'camelCase',
  recommendations: [],
  isLoading: false,
  error: null,
  detectedLanguage: '',
  detectedType: '',
  typeInference: null,
  processingTime: 0,
  history: [],
  settings: DEFAULT_SETTINGS,
  copiedId: null,
  
  teamConfig: null,
  batchRenameCode: '',
  batchRenameItems: [],
  batchRenameResult: null,
  conflictCheckResult: null,

  setInput: (input) => set({ input }),
  
  setInputType: (type) => set({ inputType: type }),
  
  setContext: (context) => set({ context }),
  
  setTargetStyle: (style) => set({ targetStyle: style }),

  getRecommendations: async () => {
    const { input, inputType, context, targetStyle, settings } = get();
    
    if (!input.trim()) {
      set({ error: '请输入变量描述或代码上下文', recommendations: [] });
      return;
    }

    set({ isLoading: true, error: null });
    
    try {
      const response = await fetch('/api/naming/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          input,
          inputType,
          context: context || undefined,
          targetStyle,
          maxResults: settings.maxRecommendations
        })
      });

      const data: NamingResponse = await response.json();
      
      if (data.success) {
        set({
          recommendations: data.recommendations,
          detectedLanguage: data.detectedLanguage,
          detectedType: data.detectedType,
          typeInference: data.typeInference || null,
          processingTime: data.processingTime,
          isLoading: false
        });
      } else {
        set({ error: '获取推荐失败', isLoading: false });
      }
    } catch (err) {
      set({ error: '网络错误，请稍后重试', isLoading: false });
    }
  },

  copyToClipboard: async (id, name) => {
    try {
      await navigator.clipboard.writeText(name);
      set({ copiedId: id });
      setTimeout(() => set({ copiedId: null }), 2000);
    } catch (err) {
      console.error('复制失败:', err);
    }
  },

  recordSelection: async (input, selectedName, style) => {
    try {
      await fetch('/api/naming/record', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ input, selectedName, style })
      });
      get().fetchHistory();
    } catch (err) {
      console.error('记录选择失败:', err);
    }
  },

  fetchHistory: async () => {
    try {
      const response = await fetch('/api/learning/history');
      const data = await response.json();
      if (data.success) {
        set({ history: data.data });
        localStorage.setItem(STORAGE_KEYS.HISTORY, JSON.stringify(data.data));
      }
    } catch (err) {
      const localHistory = localStorage.getItem(STORAGE_KEYS.HISTORY);
      if (localHistory) {
        set({ history: JSON.parse(localHistory) });
      }
    }
  },

  toggleFavorite: async (id) => {
    try {
      const response = await fetch(`/api/learning/history/${id}/favorite`, {
        method: 'PATCH'
      });
      const data = await response.json();
      if (data.success) {
        const { history } = get();
        set({
          history: history.map(item => 
            item.id === id ? { ...item, isFavorite: data.data.isFavorite } : item
          )
        });
      }
    } catch (err) {
      console.error('切换收藏失败:', err);
    }
  },

  deleteHistoryItem: async (id) => {
    try {
      await fetch(`/api/learning/history/${id}`, { method: 'DELETE' });
      const { history } = get();
      set({ history: history.filter(item => item.id !== id) });
    } catch (err) {
      console.error('删除记录失败:', err);
    }
  },

  clearHistory: async () => {
    try {
      await fetch('/api/learning/history', { method: 'DELETE' });
      set({ history: [] });
      localStorage.removeItem(STORAGE_KEYS.HISTORY);
    } catch (err) {
      console.error('清空历史失败:', err);
    }
  },

  submitFeedback: async (id, feedback) => {
    try {
      await fetch(`/api/learning/history/${id}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feedback })
      });
      const { history } = get();
      set({
        history: history.map(item =>
          item.id === id ? { ...item, feedback } : item
        )
      });
    } catch (err) {
      console.error('提交反馈失败:', err);
    }
  },

  updateSettings: (newSettings) => {
    const { settings } = get();
    const updated = { ...settings, ...newSettings };
    set({ settings: updated });
    localStorage.setItem(STORAGE_KEYS.SETTINGS, JSON.stringify(updated));
  },

  loadSettings: () => {
    const saved = localStorage.getItem(STORAGE_KEYS.SETTINGS);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        set({ settings: parsed, targetStyle: parsed.defaultStyle });
      } catch (err) {
        console.error('加载设置失败:', err);
      }
    }
  },

  fetchTeamConfig: async () => {
    try {
      const response = await fetch('/api/advanced/team/config');
      const data = await response.json();
      if (data.success) {
        set({ teamConfig: data.data });
      }
    } catch (err) {
      console.error('获取团队配置失败:', err);
    }
  },

  updateTeamConfig: async (config) => {
    try {
      await fetch('/api/advanced/team/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      set({ teamConfig: config });
    } catch (err) {
      console.error('更新团队配置失败:', err);
    }
  },

  addTeamRule: async (rule) => {
    try {
      const response = await fetch('/api/advanced/team/rules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(rule)
      });
      const data = await response.json();
      if (data.success) {
        const { teamConfig } = get();
        if (teamConfig) {
          set({
            teamConfig: {
              ...teamConfig,
              rules: [...teamConfig.rules, data.data]
            }
          });
        }
        return data.data;
      }
    } catch (err) {
      console.error('添加规则失败:', err);
    }
    return null;
  },

  deleteTeamRule: async (id) => {
    try {
      await fetch(`/api/advanced/team/rules/${id}`, { method: 'DELETE' });
      const { teamConfig } = get();
      if (teamConfig) {
        set({
          teamConfig: {
            ...teamConfig,
            rules: teamConfig.rules.filter(r => r.id !== id)
          }
        });
      }
    } catch (err) {
      console.error('删除规则失败:', err);
    }
  },

  setBatchRenameCode: (code) => set({ batchRenameCode: code }),

  detectVariablesInCode: async (code) => {
    try {
      const response = await fetch('/api/advanced/batch/detect-variables', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, language: 'javascript' })
      });
      const data = await response.json();
      if (data.success) {
        const items: BatchRenameItem[] = data.data.map((v: any) => ({
          id: `item-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          oldName: v.name,
          newName: v.name,
          type: v.type,
          occurrences: v.occurrences,
          status: 'pending'
        }));
        set({ batchRenameItems: items, batchRenameCode: code });
      }
    } catch (err) {
      console.error('检测变量失败:', err);
    }
  },

  performBatchRename: async (items) => {
    try {
      const { batchRenameCode } = get();
      const response = await fetch('/api/advanced/batch/rename', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code: batchRenameCode,
          language: 'javascript',
          items,
          dryRun: false
        })
      });
      const data = await response.json();
      if (data.success) {
        set({ batchRenameResult: data.data });
      }
    } catch (err) {
      console.error('批量重命名失败:', err);
    }
  },

  addBatchRenameItem: (item) => {
    const { batchRenameItems } = get();
    set({ batchRenameItems: [...batchRenameItems, item] });
  },

  updateBatchRenameItem: (id, updates) => {
    const { batchRenameItems } = get();
    set({
      batchRenameItems: batchRenameItems.map(item =>
        item.id === id ? { ...item, ...updates } : item
      )
    });
  },

  removeBatchRenameItem: (id) => {
    const { batchRenameItems } = get();
    set({
      batchRenameItems: batchRenameItems.filter(item => item.id !== id)
    });
  },

  clearBatchRename: () => {
    set({
      batchRenameCode: '',
      batchRenameItems: [],
      batchRenameResult: null
    });
  },

  checkNameConflicts: async (name, code) => {
    try {
      const response = await fetch('/api/advanced/conflicts/detect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, code })
      });
      const data = await response.json();
      if (data.success) {
        set({ conflictCheckResult: data.data });
      }
    } catch (err) {
      console.error('检测冲突失败:', err);
    }
  },

  clearConflictResult: () => {
    set({ conflictCheckResult: null });
  }
}));

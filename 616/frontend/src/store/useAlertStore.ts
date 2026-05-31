import { create } from 'zustand';
import { AlertRule, AlertRuleDTO } from '@/types';
import { alertApi } from '@/api/alert';

interface AlertState {
  list: AlertRule[];
  loading: boolean;
  current: AlertRule | null;
  fetchList: (params?: {
    name?: string;
    enabled?: boolean;
    notificationType?: string;
  }) => Promise<void>;
  fetchById: (id: string) => Promise<void>;
  create: (data: AlertRuleDTO) => Promise<AlertRule>;
  update: (id: string, data: AlertRuleDTO) => Promise<AlertRule>;
  remove: (id: string) => Promise<boolean>;
  enable: (id: string) => Promise<boolean>;
  disable: (id: string) => Promise<boolean>;
  setCurrent: (rule: AlertRule | null) => void;
  reset: () => void;
}

export const useAlertStore = create<AlertState>((set, get) => ({
  list: [],
  loading: false,
  current: null,

  fetchList: async (params) => {
    set({ loading: true });
    try {
      const list = await alertApi.list(params);
      set({ list });
    } finally {
      set({ loading: false });
    }
  },

  fetchById: async (id: string) => {
    set({ loading: true });
    try {
      const rule = await alertApi.getById(id);
      set({ current: rule });
    } finally {
      set({ loading: false });
    }
  },

  create: async (data: AlertRuleDTO) => {
    const rule = await alertApi.create(data);
    set((state) => ({
      list: [...state.list, rule],
    }));
    return rule;
  },

  update: async (id: string, data: AlertRuleDTO) => {
    const rule = await alertApi.update(id, data);
    set((state) => ({
      list: state.list.map((item) => (item.id === id ? rule : item)),
      current: rule,
    }));
    return rule;
  },

  remove: async (id: string) => {
    const success = await alertApi.delete(id);
    if (success) {
      set((state) => ({
        list: state.list.filter((item) => item.id !== id),
      }));
    }
    return success;
  },

  enable: async (id: string) => {
    const success = await alertApi.enable(id);
    if (success) {
      set((state) => ({
        list: state.list.map((item) =>
          item.id === id ? { ...item, enabled: true } : item
        ),
      }));
    }
    return success;
  },

  disable: async (id: string) => {
    const success = await alertApi.disable(id);
    if (success) {
      set((state) => ({
        list: state.list.map((item) =>
          item.id === id ? { ...item, enabled: false } : item
        ),
      }));
    }
    return success;
  },

  setCurrent: (rule: AlertRule | null) => set({ current: rule }),

  reset: () =>
    set({
      list: [],
      current: null,
    }),
}));

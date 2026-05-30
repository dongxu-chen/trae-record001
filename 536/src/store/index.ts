import { create } from 'zustand';
import type { TransactionStats, AlertRecord, AlertRule } from '@/types';
import { api } from '@/api';

interface MonitorState {
  stats: TransactionStats | null;
  statsLoading: boolean;
  unacknowledgedAlertCount: number;
  alertRules: AlertRule[];
  loadStats: () => Promise<void>;
  loadAlertCount: () => Promise<void>;
  loadAlertRules: () => Promise<void>;
  addAlertRule: (rule: AlertRule) => Promise<void>;
  removeAlertRule: (name: string) => Promise<void>;
  acknowledgeAlert: (id: number, by: string) => Promise<void>;
}

export const useMonitorStore = create<MonitorState>((set, get) => ({
  stats: null,
  statsLoading: false,
  unacknowledgedAlertCount: 0,
  alertRules: [],

  loadStats: async () => {
    set({ statsLoading: true });
    try {
      const stats = await api.transactions.getStats();
      set({ stats, statsLoading: false });
    } catch {
      set({ statsLoading: false });
    }
  },

  loadAlertCount: async () => {
    try {
      const count = await api.alerts.countUnacknowledged();
      set({ unacknowledgedAlertCount: count });
    } catch {}
  },

  loadAlertRules: async () => {
    try {
      const rules = await api.alertRules.getAll();
      set({ alertRules: rules });
    } catch {}
  },

  addAlertRule: async (rule: AlertRule) => {
    await api.alertRules.add(rule);
    await get().loadAlertRules();
  },

  removeAlertRule: async (name: string) => {
    await api.alertRules.remove(name);
    await get().loadAlertRules();
  },

  acknowledgeAlert: async (id: number, by: string) => {
    await api.alerts.acknowledge(id, by);
    await get().loadAlertCount();
  },
}));

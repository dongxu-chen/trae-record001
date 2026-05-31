import { create } from 'zustand';
import type {
  DashboardStats,
  Repository,
  VersionConflict,
  Vulnerability,
  UpgradeSuggestion,
  ScanResult,
  Dependency,
} from '@/types';
import { api } from '@/utils/api';
import {
  mockRepositories,
  mockDashboardStats,
  mockConflicts,
  mockVulnerabilities,
  mockUpgrades,
  mockDependencies,
  mockScanHistory,
} from '@/utils/mockData';

interface AppStore {
  repositories: Repository[];
  dashboardStats: DashboardStats | null;
  conflicts: VersionConflict[];
  vulnerabilities: Vulnerability[];
  upgrades: UpgradeSuggestion[];
  selectedRepoId: number | null;
  serviceDependencies: Dependency[];
  serviceConflicts: VersionConflict[];
  scanHistory: ScanResult[];
  loading: Record<string, boolean>;
  error: Record<string, string | null>;

  fetchRepositories: () => Promise<void>;
  fetchDashboardStats: () => Promise<void>;
  fetchConflicts: () => Promise<void>;
  fetchVulnerabilities: (params?: { severity?: string; service?: string }) => Promise<void>;
  fetchUpgrades: (params?: { riskLevel?: string }) => Promise<void>;
  addRepository: (fullName: string) => Promise<void>;
  removeRepository: (id: number) => Promise<void>;
  triggerScan: (id: number) => Promise<void>;
  fetchServiceDependencies: (repoId: number) => Promise<void>;
  fetchServiceConflicts: (repoId: number) => Promise<void>;
  fetchScanHistory: (repoId: number) => Promise<void>;
  setSelectedRepoId: (id: number | null) => void;
}

export const useAppStore = create<AppStore>((set, get) => ({
  repositories: [],
  dashboardStats: null,
  conflicts: [],
  vulnerabilities: [],
  upgrades: [],
  selectedRepoId: null,
  serviceDependencies: [],
  serviceConflicts: [],
  scanHistory: [],
  loading: {},
  error: {},

  fetchRepositories: async () => {
    set((s) => ({ loading: { ...s.loading, repos: true } }));
    try {
      const repos = await api.repositories.list();
      set({ repositories: repos, loading: { ...get().loading, repos: false } });
    } catch (e) {
      set({ repositories: mockRepositories, loading: { ...get().loading, repos: false } });
    }
  },

  fetchDashboardStats: async () => {
    set((s) => ({ loading: { ...s.loading, dashboard: true } }));
    try {
      const stats = await api.dashboard.getStats();
      set({ dashboardStats: stats, loading: { ...get().loading, dashboard: false } });
    } catch (e) {
      set({ dashboardStats: mockDashboardStats, loading: { ...get().loading, dashboard: false } });
    }
  },

  fetchConflicts: async () => {
    set((s) => ({ loading: { ...s.loading, conflicts: true } }));
    try {
      const conflicts = await api.dependencies.getConflicts();
      set({ conflicts, loading: { ...get().loading, conflicts: false } });
    } catch (e) {
      set({ conflicts: mockConflicts, loading: { ...get().loading, conflicts: false } });
    }
  },

  fetchVulnerabilities: async (params) => {
    set((s) => ({ loading: { ...s.loading, vulns: true } }));
    try {
      const vulns = await api.vulnerabilities.list(params);
      set({ vulnerabilities: vulns, loading: { ...get().loading, vulns: false } });
    } catch (e) {
      let result = mockVulnerabilities;
      if (params?.severity && params.severity !== 'All') {
        result = result.filter((v) => v.severity === params.severity);
      }
      set({ vulnerabilities: result, loading: { ...get().loading, vulns: false } });
    }
  },

  fetchUpgrades: async (params) => {
    set((s) => ({ loading: { ...s.loading, upgrades: true } }));
    try {
      const upgrades = await api.upgrades.list(params);
      set({ upgrades, loading: { ...get().loading, upgrades: false } });
    } catch (e) {
      let result = mockUpgrades;
      if (params?.riskLevel && params.riskLevel !== 'All') {
        result = result.filter((u) => u.riskLevel === params.riskLevel);
      }
      set({ upgrades: result, loading: { ...get().loading, upgrades: false } });
    }
  },

  addRepository: async (fullName) => {
    try {
      const repo = await api.repositories.add(fullName);
      set((s) => ({ repositories: [...s.repositories, repo] }));
    } catch (e) {
      set((s) => ({ error: { ...s.error, addRepo: (e as Error).message } }));
    }
  },

  removeRepository: async (id) => {
    try {
      await api.repositories.remove(id);
      set((s) => ({ repositories: s.repositories.filter((r) => r.id !== id) }));
    } catch (e) {
      set((s) => ({ error: { ...s.error, removeRepo: (e as Error).message } }));
    }
  },

  triggerScan: async (id) => {
    try {
      await api.repositories.scan(id);
      set((s) => ({
        repositories: s.repositories.map((r) =>
          r.id === id ? { ...r, scanStatus: 'SCANNING' as const } : r
        ),
      }));
    } catch (e) {
      set((s) => ({ error: { ...s.error, scan: (e as Error).message } }));
    }
  },

  fetchServiceDependencies: async (repoId) => {
    set((s) => ({ loading: { ...s.loading, serviceDeps: true } }));
    try {
      const deps = await api.dependencies.getByService(repoId);
      set({ serviceDependencies: deps, loading: { ...get().loading, serviceDeps: false } });
    } catch (e) {
      set({ serviceDependencies: mockDependencies, loading: { ...get().loading, serviceDeps: false } });
    }
  },

  fetchServiceConflicts: async (repoId) => {
    try {
      const conflicts = await api.dependencies.getServiceConflicts(repoId);
      set({ serviceConflicts: conflicts });
    } catch (e) {
      set({ serviceConflicts: mockConflicts });
    }
  },

  fetchScanHistory: async (repoId) => {
    try {
      const history = await api.repositories.getScans(repoId);
      set({ scanHistory: history });
    } catch (e) {
      set({ scanHistory: mockScanHistory });
    }
  },

  setSelectedRepoId: (id) => set({ selectedRepoId: id }),
}));

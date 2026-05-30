import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type ThemeMode = 'light' | 'dark';

type VersionStatus = 'DRAFT' | 'PUBLISHED' | 'DEPRECATED' | 'OFFLINE';

interface ApiVersion {
  id: number;
  serviceName: string;
  version: string;
  description: string;
  status: VersionStatus;
  isDefault: boolean;
  publishTime?: string;
  deprecateTime?: string;
  offlineTime?: string;
  createTime: string;
  updateTime: string;
}

type RuleType = 'HEADER' | 'COOKIE' | 'QUERY' | 'IP';
type MatchMode = 'EQUAL' | 'CONTAIN' | 'REGEX';

interface RoutingRule {
  id: number;
  versionId: number;
  ruleType: RuleType;
  ruleKey: string;
  ruleValue: string;
  matchMode: MatchMode;
  priority: number;
  enabled: boolean;
  createTime: string;
  updateTime: string;
}

interface AppState {
  theme: ThemeMode;
  collapsed: boolean;
  versionList: ApiVersion[];
  currentVersion: ApiVersion | null;
  routingRules: RoutingRule[];
  loading: boolean;
  setTheme: (theme: ThemeMode) => void;
  toggleTheme: () => void;
  setCollapsed: (collapsed: boolean) => void;
  toggleCollapsed: () => void;
  setVersionList: (versions: ApiVersion[]) => void;
  setCurrentVersion: (version: ApiVersion | null) => void;
  addVersion: (version: ApiVersion) => void;
  updateVersion: (version: ApiVersion) => void;
  deleteVersion: (id: number) => void;
  setRoutingRules: (rules: RoutingRule[]) => void;
  addRoutingRule: (rule: RoutingRule) => void;
  updateRoutingRule: (rule: RoutingRule) => void;
  deleteRoutingRule: (id: number) => void;
  setLoading: (loading: boolean) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      theme: 'light',
      collapsed: false,
      versionList: [],
      currentVersion: null,
      routingRules: [],
      loading: false,

      setTheme: (theme) => set({ theme }),
      toggleTheme: () => set((state) => ({ theme: state.theme === 'light' ? 'dark' : 'light' })),
      setCollapsed: (collapsed) => set({ collapsed }),
      toggleCollapsed: () => set((state) => ({ collapsed: !state.collapsed })),

      setVersionList: (versions) => set({ versionList: versions }),
      setCurrentVersion: (version) => set({ currentVersion: version }),
      addVersion: (version) => set((state) => ({ versionList: [...state.versionList, version] })),
      updateVersion: (version) =>
        set((state) => ({
          versionList: state.versionList.map((v) => (v.id === version.id ? version : v)),
        })),
      deleteVersion: (id) =>
        set((state) => ({
          versionList: state.versionList.filter((v) => v.id !== id),
          currentVersion: state.currentVersion?.id === id ? null : state.currentVersion,
        })),

      setRoutingRules: (rules) => set({ routingRules: rules }),
      addRoutingRule: (rule) => set((state) => ({ routingRules: [...state.routingRules, rule] })),
      updateRoutingRule: (rule) =>
        set((state) => ({
          routingRules: state.routingRules.map((r) => (r.id === rule.id ? rule : r)),
        })),
      deleteRoutingRule: (id) =>
        set((state) => ({
          routingRules: state.routingRules.filter((r) => r.id !== id),
        })),

      setLoading: (loading) => set({ loading }),
    }),
    {
      name: 'app-storage',
      partialize: (state) => ({
        theme: state.theme,
        collapsed: state.collapsed,
        versionList: state.versionList,
        currentVersion: state.currentVersion,
        routingRules: state.routingRules,
      }),
    }
  )
);

export type { ApiVersion, RoutingRule, ThemeMode, VersionStatus, RuleType, MatchMode };

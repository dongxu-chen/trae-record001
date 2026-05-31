import { create } from 'zustand';
import type {
  TTLPolicy,
  JobStatus,
  TierStatus,
  DiskInfo,
  ClusterSnapshot,
  ExecutionResult,
  MigrationPlan,
  TableAnalysis,
  PartitionAction,
  SimulationResult,
  SavingsMetric,
  ArchiveJob,
  RoutingConfig,
  RouteResult,
} from '@/types';
import * as api from '@/api/client';

interface LifecycleState {
  policies: TTLPolicy[];
  policiesLoading: boolean;
  policiesError: string | null;

  schedulerStatus: Record<string, JobStatus>;
  schedulerLoading: boolean;
  schedulerError: string | null;

  tierStatus: TierStatus[];
  tierLoading: boolean;
  tierError: string | null;

  disks: DiskInfo[];
  disksLoading: boolean;
  disksError: string | null;

  snapshots: ClusterSnapshot[];
  currentSnapshot: ClusterSnapshot | null;
  snapshotsLoading: boolean;
  snapshotsError: string | null;

  lifecycleResult: ExecutionResult | null;
  lifecycleLoading: boolean;
  lifecycleError: string | null;

  tieringPlans: MigrationPlan[];
  tieringResult: api.MigrationResult | null;

  analysisResult: TableAnalysis | null;
  analysisLoading: boolean;
  analysisError: string | null;

  simulationResult: SimulationResult | null;
  simulationLoading: boolean;
  simulationError: string | null;
  savingsMetric: SavingsMetric | null;

  archiveJobs: ArchiveJob[];
  archiveLoading: boolean;
  archiveError: string | null;

  routingConfig: RoutingConfig | null;
  routeResult: RouteResult | null;
  routeLoading: boolean;
  routeError: string | null;

  archiveConfig: any | null;
  routingRules: any[];
  queryInfo: any | null;
  queryResults: any[] | null;

  expiredPartitions: PartitionAction[];

  fetchPolicies: () => Promise<void>;
  createPolicy: (policy: Omit<TTLPolicy, 'id' | 'created_at' | 'updated_at'>) => Promise<void>;
  updatePolicy: (id: string, policy: Omit<TTLPolicy, 'id' | 'created_at' | 'updated_at'>) => Promise<void>;
  deletePolicy: (id: string) => Promise<void>;
  fetchSchedulerStatus: () => Promise<void>;
  triggerJob: (jobType: string) => Promise<void>;
  fetchTierStatus: () => Promise<void>;
  planTiering: () => Promise<void>;
  executeTiering: (dryRun: boolean) => Promise<void>;
  evaluateLifecycle: (dryRun: boolean) => Promise<void>;
  executeLifecycle: (dryRun: boolean) => Promise<void>;
  fetchExpired: (database: string, table: string, days: number) => Promise<void>;
  fetchDisks: () => Promise<void>;
  fetchSnapshots: () => Promise<void>;
  fetchCurrentSnapshot: () => Promise<void>;
  analyzeTable: (database: string, table: string) => Promise<void>;

  runSimulation: (database: string, table: string, config: { days_to_simulate: number; daily_growth_rate: number; compression_ratio: number }) => Promise<void>;
  fetchArchives: () => Promise<void>;
  fetchRoutingConfig: () => Promise<void>;
  runQuery: (sql: string, database: string) => Promise<void>;

  createArchive: (database: string, table: string, partition: string) => Promise<void>;
  restoreArchive: (id: string) => Promise<void>;
  verifyArchive: (id: string) => Promise<void>;
  deleteArchive: (id: string) => Promise<void>;
  fetchArchiveConfig: () => Promise<void>;
  updateArchiveConfig: (config: any) => Promise<void>;

  analyzeQuery: (sql: string, database: string) => Promise<void>;
  executeRoutedQuery: (sql: string, database: string, source?: any) => Promise<void>;
  fetchRoutingRules: () => Promise<void>;
  addRoutingRule: (rule: any) => Promise<void>;
  deleteRoutingRule: (id: string) => Promise<void>;
  updateRouterConfig: (config: any) => Promise<void>;

  fetchSimulationSavings: (simulationId: string) => Promise<void>;
}

export const useLifecycleStore = create<LifecycleState>((set) => ({
  policies: [],
  policiesLoading: false,
  policiesError: null,
  schedulerStatus: {},
  schedulerLoading: false,
  schedulerError: null,
  tierStatus: [],
  tierLoading: false,
  tierError: null,
  disks: [],
  disksLoading: false,
  disksError: null,
  snapshots: [],
  currentSnapshot: null,
  snapshotsLoading: false,
  snapshotsError: null,
  lifecycleResult: null,
  lifecycleLoading: false,
  lifecycleError: null,
  tieringPlans: [],
  tieringResult: null,
  analysisResult: null,
  analysisLoading: false,
  analysisError: null,
  simulationResult: null,
  simulationLoading: false,
  simulationError: null,
  savingsMetric: null,
  archiveJobs: [],
  archiveLoading: false,
  archiveError: null,
  routingConfig: null,
  routeResult: null,
  routeLoading: false,
  routeError: null,
  archiveConfig: null,
  routingRules: [],
  queryInfo: null,
  queryResults: null,
  expiredPartitions: [],

  fetchPolicies: async () => {
    set({ policiesLoading: true, policiesError: null });
    try {
      const policies = await api.getPolicies();
      set({ policies, policiesLoading: false });
    } catch (e) {
      set({ policiesError: (e as Error).message, policiesLoading: false });
    }
  },

  createPolicy: async (policy) => {
    set({ policiesLoading: true, policiesError: null });
    try {
      const created = await api.createPolicy(policy);
      set((s) => ({ policies: [...s.policies, created], policiesLoading: false }));
    } catch (e) {
      set({ policiesError: (e as Error).message, policiesLoading: false });
    }
  },

  updatePolicy: async (id, policy) => {
    set({ policiesLoading: true, policiesError: null });
    try {
      const updated = await api.updatePolicy(id, policy);
      set((s) => ({ policies: s.policies.map((p) => (p.id === id ? updated : p)), policiesLoading: false }));
    } catch (e) {
      set({ policiesError: (e as Error).message, policiesLoading: false });
    }
  },

  deletePolicy: async (id) => {
    set({ policiesLoading: true, policiesError: null });
    try {
      await api.deletePolicy(id);
      set((s) => ({ policies: s.policies.filter((p) => p.id !== id), policiesLoading: false }));
    } catch (e) {
      set({ policiesError: (e as Error).message, policiesLoading: false });
    }
  },

  fetchSchedulerStatus: async () => {
    set({ schedulerLoading: true, schedulerError: null });
    try {
      const jobs = await api.getSchedulerStatus();
      const schedulerStatus: Record<string, JobStatus> = {};
      jobs.forEach((j) => { schedulerStatus[j.type] = j; });
      set({ schedulerStatus, schedulerLoading: false });
    } catch (e) {
      set({ schedulerError: (e as Error).message, schedulerLoading: false });
    }
  },

  triggerJob: async (jobType) => {
    try {
      await api.triggerJob(jobType as any);
      const jobs = await api.getSchedulerStatus();
      const schedulerStatus: Record<string, JobStatus> = {};
      jobs.forEach((j) => { schedulerStatus[j.type] = j; });
      set({ schedulerStatus });
    } catch (e) {
      set({ schedulerError: (e as Error).message });
    }
  },

  fetchTierStatus: async () => {
    set({ tierLoading: true, tierError: null });
    try {
      const tierStatus = await api.getTierStatus();
      set({ tierStatus, tierLoading: false });
    } catch (e) {
      set({ tierError: (e as Error).message, tierLoading: false });
    }
  },

  planTiering: async () => {
    set({ tierLoading: true, tierError: null });
    try {
      const { plans } = await api.planTiering();
      const tierStatus = await api.getTierStatus();
      set({ tieringPlans: plans, tierStatus, tierLoading: false });
    } catch (e) {
      set({ tierError: (e as Error).message, tierLoading: false });
    }
  },

  executeTiering: async (dryRun) => {
    set({ tierLoading: true, tierError: null });
    try {
      const tieringResult = await api.executeTiering(dryRun);
      const tierStatus = await api.getTierStatus();
      set({ tieringResult, tierStatus, tierLoading: false });
    } catch (e) {
      set({ tierError: (e as Error).message, tierLoading: false });
    }
  },

  evaluateLifecycle: async (dryRun) => {
    set({ lifecycleLoading: true, lifecycleError: null });
    try {
      const lifecycleResult = await api.evaluateLifecycle(dryRun);
      set({ lifecycleResult, lifecycleLoading: false });
    } catch (e) {
      set({ lifecycleError: (e as Error).message, lifecycleLoading: false });
    }
  },

  executeLifecycle: async (dryRun) => {
    set({ lifecycleLoading: true, lifecycleError: null });
    try {
      const lifecycleResult = await api.executeLifecycle(dryRun);
      set({ lifecycleResult, lifecycleLoading: false });
    } catch (e) {
      set({ lifecycleError: (e as Error).message, lifecycleLoading: false });
    }
  },

  fetchExpired: async (database, table, days) => {
    set({ lifecycleLoading: true, lifecycleError: null });
    try {
      const { expired } = await api.getExpiredPartitions(database, table, days);
      set({ expiredPartitions: expired, lifecycleLoading: false });
    } catch (e) {
      set({ lifecycleError: (e as Error).message, lifecycleLoading: false });
    }
  },

  fetchDisks: async () => {
    set({ disksLoading: true, disksError: null });
    try {
      const disks = await api.getDisks();
      set({ disks, disksLoading: false });
    } catch (e) {
      set({ disksError: (e as Error).message, disksLoading: false });
    }
  },

  fetchSnapshots: async () => {
    set({ snapshotsLoading: true, snapshotsError: null });
    try {
      const snapshots = await api.getSnapshots();
      set({ snapshots, snapshotsLoading: false });
    } catch (e) {
      set({ snapshotsError: (e as Error).message, snapshotsLoading: false });
    }
  },

  fetchCurrentSnapshot: async () => {
    set({ snapshotsLoading: true, snapshotsError: null });
    try {
      const currentSnapshot = await api.getCurrentSnapshot();
      set({ currentSnapshot, snapshotsLoading: false });
    } catch (e) {
      set({ snapshotsError: (e as Error).message, snapshotsLoading: false });
    }
  },

  analyzeTable: async (database, table) => {
    set({ analysisLoading: true, analysisError: null });
    try {
      const analysisResult = await api.analyzeTable(database, table);
      set({ analysisResult, analysisLoading: false });
    } catch (e) {
      set({ analysisError: (e as Error).message, analysisLoading: false });
    }
  },

  runSimulation: async (database, table, config) => {
    set({ simulationLoading: true, simulationError: null, simulationResult: null, savingsMetric: null });
    try {
      const simulationResult = await api.runSimulation(database, table, config);
      set({ simulationResult, simulationLoading: false });
    } catch (e) {
      set({ simulationError: (e as Error).message, simulationLoading: false });
    }
  },

  fetchArchives: async () => {
    set({ archiveLoading: true, archiveError: null });
    try {
      const archiveJobs = await api.getArchives();
      set({ archiveJobs, archiveLoading: false });
    } catch (e) {
      set({ archiveError: (e as Error).message, archiveLoading: false });
    }
  },

  fetchRoutingConfig: async () => {
    set({ routeLoading: true, routeError: null });
    try {
      const routingConfig = await api.getRouterConfig();
      set({ routingConfig, routeLoading: false });
    } catch (e) {
      set({ routeError: (e as Error).message, routeLoading: false });
    }
  },

  runQuery: async (sql: string, database: string) => {
    set({ routeLoading: true, routeError: null, routeResult: null });
    try {
      const routeResult = await api.routeQuery(sql, database);
      set({ routeResult, routeLoading: false });
    } catch (e) {
      set({ routeError: (e as Error).message, routeLoading: false });
    }
  },

  createArchive: async (database: string, table: string, partition: string) => {
    set({ archiveLoading: true, archiveError: null });
    try {
      await api.createArchive(database, table, partition);
      const archiveJobs = await api.getArchives();
      set({ archiveJobs, archiveLoading: false });
    } catch (e) {
      set({ archiveError: (e as Error).message, archiveLoading: false });
    }
  },

  restoreArchive: async (id: string) => {
    set({ archiveLoading: true, archiveError: null });
    try {
      await api.restoreArchive(id);
      const archiveJobs = await api.getArchives();
      set({ archiveJobs, archiveLoading: false });
    } catch (e) {
      set({ archiveError: (e as Error).message, archiveLoading: false });
    }
  },

  verifyArchive: async (id: string) => {
    set({ archiveLoading: true, archiveError: null });
    try {
      await api.verifyArchive(id);
      const archiveJobs = await api.getArchives();
      set({ archiveJobs, archiveLoading: false });
    } catch (e) {
      set({ archiveError: (e as Error).message, archiveLoading: false });
    }
  },

  deleteArchive: async (id: string) => {
    set({ archiveLoading: true, archiveError: null });
    try {
      await api.deleteArchive(id);
      const archiveJobs = await api.getArchives();
      set({ archiveJobs, archiveLoading: false });
    } catch (e) {
      set({ archiveError: (e as Error).message, archiveLoading: false });
    }
  },

  fetchArchiveConfig: async () => {
    set({ archiveLoading: true, archiveError: null });
    try {
      const archiveConfig = await api.getArchiveConfig();
      set({ archiveConfig, archiveLoading: false });
    } catch (e) {
      set({ archiveError: (e as Error).message, archiveLoading: false });
    }
  },

  updateArchiveConfig: async (config: any) => {
    set({ archiveLoading: true, archiveError: null });
    try {
      const archiveConfig = await api.updateArchiveConfig(config);
      set({ archiveConfig, archiveLoading: false });
    } catch (e) {
      set({ archiveError: (e as Error).message, archiveLoading: false });
    }
  },

  analyzeQuery: async (sql: string, database: string) => {
    set({ routeLoading: true, routeError: null, queryInfo: null });
    try {
      const queryInfo = await api.analyzeQuery(sql, database);
      set({ queryInfo, routeLoading: false });
    } catch (e) {
      set({ routeError: (e as Error).message, routeLoading: false });
    }
  },

  executeRoutedQuery: async (sql: string, database: string, source?: any) => {
    set({ routeLoading: true, routeError: null, queryResults: null });
    try {
      const result = await api.executeRoutedQuery(sql, database, source);
      set({ queryResults: result.results, routeLoading: false });
    } catch (e) {
      set({ routeError: (e as Error).message, routeLoading: false });
    }
  },

  fetchRoutingRules: async () => {
    set({ routeLoading: true, routeError: null });
    try {
      const routingRules = await api.getRoutingRules();
      set({ routingRules, routeLoading: false });
    } catch (e) {
      set({ routeError: (e as Error).message, routeLoading: false });
    }
  },

  addRoutingRule: async (rule: any) => {
    set({ routeLoading: true, routeError: null });
    try {
      await api.addRoutingRule(rule);
      const routingRules = await api.getRoutingRules();
      set({ routingRules, routeLoading: false });
    } catch (e) {
      set({ routeError: (e as Error).message, routeLoading: false });
    }
  },

  deleteRoutingRule: async (id: string) => {
    set({ routeLoading: true, routeError: null });
    try {
      await api.deleteRoutingRule(id);
      const routingRules = await api.getRoutingRules();
      set({ routingRules, routeLoading: false });
    } catch (e) {
      set({ routeError: (e as Error).message, routeLoading: false });
    }
  },

  updateRouterConfig: async (config: any) => {
    set({ routeLoading: true, routeError: null });
    try {
      const routingConfig = await api.updateRouterConfig(config);
      set({ routingConfig, routeLoading: false });
    } catch (e) {
      set({ routeError: (e as Error).message, routeLoading: false });
    }
  },

  fetchSimulationSavings: async (simulationId: string) => {
    set({ simulationLoading: true, simulationError: null });
    try {
      const savingsMetric = await api.getSimulationSavings(simulationId);
      set({ savingsMetric, simulationLoading: false });
    } catch (e) {
      set({ simulationError: (e as Error).message, simulationLoading: false });
    }
  },
}));

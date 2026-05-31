import { create } from 'zustand';
import { DataSource, MigrationTask, TaskStatus, dataSourceApi, taskApi } from '@/services/api';

interface AppState {
  dataSources: DataSource[];
  tasks: MigrationTask[];
  currentTask: MigrationTask | null;
  taskStatus: TaskStatus | null;
  dashboardStats: Record<string, any>;
  loading: boolean;
  sidebarCollapsed: boolean;

  fetchDataSources: () => Promise<void>;
  fetchTasks: () => Promise<void>;
  fetchDashboardStats: () => Promise<void>;
  setCurrentTask: (task: MigrationTask | null) => void;
  setTaskStatus: (status: TaskStatus | null) => void;
  toggleSidebar: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  dataSources: [],
  tasks: [],
  currentTask: null,
  taskStatus: null,
  dashboardStats: {},
  loading: false,
  sidebarCollapsed: false,

  fetchDataSources: async () => {
    set({ loading: true });
    try {
      const response = await dataSourceApi.list({ size: 100 });
      set({ dataSources: response.data.list || [] });
    } catch (error) {
      console.error('Failed to fetch data sources:', error);
      set({ dataSources: mockDataSources });
    } finally {
      set({ loading: false });
    }
  },

  fetchTasks: async () => {
    set({ loading: true });
    try {
      const response = await taskApi.list({ size: 100 });
      set({ tasks: response.data.list || [] });
    } catch (error) {
      console.error('Failed to fetch tasks:', error);
      set({ tasks: mockTasks });
    } finally {
      set({ loading: false });
    }
  },

  fetchDashboardStats: async () => {
    try {
      const response = await taskApi.getDashboardStats();
      set({ dashboardStats: response.data });
    } catch (error) {
      console.error('Failed to fetch dashboard stats:', error);
      set({
        dashboardStats: {
          total: 12,
          running: 3,
          completed: 8,
          failed: 1,
        },
      });
    }
  },

  setCurrentTask: (task) => set({ currentTask: task }),
  setTaskStatus: (status) => set({ taskStatus: status }),
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
}));

const mockDataSources: DataSource[] = [
  {
    id: '1',
    name: '生产MySQL',
    type: 'mysql',
    config: { host: 'localhost', port: 3306, database: 'prod' },
    status: 'active',
    createdAt: '2024-01-15T10:00:00Z',
    updatedAt: '2024-01-15T10:00:00Z',
  },
  {
    id: '2',
    name: '数据仓库PostgreSQL',
    type: 'postgresql',
    config: { host: 'localhost', port: 5432, database: 'warehouse' },
    status: 'active',
    createdAt: '2024-01-20T14:30:00Z',
    updatedAt: '2024-01-20T14:30:00Z',
  },
  {
    id: '3',
    name: '测试MongoDB',
    type: 'mongodb',
    config: { host: 'localhost', port: 27017, database: 'test' },
    status: 'inactive',
    createdAt: '2024-02-01T09:15:00Z',
    updatedAt: '2024-02-01T09:15:00Z',
  },
];

const mockTasks: MigrationTask[] = [
  {
    id: '1',
    name: '用户表全量同步',
    sourceId: '1',
    targetId: '2',
    mode: 'full',
    status: 'completed',
    config: { tableName: 'users' },
    createdAt: '2024-01-25T08:00:00Z',
    startedAt: '2024-01-25T08:00:00Z',
    finishedAt: '2024-01-25T08:30:00Z',
  },
  {
    id: '2',
    name: '订单数据增量同步',
    sourceId: '1',
    targetId: '2',
    mode: 'incremental',
    status: 'running',
    config: { tableName: 'orders', incrementalColumn: 'created_at' },
    createdAt: '2024-02-01T10:00:00Z',
    startedAt: '2024-02-01T10:00:00Z',
  },
  {
    id: '3',
    name: '日志归档任务',
    sourceId: '1',
    targetId: '3',
    mode: 'full',
    status: 'pending',
    config: { tableName: 'logs' },
    createdAt: '2024-02-10T15:00:00Z',
  },
];

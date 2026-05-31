import { create } from 'zustand';
import { DeadLetterMessage, DeadLetterQueryParams, PageResult, Statistics } from '@/types';
import { deadLetterApi } from '@/api/deadLetter';

interface DeadLetterState {
  list: DeadLetterMessage[];
  total: number;
  loading: boolean;
  statistics: Statistics | null;
  current: DeadLetterMessage | null;
  selectedIds: string[];
  queryParams: DeadLetterQueryParams;
  setQueryParams: (params: Partial<DeadLetterQueryParams>) => void;
  fetchList: (params?: DeadLetterQueryParams) => Promise<void>;
  fetchById: (id: string) => Promise<void>;
  fetchStatistics: () => Promise<void>;
  setSelectedIds: (ids: string[]) => void;
  reset: () => void;
}

const initialQueryParams: DeadLetterQueryParams = {
  pageNum: 1,
  pageSize: 10,
};

export const useDeadLetterStore = create<DeadLetterState>((set, get) => ({
  list: [],
  total: 0,
  loading: false,
  statistics: null,
  current: null,
  selectedIds: [],
  queryParams: initialQueryParams,

  setQueryParams: (params) =>
    set((state) => ({
      queryParams: { ...state.queryParams, ...params },
    })),

  fetchList: async (params) => {
    set({ loading: true });
    try {
      const queryParams = { ...get().queryParams, ...params };
      const result: PageResult<DeadLetterMessage> = await deadLetterApi.list(queryParams);
      set({
        list: result.list,
        total: result.total,
        queryParams,
      });
    } finally {
      set({ loading: false });
    }
  },

  fetchById: async (id: string) => {
    set({ loading: true });
    try {
      const message = await deadLetterApi.getById(id);
      set({ current: message });
    } finally {
      set({ loading: false });
    }
  },

  fetchStatistics: async () => {
    try {
      const stats = await deadLetterApi.getStatistics();
      set({ statistics: stats });
    } catch (error) {
      console.error('Failed to fetch statistics:', error);
    }
  },

  setSelectedIds: (ids: string[]) => set({ selectedIds: ids }),

  reset: () =>
    set({
      list: [],
      total: 0,
      current: null,
      selectedIds: [],
      queryParams: initialQueryParams,
    }),
}));

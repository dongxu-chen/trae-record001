import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import {
  DrillStore,
  DrillNode,
  LevelData,
  DrillState,
  StateSnapshot,
  STORAGE_KEY,
  MAX_HISTORY_SIZE,
  ROLE_CONFIG,
  UserRole,
  PredictionLevelData,
  RelatedChart,
} from '@/types/drill';
import { generateId } from '@/utils/drillUtils';
import { generatePredictionForLevel } from '@/utils/prediction';
import {
  getDataByPath,
  getRelatedCharts,
  isSensitiveData,
} from '@/data/mockData';

function createSnapshot(
  state: Pick<DrillState, 'path' | 'currentLevel' | 'chartType' | 'relatedCharts'>,
  action: StateSnapshot['action']
): StateSnapshot {
  return {
    id: generateId(),
    path: JSON.parse(JSON.stringify(state.path)),
    currentLevel: state.currentLevel,
    chartType: state.chartType,
    timestamp: Date.now(),
    action,
    relatedCharts: JSON.parse(JSON.stringify(state.relatedCharts)),
  };
}

const initialState: DrillState = {
  path: [],
  currentLevel: 0,
  chartType: 'bar',
  isDrilling: false,
  isLoading: true,
  currentData: null,
  predictionData: null,
  historyStack: [],
  historyIndex: -1,
  showPrediction: false,
  relatedCharts: getRelatedCharts(),
  linkRelatedCharts: true,
  currentRole: ROLE_CONFIG.admin,
  blockedByPermission: false,
};

export const useDrillStore = create<DrillStore>()(
  persist(
    (set, get) => ({
      ...initialState,

      drillDown: (node: DrillNode, data: LevelData) =>
        set((state) => {
          const targetLevel = state.currentLevel + 1;
          const isSensitive = isSensitiveData(
            [...pathToNames(state.path), node.name],
            node.name
          );

          if (!state.checkDrillPermission(targetLevel, isSensitive)) {
            return { blockedByPermission: true };
          }

          const snapshot = createSnapshot(
            {
              path: state.path,
              currentLevel: state.currentLevel,
              chartType: state.chartType,
              relatedCharts: state.relatedCharts,
            },
            'drillDown'
          );

          const newHistory = state.historyStack.slice(0, state.historyIndex + 1);
          newHistory.push(snapshot);

          if (newHistory.length > MAX_HISTORY_SIZE) {
            newHistory.shift();
          }

          let newRelatedCharts = state.relatedCharts;
          if (state.linkRelatedCharts) {
            newRelatedCharts = state.relatedCharts.map((chart) => {
              if (chart.isLinked && chart.isActive) {
                const relatedData = getDataByPath(
                  [...pathToNames(state.path), node.name],
                  chart.dimension
                );
                return {
                  ...chart,
                  path: [...chart.path, node],
                  currentLevel: targetLevel,
                  currentData: relatedData,
                };
              }
              return chart;
            });
          }

          return {
            path: [...state.path, node],
            currentLevel: targetLevel,
            currentData: data,
            isDrilling: false,
            blockedByPermission: false,
            historyStack: newHistory,
            historyIndex: newHistory.length - 1,
            relatedCharts: newRelatedCharts,
            predictionData: state.showPrediction
              ? generatePredictionForLevel(data)
              : null,
          };
        }),

      drillUp: (index: number) =>
        set((state) => {
          const newPath = state.path.slice(0, index + 1);
          const targetLevel = index + 1;

          if (!state.checkDrillPermission(targetLevel)) {
            return { blockedByPermission: true };
          }

          const snapshot = createSnapshot(
            {
              path: state.path,
              currentLevel: state.currentLevel,
              chartType: state.chartType,
              relatedCharts: state.relatedCharts,
            },
            'drillUp'
          );

          const newHistory = state.historyStack.slice(0, state.historyIndex + 1);
          newHistory.push(snapshot);

          if (newHistory.length > MAX_HISTORY_SIZE) {
            newHistory.shift();
          }

          let newRelatedCharts = state.relatedCharts;
          if (state.linkRelatedCharts) {
            newRelatedCharts = state.relatedCharts.map((chart) => {
              if (chart.isLinked && chart.isActive) {
                return {
                  ...chart,
                  path: chart.path.slice(0, index + 1),
                  currentLevel: targetLevel,
                };
              }
              return chart;
            });
          }

          return {
            path: newPath,
            currentLevel: targetLevel,
            isDrilling: false,
            blockedByPermission: false,
            historyStack: newHistory,
            historyIndex: newHistory.length - 1,
            relatedCharts: newRelatedCharts,
            predictionData: null,
          };
        }),

      resetDrill: () =>
        set((state) => {
          const snapshot = createSnapshot(
            {
              path: state.path,
              currentLevel: state.currentLevel,
              chartType: state.chartType,
              relatedCharts: state.relatedCharts,
            },
            'reset'
          );

          const newHistory = state.historyStack.slice(0, state.historyIndex + 1);
          newHistory.push(snapshot);

          if (newHistory.length > MAX_HISTORY_SIZE) {
            newHistory.shift();
          }

          const newRelatedCharts = state.relatedCharts.map((chart) => ({
            ...chart,
            path: [],
            currentLevel: 0,
          }));

          return {
            path: [],
            currentLevel: 0,
            isDrilling: false,
            blockedByPermission: false,
            historyStack: newHistory,
            historyIndex: newHistory.length - 1,
            relatedCharts: newRelatedCharts,
            predictionData: null,
          };
        }),

      setChartType: (type: 'bar' | 'pie' | 'line') =>
        set(() => ({
          chartType: type,
        })),

      setCurrentData: (data: LevelData | null) =>
        set((state) => ({
          currentData: data,
          predictionData:
            data && state.showPrediction ? generatePredictionForLevel(data) : null,
        })),

      setDrilling: (isDrilling: boolean) =>
        set(() => ({
          isDrilling,
        })),

      setLoading: (isLoading: boolean) =>
        set(() => ({
          isLoading,
        })),

      setBlockedByPermission: (blocked: boolean) =>
        set(() => ({
          blockedByPermission: blocked,
        })),

      restoreState: (state: Partial<DrillState>) =>
        set(() => ({
          ...state,
          isLoading: false,
        })),

      undo: () => {
        const state = get();
        if (state.historyIndex < 0) return false;

        const snapshot = state.historyStack[state.historyIndex];
        if (!snapshot) return false;

        set({
          path: snapshot.path,
          currentLevel: snapshot.currentLevel,
          chartType: snapshot.chartType,
          historyIndex: state.historyIndex - 1,
          relatedCharts: snapshot.relatedCharts || state.relatedCharts,
          predictionData: null,
        });

        return true;
      },

      redo: () => {
        const state = get();
        if (state.historyIndex >= state.historyStack.length - 1) return false;

        const nextIndex = state.historyIndex + 1;
        const snapshot = state.historyStack[nextIndex];
        if (!snapshot) return false;

        set({
          path: snapshot.path,
          currentLevel: snapshot.currentLevel,
          chartType: snapshot.chartType,
          historyIndex: nextIndex,
          relatedCharts: snapshot.relatedCharts || state.relatedCharts,
          predictionData: null,
        });

        return true;
      },

      canUndo: () => {
        const state = get();
        return state.historyIndex >= 0;
      },

      canRedo: () => {
        const state = get();
        return state.historyIndex < state.historyStack.length - 1;
      },

      jumpToSnapshot: (snapshotId: string) => {
        const state = get();
        const index = state.historyStack.findIndex((s) => s.id === snapshotId);
        if (index === -1) return false;

        const snapshot = state.historyStack[index];
        if (!snapshot) return false;

        set({
          path: snapshot.path,
          currentLevel: snapshot.currentLevel,
          chartType: snapshot.chartType,
          historyIndex: index,
          relatedCharts: snapshot.relatedCharts || state.relatedCharts,
          predictionData: null,
        });

        return true;
      },

      clearHistory: () =>
        set(() => ({
          historyStack: [],
          historyIndex: -1,
        })),

      togglePrediction: () =>
        set((state) => {
          const newShowPrediction = !state.showPrediction;
          return {
            showPrediction: newShowPrediction,
            predictionData:
              newShowPrediction && state.currentData
                ? generatePredictionForLevel(state.currentData)
                : null,
          };
        }),

      generatePrediction: () => {
        const state = get();
        if (!state.currentData) return null;
        const prediction = generatePredictionForLevel(state.currentData);
        set({ predictionData: prediction });
        return prediction;
      },

      toggleLinkRelatedCharts: () =>
        set((state) => ({
          linkRelatedCharts: !state.linkRelatedCharts,
        })),

      drillDownRelatedChart: (
        chartId: string,
        node: DrillNode,
        data: LevelData
      ) =>
        set((state) => {
          const chart = state.relatedCharts.find((c) => c.id === chartId);
          if (!chart) return {};

          const targetLevel = chart.currentLevel + 1;
          const isSensitive = isSensitiveData(
            [...pathToNames(chart.path), node.name],
            node.name
          );

          if (!state.checkDrillPermission(targetLevel, isSensitive)) {
            return { blockedByPermission: true };
          }

          const newRelatedCharts = state.relatedCharts.map((c) => {
            if (c.id === chartId) {
              return {
                ...c,
                path: [...c.path, node],
                currentLevel: targetLevel,
              };
            }
            return c;
          });

          if (state.linkRelatedCharts && chart.isLinked) {
            return {
              path: [...state.path, node],
              currentLevel: targetLevel,
              currentData: data,
              relatedCharts: newRelatedCharts,
              blockedByPermission: false,
              predictionData: state.showPrediction
                ? generatePredictionForLevel(data)
                : null,
            };
          }

          return {
            relatedCharts: newRelatedCharts,
            blockedByPermission: false,
          };
        }),

      setCurrentRole: (role: UserRole) =>
        set(() => ({
          currentRole: role,
          blockedByPermission: false,
        })),

      checkDrillPermission: (targetLevel: number, isSensitive?: boolean) => {
        const state = get();
        const { currentRole } = state;

        if (targetLevel > currentRole.maxDrillLevel) {
          return false;
        }

        if (isSensitive && !currentRole.canViewSensitive) {
          return false;
        }

        return true;
      },
    }),
    {
      name: STORAGE_KEY,
      partialize: (state) => ({
        path: state.path,
        currentLevel: state.currentLevel,
        chartType: state.chartType,
        historyStack: state.historyStack,
        historyIndex: state.historyIndex,
        showPrediction: state.showPrediction,
        relatedCharts: state.relatedCharts,
        linkRelatedCharts: state.linkRelatedCharts,
        currentRole: state.currentRole,
      }),
    }
  )
);

function pathToNames(path: DrillNode[]): string[] {
  return path.map((node) => node.name);
}

export function useDrillPath() {
  return useDrillStore((state) => state.path);
}

export function useCurrentLevel() {
  return useDrillStore((state) => state.currentLevel);
}

export function useChartType() {
  return useDrillStore((state) => state.chartType);
}

export function useCurrentData() {
  return useDrillStore((state) => state.currentData);
}

export function usePredictionData() {
  return useDrillStore((state) => state.predictionData);
}

export function useShowPrediction() {
  return useDrillStore((state) => state.showPrediction);
}

export function useIsDrilling() {
  return useDrillStore((state) => state.isDrilling);
}

export function useIsLoading() {
  return useDrillStore((state) => state.isLoading);
}

export function useHistoryStack() {
  return useDrillStore((state) => state.historyStack);
}

export function useHistoryIndex() {
  return useDrillStore((state) => state.historyIndex);
}

export function useCanUndo() {
  return useDrillStore((state) => state.historyIndex >= 0);
}

export function useCanRedo() {
  return useDrillStore(
    (state) => state.historyIndex < state.historyStack.length - 1
  );
}

export function useRelatedCharts() {
  return useDrillStore((state) => state.relatedCharts);
}

export function useLinkRelatedCharts() {
  return useDrillStore((state) => state.linkRelatedCharts);
}

export function useCurrentRole() {
  return useDrillStore((state) => state.currentRole);
}

export function useBlockedByPermission() {
  return useDrillStore((state) => state.blockedByPermission);
}

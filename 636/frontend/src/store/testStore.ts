import { create } from 'zustand';
import { TestConfig, TestReport, RealtimeMetrics, SampledMetrics } from '../types';

interface TestState {
  currentTestId: string | null;
  testConfig: TestConfig;
  isRunning: boolean;
  currentMetrics: RealtimeMetrics | null;
  metricsHistory: RealtimeMetrics[];
  currentReport: TestReport | null;
  reportList: TestReport[];

  setTestConfig: (config: TestConfig) => void;
  startTest: (testId: string) => void;
  stopTest: () => void;
  addMetrics: (metrics: RealtimeMetrics) => void;
  setCurrentReport: (report: TestReport | null) => void;
  setReportList: (reports: TestReport[]) => void;
  resetState: () => void;
}

const defaultConfig: TestConfig = {
  algorithm: 'SNOWFLAKE',
  threadCount: 10,
  durationSeconds: 10,
  snowflakeConfig: {
    workerId: 1,
    datacenterId: 1,
    clockMode: 'NORMAL',
    clockOffsetMs: 10,
    clockBackProbability: 0.001,
  },
  segmentConfig: {
    segmentSize: 1000,
  },
  uniquenessConfig: {
    sampleSize: 10000,
    falsePositiveProbability: 0.0001,
  },
};

export const useTestStore = create<TestState>((set) => ({
  currentTestId: null,
  testConfig: defaultConfig,
  isRunning: false,
  currentMetrics: null,
  metricsHistory: [],
  currentReport: null,
  reportList: [],

  setTestConfig: (config) => set({ testConfig: config }),

  startTest: (testId) =>
    set({
      currentTestId: testId,
      isRunning: true,
      metricsHistory: [],
      currentMetrics: null,
      currentReport: null,
    }),

  stopTest: () => set({ isRunning: false }),

  addMetrics: (metrics) =>
    set((state) => ({
      currentMetrics: metrics,
      metricsHistory: [...state.metricsHistory, metrics],
    })),

  setCurrentReport: (report) => set({ currentReport: report, isRunning: false }),

  setReportList: (reports) => set({ reportList: reports }),

  resetState: () =>
    set({
      currentTestId: null,
      isRunning: false,
      currentMetrics: null,
      metricsHistory: [],
      currentReport: null,
    }),
}));

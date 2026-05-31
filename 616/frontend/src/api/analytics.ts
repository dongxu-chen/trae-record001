import { request } from './request';
import { MqType } from '@/types/enums';

export interface PredictionResult {
  success: boolean;
  message?: string;
  data?: {
    trend: string;
    growthRate: string;
    predictedTotal: number;
    alertLevel: string;
    alertMessage?: string;
    metrics: Record<string, any>;
    dailyPredictions: Array<{
      time: string;
      predicted: number;
      lowerBound: number;
      upperBound: number;
      confidence: number;
    }>;
  };
  historicalDataPoints?: number;
}

export interface RepairResult {
  success: boolean;
  message?: string;
  repaired: boolean;
  repairType?: string;
  repairSteps?: string[];
  confidence?: number;
  originalError?: string;
  repairedBody?: string;
  autoReplayResult?: Record<string, any>;
  autoReplaySkipped?: boolean;
  skipReason?: string;
}

export interface TimelineDataPoint {
  timestamp: string;
  count: number;
  breakdown?: Record<string, number>;
}

export interface TimelineResult {
  data: TimelineDataPoint[];
  summary: Record<string, any>;
  interval: string;
  startDate: string;
  endDate: string;
}

export interface HeatmapCell {
  x: number;
  y: number;
  value: number;
  label: string;
}

export interface HeatmapData {
  cells: HeatmapCell[];
  xLabels: string[];
  yLabels: string[];
  maxValue: number;
  minValue: number;
}

export interface SankeyNode {
  name: string;
  category: number;
}

export interface SankeyLink {
  source: number;
  target: number;
  value: number;
}

export interface SankeyData {
  nodes: SankeyNode[];
  links: SankeyLink[];
}

export interface VisualizationResult {
  success: boolean;
  message?: string;
  data?: {
    timeline?: TimelineResult;
    heatmap?: HeatmapData;
    sankey?: SankeyData;
    insights?: Record<string, any>;
  };
}

export interface RepairCapabilities {
  strategies: Array<{
    type: string;
    name: string;
    description: string;
    confidence: number;
  }>;
  totalStrategies: number;
  autoReplayEnabled: boolean;
  minConfidenceForAutoReplay: number;
}

export const analyticsApi = {
  predictTrend: (params?: {
    topic?: string;
    mqType?: MqType;
    forecastDays?: number;
    startTime?: string;
    endTime?: string;
  }): Promise<PredictionResult> => {
    return request<PredictionResult>({
      url: '/analytics/prediction/trend',
      method: 'get',
      params,
    });
  },

  autoRepair: (id: string, autoReplay?: boolean): Promise<RepairResult> => {
    return request<RepairResult>({
      url: `/analytics/auto-repair/${id}`,
      method: 'post',
      params: { autoReplay },
    });
  },

  batchAutoRepair: (ids: string[], autoReplay?: boolean): Promise<Record<string, any>> => {
    return request<Record<string, any>>({
      url: '/analytics/auto-repair/batch',
      method: 'post',
      data: ids,
      params: { autoReplay },
    });
  },

  getRepairCapabilities: (): Promise<RepairCapabilities> => {
    return request<RepairCapabilities>({
      url: '/analytics/auto-repair/capabilities',
      method: 'get',
    });
  },

  getVisualization: (params?: {
    type?: string;
    topic?: string;
    mqType?: MqType;
    interval?: string;
    startTime?: string;
    endTime?: string;
  }): Promise<VisualizationResult> => {
    return request<VisualizationResult>({
      url: '/analytics/visualization',
      method: 'get',
      params,
    });
  },

  getTimeline: (params?: {
    topic?: string;
    mqType?: MqType;
    interval?: string;
    startTime?: string;
    endTime?: string;
  }): Promise<VisualizationResult> => {
    return request<VisualizationResult>({
      url: '/analytics/visualization/timeline',
      method: 'get',
      params,
    });
  },

  getHeatmap: (params?: {
    topic?: string;
    mqType?: MqType;
    startTime?: string;
    endTime?: string;
  }): Promise<VisualizationResult> => {
    return request<VisualizationResult>({
      url: '/analytics/visualization/heatmap',
      method: 'get',
      params,
    });
  },

  getSankey: (params?: {
    topic?: string;
    mqType?: MqType;
    startTime?: string;
    endTime?: string;
  }): Promise<VisualizationResult> => {
    return request<VisualizationResult>({
      url: '/analytics/visualization/sankey',
      method: 'get',
      params,
    });
  },

  getVisualizationOptions: (): Promise<Record<string, any>> => {
    return request<Record<string, any>>({
      url: '/analytics/visualization/options',
      method: 'get',
    });
  },
};

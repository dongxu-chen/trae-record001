export interface DrillNode {
  id: string;
  name: string;
  level: number;
  parentId: string | null;
}

export interface PredictionData {
  predictedValue: number;
  lowerBound: number;
  upperBound: number;
  confidence: number;
  trend: 'up' | 'down' | 'stable';
  method: string;
}

export interface DataPoint {
  name: string;
  value: number;
  hasChildren: boolean;
  isSensitive?: boolean;
  prediction?: PredictionData;
  relatedDimensions?: string[];
}

export interface LevelData {
  level: number;
  levelName: string;
  parentId: string | null;
  data: DataPoint[];
  dimension: string;
}

export interface PredictionLevelData {
  level: number;
  levelName: string;
  parentId: string | null;
  data: (DataPoint & { prediction?: PredictionData })[];
}

export interface RelatedChart {
  id: string;
  title: string;
  dimension: string;
  chartType: 'bar' | 'pie' | 'line';
  path: DrillNode[];
  currentLevel: number;
  isActive: boolean;
  isLinked: boolean;
}

export interface UserRole {
  role: 'admin' | 'manager' | 'viewer';
  maxDrillLevel: number;
  canViewSensitive: boolean;
  name: string;
}

export interface StateSnapshot {
  id: string;
  path: DrillNode[];
  currentLevel: number;
  chartType: 'bar' | 'pie' | 'line';
  timestamp: number;
  action: 'drillDown' | 'drillUp' | 'reset' | 'init' | 'restore';
  relatedCharts?: RelatedChart[];
}

export interface DrillState {
  path: DrillNode[];
  currentLevel: number;
  chartType: 'bar' | 'pie' | 'line';
  isDrilling: boolean;
  isLoading: boolean;
  currentData: LevelData | null;
  predictionData: PredictionLevelData | null;
  historyStack: StateSnapshot[];
  historyIndex: number;
  showPrediction: boolean;
  relatedCharts: RelatedChart[];
  linkRelatedCharts: boolean;
  currentRole: UserRole;
  blockedByPermission: boolean;
}

export interface DrillActions {
  drillDown: (node: DrillNode, data: LevelData) => void;
  drillUp: (index: number) => void;
  resetDrill: () => void;
  setChartType: (type: 'bar' | 'pie' | 'line') => void;
  setCurrentData: (data: LevelData | null) => void;
  setDrilling: (isDrilling: boolean) => void;
  setLoading: (isLoading: boolean) => void;
  setBlockedByPermission: (blocked: boolean) => void;
  restoreState: (state: Partial<DrillState>) => void;
  undo: () => boolean;
  redo: () => boolean;
  canUndo: () => boolean;
  canRedo: () => boolean;
  jumpToSnapshot: (snapshotId: string) => boolean;
  clearHistory: () => void;
  togglePrediction: () => void;
  generatePrediction: () => PredictionLevelData | null;
  toggleLinkRelatedCharts: () => void;
  drillDownRelatedChart: (chartId: string, node: DrillNode, data: LevelData) => void;
  setCurrentRole: (role: UserRole) => void;
  checkDrillPermission: (targetLevel: number, isSensitive?: boolean) => boolean;
}

export type DrillStore = DrillState & DrillActions;

export const LEVEL_NAMES = ['全国', '省份', '城市', '区县'];

export const STORAGE_KEY = 'chart_drill_state';
export const MAX_HISTORY_SIZE = 50;

export const ROLE_CONFIG: Record<UserRole['role'], UserRole> = {
  admin: {
    role: 'admin',
    maxDrillLevel: 3,
    canViewSensitive: true,
    name: '管理员',
  },
  manager: {
    role: 'manager',
    maxDrillLevel: 2,
    canViewSensitive: true,
    name: '经理',
  },
  viewer: {
    role: 'viewer',
    maxDrillLevel: 1,
    canViewSensitive: false,
    name: '查看者',
  },
};

export interface EChartsOption {
  tooltip?: {
    trigger?: string;
    axisPointer?: {
      type?: string;
    };
    formatter?: (params: any) => string;
  };
  legend?: {
    show?: boolean;
    orient?: string;
    top?: string | number;
    right?: string | number;
    textStyle?: {
      color?: string;
    };
  };
  grid?: {
    left?: string;
    right?: string;
    bottom?: string;
    top?: string;
    containLabel?: boolean;
  };
  xAxis?: {
    type?: string;
    data?: string[];
    axisLabel?: {
      color?: string;
      rotate?: number;
      fontSize?: number;
    };
    axisLine?: {
      lineStyle?: {
        color?: string;
      };
    };
  };
  yAxis?: {
    type?: string;
    axisLabel?: {
      color?: string;
      fontSize?: number;
    };
    axisLine?: {
      lineStyle?: {
        color?: string;
      };
    };
    splitLine?: {
      lineStyle?: {
        color?: string;
        type?: string;
      };
    };
  };
  series?: {
    type?: string;
    data?: any[];
    itemStyle?: {
      color?: any;
      borderRadius?: number | number[];
    };
    label?: {
      show?: boolean;
      position?: string;
      color?: string;
      fontSize?: number;
      formatter?: (params: any) => string;
    };
    emphasis?: {
      itemStyle?: {
        shadowBlur?: number;
        shadowColor?: string;
      };
      label?: {
        show?: boolean;
        fontSize?: number;
        fontWeight?: string;
      };
    };
    barWidth?: string | number;
    smooth?: boolean;
    symbol?: string;
    symbolSize?: number;
    lineStyle?: {
      width?: number;
      color?: any;
      type?: string;
    };
    areaStyle?: {
      color?: any;
    };
    radius?: string[];
    center?: string[];
    cursor?: string;
    name?: string;
    stack?: string;
  }[];
}

export interface UploadResponse {
  fileId: string;
  columns: string[];
  preview: Record<string, any>[];
  stats: {
    rowCount: number;
    columnCount: number;
    missingValues: Record<string, number>;
    dtypes: Record<string, string>;
  };
}

export interface ColumnInfo {
  name: string;
  type: 'numeric' | 'categorical' | 'binary';
  uniqueValues: number;
  sampleValues: any[];
}

export interface AnalysisRequest {
  fileId: string;
  treatment: string;
  outcome: string;
  covariates: string[];
  method: 'psm' | 'did';
  timeVariable?: string;
  postTreatmentIndicator?: string;
  data?: Record<string, any>[];
}

export interface EffectEstimate {
  estimate: number;
  stdError: number;
  pValue: number;
  confidenceInterval: [number, number];
}

export interface BalanceCheck {
  before: Record<string, { stdDiff: number }>;
  after: Record<string, { stdDiff: number }>;
}

export interface PropensityScores {
  treated: number[];
  control: number[];
}

export interface ParallelTrend {
  timePoints: string[];
  treatedMeans: number[];
  controlMeans: number[];
}

export interface EValueResult {
  e_value: number;
  lower_ci_e_value: number;
  risk_ratio: number;
  lower_bound_rr: number;
  interpretation: string;
}

export interface RosenbaumBoundsResult {
  bounds: Array<{
    gamma: number;
    p_upper: number;
    p_lower: number;
    z_upper: number;
    z_lower: number;
    p_value_upper: number;
    p_value_lower: number;
    significant_upper: boolean;
    significant_lower: boolean;
    range: [number, number];
  }>;
  critical_gamma: number;
  interpretation: string;
}

export interface SensitivityAnalysisResult {
  e_value: EValueResult;
  rosenbaum_bounds: RosenbaumBoundsResult;
  convergence_correlation: {
    critical_correlation: number;
    z_statistic: number;
    interpretation: string;
  };
  omitted_variable_scenarios: Array<{
    assumed_correlation_with_outcome: number;
    assumed_correlation_with_treatment: number;
    bias_magnitude: number;
    adjusted_estimate: number;
    adjusted_se: number;
    adjusted_p_value: number;
    still_significant: boolean;
  }>;
  robustness_summary: {
    e_value_gt_2: boolean;
    critical_gamma_gt_1_5: boolean;
    overall_robustness: 'high' | 'medium' | 'low';
  };
}

export interface CausalGraphNode {
  id: string;
  label: string;
  type: 'treatment' | 'outcome' | 'covariate';
  color: string;
  position: { x: number; y: number };
  size: number;
}

export interface CausalGraphEdge {
  source: string;
  target: string;
  type: 'causal' | 'confounder' | 'correlated';
  direction: 'forward' | 'undirected';
  strength: number;
  has_causal_path: boolean;
}

export interface BackdoorPathsResult {
  backdoor_paths: string[][];
  suggested_adjustment: string[];
  total_paths: number;
  backdoor_path_count: number;
}

export interface CausalGraphResult {
  nodes: CausalGraphNode[];
  edges: CausalGraphEdge[];
  adjacency_matrix: boolean[][];
  significance_level: number;
  backdoor_paths?: BackdoorPathsResult;
}

export interface LassoSelectionResult {
  selected_covariates: string[];
  covariate_importance: Array<{
    covariate: string;
    treatment_importance: number;
    outcome_importance: number;
    selection_frequency: number;
    combined_importance: number;
  }>;
  method_used: string;
}

export interface EnhancedPlaceboResult {
  random_assignment?: {
    p_value: number;
    mean_effect: number;
    all_effects: number[];
  };
  in_time_placebo?: {
    p_value: number;
    mean_effect: number;
    all_effects: number[];
  };
  outcome_placebo?: {
    p_value: number;
    mean_effect: number;
    all_effects: number[];
  };
  combined?: {
    p_value: number;
    mean_effect: number;
    all_effects: number[];
  };
}

export interface ParallelTrendTestsResult {
  graphical?: ParallelTrend;
  statistical?: {
    f_statistic: number;
    p_value: number;
    passed: boolean;
    note: string;
  };
  event_study?: any;
}

export interface RobustnessTests {
  placeboTest?: {
    estimate: number;
    pValue: number;
  };
  sensitivityAnalysis?: {
    rhoValues: number[];
    estimateBounds: [number, number][];
    e_value?: EValueResult;
    rosenbaum?: RosenbaumBoundsResult;
  };
  differentMethods?: Array<{
    method: string;
    estimate: number;
    stdError: number;
  }>;
  enhancedPlacebo?: EnhancedPlaceboResult;
}

export interface AnalysisResult {
  method: string;
  ate: EffectEstimate;
  att: EffectEstimate;
  balanceCheck?: BalanceCheck;
  propensityScores?: PropensityScores;
  parallelTrend?: ParallelTrend;
  robustnessTests: RobustnessTests;
  charts: {
    propensityDistribution?: any;
    balancePlot?: any;
    parallelTrendPlot?: any;
    robustnessPlot?: any;
  };
  sampleSize?: {
    total: number;
    treated: number;
    control: number;
  };
  matchedSampleSize?: {
    total: number;
    treated: number;
    control: number;
  };
  lassoSelection?: LassoSelectionResult;
  parallelTrendTests?: ParallelTrendTestsResult;
  causal_graph?: CausalGraphResult;
  sensitivity_analysis?: SensitivityAnalysisResult;
}

export type AnalysisMethod = 'psm' | 'did';

export interface DataStoreState {
  fileId: string | null;
  columns: string[];
  data: Record<string, any>[];
  stats: UploadResponse['stats'] | null;
  columnInfo: ColumnInfo[];
  treatment: string | null;
  outcome: string | null;
  covariates: string[];
  method: AnalysisMethod;
  timeVariable: string | null;
  result: AnalysisResult | null;
  isLoading: boolean;
  error: string | null;
}

export interface DataStore extends DataStoreState {
  setFileId: (fileId: string | null) => void;
  setColumns: (columns: string[]) => void;
  setData: (data: Record<string, any>[]) => void;
  setStats: (stats: UploadResponse['stats'] | null) => void;
  setColumnInfo: (columnInfo: ColumnInfo[]) => void;
  setTreatment: (treatment: string | null) => void;
  setOutcome: (outcome: string | null) => void;
  setCovariates: (covariates: string[]) => void;
  setMethod: (method: AnalysisMethod) => void;
  setTimeVariable: (timeVariable: string | null) => void;
  setResult: (result: AnalysisResult | null) => void;
  setIsLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  resetData: () => void;
}

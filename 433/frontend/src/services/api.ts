import axios from 'axios';

const API_BASE = '/api/v1';

export interface NamespaceInfo {
  name: string;
  labels: Record<string, string>;
  phase: string;
}

export interface CostBreakdown {
  cpu: number;
  memory: number;
  storage: number;
  network: number;
  total: number;
}

export interface ResourceUsage {
  cpuCores: number;
  memoryGB: number;
  storageUsedGB: number;
  storageCapacityGB: number;
  networkInternalRxGB: number;
  networkInternalTxGB: number;
  networkExternalRxGB: number;
  networkExternalTxGB: number;
  cpuRequestCores: number;
  memoryRequestGB: number;
}

export interface ResourceContention {
  namespace: string;
  cpuThrottledTime: number;
  memoryOOMCount: number;
  contentionScore: number;
  recommendedCPU: number;
  recommendedMemory: number;
  contentionLevel: string;
}

export interface BudgetAlert {
  namespace: string;
  currentCost: number;
  budget: number;
  percentage: number;
  level: string;
  message: string;
  daysRemaining: number;
  projectedCost: number;
}

export interface PriceComparison {
  scenario: string;
  monthlyCpuCost: number;
  monthlyMemoryCost: number;
  totalMonthlyCost: number;
  upfrontCost?: number;
  annualSavings?: number;
  savingsPercent?: number;
  breakEvenMonths?: number;
}

export interface SpotRecommendation {
  namespace: string;
  cpuCores: number;
  memoryGB: number;
  onDemandMonthly: number;
  spotMonthly: number;
  monthlySavings: number;
  savingsPercent: number;
  interruptionRisk: string;
  workloadType: string;
  eligible: boolean;
  reason: string;
}

export interface IdleResource {
  namespace: string;
  resourceType: string;
  requested: number;
  used: number;
  idleAmount: number;
  idleCost: number;
  utilization: number;
}

export interface CostPrediction {
  namespace: string;
  currentCost: number;
  predictedCost30D: number;
  predictedCost90D: number;
  growthRate: number;
}

export interface OptimizationSuggestion {
  namespace: string;
  type: string;
  description: string;
  estimatedSavings: number;
  severity: string;
}

export const api = {
  health: () => axios.get(`${API_BASE}/health`),

  getNamespaces: () => axios.get<NamespaceInfo[]>(`${API_BASE}/namespaces`),

  getPods: (namespace?: string) =>
    axios.get(`${API_BASE}/pods`, { params: namespace ? { namespace } : {} }),

  getNodes: () => axios.get(`${API_BASE}/nodes`),

  getNamespaceCosts: (durationHours: number) =>
    axios.post<{ data: NamespaceCost[] }>(`${API_BASE}/cost/namespace`, {
      durationHours,
    }),

  getProjectCosts: (durationHours: number, projectLabel: string) =>
    axios.post<{ data: ProjectCost[] }>(`${API_BASE}/cost/project`, {
      durationHours,
      projectLabel,
    }),

  getLabelCosts: (durationHours: number, labelKey: string) =>
    axios.post<{ data: LabelCost[] }>(`${API_BASE}/cost/label`, {
      durationHours,
      labelKey,
    }),

  getIdleResources: (duration: number = 24) =>
    axios.get<{ data: IdleResource[] }>(`${API_BASE}/cost/idle`, {
      params: { duration },
    }),

  getResourceContention: (duration: number = 24) =>
    axios.get<{ data: ResourceContention[] }>(`${API_BASE}/cost/contention`, {
      params: { duration },
    }),

  getCostPrediction: (namespace: string, durationHours: number = 720) =>
    axios.post<CostPrediction>(`${API_BASE}/cost/predict`, {
      namespace,
      durationHours,
    }),

  getOptimizations: (duration: number = 24) =>
    axios.get<{ data: OptimizationSuggestion[] }>(`${API_BASE}/optimizations`, {
      params: { duration },
    }),

  getBudgetAlerts: (duration: number = 24) =>
    axios.get<{ data: BudgetAlert[]; count: number }>(`${API_BASE}/budgets/alerts`, {
      params: { duration },
    }),

  getBudgets: () =>
    axios.get<{ defaultBudget: number; namespaces: Record<string, number> }>(`${API_BASE}/budgets`),

  setBudget: (namespace: string, budget: number) =>
    axios.post(`${API_BASE}/budgets`, { namespace, budget }),

  comparePricing: (cpuCores: number, memoryGB: number) =>
    axios.post<{ data: PriceComparison[] }>(`${API_BASE}/pricing/compare`, {
      cpuCores,
      memoryGB,
    }),

  getSpotRecommendations: (duration: number = 24) =>
    axios.get<{ data: SpotRecommendation[]; eligibleCount: number; totalMonthlySavings: number }>(`${API_BASE}/pricing/spot-recommendations`, {
      params: { duration },
    }),

  getCurrentBilling: (startDate: string, endDate: string) =>
    axios.post(`${API_BASE}/billing/current`, { startDate, endDate }),

  getBillingForecast: (startDate: string, endDate: string) =>
    axios.post(`${API_BASE}/billing/forecast`, { startDate, endDate }),

  getBillingByService: (startDate: string, endDate: string) =>
    axios.post(`${API_BASE}/billing/services`, { startDate, endDate }),
};

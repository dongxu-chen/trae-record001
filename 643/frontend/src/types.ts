export interface Service {
  id: string;
  name: string;
  dependencies: string[];
}

export interface PerformanceData {
  serviceId: string;
  timestamp: string;
  cpuUsage: number;
  memoryUsage: number;
  requestsPerSec: number;
  avgLatencyMs: number;
  p99LatencyMs: number;
  errorRate: number;
}

export interface LoadTestData {
  serviceId: string;
  concurrentUsers: number;
  throughput: number;
  avgLatencyMs: number;
  p99LatencyMs: number;
  cpuUsage: number;
  memoryUsage: number;
  errorRate: number;
}

export interface ServerConfig {
  id: string;
  name: string;
  cpuCores: number;
  memoryGB: number;
  costPerHour: number;
  maxRequestsPerSec: number;
}

export interface CapacityResult {
  serviceId: string;
  serverConfig: ServerConfig;
  requiredServers: number;
  recommendedServers: number;
  estimatedCpuUsage: number;
  estimatedMemoryUsage: number;
  estimatedLatencyMs: number;
  queueLength: number;
  utilization: number;
  monthlyCost: number;
  breakdown: CostBreakdown;
}

export interface CostBreakdown {
  computeCost: number;
  storageCost: number;
  networkCost: number;
  laborCost: number;
  totalCost: number;
}

export interface DependencyResult {
  serviceId: string;
  requiredServers: number;
  dependencyImpact: Record<string, number>;
  totalCapacity: number;
}

export interface CalibrationFactor {
  serviceId: string;
  cpuCorrection: number;
  memoryCorrection: number;
  latencyCorrection: number;
}

export interface TrafficData {
  timestamp: string;
  requestsPerSec: number;
}

export interface TrafficForecast {
  serviceId: string;
  forecastPeriod: number;
  growthRate: number;
  historicalData: TrafficData[];
  predictedData: TrafficData[];
}

export interface EvaluationRequest {
  services: Service[];
  performanceData: PerformanceData[];
  loadTestData: LoadTestData[];
  serverConfigs: ServerConfig[];
  forecastPeriodDays: number;
  targetUtilization: number;
  maxLatencyMs: number;
  includeDependencies: boolean;
}

export interface EvaluationResponse {
  results: CapacityResult[];
  dependencyResults: DependencyResult[];
  trafficForecasts: TrafficForecast[];
  calibrationFactors: CalibrationFactor[];
  totalMonthlyCost: number;
}

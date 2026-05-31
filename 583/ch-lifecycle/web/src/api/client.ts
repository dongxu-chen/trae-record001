import type {
  TTLPolicy,
  ExecutionResult,
  PartitionAction,
  MigrationPlan,
  MigrationResult,
  TierStatus,
  JobStatus,
  JobType,
  TableAnalysis,
  TableInfo,
  PartitionInfo,
  DiskInfo,
  StoragePolicyInfo,
  ClusterSnapshot,
  ArchiveConfig,
  ArchiveJob,
  CreateArchiveRequest,
  RoutingConfig,
  QueryInfo,
  RouteResult,
  RoutingRule,
  CreateRoutingRuleRequest,
  QuerySource,
  SimulationResult,
  SavingsMetric,
  ChartData,
} from '../types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `Request failed: ${res.status}`);
  }
  return res.json();
}

export async function getPolicies(): Promise<TTLPolicy[]> {
  const data = await request<{ policies: TTLPolicy[] }>('/policies');
  return data.policies;
}

export async function getPolicy(id: string): Promise<TTLPolicy> {
  return request<TTLPolicy>(`/policies/${id}`);
}

export async function createPolicy(policy: Omit<TTLPolicy, 'id' | 'created_at' | 'updated_at'>): Promise<TTLPolicy> {
  return request<TTLPolicy>('/policies', {
    method: 'POST',
    body: JSON.stringify(policy),
  });
}

export async function updatePolicy(id: string, policy: Omit<TTLPolicy, 'id' | 'created_at' | 'updated_at'>): Promise<TTLPolicy> {
  return request<TTLPolicy>(`/policies/${id}`, {
    method: 'PUT',
    body: JSON.stringify(policy),
  });
}

export async function deletePolicy(id: string): Promise<void> {
  await request(`/policies/${id}`, { method: 'DELETE' });
}

export async function evaluateLifecycle(dryRun = true): Promise<ExecutionResult> {
  return request<ExecutionResult>(`/lifecycle/evaluate?dry_run=${dryRun}`);
}

export async function executeLifecycle(dryRun = false): Promise<ExecutionResult> {
  return request<ExecutionResult>(`/lifecycle/execute?dry_run=${dryRun}`, {
    method: 'POST',
  });
}

export async function getExpiredPartitions(database: string, table: string, retentionDays = 90): Promise<{ expired: PartitionAction[]; count: number }> {
  return request<{ expired: PartitionAction[]; count: number }>(
    `/lifecycle/expired?database=${encodeURIComponent(database)}&table=${encodeURIComponent(table)}&retention_days=${retentionDays}`,
  );
}

export async function planTiering(): Promise<{ plans: MigrationPlan[]; count: number }> {
  return request<{ plans: MigrationPlan[]; count: number }>('/tiering/plan');
}

export async function executeTiering(dryRun = false): Promise<MigrationResult> {
  return request<MigrationResult>(`/tiering/execute?dry_run=${dryRun}`, {
    method: 'POST',
  });
}

export async function getTierStatus(): Promise<TierStatus[]> {
  const data = await request<{ tiers: TierStatus[] }>('/tiering/status');
  return data.tiers;
}

export async function getSchedulerStatus(): Promise<JobStatus[]> {
  const data = await request<{ jobs: Record<string, JobStatus> }>('/scheduler/status');
  return Object.values(data.jobs);
}

export async function triggerJob(jobType: JobType): Promise<void> {
  await request(`/scheduler/trigger/${jobType}`, { method: 'POST' });
}

export async function analyzeTable(database: string, table: string): Promise<TableAnalysis> {
  return request<TableAnalysis>(`/advisor/analyze/${encodeURIComponent(database)}/${encodeURIComponent(table)}`);
}

export async function analyzeDatabase(database: string): Promise<TableAnalysis[]> {
  const data = await request<{ analyses: TableAnalysis[] }>(`/advisor/analyze/${encodeURIComponent(database)}`);
  return data.analyses;
}

export async function getTables(database: string): Promise<TableInfo[]> {
  const data = await request<{ tables: TableInfo[] }>(`/cluster/tables?database=${encodeURIComponent(database)}`);
  return data.tables;
}

export async function getPartitions(database: string, table: string): Promise<{ partitions: PartitionInfo[]; count: number }> {
  return request<{ partitions: PartitionInfo[]; count: number }>(
    `/cluster/tables/${encodeURIComponent(database)}/${encodeURIComponent(table)}/partitions`,
  );
}

export async function getDisks(): Promise<DiskInfo[]> {
  const data = await request<{ disks: DiskInfo[] }>('/cluster/disks');
  return data.disks;
}

export async function getStoragePolicies(): Promise<StoragePolicyInfo[]> {
  const data = await request<{ policies: StoragePolicyInfo[] }>('/cluster/storage-policies');
  return data.policies;
}

export async function getSnapshots(): Promise<ClusterSnapshot[]> {
  const data = await request<{ snapshots: ClusterSnapshot[] }>('/monitor/snapshots');
  return data.snapshots;
}

export async function getCurrentSnapshot(): Promise<ClusterSnapshot> {
  return request<ClusterSnapshot>('/monitor/snapshot/current');
}

export async function runSimulation(
  database: string,
  table: string,
  config: { days_to_simulate: number; daily_growth_rate: number; compression_ratio: number },
): Promise<SimulationResult> {
  return request<SimulationResult>(
    `/simulator/run?database=${encodeURIComponent(database)}&table=${encodeURIComponent(table)}`,
    {
      method: 'POST',
      body: JSON.stringify(config),
    },
  );
}

export async function getSimulationSavings(simulationId: string): Promise<SavingsMetric> {
  return request<SavingsMetric>(`/simulator/${simulationId}/savings`);
}

export async function getSimulationCharts(simulationId: string): Promise<ChartData> {
  return request<ChartData>(`/simulator/${simulationId}/charts`);
}

export async function getArchives(): Promise<ArchiveJob[]> {
  const data = await request<{ archives: ArchiveJob[] }>('/archive/jobs');
  return data.archives;
}

export async function getArchive(id: string): Promise<ArchiveJob> {
  return request<ArchiveJob>(`/archive/jobs/${id}`);
}

export async function createArchive(database: string, table: string, partition: string): Promise<ArchiveJob> {
  return request<ArchiveJob>('/archive/jobs', {
    method: 'POST',
    body: JSON.stringify({ database, table, partition }),
  });
}

export async function exportArchive(id: string): Promise<void> {
  await request(`/archive/jobs/${id}/export`, { method: 'POST' });
}

export async function restoreArchive(id: string): Promise<void> {
  await request(`/archive/jobs/${id}/restore`, { method: 'POST' });
}

export async function verifyArchive(id: string): Promise<{ verified: boolean }> {
  return request<{ verified: boolean }>(`/archive/jobs/${id}/verify`, {
    method: 'POST',
  });
}

export async function deleteArchive(id: string): Promise<void> {
  await request(`/archive/jobs/${id}`, { method: 'DELETE' });
}

export async function getArchiveConfig(): Promise<ArchiveConfig> {
  return request<ArchiveConfig>('/archive/config');
}

export async function updateArchiveConfig(config: Partial<ArchiveConfig>): Promise<ArchiveConfig> {
  return request<ArchiveConfig>('/archive/config', {
    method: 'PUT',
    body: JSON.stringify(config),
  });
}

export async function analyzeQuery(sql: string, database: string): Promise<QueryInfo> {
  return request<QueryInfo>('/router/analyze', {
    method: 'POST',
    body: JSON.stringify({ sql, database }),
  });
}

export async function routeQuery(sql: string, database: string): Promise<RouteResult> {
  return request<RouteResult>('/router/route', {
    method: 'POST',
    body: JSON.stringify({ sql, database }),
  });
}

export async function executeRoutedQuery(
  sql: string,
  database: string,
  source?: QuerySource,
): Promise<{ source: QuerySource; results: any[]; count: number }> {
  return request<{ source: QuerySource; results: any[]; count: number }>('/router/execute', {
    method: 'POST',
    body: JSON.stringify({ sql, database, source }),
  });
}

export async function getRoutingRules(): Promise<RoutingRule[]> {
  const data = await request<{ rules: RoutingRule[] }>('/router/rules');
  return data.rules;
}

export async function addRoutingRule(rule: Omit<RoutingRule, 'id'>): Promise<RoutingRule> {
  return request<RoutingRule>('/router/rules', {
    method: 'POST',
    body: JSON.stringify(rule),
  });
}

export async function deleteRoutingRule(id: string): Promise<void> {
  await request(`/router/rules/${id}`, { method: 'DELETE' });
}

export async function getRouterConfig(): Promise<RoutingConfig> {
  return request<RoutingConfig>('/router/config');
}

export async function updateRouterConfig(config: RoutingConfig): Promise<RoutingConfig> {
  return request<RoutingConfig>('/router/config', {
    method: 'PUT',
    body: JSON.stringify(config),
  });
}

export async function simulateLifecycle(params: Record<string, unknown>): Promise<SimulationResult> {
  return request<SimulationResult>('/simulator/simulate', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function calculateSavings(
  params: Record<string, unknown>,
): Promise<{ savings: SavingsMetric; charts: ChartData; result: SimulationResult }> {
  return request<{ savings: SavingsMetric; charts: ChartData; result: SimulationResult }>('/simulator/savings', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

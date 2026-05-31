import type {
  DashboardStats,
  Repository,
  Dependency,
  VersionConflict,
  Vulnerability,
  UpgradeSuggestion,
  BatchPRRequest,
  BatchPRResponse,
  ScanResult,
  ProjectHealthResponse,
  HealthScore,
  UsageAnalysisResponse,
  AutoUpgradeResponse,
  AutoUpgradeExecutionResponse,
  AutoUpgradeConfigResponse,
} from '@/types';

const API_BASE = 'http://localhost:8080/api';

async function fetchApi<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) throw new Error(`API Error: ${res.status} ${res.statusText}`);
  return res.json();
}

export const api = {
  dashboard: {
    getStats: () => fetchApi<DashboardStats>('/dashboard/stats'),
  },
  repositories: {
    list: () => fetchApi<Repository[]>('/repositories'),
    add: (fullName: string) =>
      fetchApi<Repository>('/repositories', {
        method: 'POST',
        body: JSON.stringify({ fullName }),
      }),
    remove: (id: number) =>
      fetchApi<void>(`/repositories/${id}`, { method: 'DELETE' }),
    scan: (id: number) =>
      fetchApi<void>(`/repositories/${id}/scan`, { method: 'POST' }),
    getScans: (id: number) =>
      fetchApi<ScanResult[]>(`/repositories/${id}/scans`),
  },
  dependencies: {
    getByService: (repoId: number) =>
      fetchApi<Dependency[]>(`/services/${repoId}/dependencies`),
    getConflicts: () => fetchApi<VersionConflict[]>('/conflicts'),
    getServiceConflicts: (repoId: number) =>
      fetchApi<VersionConflict[]>(`/services/${repoId}/conflicts`),
    getFullTree: (repoId: number) =>
      fetchApi<any[]>(`/services/${repoId}/dependencies/full-tree`),
  },
  health: {
    getProjectHealth: (repoId: number) =>
      fetchApi<ProjectHealthResponse>(`/services/${repoId}/health`),
    getDependencyHealth: (repoId: number, depId: number) =>
      fetchApi<HealthScore>(`/services/${repoId}/dependencies/${depId}/health`),
  },
  usage: {
    analyze: (repoId: number, projectRoot?: string) =>
      fetchApi<UsageAnalysisResponse>(`/services/${repoId}/usage-analysis`, {
        method: 'POST',
        body: JSON.stringify({ projectRoot }),
      }),
  },
  autoUpgrade: {
    getCandidates: (repoId: number) =>
      fetchApi<AutoUpgradeResponse>(`/services/${repoId}/auto-upgrade/candidates`),
    execute: (repoId: number, userId?: string) =>
      fetchApi<AutoUpgradeExecutionResponse>(`/services/${repoId}/auto-upgrade/execute`, {
        method: 'POST',
        body: JSON.stringify({ userId }),
      }),
    getConfig: () =>
      fetchApi<AutoUpgradeConfigResponse>('/auto-upgrade/config'),
  },
  vulnerabilities: {
    list: (params?: { severity?: string; service?: string }) => {
      const query = new URLSearchParams();
      if (params?.severity) query.set('severity', params.severity);
      if (params?.service) query.set('service', params.service);
      const qs = query.toString();
      return fetchApi<Vulnerability[]>(`/vulnerabilities${qs ? `?${qs}` : ''}`);
    },
    get: (cveId: string) =>
      fetchApi<Vulnerability>(`/vulnerabilities/${cveId}`),
    getStats: () =>
      fetchApi<{ critical: number; high: number; medium: number; low: number }>('/vulnerabilities/stats'),
  },
  upgrades: {
    list: (params?: { riskLevel?: string }) => {
      const query = new URLSearchParams();
      if (params?.riskLevel) query.set('riskLevel', params.riskLevel);
      const qs = query.toString();
      return fetchApi<UpgradeSuggestion[]>(`/upgrades${qs ? `?${qs}` : ''}`);
    },
    createBatchPR: (request: { upgradeIds: number[]; autoCreatePR?: boolean }) =>
      fetchApi<BatchPRResponse>('/upgrades/batch-pr', {
        method: 'POST',
        body: JSON.stringify(request),
      }),
    verifyAndCreatePR: (upgradeIds: number[], autoCreatePR: boolean = false) =>
      fetchApi<BatchPRVerifyResponse>('/upgrades/batch-pr/verify', {
        method: 'POST',
        body: JSON.stringify({ upgradeIds, autoCreatePR }),
      }),
    verifyBuild: (repoId: number, upgradeIds: number[]) =>
      fetchApi<BuildVerificationResult>(`/upgrades/verify/${repoId}`, {
        method: 'POST',
        body: JSON.stringify(upgradeIds),
      }),
    getCompatibility: (groupId: string, artifactId: string, currentVersion: string, targetVersion: string) =>
      fetchApi<any>(
        `/upgrades/compatibility/${groupId}/${artifactId}?currentVersion=${currentVersion}&latestVersion=${targetVersion}`
      ),
  },
};

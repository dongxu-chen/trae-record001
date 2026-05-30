import axios from 'axios';
import type {
  Policy,
  ListPoliciesResponse,
  ConflictDetectionResult,
  ImpactAnalysisResult,
  PolicyRecommendation,
  CanaryDeployment,
  ServiceTopology,
  PolicyEvaluationResult
} from '../types';

const API_BASE = '/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

export const policyApi = {
  listPolicies: (type?: string, namespace?: string) => {
    const params = new URLSearchParams();
    if (type) params.append('type', type);
    if (namespace) params.append('namespace', namespace);
    return api.get<ListPoliciesResponse>(`/policies?${params.toString()}`);
  },

  getPolicy: (id: string) => {
    return api.get<Policy>(`/policies/${id}`);
  },

  createPolicy: (policy: Partial<Policy>) => {
    return api.post<Policy>('/policies', policy);
  },

  updatePolicy: (id: string, policy: Partial<Policy>) => {
    return api.put<Policy>(`/policies/${id}`, policy);
  },

  deletePolicy: (id: string) => {
    return api.delete(`/policies/${id}`);
  },

  evaluatePolicy: (id: string, input: Record<string, any>) => {
    return api.post<PolicyEvaluationResult>(`/policies/${id}/evaluate`, input);
  }
};

export const analysisApi = {
  detectConflict: (policyId: string) => {
    return api.post<ConflictDetectionResult>('/analysis/conflict', { policy_id: policyId });
  },

  analyzeImpact: (policyId: string) => {
    return api.post<ImpactAnalysisResult>('/analysis/impact', { policy_id: policyId });
  }
};

export const recommendationApi = {
  getRecommendations: () => {
    return api.get<{ total: number; items: PolicyRecommendation[] }>('/recommendations');
  },

  applyRecommendation: (id: string) => {
    return api.post(`/recommendations/${id}/apply`);
  }
};

export const canaryApi = {
  listDeployments: () => {
    return api.get<{ total: number; items: CanaryDeployment[] }>('/canary');
  },

  startDeployment: (policyId: string, strategy: string, duration?: string) => {
    return api.post<CanaryDeployment>('/canary/start', {
      policy_id: policyId,
      strategy,
      duration
    });
  },

  getDeployment: (policyId: string) => {
    return api.get<CanaryDeployment>(`/canary/${policyId}`);
  },

  pauseDeployment: (policyId: string) => {
    return api.post(`/canary/${policyId}/pause`);
  },

  resumeDeployment: (policyId: string) => {
    return api.post(`/canary/${policyId}/resume`);
  },

  promoteDeployment: (policyId: string) => {
    return api.post(`/canary/${policyId}/promote`);
  },

  rollbackDeployment: (policyId: string) => {
    return api.post(`/canary/${policyId}/rollback`);
  }
};

export const topologyApi = {
  getTopology: (namespaces: string[]) => {
    const params = namespaces.map(ns => `namespaces=${encodeURIComponent(ns)}`).join('&');
    return api.get<ServiceTopology>(`/topology?${params}`);
  },

  getNamespaces: () => {
    return api.get<{ namespaces: string[] }>('/topology/namespaces');
  }
};

export const opaApi = {
  listPolicies: () => {
    return api.get<{ total: number; items: any[] }>('/opa/policies');
  },

  evaluate: (policyPath: string, input: Record<string, any>) => {
    return api.post<PolicyEvaluationResult>('/opa/evaluate', {
      policy_path: policyPath,
      input
    });
  }
};

export const healthApi = {
  check: () => {
    return api.get('/health');
  }
};

export default api;

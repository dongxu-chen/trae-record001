import axios from 'axios';

const API_BASE = 'http://localhost:8080/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const healthCheck = () => api.get('/health');

export const addTrace = (trace) => api.post('/traces', trace);

export const getServiceGraph = () => api.get('/service-graph');

export const getCallRelations = () => api.get('/call-relations');

export const generatePolicies = (edges) => api.post('/policies/generate', { edges });

export const optimizePolicies = (policies) => api.post('/policies/optimize', { policies });

export const generateIstioYAML = (policy) => api.post('/policies/istio-yaml', { policy });

export const detectConflicts = (policies) => api.post('/conflicts/detect', { policies });

export const simulate = (request) => api.post('/simulate', request);

export const simulateBatch = (request) => api.post('/simulate/batch', request);

export const getCoverageReport = (policies, calls) => api.post('/coverage', { policies, calls });

export const getComplianceRules = () => api.get('/compliance/rules');

export const checkCompliance = (policies, graph) => api.post('/compliance/check', { policies, graph });

export const loadSampleData = () => api.post('/sample-data');

export const clearData = () => api.delete('/data');

export const setSamplingConfig = (config) => api.post('/sampling/config', config);

export const getSamplingStats = () => api.get('/sampling/stats');

export const detectPolicyChanges = (oldPolicies, newPolicies) => api.post('/policies/changes', { oldPolicies, newPolicies });

export const simulateIncremental = (request) => api.post('/simulate/incremental', request);

export const setSimulationBaseline = (request) => api.post('/simulate/baseline', request);

export const getComplianceScenarios = (category) => api.get(`/compliance/scenarios${category ? `?category=${category}` : ''}`);

export const checkSemanticCompliance = (policies, graph, scenarios) => api.post('/compliance/semantic', { policies, graph, scenarios });

export const deployPolicies = (request) => api.post('/deployment/deploy', request);

export const quickDeployPolicies = (targetNamespace, autoRollback, dryRun) => api.post('/deployment/quick-deploy', { targetNamespace, autoRollback, dryRun });

export const rollbackDeployment = (deploymentId) => api.post('/deployment/rollback', { deploymentId });

export const getDeployment = (id) => api.get(`/deployment/${id}`);

export const listDeployments = () => api.get('/deployments');

export const generateYAML = (policies) => api.post('/deployment/generate-yaml', { policies });

export const evaluateEffectiveness = (request) => api.post('/effectiveness/evaluate', request);

export const compareSuccessRates = (beforePolicies, afterPolicies, testRequests) => api.post('/effectiveness/compare-rates', { beforePolicies, afterPolicies, testRequests });

export const getCoverageVisualization = (policies, graph) => api.post('/visualization/coverage', { policies, graph });

export default api;

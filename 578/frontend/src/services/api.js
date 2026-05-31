import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8080/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const jobApi = {
  getAllJobs: () => api.get('/jobs'),
  analyzeJob: (jobId) => api.get(`/jobs/${jobId}/analyze`),
  getJobHistory: (jobId) => api.get(`/jobs/${jobId}/history`),
  getJobTrends: (jobId) => api.get(`/jobs/${jobId}/trends`),
  predictResourceNeeds: (jobId, loadMultiplier) =>
    api.get(`/jobs/${jobId}/predict?loadMultiplier=${loadMultiplier}`),
  getEfficiencyReport: () => api.get('/jobs/efficiency-report'),
  getMockAnalysis: () => api.get('/jobs/demo/mock-analysis'),
  getCalibrationReport: (jobId) => api.get(`/jobs/${jobId}/calibration-report`),
  getSkewDetectionReport: (jobId, vertexName) =>
    api.get(`/jobs/${jobId}/skew-detection-report?vertexName=${vertexName}`),
  getHealthScore: (jobId) => api.get(`/jobs/${jobId}/health-score`),
  getWarnings: (jobId) => api.get(`/jobs/${jobId}/warnings`),
  getHealthDashboard: (jobId) => api.get(`/jobs/${jobId}/health-dashboard`),
  getMockHealthDashboard: () => api.get('/jobs/demo/mock-health-dashboard'),
};

export const recommendationApi = {
  getRecommendation: (jobId) => api.get(`/recommendations/${jobId}`),
  applyRecommendation: (jobId, config) =>
    api.post(`/recommendations/${jobId}/apply`, config),
  getCostComparison: (jobId) => api.get(`/recommendations/${jobId}/cost-comparison`),
  getTCO: (jobId, months) => api.get(`/recommendations/${jobId}/tco?months=${months}`),
  getOptimizationTips: (jobId) => api.get(`/recommendations/${jobId}/optimization-tips`),
  getMockRecommendation: () => api.get('/recommendations/demo/mock-recommendation'),
  autoAdjust: (jobId, dryRun) =>
    api.post(`/recommendations/${jobId}/auto-adjust?dryRun=${dryRun}`),
  batchAutoAdjust: (jobIds, dryRun) =>
    api.post(`/recommendations/auto-adjust/batch?dryRun=${dryRun}`, jobIds),
  getAdjustmentPreview: (jobId) => api.get(`/recommendations/${jobId}/adjustment-preview`),
};

export const comparisonApi = {
  compareByType: (jobType) => api.get(`/jobs/comparison/by-type/${jobType}`),
  compareCustom: (jobIds) => api.post('/jobs/comparison/custom', jobIds),
  getComparisonMatrix: (jobIds) => api.post('/jobs/comparison/matrix', jobIds),
  getJobTypes: () => api.get('/jobs/comparison/types'),
  getTypeDistribution: () => api.get('/jobs/comparison/type-distribution'),
  getMockComparison: () => api.get('/jobs/comparison/demo/mock-comparison'),
};

export const costApi = {
  calculateCost: (config) => api.post('/cost/calculate', config),
  compareCosts: (current, proposed) =>
    api.post('/cost/compare', { current, proposed }),
  calculateTCO: (config, months) =>
    api.post(`/cost/tco?months=${months}`, config),
  simulateScaling: (config, factors) =>
    api.post('/cost/simulate-scaling?factors=${factors.join(',')}', config),
  getSimulatorData: () => api.get('/cost/simulator'),
  getNetworkCostReport: (jobId) =>
    jobId ? api.get(`/cost/network-report/${jobId}`) : api.get('/cost/network-report'),
};

export default api;

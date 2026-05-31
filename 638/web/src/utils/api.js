const API_BASE = '/api/v1';

async function request(url, options = {}) {
  const response = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  const data = await response.json();
  if (!data.success) throw new Error(data.error || 'API request failed');
  return data.data;
}

export const api = {
  getMetrics: (ns, deploy) => request(`/namespaces/${ns}/deployments/${deploy}/metrics`),
  getRecommendation: (ns, deploy) => request(`/namespaces/${ns}/deployments/${deploy}/recommendation`),
  getPrediction: (ns, deploy) => request(`/namespaces/${ns}/deployments/${deploy}/prediction`),
  getCost: (ns, deploy) => request(`/namespaces/${ns}/deployments/${deploy}/cost`),
  getAutotune: (ns, deploy) => request(`/namespaces/${ns}/deployments/${deploy}/autotune`),
  scale: (ns, deploy, replicas) => request(`/namespaces/${ns}/deployments/${deploy}/scale`, {
    method: 'POST',
    body: JSON.stringify({ replicas }),
  }),
  addWatch: (ns, deploy) => request(`/namespaces/${ns}/deployments/${deploy}/watch`, { method: 'POST' }),
  removeWatch: (ns, deploy) => request(`/namespaces/${ns}/deployments/${deploy}/watch`, { method: 'DELETE' }),
  getDashboard: () => request('/dashboard'),
  getHealth: () => request('/health'),
  getTuning: () => request('/tuning'),
  getTuningHistory: () => request('/tuning/history'),
  getLinkages: () => request('/linkages'),
  addLinkage: (dep) => request('/linkages', {
    method: 'POST',
    body: JSON.stringify(dep),
  }),
  getPendingLinkages: () => request('/linkages/pending'),
  getCostBenefitHistory: () => request('/cost-benefit/history'),
};

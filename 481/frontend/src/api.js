const API_BASE = '/api/health';

export async function fetchDashboard() {
  const res = await fetch(`${API_BASE}/dashboard`);
  if (!res.ok) throw new Error('Failed to fetch dashboard');
  return res.json();
}

export async function fetchAllScores() {
  const res = await fetch(`${API_BASE}/scores`);
  if (!res.ok) throw new Error('Failed to fetch scores');
  return res.json();
}

export async function fetchTaskScore(taskName) {
  const res = await fetch(`${API_BASE}/scores/${taskName}`);
  if (!res.ok) throw new Error('Failed to fetch task score');
  return res.json();
}

export async function fetchScoreTrend(taskName, hours = 24) {
  const res = await fetch(`${API_BASE}/trend/${taskName}?hours=${hours}`);
  if (!res.ok) throw new Error('Failed to fetch trend');
  return res.json();
}

export async function fetchUnhealthyTasks(threshold = 60) {
  const res = await fetch(`${API_BASE}/unhealthy?threshold=${threshold}`);
  if (!res.ok) throw new Error('Failed to fetch unhealthy tasks');
  return res.json();
}

export async function triggerCalculation() {
  const res = await fetch(`${API_BASE}/calculate`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to trigger calculation');
  return res.text();
}

export async function fetchWeightConfig(taskName) {
  const res = await fetch(`${API_BASE}/weights/${taskName}`);
  if (!res.ok && res.status !== 404) throw new Error('Failed to fetch weight config');
  return res.ok ? res.json() : null;
}

export async function saveWeightConfig(taskName, config) {
  const res = await fetch(`${API_BASE}/weights/${taskName}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error('Failed to save weight config');
  return res.json();
}

export async function fetchDefaultWeights(importance) {
  const res = await fetch(`${API_BASE}/weights/default/${importance}`);
  if (!res.ok) throw new Error('Failed to fetch default weights');
  return res.json();
}

export async function fetchDependencies(taskName) {
  const res = await fetch(`${API_BASE}/dependencies/${taskName}`);
  if (!res.ok) throw new Error('Failed to fetch dependencies');
  return res.json();
}

export async function addDependency(taskName, dependency) {
  const res = await fetch(`${API_BASE}/dependencies/${taskName}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(dependency),
  });
  if (!res.ok) throw new Error('Failed to add dependency');
  return res.json();
}

export async function fetchUpstreamIssues(taskName) {
  const res = await fetch(`${API_BASE}/upstream-issues/${taskName}`);
  if (!res.ok) throw new Error('Failed to fetch upstream issues');
  return res.json();
}

export async function fetchHealthPrediction(taskName, horizonHours = 72) {
  const res = await fetch(`${API_BASE}/predict/${taskName}?horizonHours=${horizonHours}`);
  if (!res.ok) throw new Error('Failed to fetch health prediction');
  return res.json();
}

export async function fetchPredictionHistory(taskName) {
  const res = await fetch(`${API_BASE}/predict/history/${taskName}`);
  if (!res.ok) throw new Error('Failed to fetch prediction history');
  return res.json();
}

export async function triggerAllPredictions() {
  const res = await fetch(`${API_BASE}/predict/all`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to trigger predictions');
  return res.text();
}

export async function fetchAutoRepair(taskName) {
  const res = await fetch(`${API_BASE}/auto-repair/${taskName}`);
  if (!res.ok) throw new Error('Failed to fetch auto-repair data');
  return res.json();
}

export async function fetchRepairHistory(taskName) {
  const res = await fetch(`${API_BASE}/auto-repair/history/${taskName}`);
  if (!res.ok) throw new Error('Failed to fetch repair history');
  return res.json();
}

export async function applyManualRepair(taskName, repairData) {
  const res = await fetch(`${API_BASE}/auto-repair/manual/${taskName}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(repairData),
  });
  if (!res.ok) throw new Error('Failed to apply manual repair');
  return res.json();
}

export async function updateRepairStatus(repairId, statusData) {
  const res = await fetch(`${API_BASE}/auto-repair/status/${repairId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(statusData),
  });
  if (!res.ok) throw new Error('Failed to update repair status');
  return res.text();
}

export async function triggerAutoRepairAll() {
  const res = await fetch(`${API_BASE}/auto-repair/all`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to trigger auto-repair for all tasks');
  return res.text();
}

export async function fetchSlaPrediction(taskName, slaTarget = 80) {
  const res = await fetch(`${API_BASE}/sla/${taskName}?slaTarget=${slaTarget}`);
  if (!res.ok) throw new Error('Failed to fetch SLA prediction');
  return res.json();
}

export async function fetchSlaHistory(taskName) {
  const res = await fetch(`${API_BASE}/sla/history/${taskName}`);
  if (!res.ok) throw new Error('Failed to fetch SLA history');
  return res.json();
}

export async function triggerSlaPredictionAll() {
  const res = await fetch(`${API_BASE}/sla/all`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to trigger SLA prediction for all tasks');
  return res.text();
}

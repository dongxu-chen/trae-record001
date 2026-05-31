const API_BASE = '/api/v1';

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const resp = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  const data = await resp.json();
  if (!data.success) throw new Error(data.message || 'Request failed');
  return data.data;
}

export const cacheApi = {
  list: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/caches${qs ? '?' + qs : ''}`);
  },
  get: (id) => request(`/caches/${id}`),
  create: (entry) => request('/caches', { method: 'POST', body: JSON.stringify(entry) }),
  createWithDeps: (entry, fileContents) => request('/caches/with-deps', {
    method: 'POST',
    body: JSON.stringify({ entry, file_contents: fileContents }),
  }),
  delete: (id) => request(`/caches/${id}`, { method: 'DELETE' }),
  download: (id) => `${API_BASE}/caches/${id}/download`,
  recordAccess: (id) => request(`/caches/${id}/access`, { method: 'POST' }),
  checkDeps: (cacheType, jobName, fileContents) => request('/caches/check-deps', {
    method: 'POST',
    body: JSON.stringify({ cache_type: cacheType, job_name: jobName, file_contents: fileContents }),
  }),
  upload: async (formData) => {
    const resp = await fetch(`${API_BASE}/caches/upload`, {
      method: 'POST',
      body: formData,
    });
    const data = await resp.json();
    if (!data.success) throw new Error(data.message);
    return data.data;
  },
  uploadWithDeps: async (formData) => {
    const resp = await fetch(`${API_BASE}/caches/upload-with-deps`, {
      method: 'POST',
      body: formData,
    });
    const data = await resp.json();
    if (!data.success) throw new Error(data.message);
    return data.data;
  },
};

export const versionApi = {
  list: (type = '') => {
    const qs = type ? `?type=${type}` : '';
    return request(`/versions${qs}`);
  },
  promote: (type, version) => request(`/versions/${type}/promote`, {
    method: 'POST',
    body: JSON.stringify({ version }),
  }),
};

export const warmupApi = {
  create: (task) => request('/warmup', { method: 'POST', body: JSON.stringify(task) }),
  list: () => request('/warmup'),
  get: (id) => request(`/warmup/${id}`),
  fromJenkins: (params) => request('/warmup/jenkins', { method: 'POST', body: JSON.stringify(params) }),
  checkAndTrigger: (params) => request('/warmup/check-and-trigger', {
    method: 'POST',
    body: JSON.stringify(params),
  }),
  listDependencyEvents: (cacheType = '', jobName = '') => {
    const params = new URLSearchParams();
    if (cacheType) params.set('type', cacheType);
    if (jobName) params.set('job', jobName);
    const qs = params.toString();
    return request(`/warmup/dependency-events${qs ? '?' + qs : ''}`);
  },
  setAutoWarmup: (enabled) => request('/warmup/auto-warmup', {
    method: 'POST',
    body: JSON.stringify({ enabled }),
  }),
};

export const cleanupApi = {
  listPolicies: () => request('/cleanup/policies'),
  getPolicy: (id) => request(`/cleanup/policies/${id}`),
  createPolicy: (policy) => request('/cleanup/policies', { method: 'POST', body: JSON.stringify(policy) }),
  updatePolicy: (id, updates) => request(`/cleanup/policies/${id}`, { method: 'PUT', body: JSON.stringify(updates) }),
  deletePolicy: (id) => request(`/cleanup/policies/${id}`, { method: 'DELETE' }),
  executePolicy: (id) => request(`/cleanup/policies/${id}/execute`, { method: 'POST' }),
  listResults: () => request('/cleanup/results'),
  evictBySize: (cacheType, maxSize) => request('/cleanup/evict', {
    method: 'POST',
    body: JSON.stringify({ cache_type: cacheType, max_size: maxSize }),
  }),
};

export const jenkinsApi = {
  listJobs: () => request('/jenkins/jobs'),
  getBuild: (name, number) => request(`/jenkins/jobs/${name}/builds/${number}`),
  getLatestBuild: (name) => request(`/jenkins/jobs/${name}/latest`),
  triggerBuild: (name, parameters = {}) => request(`/jenkins/jobs/${name}/trigger`, {
    method: 'POST',
    body: JSON.stringify({ parameters }),
  }),
  testConnection: () => request('/jenkins/test'),
};

export const dependencyApi = {
  computeHash: (params) => request('/dependencies/hash', {
    method: 'POST',
    body: JSON.stringify(params),
  }),
  getLatestHash: (cacheType, jobName) => {
    const qs = new URLSearchParams({ type: cacheType, job: jobName }).toString();
    return request(`/dependencies/latest-hash?${qs}`);
  },
  getPatterns: (cacheType = '') => {
    const qs = cacheType ? `?type=${cacheType}` : '';
    return request(`/dependencies/patterns${qs}`);
  },
};

export const statsApi = {
  get: () => request('/stats'),
};

export const healthApi = {
  check: () => request('/health'),
};

export const groupsApi = {
  list: () => request('/groups'),
  get: (id) => request(`/groups/${id}`),
  create: (group) => request('/groups', { method: 'POST', body: JSON.stringify(group) }),
  update: (id, updates) => request(`/groups/${id}`, { method: 'PUT', body: JSON.stringify(updates) }),
  delete: (id) => request(`/groups/${id}`, { method: 'DELETE' }),
  addJob: (id, jobName) => request(`/groups/${id}/jobs`, {
    method: 'POST',
    body: JSON.stringify({ job_name: jobName }),
  }),
  removeJob: (id, jobName) => request(`/groups/${id}/jobs/${jobName}`, { method: 'DELETE' }),
};

export const sharingApi = {
  findSimilar: (params) => request('/sharing/find-similar', {
    method: 'POST',
    body: JSON.stringify(params),
  }),
  getGroupsForJob: (jobName) => request(`/sharing/job/${jobName}`),
};

export const hitsApi = {
  record: (params) => request('/hits', { method: 'POST', body: JSON.stringify(params) }),
  list: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/hits${qs ? '?' + qs : ''}`);
  },
  getStats: (cacheType = '', jobName = '', timeRange = '24h') => {
    const qs = new URLSearchParams({
      type: cacheType,
      job: jobName,
      range: timeRange,
    }).toString();
    return request(`/hits/stats?${qs}`);
  },
  getBuildHits: (jobName, buildNumber) => request(`/hits/build/${jobName}/${buildNumber}`),
  getTopMissed: (cacheType = '', jobName = '', limit = 20) => {
    const qs = new URLSearchParams({
      type: cacheType,
      job: jobName,
      limit: limit.toString(),
    }).toString();
    return request(`/hits/missed?${qs}`);
  },
  cleanOld: (maxAge = '720h') => {
    const qs = new URLSearchParams({ max_age: maxAge }).toString();
    return request(`/hits/clean?${qs}`, { method: 'DELETE' });
  },
};

export const backendsApi = {
  list: () => request('/backends'),
  add: (backend) => request('/backends', { method: 'POST', body: JSON.stringify(backend) }),
  remove: (id) => request(`/backends/${id}`, { method: 'DELETE' }),
};

export const migrationApi = {
  listTasks: () => request('/migration/tasks'),
  getTask: (id) => request(`/migration/tasks/${id}`),
  createTask: (task) => request('/migration/tasks', {
    method: 'POST',
    body: JSON.stringify(task),
  }),
  startTask: (id) => request(`/migration/tasks/${id}/start`, { method: 'POST' }),
  pauseTask: (id) => request(`/migration/tasks/${id}/pause`, { method: 'POST' }),
  resumeTask: (id) => request(`/migration/tasks/${id}/resume`, { method: 'POST' }),
  cancelTask: (id) => request(`/migration/tasks/${id}/cancel`, { method: 'POST' }),
  getProgress: (id) => request(`/migration/tasks/${id}/progress`),
};

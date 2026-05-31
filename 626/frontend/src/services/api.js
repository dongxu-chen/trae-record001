import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

export const tenantApi = {
  create: (data) => api.post('/tenant', data),
  get: (tenantId) => api.get(`/tenant/${tenantId}`),
  update: (data) => api.put('/tenant', data),
  delete: (tenantId) => api.delete(`/tenant/${tenantId}`),
  list: () => api.get('/tenant/list'),
  getUsage: (tenantId) => api.get(`/tenant/${tenantId}/usage`),
  getWarnings: (tenantId) => api.get(`/tenant/${tenantId}/warnings`),
  transferTry: (data) => api.post('/tenant/transfer/try', data),
  transferConfirm: (data) => api.post('/tenant/transfer/confirm', data),
  transferCancel: (data) => api.post('/tenant/transfer/cancel', data),
  getTransferTransaction: (txId) => api.get(`/tenant/transfer/${txId}`),
  preConsume: (data) => api.post('/tenant/preconsume', data),
  release: (data) => api.post('/tenant/release', data),
  confirm: (data) => api.post('/tenant/confirm', data),
};

export const poolApi = {
  create: (data) => api.post('/pool', data),
  get: (poolId) => api.get(`/pool/${poolId}`),
  update: (data) => api.put('/pool', data),
  delete: (poolId) => api.delete(`/pool/${poolId}`),
  list: () => api.get('/pool/list'),
  addMember: (poolId, data) => api.post(`/pool/${poolId}/member`, data),
  removeMember: (poolId, tenantId) => api.delete(`/pool/${poolId}/member/${tenantId}`),
  getMembers: (poolId) => api.get(`/pool/${poolId}/members`),
  getStats: (poolId) => api.get(`/pool/${poolId}/stats`),
  consume: (poolId, data) => api.post(`/pool/${poolId}/consume`, data),
};

export const marketApi = {
  placeSell: (data) => api.post('/market/sell', data),
  placeBuy: (data) => api.post('/market/buy', data),
  cancel: (orderId) => api.post(`/market/cancel/${orderId}`),
  getOrder: (orderId) => api.get(`/market/order/${orderId}`),
  getMyOrders: (tenantId) => api.get(`/market/orders/${tenantId}`),
  getSellOrderBook: (granularity) => api.get(`/market/orderbook/${granularity}/sell`),
  getBuyOrderBook: (granularity) => api.get(`/market/orderbook/${granularity}/buy`),
  getRecentTrades: (granularity, limit) => api.get(`/market/trades/${granularity}?limit=${limit || 50}`),
  getStats: (granularity) => api.get(`/market/stats/${granularity}`),
};

export const profileApi = {
  get: (tenantId, refresh) => api.get(`/profile/${tenantId}?refresh=${refresh || false}`),
  generate: (tenantId) => api.get(`/profile/${tenantId}/generate`),
  getHistory: (tenantId, granularity, limit) => api.get(`/profile/${tenantId}/history/${granularity}?limit=${limit || 100}`),
};

export const rateLimitApi = {
  check: (data) => api.post('/ratelimit/check', data),
};

export default api;

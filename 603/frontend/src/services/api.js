import axios from 'axios';

const API_BASE = '/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
});

export const healthCheck = () => api.get('/health');

export const getTopics = () => api.get('/topics');
export const addTopic = (topic) => api.post('/topics', { topic });
export const removeTopic = (topic) => api.delete(`/topics/${topic}`);

export const getBacklogs = () => api.get('/topics/backlog');
export const getBacklogHistory = (topic, subscription = 'default') =>
  api.get(`/topics/${topic}/history?subscription=${subscription}`);

export const getConsumerCount = (topic, subscription) =>
  api.get(`/autoscale/${topic}/${subscription}`);
export const setConsumerCount = (topic, subscription, count) =>
  api.post(`/autoscale/${topic}/${subscription}`, { count });
export const getScaleState = (topic, subscription) =>
  api.get(`/autoscale/${topic}/${subscription}/state`);

export const getPartitionCount = (topic) => api.get(`/partitions/${topic}`);
export const setPartitionCount = (topic, count) =>
  api.post(`/partitions/${topic}`, { count });

export const getRateLimit = (topic) => api.get(`/ratelimit/${topic}`);
export const setRateLimit = (topic, rate) =>
  api.post(`/ratelimit/${topic}`, { rate });
export const setSubscriptionRateLimit = (topic, subscription, rate) =>
  api.post(`/ratelimit/${topic}/subscription/${subscription}`, { rate });
export const getSubscriptionRateLimit = (topic, subscription) =>
  api.get(`/ratelimit/${topic}/subscription/${subscription}`);
export const getThrottleStatus = (topic) =>
  api.get(`/ratelimit/${topic}/status`);

export const getPrediction = (topic) => api.get(`/predictions/${topic}`);

export const getStrategies = () => api.get('/strategies');
export const getStrategy = (topic) => api.get(`/strategies/${topic}`);
export const setStrategy = (strategy) => api.post('/strategies', strategy);
export const deleteStrategy = (topic) => api.delete(`/strategies/${topic}`);

export const getAuditLogs = () => api.get('/audit');
export const getAuditLogsByTopic = (topic) => api.get(`/audit/topic/${topic}`);

export const getDLQAllStats = () => api.get('/dlq/stats');
export const getDLQStats = (topic, subscription) =>
  api.get(`/dlq/stats/${topic}/${subscription}`);
export const configureDLQ = (topic, subscription, config) =>
  api.post(`/dlq/config/${topic}/${subscription}`, config);
export const retryFromDLQ = (topic, subscription, maxMessages = 100) =>
  api.post(`/dlq/retry/${topic}/${subscription}`, { max_messages: maxMessages });
export const enableDLQ = (topic, subscription) =>
  api.post(`/dlq/enable/${topic}/${subscription}`);
export const disableDLQ = (topic, subscription) =>
  api.post(`/dlq/disable/${topic}/${subscription}`);

export const replayMessages = (req) => api.post('/replay', req);
export const replayLastN = (topic, count, targetTopic = '') =>
  api.post(`/replay/last/${topic}`, { count, target_topic: targetTopic });
export const getReplayStatus = (topic) => api.get(`/replay/status/${topic}`);
export const getReplayHistory = (topic = '') =>
  api.get(`/replay/history${topic ? `?topic=${topic}` : ''}`);
export const cancelReplay = (topic) => api.post(`/replay/cancel/${topic}`);

export const getDelayAllStats = () => api.get('/delay/stats');
export const getDelayStats = (topic) => api.get(`/delay/stats/${topic}`);
export const registerSubscription = (topic, subscription, priority) =>
  api.post(`/delay/register/${topic}/${subscription}`, { priority });
export const pauseSubscription = (topic, subscription) =>
  api.post(`/delay/pause/${topic}/${subscription}`);
export const resumeSubscription = (topic, subscription) =>
  api.post(`/delay/resume/${topic}/${subscription}`);

export default api;

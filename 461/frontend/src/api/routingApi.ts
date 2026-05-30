import { httpGet, httpPost, httpPut, httpDelete } from './request';
import type { RoutingRule, RoutingMetric, PageResult } from '../types';

const BASE_URL = '/api/routing-manager/rules';
const METRICS_URL = '/api/routing-manager/metrics';

const mockRoutingRules: RoutingRule[] = [
  {
    id: '1',
    apiName: '用户服务',
    versionWeights: { v1: 30, v2: 70 },
    strategy: 'WEIGHTED',
    grayStrategy: {
      type: 'USER_ID',
      includeList: ['1001', '1002', '1003'],
      excludeList: ['9999']
    },
    createdAt: '2024-03-15T10:00:00Z',
    enabled: true
  },
  {
    id: '2',
    apiName: '订单服务',
    versionWeights: { v1: 0, v2: 100 },
    strategy: 'PATH',
    matchExpression: '/api/v2/orders/**',
    createdAt: '2024-04-01T09:00:00Z',
    enabled: true
  },
  {
    id: '3',
    apiName: '商品服务',
    versionWeights: { v1: 50, v2: 50 },
    strategy: 'HEADER',
    matchExpression: 'X-API-Version=v2',
    grayStrategy: {
      type: 'WEIGHT',
      weight: 20
    },
    createdAt: '2024-04-20T14:30:00Z',
    enabled: true
  },
  {
    id: '4',
    apiName: '支付服务',
    versionWeights: { v1: 100, v2: 0 },
    strategy: 'QUERY',
    matchExpression: 'apiVersion=v1',
    createdAt: '2024-05-10T11:00:00Z',
    enabled: false
  },
  {
    id: '5',
    apiName: '通知服务',
    versionWeights: { v1: 10, v2: 90 },
    strategy: 'WEIGHTED',
    grayStrategy: {
      type: 'IP',
      includeList: ['192.168.1.0/24', '10.0.0.0/8'],
      weight: 30
    },
    createdAt: '2024-05-20T16:45:00Z',
    enabled: true
  }
];

const mockMetrics: RoutingMetric[] = [
  {
    apiName: '用户服务',
    totalRequests: 125680,
    v1Requests: 37704,
    v2Requests: 87976,
    successRate: 99.8,
    avgResponseTime: 45
  },
  {
    apiName: '订单服务',
    totalRequests: 89450,
    v1Requests: 0,
    v2Requests: 89450,
    successRate: 99.5,
    avgResponseTime: 78
  },
  {
    apiName: '商品服务',
    totalRequests: 234560,
    v1Requests: 117280,
    v2Requests: 117280,
    successRate: 99.9,
    avgResponseTime: 32
  },
  {
    apiName: '支付服务',
    totalRequests: 45230,
    v1Requests: 45230,
    v2Requests: 0,
    successRate: 99.7,
    avgResponseTime: 120
  },
  {
    apiName: '通知服务',
    totalRequests: 67890,
    v1Requests: 6789,
    v2Requests: 61101,
    successRate: 98.9,
    avgResponseTime: 56
  }
];

const delay = <T>(data: T, ms = 300): Promise<T> => {
  return new Promise((resolve) => setTimeout(() => resolve(data), ms));
};

export const getRoutingRules = async (params?: {
  page?: number;
  pageSize?: number;
  apiName?: string;
  enabled?: boolean;
}): Promise<PageResult<RoutingRule>> => {
  let filtered = [...mockRoutingRules];
  if (params?.apiName) {
    filtered = filtered.filter((r) => r.apiName.includes(params.apiName!));
  }
  if (params?.enabled !== undefined) {
    filtered = filtered.filter((r) => r.enabled === params.enabled);
  }

  const page = params?.page || 1;
  const pageSize = params?.pageSize || 10;
  const start = (page - 1) * pageSize;
  const end = start + pageSize;

  return delay({
    list: filtered.slice(start, end),
    total: filtered.length,
    page,
    pageSize
  });
};

export const getRoutingRuleDetail = async (id: string): Promise<RoutingRule> => {
  const rule = mockRoutingRules.find((r) => r.id === id);
  if (!rule) {
    throw new Error('路由规则不存在');
  }
  return delay(rule);
};

export const createRoutingRule = async (data: Partial<RoutingRule>): Promise<RoutingRule> => {
  const newRule: RoutingRule = {
    id: String(mockRoutingRules.length + 1),
    apiName: data.apiName || '',
    versionWeights: data.versionWeights || { v1: 50, v2: 50 },
    strategy: data.strategy || 'PATH',
    matchExpression: data.matchExpression,
    grayStrategy: data.grayStrategy,
    createdAt: new Date().toISOString(),
    enabled: data.enabled ?? true
  };
  mockRoutingRules.push(newRule);
  return delay(newRule, 500);
};

export const updateRoutingRule = async (id: string, data: Partial<RoutingRule>): Promise<RoutingRule> => {
  const index = mockRoutingRules.findIndex((r) => r.id === id);
  if (index === -1) {
    throw new Error('路由规则不存在');
  }
  mockRoutingRules[index] = {
    ...mockRoutingRules[index],
    ...data
  };
  return delay(mockRoutingRules[index], 500);
};

export const deleteRoutingRule = async (id: string): Promise<void> => {
  const index = mockRoutingRules.findIndex((r) => r.id === id);
  if (index === -1) {
    throw new Error('路由规则不存在');
  }
  mockRoutingRules.splice(index, 1);
  return delay(undefined, 300);
};

export const getRoutingMetrics = async (): Promise<RoutingMetric[]> => {
  return delay(mockMetrics);
};

export const routingApi = {
  getList: (params?: Parameters<typeof getRoutingRules>[0]) => httpGet<PageResult<RoutingRule>>(BASE_URL, { params }).catch(() => getRoutingRules(params)),
  getDetail: (id: string) => httpGet<RoutingRule>(`${BASE_URL}/${id}`).catch(() => getRoutingRuleDetail(id)),
  create: (data: Partial<RoutingRule>) => httpPost<RoutingRule>(BASE_URL, data).catch(() => createRoutingRule(data)),
  update: (id: string, data: Partial<RoutingRule>) => httpPut<RoutingRule>(`${BASE_URL}/${id}`, data).catch(() => updateRoutingRule(id, data)),
  delete: (id: string) => httpDelete<void>(`${BASE_URL}/${id}`).catch(() => deleteRoutingRule(id)),
  getMetrics: () => httpGet<RoutingMetric[]>(METRICS_URL).catch(() => getRoutingMetrics())
};

export default routingApi;

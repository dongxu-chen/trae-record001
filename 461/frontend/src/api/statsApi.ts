import { httpGet, httpPost } from './request';
import type { VersionStatsData, DeprecatedVersionSchedule } from '../types';

const BASE_URL = '/api/version-manager/versions';

const delay = <T>(data: T, ms = 300): Promise<T> => {
  return new Promise((resolve) => setTimeout(() => resolve(data), ms));
};

const mockVersionStats: VersionStatsData = {
  versions: [
    {
      serviceName: '用户服务',
      version: 'v1.0.0',
      callCount: 125000,
      successCount: 123500,
      failCount: 1500,
      avgResponseTime: 45,
      percentage: 35.2,
    },
    {
      serviceName: '用户服务',
      version: 'v2.0.0',
      callCount: 98500,
      successCount: 97800,
      failCount: 700,
      avgResponseTime: 52,
      percentage: 27.7,
    },
    {
      serviceName: '订单服务',
      version: 'v2.1.0',
      callCount: 75000,
      successCount: 74200,
      failCount: 800,
      avgResponseTime: 89,
      percentage: 21.1,
    },
    {
      serviceName: '订单服务',
      version: 'v1.5.0',
      callCount: 38000,
      successCount: 36500,
      failCount: 1500,
      avgResponseTime: 120,
      percentage: 10.7,
    },
    {
      serviceName: '支付服务',
      version: 'v3.0.0-beta',
      callCount: 19000,
      successCount: 18200,
      failCount: 800,
      avgResponseTime: 156,
      percentage: 5.3,
    },
  ],
  totalCalls: 355500,
  trendData: {
    dates: ['05-22', '05-23', '05-24', '05-25', '05-26', '05-27', '05-28'],
    versions: {
      'v1.0.0': [42000, 41000, 40000, 39000, 38000, 36000, 34000],
      'v2.0.0': [12000, 15000, 18000, 22000, 26000, 30000, 35000],
      'v2.1.0': [8000, 10000, 12000, 14000, 16000, 18000, 20000],
      'v1.5.0': [15000, 14000, 13000, 12000, 11000, 10000, 9000],
    },
  },
};

const mockDeprecatedSchedules: DeprecatedVersionSchedule[] = [
  {
    id: '4',
    serviceName: '订单服务',
    version: 'v2.0.0',
    status: 'DEPRECATED',
    deprecateTime: '2024-06-01T00:00:00Z',
    plannedRetireTime: '2026-06-28T00:00:00Z',
    deprecationMessage: '该版本将于30天后下线，请尽快升级到v2.1.0版本',
    daysRemaining: 30,
  },
  {
    id: '6',
    serviceName: '用户服务',
    version: 'v1.0.0',
    status: 'DEPRECATED',
    deprecateTime: '2024-03-15T00:00:00Z',
    plannedRetireTime: '2026-08-15T00:00:00Z',
    deprecationMessage: '该版本将于78天后下线，请尽快升级到v2.0.0版本',
    daysRemaining: 78,
  },
  {
    id: '7',
    serviceName: '支付服务',
    version: 'v1.0.0',
    status: 'OFFLINE',
    deprecateTime: '2024-01-01T00:00:00Z',
    plannedRetireTime: '2026-05-20T00:00:00Z',
    deprecationMessage: '该版本已超期下线，所有请求将被拒绝',
    daysRemaining: -8,
  },
];

export const getVersionStats = async (params?: {
  serviceName?: string;
  startDate?: string;
  endDate?: string;
}): Promise<VersionStatsData> => {
  return httpGet<VersionStatsData>(`${BASE_URL}/stats`, { params }).catch(() => delay(mockVersionStats));
};

export const getDeprecatedVersions = async (): Promise<DeprecatedVersionSchedule[]> => {
  return httpGet<DeprecatedVersionSchedule[]>(`${BASE_URL}/deprecated`).catch(() => delay(mockDeprecatedSchedules));
};

export const updateDeprecationSchedule = async (
  id: string,
  data: { plannedRetireTime: string; deprecationMessage: string }
): Promise<void> => {
  return httpPost<void>(`${BASE_URL}/${id}/deprecation-schedule`, data).catch(() => delay(undefined));
};

export const syncDeprecationConfig = async (id: string): Promise<void> => {
  return httpPost<void>(`${BASE_URL}/${id}/sync-deprecation-config`).catch(() => delay(undefined));
};

export const statsApi = {
  getVersionStats,
  getDeprecatedVersions,
  updateDeprecationSchedule,
  syncDeprecationConfig,
};

export default statsApi;

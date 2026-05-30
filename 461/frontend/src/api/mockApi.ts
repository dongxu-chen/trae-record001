import { httpGet, httpPost, httpPut, httpDelete } from './request';
import type { MockVersionConfig, MockType } from '../types';

const BASE_URL = '/api/version-manager/mock-configs';

const delay = <T>(data: T, ms = 300): Promise<T> => {
  return new Promise((resolve) => setTimeout(() => resolve(data), ms));
};

const mockConfigs: MockVersionConfig[] = [
  {
    id: '1',
    versionId: '6',
    path: '/api/v1/users/{id}',
    method: 'GET',
    mockType: 'SUCCESS',
    delayMs: 0,
    errorCode: 200,
    customResponse: '{"id":1,"name":"Mock User","email":"mock@example.com","createdAt":"2024-01-01T00:00:00"}',
    enabled: true,
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
  {
    id: '2',
    versionId: '6',
    path: '/api/v1/users',
    method: 'POST',
    mockType: 'DELAY',
    delayMs: 2000,
    errorCode: 200,
    customResponse: '{"id":2,"name":"New User"}',
    enabled: true,
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
  {
    id: '3',
    versionId: '6',
    path: '/api/v1/users/{id}',
    method: 'PUT',
    mockType: 'ERROR',
    delayMs: 0,
    errorCode: 500,
    errorMessage: '服务器内部错误-Mock模拟',
    enabled: true,
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
  {
    id: '4',
    versionId: '7',
    path: '/api/v1/orders/{id}',
    method: 'GET',
    mockType: 'CUSTOM',
    delayMs: 500,
    errorCode: 200,
    customResponse: '{"id":1,"orderNo":"ORD-MOCK-001","status":"PENDING","totalAmount":99.99}',
    enabled: true,
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
];

export const getMockConfigsByVersionId = async (versionId: string): Promise<MockVersionConfig[]> => {
  return httpGet<MockVersionConfig[]>(`${BASE_URL}/version/${versionId}`)
    .catch(() => delay(mockConfigs.filter(c => c.versionId === versionId)));
};

export const getMockConfigById = async (id: string): Promise<MockVersionConfig> => {
  return httpGet<MockVersionConfig>(`${BASE_URL}/${id}`)
    .catch(() => {
      const config = mockConfigs.find(c => c.id === id);
      if (!config) throw new Error('Mock配置不存在');
      return delay(config);
    });
};

export const createMockConfig = async (data: Partial<MockVersionConfig>): Promise<MockVersionConfig> => {
  return httpPost<MockVersionConfig>(BASE_URL, data)
    .catch(() => {
      const newConfig: MockVersionConfig = {
        id: String(mockConfigs.length + 1),
        versionId: data.versionId || '',
        path: data.path || '',
        method: data.method || 'GET',
        mockType: data.mockType || 'SUCCESS',
        delayMs: data.delayMs || 0,
        errorCode: data.errorCode || 200,
        errorMessage: data.errorMessage,
        customResponse: data.customResponse,
        enabled: data.enabled !== false,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      mockConfigs.push(newConfig);
      return delay(newConfig, 500);
    });
};

export const updateMockConfig = async (id: string, data: Partial<MockVersionConfig>): Promise<MockVersionConfig> => {
  return httpPut<MockVersionConfig>(BASE_URL, { ...data, id })
    .catch(() => {
      const index = mockConfigs.findIndex(c => c.id === id);
      if (index === -1) throw new Error('Mock配置不存在');
      mockConfigs[index] = {
        ...mockConfigs[index],
        ...data,
        updatedAt: new Date().toISOString(),
      };
      return delay(mockConfigs[index], 500);
    });
};

export const deleteMockConfig = async (id: string): Promise<void> => {
  return httpDelete<void>(`${BASE_URL}/${id}`)
    .catch(() => {
      const index = mockConfigs.findIndex(c => c.id === id);
      if (index === -1) throw new Error('Mock配置不存在');
      mockConfigs.splice(index, 1);
      return delay(undefined, 300);
    });
};

export const toggleMockConfig = async (id: string, enabled: boolean): Promise<MockVersionConfig> => {
  return httpPost<MockVersionConfig>(`${BASE_URL}/${id}/toggle`, {}, { params: { enabled } })
    .catch(() => {
      const config = mockConfigs.find(c => c.id === id);
      if (!config) throw new Error('Mock配置不存在');
      config.enabled = enabled;
      config.updatedAt = new Date().toISOString();
      return delay(config, 300);
    });
};

export const syncMockConfig = async (id: string): Promise<void> => {
  return httpPost<void>(`${BASE_URL}/${id}/sync`)
    .catch(() => delay(undefined, 300));
};

export const getAllEnabledMockConfigs = async (): Promise<MockVersionConfig[]> => {
  return httpGet<MockVersionConfig[]>(`${BASE_URL}/enabled`)
    .catch(() => delay(mockConfigs.filter(c => c.enabled)));
};

export const mockApi = {
  getByVersionId: getMockConfigsByVersionId,
  getById: getMockConfigById,
  create: createMockConfig,
  update: updateMockConfig,
  delete: deleteMockConfig,
  toggle: toggleMockConfig,
  sync: syncMockConfig,
  getAllEnabled: getAllEnabledMockConfigs,
};

export default mockApi;

import { httpGet, httpPost, httpPut, httpDelete } from './request';
import type { ApiVersion, ApiVersionStatus, PageResult } from '../types';

const BASE_URL = '/api/version-manager/versions';

const mockVersions: ApiVersion[] = [
  {
    id: '1',
    name: '用户服务',
    version: 'v1',
    status: 'ACTIVE',
    description: '用户服务v1版本，提供基础用户管理功能',
    basePath: '/api/v1',
    openApiSpec: JSON.stringify({
      openapi: '3.0.0',
      info: { title: '用户服务 v1', version: '1.0.0' },
      paths: {
        '/users': {
          get: { summary: '获取用户列表', responses: { '200': { description: '成功' } } },
          post: { summary: '创建用户', responses: { '200': { description: '成功' } } }
        },
        '/users/{id}': {
          get: { summary: '获取用户详情', responses: { '200': { description: '成功' } } },
          put: { summary: '更新用户', responses: { '200': { description: '成功' } } },
          delete: { summary: '删除用户', responses: { '200': { description: '成功' } } }
        }
      }
    }),
    createdAt: '2024-01-15T10:00:00Z',
    updatedAt: '2024-03-20T14:30:00Z'
  },
  {
    id: '2',
    name: '用户服务',
    version: 'v2',
    status: 'ACTIVE',
    description: '用户服务v2版本，新增用户等级和积分系统',
    basePath: '/api/v2',
    openApiSpec: JSON.stringify({
      openapi: '3.0.0',
      info: { title: '用户服务 v2', version: '2.0.0' },
      paths: {
        '/users': {
          get: { summary: '获取用户列表（支持分页）', responses: { '200': { description: '成功' } } },
          post: { summary: '创建用户（必填手机号）', responses: { '200': { description: '成功' } } }
        },
        '/users/{id}': {
          get: { summary: '获取用户详情（含等级信息）', responses: { '200': { description: '成功' } } },
          put: { summary: '更新用户信息', responses: { '200': { description: '成功' } } },
          delete: { summary: '删除用户', responses: { '200': { description: '成功' } } }
        },
        '/users/{id}/points': {
          get: { summary: '获取用户积分', responses: { '200': { description: '成功' } } },
          post: { summary: '调整用户积分', responses: { '200': { description: '成功' } } }
        }
      }
    }),
    createdAt: '2024-03-01T09:00:00Z',
    updatedAt: '2024-05-10T11:20:00Z'
  },
  {
    id: '3',
    name: '订单服务',
    version: 'v1',
    status: 'ACTIVE',
    description: '订单服务v1版本，提供基础订单管理功能',
    basePath: '/api/v1',
    openApiSpec: JSON.stringify({
      openapi: '3.0.0',
      info: { title: '订单服务 v1', version: '1.0.0' },
      paths: {
        '/orders': {
          get: { summary: '获取订单列表', responses: { '200': { description: '成功' } } },
          post: { summary: '创建订单', responses: { '200': { description: '成功' } } }
        },
        '/orders/{id}': {
          get: { summary: '获取订单详情', responses: { '200': { description: '成功' } } },
          put: { summary: '更新订单', responses: { '200': { description: '成功' } } }
        }
      }
    }),
    createdAt: '2024-02-10T15:00:00Z',
    updatedAt: '2024-04-15T16:45:00Z'
  },
  {
    id: '4',
    name: '订单服务',
    version: 'v2',
    status: 'DEPRECATED',
    description: '订单服务v2版本，待废弃，请使用v3版本',
    basePath: '/api/v2',
    openApiSpec: JSON.stringify({
      openapi: '3.0.0',
      info: { title: '订单服务 v2', version: '2.0.0' },
      paths: {
        '/orders': {
          get: { summary: '获取订单列表', deprecated: true, responses: { '200': { description: '成功' } } }
        }
      }
    }),
    createdAt: '2024-04-01T08:30:00Z',
    updatedAt: '2024-06-01T10:00:00Z',
    deprecatedAt: '2024-06-01T00:00:00Z',
    retireAt: '2024-12-01T00:00:00Z'
  },
  {
    id: '5',
    name: '支付服务',
    version: 'v1',
    status: 'DRAFT',
    description: '支付服务v1版本，开发中',
    basePath: '/api/v1',
    openApiSpec: JSON.stringify({
      openapi: '3.0.0',
      info: { title: '支付服务 v1', version: '1.0.0' },
      paths: {}
    }),
    createdAt: '2024-05-20T13:00:00Z',
    updatedAt: '2024-05-25T09:15:00Z'
  }
];

const delay = <T>(data: T, ms = 300): Promise<T> => {
  return new Promise((resolve) => setTimeout(() => resolve(data), ms));
};

export const getVersionList = async (params?: {
  page?: number;
  pageSize?: number;
  name?: string;
  status?: ApiVersionStatus;
}): Promise<PageResult<ApiVersion>> => {
  let filtered = [...mockVersions];
  if (params?.name) {
    filtered = filtered.filter((v) => v.name.includes(params.name!));
  }
  if (params?.status) {
    filtered = filtered.filter((v) => v.status === params.status);
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

export const getVersionDetail = async (id: string): Promise<ApiVersion> => {
  const version = mockVersions.find((v) => v.id === id);
  if (!version) {
    throw new Error('版本不存在');
  }
  return delay(version);
};

export const createVersion = async (data: Partial<ApiVersion>): Promise<ApiVersion> => {
  const newVersion: ApiVersion = {
    id: String(mockVersions.length + 1),
    name: data.name || '',
    version: data.version || 'v1',
    status: data.status || 'DRAFT',
    description: data.description || '',
    basePath: data.basePath || '/api/v1',
    openApiSpec: data.openApiSpec || JSON.stringify({
      openapi: '3.0.0',
      info: { title: data.name, version: data.version },
      paths: {}
    }),
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    deprecatedAt: data.deprecatedAt,
    retireAt: data.retireAt
  };
  mockVersions.push(newVersion);
  return delay(newVersion, 500);
};

export const updateVersion = async (id: string, data: Partial<ApiVersion>): Promise<ApiVersion> => {
  const index = mockVersions.findIndex((v) => v.id === id);
  if (index === -1) {
    throw new Error('版本不存在');
  }
  mockVersions[index] = {
    ...mockVersions[index],
    ...data,
    updatedAt: new Date().toISOString()
  };
  return delay(mockVersions[index], 500);
};

export const deleteVersion = async (id: string): Promise<void> => {
  const index = mockVersions.findIndex((v) => v.id === id);
  if (index === -1) {
    throw new Error('版本不存在');
  }
  mockVersions.splice(index, 1);
  return delay(undefined, 300);
};

export const publishVersion = async (id: string): Promise<ApiVersion> => {
  const version = mockVersions.find((v) => v.id === id);
  if (!version) {
    throw new Error('版本不存在');
  }
  version.status = 'ACTIVE';
  version.updatedAt = new Date().toISOString();
  return delay(version, 500);
};

export const deprecateVersion = async (id: string): Promise<ApiVersion> => {
  const version = mockVersions.find((v) => v.id === id);
  if (!version) {
    throw new Error('版本不存在');
  }
  version.status = 'DEPRECATED';
  version.deprecatedAt = new Date().toISOString();
  version.updatedAt = new Date().toISOString();
  return delay(version, 500);
};

export const retireVersion = async (id: string): Promise<ApiVersion> => {
  const version = mockVersions.find((v) => v.id === id);
  if (!version) {
    throw new Error('版本不存在');
  }
  version.status = 'RETIRED';
  version.updatedAt = new Date().toISOString();
  return delay(version, 500);
};

export const versionApi = {
  getList: (params?: Parameters<typeof getVersionList>[0]) => httpGet<PageResult<ApiVersion>>(BASE_URL, { params }).catch(() => getVersionList(params)),
  getDetail: (id: string) => httpGet<ApiVersion>(`${BASE_URL}/${id}`).catch(() => getVersionDetail(id)),
  create: (data: Partial<ApiVersion>) => httpPost<ApiVersion>(BASE_URL, data).catch(() => createVersion(data)),
  update: (id: string, data: Partial<ApiVersion>) => httpPut<ApiVersion>(`${BASE_URL}/${id}`, data).catch(() => updateVersion(id, data)),
  delete: (id: string) => httpDelete<void>(`${BASE_URL}/${id}`).catch(() => deleteVersion(id)),
  publish: (id: string) => httpPost<ApiVersion>(`${BASE_URL}/${id}/publish`).catch(() => publishVersion(id)),
  deprecate: (id: string) => httpPost<ApiVersion>(`${BASE_URL}/${id}/deprecate`).catch(() => deprecateVersion(id)),
  retire: (id: string) => httpPost<ApiVersion>(`${BASE_URL}/${id}/retire`).catch(() => retireVersion(id))
};

export default versionApi;

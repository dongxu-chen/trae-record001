import { httpGet, httpPost } from './request';
import type { VersionDiff, CompatibilityReport, DiffRequest, DiffResult } from '../types';

const BASE_URL = '/api/compare';

const mockVersionDiff: VersionDiff = {
  baseVersion: 'v1',
  targetVersion: 'v2',
  breakingChanges: [
    {
      type: 'REMOVE',
      path: '/users/{id}',
      field: 'response.email',
      oldValue: 'string',
      newValue: undefined,
      description: '移除了用户邮箱字段',
      level: 'ERROR'
    },
    {
      type: 'MODIFY',
      path: '/users',
      field: 'request.phone',
      oldValue: 'optional',
      newValue: 'required',
      description: '创建用户时手机号变为必填项',
      level: 'ERROR'
    },
    {
      type: 'REMOVE',
      path: '/orders/{id}',
      field: 'response.discount',
      oldValue: 'number',
      newValue: undefined,
      description: '移除了订单折扣字段',
      level: 'ERROR'
    }
  ],
  nonBreakingChanges: [
    {
      type: 'ADD',
      path: '/users/{id}/points',
      field: 'GET',
      oldValue: undefined,
      newValue: 'endpoint',
      description: '新增获取用户积分接口',
      level: 'INFO'
    },
    {
      type: 'ADD',
      path: '/users/{id}/points',
      field: 'POST',
      oldValue: undefined,
      newValue: 'endpoint',
      description: '新增调整用户积分接口',
      level: 'INFO'
    },
    {
      type: 'MODIFY',
      path: '/users',
      field: 'response.pagination',
      oldValue: 'none',
      newValue: 'supported',
      description: '用户列表接口支持分页查询',
      level: 'INFO'
    },
    {
      type: 'ADD',
      path: '/users/{id}',
      field: 'response.level',
      oldValue: undefined,
      newValue: 'string',
      description: '新增用户等级字段',
      level: 'INFO'
    }
  ],
  deprecatedChanges: [
    {
      type: 'MODIFY',
      path: '/orders',
      field: 'GET',
      oldValue: 'active',
      newValue: 'deprecated',
      description: '获取订单列表接口已废弃',
      level: 'WARNING'
    },
    {
      type: 'MODIFY',
      path: '/orders/{id}',
      field: 'PUT',
      oldValue: 'active',
      newValue: 'deprecated',
      description: '更新订单接口已废弃，建议使用PATCH',
      level: 'WARNING'
    }
  ],
  responseChanges: [
    {
      type: 'MODIFY',
      path: '/users/{id}',
      field: 'response.statusCode',
      oldValue: '200 OK',
      newValue: '200 OK',
      description: '响应状态码未变化',
      level: 'INFO'
    },
    {
      type: 'ADD',
      path: '/users/{id}',
      field: 'response.header.X-Request-Id',
      oldValue: undefined,
      newValue: 'string',
      description: '新增响应头X-Request-Id用于追踪',
      level: 'INFO'
    },
    {
      type: 'MODIFY',
      path: '/users/{id}',
      field: 'response.age',
      oldValue: 'integer',
      newValue: 'string',
      description: '年龄字段类型从int改为string，向后兼容（int→string是兼容的）',
      level: 'INFO'
    },
    {
      type: 'MODIFY',
      path: '/users/{id}',
      field: 'response.score',
      oldValue: 'min=0, max=100',
      newValue: 'min=0, max=1000',
      description: '分数字段最大值从100扩展到1000，向后兼容',
      level: 'INFO'
    },
    {
      type: 'MODIFY',
      path: '/users/{id}',
      field: 'response.role',
      oldValue: 'enum: [user, admin]',
      newValue: 'enum: [user, admin, moderator]',
      description: '角色枚举新增moderator，向后兼容',
      level: 'INFO'
    }
  ]
};

const mockCompatibilityReport: CompatibilityReport = {
  isCompatible: false,
  breakingChangeCount: 3,
  warningCount: 2,
  backwardCompatibilityScore: 65,
  backwardCompatibilityLevel: 'MODERATE',
  migrationComplexity: 45,
  details: [
    '检测到3个破坏性变更，可能导致现有客户端无法正常工作',
    '创建用户接口：phone字段从可选变为必填',
    '用户详情接口：移除了email字段',
    '订单详情接口：移除了discount字段',
    '2个接口已标记为废弃，建议尽快迁移',
    '向后兼容性分析：虽然存在破坏性变更，但5个返回值变更是向后兼容的',
    '响应头新增X-Request-Id用于请求追踪',
    '年龄字段类型从int改为string（向后兼容）',
    '分数字段最大值从100扩展到1000（向后兼容）',
    '角色枚举新增moderator（向后兼容）'
  ],
  recommendations: [
    '建议为移除的email字段提供过渡期，在v2版本中先标记为废弃',
    '建议将phone字段改为可选，并在后端提供默认值或验证逻辑',
    '建议为废弃的订单接口提供至少3个月的迁移期',
    '建议更新客户端SDK以支持新的用户积分和等级字段',
    '建议提供版本迁移文档，详细说明变更内容和升级步骤'
  ],
  backwardCompatibilityAnalysis: '向后兼容性等级：一般（65分）\n\n虽然检测到3个破坏性变更需要客户端适配，但大部分返回值变更是向后兼容的。\n\n向后兼容的变更包括：\n✓ 新增响应头X-Request-Id（不影响现有客户端）\n✓ 字段类型int → string（可自动转换）\n✓ 数值范围扩展（min/max放宽）\n✓ 枚举值新增（只增不减）\n\n迁移复杂度评估：中等（45/100）\n\n建议采用分批次推送策略，控制推送速率，建议参数：\n• 推荐批次数量：10批\n• 每批流量：2000用户/批\n• 批次间隔：2小时\n• 监控阈值：错误率>1%或响应时间增加>20%时自动暂停\n• 总预计耗时：约20小时',
  rateLimitingRecommendation: '基于向后兼容性评分65分，迁移复杂度45分，推荐配置：\n\n批次数量：10批\n每批大小：2000\n批次间隔：7200000毫秒（2小时）\n监控指标：\n• 错误率阈值：1%\n• 响应时间阈值：+20%\n• 用户投诉阈值：0.1%\n\n自动回滚条件：\n• 连续3个批次错误率>5%\n• 错误率>10%立即回滚',
  backwardCompatibleChanges: [
    {
      type: 'ADD',
      path: '/users/{id}',
      field: 'response.header.X-Request-Id',
      newValue: 'string',
      description: '新增响应头X-Request-Id用于追踪',
      level: 'INFO'
    },
    {
      type: 'MODIFY',
      path: '/users/{id}',
      field: 'response.age',
      oldValue: 'integer',
      newValue: 'string',
      description: '年龄字段类型从int改为string，向后兼容',
      level: 'INFO'
    },
    {
      type: 'MODIFY',
      path: '/users/{id}',
      field: 'response.score',
      oldValue: 'min=0, max=100',
      newValue: 'min=0, max=1000',
      description: '分数字段最大值从100扩展到1000，向后兼容',
      level: 'INFO'
    }
  ]
};

const mockDiffResults: DiffResult[] = [
  {
    id: '1',
    baseVersionId: '1',
    targetVersionId: '2',
    diffContent: mockVersionDiff,
    breakingChanges: 3,
    warningChanges: 2,
    isCompatible: false,
    createdAt: '2024-05-15T10:30:00Z'
  },
  {
    id: '2',
    baseVersionId: '3',
    targetVersionId: '4',
    diffContent: {
      baseVersion: 'v1',
      targetVersion: 'v2',
      breakingChanges: [],
      nonBreakingChanges: [
        {
          type: 'ADD',
          path: '/orders/{id}/tracking',
          field: 'GET',
          description: '新增订单物流跟踪接口',
          level: 'INFO'
        }
      ],
      deprecatedChanges: [
        {
          type: 'MODIFY',
          path: '/orders',
          field: 'GET',
          oldValue: 'active',
          newValue: 'deprecated',
          description: '获取订单列表接口已废弃',
          level: 'WARNING'
        }
      ]
    },
    breakingChanges: 0,
    warningChanges: 1,
    isCompatible: true,
    createdAt: '2024-05-20T14:00:00Z'
  }
];

const delay = <T>(data: T, ms = 500): Promise<T> => {
  return new Promise((resolve) => setTimeout(() => resolve(data), ms));
};

export const compareVersions = async (request: DiffRequest): Promise<VersionDiff> => {
  console.log('[Compare] Comparing versions:', request);
  return delay(mockVersionDiff);
};

export const checkCompatibility = async (request: DiffRequest): Promise<CompatibilityReport> => {
  console.log('[Compatibility] Checking compatibility:', request);
  return delay(mockCompatibilityReport);
};

export const getDiffReport = async (id: string): Promise<DiffResult> => {
  const report = mockDiffResults.find((r) => r.id === id);
  if (!report) {
    throw new Error('对比报告不存在');
  }
  return delay(report);
};

export const getDiffReports = async (): Promise<DiffResult[]> => {
  return delay(mockDiffResults);
};

export const compareApi = {
  diff: (request: DiffRequest) => httpPost<VersionDiff>(`${BASE_URL}/diff`, request).catch(() => compareVersions(request)),
  compatibility: (request: DiffRequest) => httpPost<CompatibilityReport>(`${BASE_URL}/compatibility`, request).catch(() => checkCompatibility(request)),
  getReport: (id: string) => httpGet<DiffResult>(`${BASE_URL}/reports/${id}`).catch(() => getDiffReport(id)),
  getReports: () => httpGet<DiffResult[]>(`${BASE_URL}/reports`).catch(() => getDiffReports())
};

export default compareApi;

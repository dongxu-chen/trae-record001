import { useState, useMemo } from 'react';
import { Select, Card, Typography, Row, Col, Tag, Space, Alert } from 'antd';
import { BookOutlined, ApiOutlined, CheckCircleOutlined } from '@ant-design/icons';
import SwaggerUI from 'swagger-ui-react';
import 'swagger-ui-react/swagger-ui.css';

const { Title, Text } = Typography;
const { Option } = Select;

interface VersionInfo {
  version: string;
  name: string;
  description: string;
  status: 'active' | 'deprecated' | 'draft';
  specUrl: string;
}

const mockVersions: VersionInfo[] = [
  {
    version: 'v3.0.0-beta',
    name: 'v3.0.0 (测试版)',
    description: '全新架构版本，支持微服务拆分',
    status: 'draft',
    specUrl: '/v3/api-docs',
  },
  {
    version: 'v2.1.0',
    name: 'v2.1.0 (稳定版)',
    description: '新增支付集成，性能优化',
    status: 'active',
    specUrl: '/v2/api-docs',
  },
  {
    version: 'v2.0.0',
    name: 'v2.0.0 (稳定版)',
    description: '重构版本，支持新的认证机制',
    status: 'active',
    specUrl: '/v2/api-docs',
  },
  {
    version: 'v1.5.0',
    name: 'v1.5.0 (已废弃)',
    description: '增加批量操作功能，建议升级到 v2.x',
    status: 'deprecated',
    specUrl: '/v1/api-docs',
  },
  {
    version: 'v1.0.0',
    name: 'v1.0.0 (已废弃)',
    description: '初始版本，提供基础用户管理功能',
    status: 'deprecated',
    specUrl: '/v1/api-docs',
  },
];

const mockSwaggerSpec = (version: string) => ({
  openapi: '3.0.1',
  info: {
    title: `API 文档 - ${version}`,
    description: `这是 ${version} 版本的 API 文档，包含所有可用的接口定义和调用说明。`,
    version: version,
    contact: {
      name: 'API 团队',
      email: 'api-support@example.com',
    },
  },
  servers: [
    {
      url: `http://localhost:8080/api/${version}`,
      description: '开发环境',
    },
    {
      url: `https://api.example.com/${version}`,
      description: '生产环境',
    },
  ],
  tags: [
    { name: '用户管理', description: '用户相关操作接口' },
    { name: '订单管理', description: '订单相关操作接口' },
    { name: '商品管理', description: '商品相关操作接口' },
  ],
  paths: {
    '/users': {
      get: {
        tags: ['用户管理'],
        summary: '获取用户列表',
        description: '分页获取系统中的所有用户信息',
        operationId: 'getUsers',
        parameters: [
          { name: 'page', in: 'query', description: '页码', schema: { type: 'integer', default: 1 } },
          { name: 'size', in: 'query', description: '每页数量', schema: { type: 'integer', default: 10 } },
        ],
        responses: {
          '200': { description: '成功获取用户列表' },
        },
      },
      post: {
        tags: ['用户管理'],
        summary: '创建用户',
        description: '创建一个新的用户',
        operationId: 'createUser',
        requestBody: {
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  name: { type: 'string', example: '张三' },
                  email: { type: 'string', example: 'zhangsan@example.com' },
                  phone: { type: 'string', example: '13800138000' },
                },
                required: ['name', 'email'],
              },
            },
          },
        },
        responses: {
          '201': { description: '用户创建成功' },
          '400': { description: '请求参数错误' },
        },
      },
    },
    '/users/{id}': {
      get: {
        tags: ['用户管理'],
        summary: '获取用户详情',
        description: '根据用户ID获取用户详细信息',
        operationId: 'getUserById',
        parameters: [
          { name: 'id', in: 'path', required: true, description: '用户ID', schema: { type: 'string' } },
        ],
        responses: {
          '200': { description: '成功获取用户信息' },
          '404': { description: '用户不存在' },
        },
      },
      put: {
        tags: ['用户管理'],
        summary: '更新用户信息',
        description: '更新指定用户的信息',
        operationId: 'updateUser',
        parameters: [
          { name: 'id', in: 'path', required: true, description: '用户ID', schema: { type: 'string' } },
        ],
        requestBody: {
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  name: { type: 'string' },
                  email: { type: 'string' },
                  phone: { type: 'string' },
                },
              },
            },
          },
        },
        responses: {
          '200': { description: '用户信息更新成功' },
          '404': { description: '用户不存在' },
        },
      },
      delete: {
        tags: ['用户管理'],
        summary: '删除用户',
        description: '删除指定的用户',
        operationId: 'deleteUser',
        parameters: [
          { name: 'id', in: 'path', required: true, description: '用户ID', schema: { type: 'string' } },
        ],
        responses: {
          '204': { description: '用户删除成功' },
          '404': { description: '用户不存在' },
        },
      },
    },
    '/orders': {
      get: {
        tags: ['订单管理'],
        summary: '获取订单列表',
        description: '获取当前用户的所有订单',
        operationId: 'getOrders',
        parameters: [
          { name: 'status', in: 'query', description: '订单状态', schema: { type: 'string' } },
          { name: 'page', in: 'query', description: '页码', schema: { type: 'integer', default: 1 } },
        ],
        responses: {
          '200': { description: '成功获取订单列表' },
        },
      },
      post: {
        tags: ['订单管理'],
        summary: '创建订单',
        description: '创建一个新的订单',
        operationId: 'createOrder',
        requestBody: {
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  productId: { type: 'string' },
                  quantity: { type: 'integer', minimum: 1 },
                  amount: { type: 'number' },
                },
                required: ['productId', 'quantity', 'amount'],
              },
            },
          },
        },
        responses: {
          '201': { description: '订单创建成功' },
        },
      },
    },
    '/orders/{id}': {
      get: {
        tags: ['订单管理'],
        summary: '获取订单详情',
        operationId: 'getOrderById',
        parameters: [
          { name: 'id', in: 'path', required: true, description: '订单ID', schema: { type: 'string' } },
        ],
        responses: {
          '200': { description: '成功获取订单详情' },
          '404': { description: '订单不存在' },
        },
      },
    },
    ...(version.startsWith('v2') ? {
      '/products': {
        get: {
          tags: ['商品管理'],
          summary: '获取商品列表',
          description: '获取所有商品信息（v2新增）',
          operationId: 'getProducts',
          parameters: [
            { name: 'category', in: 'query', description: '商品分类', schema: { type: 'string' } },
          ],
          responses: {
            '200': { description: '成功获取商品列表' },
          },
        },
      },
      '/products/{id}': {
        get: {
          tags: ['商品管理'],
          summary: '获取商品详情',
          operationId: 'getProductById',
          parameters: [
            { name: 'id', in: 'path', required: true, description: '商品ID', schema: { type: 'string' } },
          ],
          responses: {
            '200': { description: '成功获取商品详情' },
          },
        },
      },
    } : {}),
    ...(version.startsWith('v3') ? {
      '/products/{id}/stock': {
        get: {
          tags: ['商品管理'],
          summary: '获取商品库存（v3新增）',
          operationId: 'getProductStock',
          parameters: [
            { name: 'id', in: 'path', required: true, description: '商品ID', schema: { type: 'string' } },
          ],
          responses: {
            '200': { description: '成功获取库存信息' },
          },
        },
      },
      '/payments': {
        post: {
          tags: ['支付管理'],
          summary: '创建支付（v3新增）',
          operationId: 'createPayment',
          requestBody: {
            content: {
              'application/json': {
                schema: {
                  type: 'object',
                  properties: {
                    orderId: { type: 'string' },
                    amount: { type: 'number' },
                    payMethod: { type: 'string', enum: ['alipay', 'wechat', 'card'] },
                  },
                },
              },
            },
          },
          responses: {
            '201': { description: '支付创建成功' },
          },
        },
      },
    } : {}),
  },
  components: {
    securitySchemes: {
      bearerAuth: {
        type: 'http',
        scheme: 'bearer',
        bearerFormat: 'JWT',
        description: '请输入 Bearer {token}',
      },
    },
  },
  security: [{ bearerAuth: [] }],
});

const statusMap: Record<string, { text: string; color: string }> = {
  active: { text: '活跃', color: 'green' },
  deprecated: { text: '已废弃', color: 'orange' },
  draft: { text: '测试中', color: 'blue' },
};

export default function SwaggerDocs() {
  const [selectedVersion, setSelectedVersion] = useState<string>('v2.1.0');

  const currentVersion = useMemo(
    () => mockVersions.find((v) => v.version === selectedVersion) || mockVersions[0],
    [selectedVersion]
  );

  const spec = useMemo(() => mockSwaggerSpec(selectedVersion), [selectedVersion]);

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <Card>
        <Row justify="space-between" align="middle" style={{ marginBottom: 20 }}>
          <Col>
            <Space>
              <ApiOutlined style={{ fontSize: 24, color: '#165DFF' }} />
              <Title level={3} style={{ margin: 0 }}>
                API 文档中心
              </Title>
            </Space>
            <Text type="secondary" className="mt-2 block">
              选择版本查看对应的 API 文档，支持在线调试
            </Text>
          </Col>
          <Col>
            <Space>
              <BookOutlined />
              <Text strong>版本选择：</Text>
              <Select
                value={selectedVersion}
                onChange={setSelectedVersion}
                style={{ width: 280 }}
                size="large"
                placeholder="选择 API 版本"
              >
                {mockVersions.map((v) => (
                  <Option key={v.version} value={v.version}>
                    <Space>
                      <span>{v.name}</span>
                      <Tag color={statusMap[v.status].color}>{statusMap[v.status].text}</Tag>
                    </Space>
                  </Option>
                ))}
              </Select>
            </Space>
          </Col>
        </Row>

        {currentVersion.status === 'deprecated' && (
          <Alert
            message="该版本已废弃"
            description="此版本已不再维护，建议尽快升级到最新稳定版。"
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}
        {currentVersion.status === 'draft' && (
          <Alert
            message="该版本为测试版"
            description="此版本正在测试中，可能存在不稳定因素，请勿在生产环境使用。"
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        <Card
          size="small"
          style={{ marginBottom: 16 }}
          bodyStyle={{ padding: '12px 16px' }}
        >
          <Row align="middle" gutter={16}>
            <Col>
              <Space>
                <CheckCircleOutlined style={{ color: '#52c41a' }} />
                <Text strong>当前版本：</Text>
                <code className="bg-gray-100 px-2 py-1 rounded">{currentVersion.version}</code>
              </Space>
            </Col>
            <Col>
              <Text type="secondary">{currentVersion.description}</Text>
            </Col>
          </Row>
        </Card>

        <div className="swagger-wrapper">
          <SwaggerUI
            spec={spec}
            tryItOutEnabled={true}
            supportedSubmitMethods={['get', 'put', 'post', 'delete', 'patch']}
            showRequestHeaders={true}
            defaultModelsExpandDepth={1}
            defaultModelExpandDepth={1}
          />
        </div>
      </Card>
    </div>
  );
}

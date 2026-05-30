import { useState, useMemo } from 'react';
import {
  Card,
  Descriptions,
  Tag,
  Typography,
  Table,
  Tabs,
  Button,
  Space,
  Row,
  Col,
  Statistic,
  Divider,
  Breadcrumb,
} from 'antd';
import {
  ArrowLeftOutlined,
  PlayCircleOutlined,
  StopOutlined,
  DeleteOutlined,
  ApiOutlined,
  ClockCircleOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import {
  ArrowDown,
  ArrowUp,
  Edit3,
  Trash2,
} from 'lucide-react';
import { useParams, useNavigate } from 'react-router-dom';
import SwaggerUI from 'swagger-ui-react';
import 'swagger-ui-react/swagger-ui.css';
import type { ColumnsType } from 'antd/es/table';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

type VersionStatus = 'active' | 'deprecated' | 'offline' | 'draft';
type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE';

interface ApiVersion {
  id: string;
  version: string;
  name: string;
  status: VersionStatus;
  apiCount: number;
  traffic: number;
  createTime: string;
  updateTime: string;
  description: string;
  basePath: string;
  maintainer: string;
  contactEmail: string;
}

interface ApiEndpoint {
  id: string;
  path: string;
  method: HttpMethod;
  summary: string;
  description: string;
  tags: string[];
  deprecated: boolean;
}

const mockVersions: Record<string, ApiVersion> = {
  '1': {
    id: '1',
    version: 'v1.0.0',
    name: '用户服务 v1',
    status: 'active',
    apiCount: 12,
    traffic: 35,
    createTime: '2026-01-15 10:30:00',
    updateTime: '2026-05-20 14:20:00',
    description: '初始版本，提供基础用户管理功能，包括用户的增删改查、登录认证等核心功能。',
    basePath: '/api/v1',
    maintainer: '张三',
    contactEmail: 'zhangsan@example.com',
  },
  '2': {
    id: '2',
    version: 'v1.5.0',
    name: '用户服务 v1.5',
    status: 'deprecated',
    apiCount: 15,
    traffic: 5,
    createTime: '2026-02-20 09:15:00',
    updateTime: '2026-05-10 11:30:00',
    description: '增加批量操作功能，已废弃，建议迁移至 v2.0.0 版本。',
    basePath: '/api/v1.5',
    maintainer: '张三',
    contactEmail: 'zhangsan@example.com',
  },
  '3': {
    id: '3',
    version: 'v2.0.0',
    name: '用户服务 v2',
    status: 'active',
    apiCount: 18,
    traffic: 30,
    createTime: '2026-03-01 16:45:00',
    updateTime: '2026-05-25 09:10:00',
    description: '重构版本，性能优化，支持新的认证机制（JWT Token），响应速度提升 50%。',
    basePath: '/api/v2',
    maintainer: '李四',
    contactEmail: 'lisi@example.com',
  },
};

const mockEndpoints: Record<string, ApiEndpoint[]> = {
  '1': [
    {
      id: '1-1',
      path: '/users',
      method: 'GET',
      summary: '获取用户列表',
      description: '分页获取系统中所有用户的信息',
      tags: ['用户管理'],
      deprecated: false,
    },
    {
      id: '1-2',
      path: '/users',
      method: 'POST',
      summary: '创建用户',
      description: '创建一个新的用户账号',
      tags: ['用户管理'],
      deprecated: false,
    },
    {
      id: '1-3',
      path: '/users/{id}',
      method: 'GET',
      summary: '获取用户详情',
      description: '根据用户ID获取用户的详细信息',
      tags: ['用户管理'],
      deprecated: false,
    },
    {
      id: '1-4',
      path: '/users/{id}',
      method: 'PUT',
      summary: '更新用户信息',
      description: '更新指定用户的基本信息',
      tags: ['用户管理'],
      deprecated: false,
    },
    {
      id: '1-5',
      path: '/users/{id}',
      method: 'DELETE',
      summary: '删除用户',
      description: '删除指定的用户账号',
      tags: ['用户管理'],
      deprecated: true,
    },
    {
      id: '1-6',
      path: '/users/{id}/roles',
      method: 'GET',
      summary: '获取用户角色',
      description: '获取指定用户的角色列表',
      tags: ['权限管理'],
      deprecated: false,
    },
    {
      id: '1-7',
      path: '/auth/login',
      method: 'POST',
      summary: '用户登录',
      description: '用户登录认证，返回Session',
      tags: ['认证'],
      deprecated: false,
    },
    {
      id: '1-8',
      path: '/auth/logout',
      method: 'POST',
      summary: '用户登出',
      description: '用户登出，销毁Session',
      tags: ['认证'],
      deprecated: false,
    },
  ],
  '2': [
    {
      id: '2-1',
      path: '/users',
      method: 'GET',
      summary: '获取用户列表',
      description: '分页获取系统中所有用户的信息，支持高级筛选',
      tags: ['用户管理'],
      deprecated: false,
    },
    {
      id: '2-2',
      path: '/users/batch',
      method: 'POST',
      summary: '批量创建用户',
      description: '一次性创建多个用户账号',
      tags: ['用户管理'],
      deprecated: false,
    },
  ],
  '3': [
    {
      id: '3-1',
      path: '/users',
      method: 'GET',
      summary: '获取用户列表',
      description: '分页获取系统中所有用户的信息，支持高级筛选和排序',
      tags: ['用户管理'],
      deprecated: false,
    },
    {
      id: '3-2',
      path: '/users',
      method: 'POST',
      summary: '创建用户',
      description: '创建一个新的用户账号，支持更多字段',
      tags: ['用户管理'],
      deprecated: false,
    },
    {
      id: '3-3',
      path: '/users/{id}',
      method: 'GET',
      summary: '获取用户详情',
      description: '根据用户ID获取用户的详细信息，包含扩展信息',
      tags: ['用户管理'],
      deprecated: false,
    },
    {
      id: '3-4',
      path: '/auth/token',
      method: 'POST',
      summary: '获取访问令牌',
      description: '使用用户名密码获取JWT访问令牌',
      tags: ['认证'],
      deprecated: false,
    },
    {
      id: '3-5',
      path: '/auth/refresh',
      method: 'POST',
      summary: '刷新访问令牌',
      description: '使用刷新令牌获取新的访问令牌',
      tags: ['认证'],
      deprecated: false,
    },
  ],
};

const mockSwaggerSpec: Record<string, object> = {
  '1': {
    openapi: '3.0.0',
    info: {
      title: '用户服务 v1.0.0',
      version: '1.0.0',
      description: '初始版本，提供基础用户管理功能',
    },
    servers: [{ url: '/api/v1' }],
    paths: {
      '/users': {
        get: {
          summary: '获取用户列表',
          tags: ['用户管理'],
          responses: { '200': { description: '成功返回用户列表' } },
        },
        post: {
          summary: '创建用户',
          tags: ['用户管理'],
          requestBody: {
            content: {
              'application/json': {
                schema: {
                  type: 'object',
                  properties: {
                    name: { type: 'string' },
                    email: { type: 'string' },
                  },
                },
              },
            },
          },
          responses: { '201': { description: '用户创建成功' } },
        },
      },
      '/users/{id}': {
        get: {
          summary: '获取用户详情',
          tags: ['用户管理'],
          parameters: [{ name: 'id', in: 'path', required: true, schema: { type: 'integer' } }],
          responses: { '200': { description: '成功返回用户详情' } },
        },
        put: {
          summary: '更新用户信息',
          tags: ['用户管理'],
          parameters: [{ name: 'id', in: 'path', required: true, schema: { type: 'integer' } }],
          responses: { '200': { description: '用户信息更新成功' } },
        },
        delete: {
          summary: '删除用户',
          tags: ['用户管理'],
          deprecated: true,
          parameters: [{ name: 'id', in: 'path', required: true, schema: { type: 'integer' } }],
          responses: { '204': { description: '用户删除成功' } },
        },
      },
      '/auth/login': {
        post: {
          summary: '用户登录',
          tags: ['认证'],
          responses: { '200': { description: '登录成功' } },
        },
      },
    },
  },
  '3': {
    openapi: '3.0.0',
    info: {
      title: '用户服务 v2.0.0',
      version: '2.0.0',
      description: '重构版本，性能优化，支持新的认证机制',
    },
    servers: [{ url: '/api/v2' }],
    paths: {
      '/users': {
        get: {
          summary: '获取用户列表',
          tags: ['用户管理'],
          responses: { '200': { description: '成功返回用户列表' } },
        },
        post: {
          summary: '创建用户',
          tags: ['用户管理'],
          responses: { '201': { description: '用户创建成功' } },
        },
      },
      '/auth/token': {
        post: {
          summary: '获取访问令牌',
          tags: ['认证'],
          responses: { '200': { description: '令牌获取成功' } },
        },
      },
      '/auth/refresh': {
        post: {
          summary: '刷新访问令牌',
          tags: ['认证'],
          responses: { '200': { description: '令牌刷新成功' } },
        },
      },
    },
  },
};

const statusMap: Record<VersionStatus, { text: string; color: string }> = {
  active: { text: '活跃', color: 'green' },
  deprecated: { text: '已废弃', color: 'orange' },
  offline: { text: '已下线', color: 'red' },
  draft: { text: '草稿', color: 'default' },
};

const methodMap: Record<HttpMethod, { icon: JSX.Element; color: string }> = {
  GET: { icon: <ArrowDown size={16} />, color: 'green' },
  POST: { icon: <ArrowUp size={16} />, color: 'blue' },
  PUT: { icon: <Edit3 size={16} />, color: 'orange' },
  DELETE: { icon: <Trash2 size={16} />, color: 'red' },
};

export default function VersionDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('info');

  const version = useMemo(() => mockVersions[id || '1'] || mockVersions['1'], [id]);
  const endpoints = useMemo(() => mockEndpoints[id || '1'] || [], [id]);
  const swaggerSpec = useMemo(() => mockSwaggerSpec[id || '1'] || mockSwaggerSpec['1'], [id]);

  const getStats = () => {
    const stats = {
      get: 0,
      post: 0,
      put: 0,
      delete: 0,
      deprecated: 0,
    };
    endpoints.forEach((ep) => {
      stats[ep.method.toLowerCase() as keyof typeof stats]++;
      if (ep.deprecated) stats.deprecated++;
    });
    return stats;
  };

  const stats = getStats();

  const columns: ColumnsType<ApiEndpoint> = [
    {
      title: '方法',
      dataIndex: 'method',
      key: 'method',
      width: 100,
      render: (method: HttpMethod) => (
        <Tag color={methodMap[method].color} icon={methodMap[method].icon}>
          {method}
        </Tag>
      ),
    },
    {
      title: '路径',
      dataIndex: 'path',
      key: 'path',
      width: 200,
      render: (text, record) => (
        <Space>
          <code className="bg-gray-100 px-2 py-1 rounded text-sm">{text}</code>
          {record.deprecated && <Tag color="red">已废弃</Tag>}
        </Space>
      ),
    },
    {
      title: '摘要',
      dataIndex: 'summary',
      key: 'summary',
      width: 200,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      width: 150,
      render: (tags: string[]) => (
        <Space wrap>
          {tags.map((tag) => (
            <Tag key={tag} color="blue">
              {tag}
            </Tag>
          ))}
        </Space>
      ),
    },
  ];

  const getActionButton = () => {
    const buttons: JSX.Element[] = [];

    if (version.status === 'draft') {
      buttons.push(
        <Button key="publish" type="primary" icon={<PlayCircleOutlined />}>
          发布版本
        </Button>
      );
    }

    if (version.status === 'active') {
      buttons.push(
        <Button key="deprecate" icon={<StopOutlined />} danger>
          标记废弃
        </Button>
      );
    }

    if (version.status === 'deprecated') {
      buttons.push(
        <Button key="offline" icon={<DeleteOutlined />} danger>
          下线版本
        </Button>
      );
    }

    return <Space>{buttons}</Space>;
  };

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <Breadcrumb style={{ marginBottom: 16 }}>
        <Breadcrumb.Item onClick={() => navigate('/versions')} className="cursor-pointer">
          版本列表
        </Breadcrumb.Item>
        <Breadcrumb.Item>{version.name}</Breadcrumb.Item>
      </Breadcrumb>

      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Space align="center">
              <Button
                icon={<ArrowLeftOutlined />}
                onClick={() => navigate('/versions')}
                type="text"
              />
              <Title level={3} style={{ margin: 0 }}>
                {version.name}
              </Title>
              <Tag color={statusMap[version.status].color}>{statusMap[version.status].text}</Tag>
              <code className="bg-gray-100 px-2 py-1 rounded">{version.version}</code>
            </Space>
          </Col>
          <Col>{getActionButton()}</Col>
        </Row>

        <Divider style={{ margin: '16px 0' }} />

        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={6}>
            <Statistic
              title="接口总数"
              value={version.apiCount}
              prefix={<ApiOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Statistic
              title="GET 接口"
              value={stats.get}
              prefix={<ArrowDown size={16} />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Statistic
              title="POST 接口"
              value={stats.post}
              prefix={<ArrowUp size={16} />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Statistic
              title="流量占比"
              value={version.traffic}
              suffix="%"
              prefix={<RocketOutlined />}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Col>
        </Row>
      </Card>

      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane tab="基本信息" key="info">
            <Descriptions bordered column={2}>
              <Descriptions.Item label="版本号">
                <code className="bg-gray-100 px-2 py-1 rounded">{version.version}</code>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={statusMap[version.status].color}>
                  {statusMap[version.status].text}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="基础路径" span={2}>
                <code className="bg-gray-100 px-2 py-1 rounded">{version.basePath}</code>
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                <Space>
                  <ClockCircleOutlined />
                  {version.createTime}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="更新时间">
                <Space>
                  <ClockCircleOutlined />
                  {version.updateTime}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="维护人员">{version.maintainer}</Descriptions.Item>
              <Descriptions.Item label="联系邮箱">{version.contactEmail}</Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>
                <Text>{version.description}</Text>
              </Descriptions.Item>
            </Descriptions>
          </TabPane>

          <TabPane tab={`接口列表 (${endpoints.length})`} key="apis">
            <Table
              columns={columns}
              dataSource={endpoints}
              rowKey="id"
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 个接口`,
              }}
            />
          </TabPane>

          <TabPane tab="Swagger 文档" key="swagger">
            <div className="swagger-container bg-white rounded-lg">
              <SwaggerUI spec={swaggerSpec} tryItOutEnabled={false} />
            </div>
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
}

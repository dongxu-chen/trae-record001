import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Upload,
  message,
  Tabs,
  Tag,
  Row,
  Col,
  Statistic,
  Divider,
  Select,
  Tooltip,
  CopyOutlined,
} from 'antd';
import {
  UploadOutlined,
  PlusOutlined,
  FileTextOutlined,
  SearchOutlined,
  EditOutlined,
  ReloadOutlined,
  CloudUploadOutlined,
} from '@ant-design/icons';
import type { Document, Query, Annotation, ModelInfo } from '@/types';
import {
  getDocuments,
  getQueries,
  getAnnotations,
  getModels,
  createDocument,
  createQuery,
  createModel,
} from '@/services/api';
import dayjs from 'dayjs';

const { Option } = Select;

const QUERY_TYPES = [
  { value: 'informational', label: '信息查询', color: 'blue' },
  { value: 'navigational', label: '导航查询', color: 'green' },
  { value: 'transactional', label: '事务查询', color: 'orange' },
  { value: 'exploratory', label: '探索查询', color: 'purple' },
];

const getQueryTypeTag = (type?: string) => {
  const qt = QUERY_TYPES.find(q => q.value === type);
  if (!qt) return <Tag color="default">未分类</Tag>;
  return <Tag color={qt.color}>{qt.label}</Tag>;
};

const { TabPane } = Tabs;
const { TextArea } = Input;

const DataManagement: React.FC = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [queries, setQueries] = useState<Query[]>([]);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('documents');

  const [showDocModal, setShowDocModal] = useState(false);
  const [showQueryModal, setShowQueryModal] = useState(false);
  const [showModelModal, setShowModelModal] = useState(false);
  const [docForm] = Form.useForm();
  const [queryForm] = Form.useForm();
  const [modelForm] = Form.useForm();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [docsRes, queriesRes, annRes, modelsRes] = await Promise.all([
        getDocuments(1, 100),
        getQueries(1, 100),
        getAnnotations(1, 100),
        getModels(),
      ]);
      setDocuments(docsRes.data);
      setQueries(queriesRes.data);
      setAnnotations(annRes.data);
      setModels(modelsRes.data);
    } catch (err: any) {
      message.error('加载数据失败：' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleAddDocument = async (values: any) => {
    try {
      await createDocument(values);
      message.success('文档添加成功');
      setShowDocModal(false);
      docForm.resetFields();
      loadData();
    } catch (err: any) {
      message.error('添加失败：' + (err.response?.data?.detail || err.message));
    }
  };

  const handleAddQuery = async (values: any) => {
    try {
      await createQuery(values);
      message.success('查询添加成功');
      setShowQueryModal(false);
      queryForm.resetFields();
      loadData();
    } catch (err: any) {
      message.error('添加失败：' + (err.response?.data?.detail || err.message));
    }
  };

  const handleAddModel = async (values: any) => {
    try {
      await createModel({ ...values, is_active: true });
      message.success('模型添加成功');
      setShowModelModal(false);
      modelForm.resetFields();
      loadData();
    } catch (err: any) {
      message.error('添加失败：' + (err.response?.data?.detail || err.message));
    }
  };

  const documentColumns = [
    {
      title: '文档ID',
      dataIndex: 'doc_id',
      key: 'doc_id',
      width: 120,
      render: (id: string) => <Tag color="blue">{id}</Tag>,
    },
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
    },
    {
      title: '内容摘要',
      dataIndex: 'content',
      key: 'content',
      ellipsis: true,
      render: (content: string) => content.slice(0, 100) + '...',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm:ss'),
    },
  ];

  const queryColumns = [
    {
      title: '查询ID',
      dataIndex: 'query_id',
      key: 'query_id',
      width: 120,
      render: (id: string) => <Tag color="green">{id}</Tag>,
    },
    {
      title: '查询文本',
      dataIndex: 'query_text',
      key: 'query_text',
    },
    {
      title: '查询类型',
      dataIndex: 'query_type',
      key: 'query_type',
      width: 120,
      render: (type?: string) => getQueryTypeTag(type),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm:ss'),
    },
  ];

  const annotationColumns = [
    {
      title: '查询ID',
      dataIndex: 'query_id',
      key: 'query_id',
      width: 120,
      render: (id: string) => <Tag color="green">{id}</Tag>,
    },
    {
      title: '文档ID',
      dataIndex: 'doc_id',
      key: 'doc_id',
      width: 120,
      render: (id: string) => <Tag color="blue">{id}</Tag>,
    },
    {
      title: '相关性',
      dataIndex: 'relevance',
      key: 'relevance',
      width: 120,
      render: (rel: number) => {
        const colors = ['error', 'warning', 'processing', 'success'];
        const labels = ['不相关', '一般相关', '相关', '高度相关'];
        return <Tag color={colors[rel]}>{labels[rel]}</Tag>;
      },
    },
    {
      title: 'Request ID',
      dataIndex: 'request_id',
      key: 'request_id',
      width: 200,
      render: (rid?: string) => {
        if (!rid) return <span style={{ color: '#999' }}>-</span>;
        return (
          <Tooltip title="点击复制">
            <Tag
              color="geekblue"
              style={{ cursor: 'pointer', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis' }}
              onClick={() => {
                navigator.clipboard.writeText(rid);
                message.success('已复制Request ID');
              }}
            >
              <CopyOutlined style={{ marginRight: 4 }} />
              {rid}
            </Tag>
          </Tooltip>
        );
      },
    },
    {
      title: '标注者',
      dataIndex: 'annotator',
      key: 'annotator',
      width: 100,
    },
    {
      title: '标注时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm:ss'),
    },
  ];

  const modelColumns = [
    {
      title: '模型名称',
      dataIndex: 'model_name',
      key: 'model_name',
      width: 180,
      render: (name: string) => (
        <Space>
          <Tag color="purple">{name}</Tag>
        </Space>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: 'Endpoint',
      dataIndex: 'endpoint',
      key: 'endpoint',
      render: (ep: string) => ep || '-',
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (active: boolean) => (
        <Tag color={active ? 'success' : 'default'}>
          {active ? '活跃' : '未激活'}
        </Tag>
      ),
    },
  ];

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>数据管理</h2>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card className="metric-card">
            <Statistic
              title={<span><FileTextOutlined /> 文档总数</span>}
              value={documents.length}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card className="metric-card">
            <Statistic
              title={<span><SearchOutlined /> 查询总数</span>}
              value={queries.length}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card className="metric-card">
            <Statistic
              title={<span><EditOutlined /> 标注总数</span>}
              value={annotations.length}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card className="metric-card">
            <Statistic
              title={<span><CloudUploadOutlined /> 模型总数</span>}
              value={models.length}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={loadData}>
              刷新
            </Button>
          </Space>
        }
      >
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane
            tab={
              <Space>
                <FileTextOutlined /> 文档管理
              </Space>
            }
            key="documents"
          >
            <div style={{ marginBottom: 16, textAlign: 'right' }}>
              <Space>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => setShowDocModal(true)}
                >
                  添加文档
                </Button>
                <Upload
                  accept=".json,.csv"
                  showUploadList={false}
                  beforeUpload={(file) => {
                    message.info(`文件 ${file.name} 上传功能待实现`);
                    return false;
                  }}
                >
                  <Button icon={<UploadOutlined />}>批量导入</Button>
                </Upload>
              </Space>
            </div>
            <Table
              columns={documentColumns}
              dataSource={documents}
              rowKey="doc_id"
              loading={loading}
              pagination={{ pageSize: 10 }}
              scroll={{ x: 800 }}
            />
          </TabPane>

          <TabPane
            tab={
              <Space>
                <SearchOutlined /> 查询管理
              </Space>
            }
            key="queries"
          >
            <div style={{ marginBottom: 16, textAlign: 'right' }}>
              <Space>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => setShowQueryModal(true)}
                >
                  添加查询
                </Button>
                <Upload
                  accept=".json,.csv"
                  showUploadList={false}
                  beforeUpload={(file) => {
                    message.info(`文件 ${file.name} 上传功能待实现`);
                    return false;
                  }}
                >
                  <Button icon={<UploadOutlined />}>批量导入</Button>
                </Upload>
              </Space>
            </div>
            <Table
              columns={queryColumns}
              dataSource={queries}
              rowKey="query_id"
              loading={loading}
              pagination={{ pageSize: 10 }}
              scroll={{ x: 800 }}
            />
          </TabPane>

          <TabPane
            tab={
              <Space>
                <EditOutlined /> 标注管理
              </Space>
            }
            key="annotations"
          >
            <Table
              columns={annotationColumns}
              dataSource={annotations}
              rowKey={(record) => `${record.query_id}_${record.doc_id}`}
              loading={loading}
              pagination={{ pageSize: 10 }}
              scroll={{ x: 800 }}
            />
          </TabPane>

          <TabPane
            tab={
              <Space>
                <CloudUploadOutlined /> 模型管理
              </Space>
            }
            key="models"
          >
            <div style={{ marginBottom: 16, textAlign: 'right' }}>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => setShowModelModal(true)}
              >
                添加模型
              </Button>
            </div>
            <Table
              columns={modelColumns}
              dataSource={models}
              rowKey="model_name"
              loading={loading}
              pagination={false}
              scroll={{ x: 800 }}
            />
          </TabPane>
        </Tabs>
      </Card>

      <Modal
        title="添加文档"
        open={showDocModal}
        onCancel={() => setShowDocModal(false)}
        footer={null}
        destroyOnClose
      >
        <Form form={docForm} layout="vertical" onFinish={handleAddDocument}>
          <Form.Item
            name="doc_id"
            label="文档ID"
            rules={[{ required: true, message: '请输入文档ID' }]}
          >
            <Input placeholder="例如: doc_001" />
          </Form.Item>
          <Form.Item
            name="title"
            label="标题"
            rules={[{ required: true, message: '请输入标题' }]}
          >
            <Input placeholder="文档标题" />
          </Form.Item>
          <Form.Item
            name="content"
            label="内容"
            rules={[{ required: true, message: '请输入内容' }]}
          >
            <TextArea rows={4} placeholder="文档内容" />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                保存
              </Button>
              <Button onClick={() => setShowDocModal(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="添加查询"
        open={showQueryModal}
        onCancel={() => setShowQueryModal(false)}
        footer={null}
        destroyOnClose
      >
        <Form form={queryForm} layout="vertical" onFinish={handleAddQuery}>
          <Form.Item
            name="query_id"
            label="查询ID"
            rules={[{ required: true, message: '请输入查询ID' }]}
          >
            <Input placeholder="例如: q_001" />
          </Form.Item>
          <Form.Item
            name="query_text"
            label="查询文本"
            rules={[{ required: true, message: '请输入查询文本' }]}
          >
            <Input placeholder="搜索查询内容" />
          </Form.Item>
          <Form.Item
            name="query_type"
            label="查询类型"
            rules={[{ required: true, message: '请选择查询类型' }]}
          >
            <Select placeholder="请选择查询类型">
              {QUERY_TYPES.map(qt => (
                <Option key={qt.value} value={qt.value}>
                  <Tag color={qt.color} style={{ marginRight: 8 }}>{qt.label}</Tag>
                </Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="description" label="描述">
            <TextArea rows={3} placeholder="查询描述（可选）" />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                保存
              </Button>
              <Button onClick={() => setShowQueryModal(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="添加模型"
        open={showModelModal}
        onCancel={() => setShowModelModal(false)}
        footer={null}
        destroyOnClose
      >
        <Form form={modelForm} layout="vertical" onFinish={handleAddModel}>
          <Form.Item
            name="model_name"
            label="模型名称"
            rules={[{ required: true, message: '请输入模型名称' }]}
          >
            <Input placeholder="例如: bm25_v2" />
          </Form.Item>
          <Form.Item name="description" label="模型描述">
            <TextArea rows={3} placeholder="模型描述信息" />
          </Form.Item>
          <Form.Item name="endpoint" label="API Endpoint">
            <Input placeholder="http://localhost:8080/search" />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                保存
              </Button>
              <Button onClick={() => setShowModelModal(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default DataManagement;

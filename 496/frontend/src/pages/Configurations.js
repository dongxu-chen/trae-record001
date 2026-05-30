import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Tag,
  Button,
  Switch,
  Modal,
  message,
  Space,
  Descriptions,
  Row,
  Col,
} from 'antd';
import {
  EditOutlined,
  DeleteOutlined,
  DownloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import { rateLimitAPI, topologyAPI } from '../services/api';

function Configurations() {
  const [loading, setLoading] = useState(true);
  const [configs, setConfigs] = useState({});
  const [services, setServices] = useState([]);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selectedConfig, setSelectedConfig] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [configsRes, servicesRes] = await Promise.all([
        rateLimitAPI.getAllConfigs(),
        topologyAPI.getServices(),
      ]);
      setConfigs(configsRes.data);
      setServices(servicesRes.data);
    } catch (error) {
      console.error('Failed to load configurations:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleConfig = async (serviceId, enabled) => {
    try {
      await rateLimitAPI.toggleConfig(serviceId, enabled);
      message.success(`配置已${enabled ? '启用' : '禁用'}`);
      loadData();
    } catch (error) {
      message.error('操作失败');
    }
  };

  const deleteConfig = async (serviceId) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除此限流配置吗？',
      onOk: async () => {
        try {
          await rateLimitAPI.deleteConfig(serviceId);
          message.success('配置已删除');
          loadData();
        } catch (error) {
          message.error('删除失败');
        }
      },
    });
  };

  const exportConfig = async (serviceId) => {
    try {
      const res = await rateLimitAPI.exportConfig(serviceId);
      const blob = new Blob([res.data], { type: 'text/yaml' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ratelimit-${serviceId}.yaml`;
      a.click();
      URL.revokeObjectURL(url);
      message.success('配置已导出');
    } catch (error) {
      message.error('导出失败');
    }
  };

  const viewDetail = (config) => {
    setSelectedConfig(config);
    setDetailModalVisible(true);
  };

  const configList = Object.entries(configs).map(([serviceId, config]) => ({
    serviceId,
    ...config,
  }));

  const columns = [
    {
      title: '服务ID',
      dataIndex: 'serviceId',
      key: 'serviceId',
      render: (id) => {
        const service = services.find(s => s.serviceId === id);
        return service?.serviceName || id;
      },
    },
    {
      title: '服务级QPS',
      dataIndex: ['serviceLevelRule', 'qpsThreshold'],
      key: 'serviceQps',
    },
    {
      title: '突发容量',
      dataIndex: ['serviceLevelRule', 'burstCapacity'],
      key: 'burst',
    },
    {
      title: '接口规则数',
      key: 'apiCount',
      render: (_, record) => Object.keys(record.apiLevelRules || {}).length,
    },
    {
      title: '策略',
      dataIndex: 'strategy',
      key: 'strategy',
      render: (v) => <Tag color="blue">{v}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'status',
      render: (enabled, record) => (
        <Switch
          checked={enabled}
          checkedChildren="启用"
          unCheckedChildren="禁用"
          onChange={(val) => toggleConfig(record.serviceId, val)}
        />
      ),
    },
    {
      title: '更新时间',
      key: 'updateTime',
      render: (_, record) => new Date(record.updateTime).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={() => viewDetail(record)}
          >
            详情
          </Button>
          <Button
            type="text"
            size="small"
            icon={<DownloadOutlined />}
            onClick={() => exportConfig(record.serviceId)}
          >
            导出
          </Button>
          <Button
            type="text"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => deleteConfig(record.serviceId)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>配置管理</h2>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <CheckCircleOutlined style={{ fontSize: 24, color: '#52c41a' }} />
              <div>
                <div style={{ fontSize: 24, fontWeight: 'bold' }}>
                  {configList.filter(c => c.enabled).length}
                </div>
                <div style={{ color: '#666' }}>已启用配置</div>
              </div>
            </div>
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <CloseCircleOutlined style={{ fontSize: 24, color: '#ff4d4f' }} />
              <div>
                <div style={{ fontSize: 24, fontWeight: 'bold' }}>
                  {configList.filter(c => !c.enabled).length}
                </div>
                <div style={{ color: '#666' }}>已禁用配置</div>
              </div>
            </div>
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <DownloadOutlined style={{ fontSize: 24, color: '#1890ff' }} />
              <div>
                <div style={{ fontSize: 24, fontWeight: 'bold' }}>
                  {configList.length}
                </div>
                <div style={{ color: '#666' }}>配置总数</div>
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      <Card title="限流配置列表" loading={loading}>
        <Table
          columns={columns}
          dataSource={configList}
          rowKey="serviceId"
          pagination={{ pageSize: 10 }}
          locale={{
            emptyText: '暂无配置，请在"限流推荐"页面应用推荐配置',
          }}
        />
      </Card>

      <Modal
        title="配置详情"
        visible={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            关闭
          </Button>,
        ]}
        width={800}
      >
        {selectedConfig && (
          <div>
            <Descriptions bordered column={2}>
              <Descriptions.Item label="服务ID" span={2}>
                {selectedConfig.serviceId}
              </Descriptions.Item>
              <Descriptions.Item label="服务级QPS">
                {selectedConfig.serviceLevelRule?.qpsThreshold}
              </Descriptions.Item>
              <Descriptions.Item label="突发容量">
                {selectedConfig.serviceLevelRule?.burstCapacity}
              </Descriptions.Item>
              <Descriptions.Item label="限流类型">
                {selectedConfig.serviceLevelRule?.limitType}
              </Descriptions.Item>
              <Descriptions.Item label="降级策略">
                {selectedConfig.serviceLevelRule?.fallbackStrategy}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间" span={2}>
                {new Date(selectedConfig.createTime).toLocaleString('zh-CN')}
              </Descriptions.Item>
              <Descriptions.Item label="更新时间" span={2}>
                {new Date(selectedConfig.updateTime).toLocaleString('zh-CN')}
              </Descriptions.Item>
            </Descriptions>

            {Object.keys(selectedConfig.apiLevelRules || {}).length > 0 && (
              <div style={{ marginTop: 24 }}>
                <h4>接口级规则</h4>
                <Table
                  dataSource={Object.entries(selectedConfig.apiLevelRules).map(([path, rule]) => ({
                    key: path,
                    path,
                    ...rule,
                  }))}
                  columns={[
                    { title: '接口路径', dataIndex: 'path', key: 'path' },
                    { title: 'QPS阈值', dataIndex: 'qpsThreshold', key: 'qps' },
                    { title: '突发容量', dataIndex: 'burstCapacity', key: 'burst' },
                    { title: '限流类型', dataIndex: 'limitType', key: 'type' },
                  ]}
                  pagination={false}
                  size="small"
                />
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}

export default Configurations;

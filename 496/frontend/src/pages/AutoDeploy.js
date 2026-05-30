import React, { useState, useEffect } from 'react';
import {
  Card, Button, Table, Tag, Steps, message, Row, Col, Statistic,
  Modal, Space, Alert, Descriptions, Result,
} from 'antd';
import {
  RocketOutlined, RollbackOutlined, CheckCircleOutlined,
  CloseCircleOutlined, CloudUploadOutlined, HistoryOutlined,
} from '@ant-design/icons';
import { deployAPI, topologyAPI } from '../services/api';

function AutoDeploy() {
  const [loading, setLoading] = useState(false);
  const [deployResult, setDeployResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [services, setServices] = useState([]);
  const [rollbackModalVisible, setRollbackModalVisible] = useState(false);
  const [selectedDeploy, setSelectedDeploy] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [servicesRes, historyRes] = await Promise.all([
        topologyAPI.getServices(),
        deployAPI.getHistory(),
      ]);
      setServices(servicesRes.data);
      setHistory(historyRes.data);
    } catch (error) {
      console.error('Failed to load data:', error);
    }
  };

  const deployToGateway = async () => {
    try {
      setLoading(true);
      const res = await deployAPI.deployToGateway('gateway', true);
      setDeployResult(res.data);
      message.success('限流配置已自动部署到网关');
      loadData();
    } catch (error) {
      message.error('部署失败');
    } finally {
      setLoading(false);
    }
  };

  const deploySingleService = async (serviceId) => {
    try {
      setLoading(true);
      const res = await deployAPI.deployService(serviceId);
      setDeployResult(res.data);
      message.success(`${serviceId} 限流配置已部署`);
      loadData();
    } catch (error) {
      message.error('部署失败');
    } finally {
      setLoading(false);
    }
  };

  const handleRollback = async (deployId) => {
    try {
      await deployAPI.rollback(deployId);
      message.success('已回滚');
      setRollbackModalVisible(false);
      loadData();
    } catch (error) {
      message.error('回滚失败');
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'SUCCESS': return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'PARTIAL_SUCCESS': return <CloseCircleOutlined style={{ color: '#faad14' }} />;
      case 'FAILED': return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'ROLLED_BACK': return <RollbackOutlined style={{ color: '#999' }} />;
      default: return null;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'SUCCESS': return 'green';
      case 'PARTIAL_SUCCESS': return 'orange';
      case 'FAILED': return 'red';
      case 'ROLLED_BACK': return 'default';
      default: return 'blue';
    }
  };

  const columns = [
    { title: '服务', dataIndex: 'serviceId', key: 'serviceId' },
    { title: 'API路径', dataIndex: 'apiPath', key: 'apiPath' },
    { title: 'QPS阈值', dataIndex: 'qpsThreshold', key: 'qps' },
    { title: '突发容量', dataIndex: 'burstCapacity', key: 'burst' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => <Tag color={getStatusColor(status)} icon={getStatusIcon(status)}>{status}</Tag>,
    },
    { title: '消息', dataIndex: 'message', key: 'message' },
  ];

  const historyColumns = [
    { title: '部署ID', dataIndex: 'deployId', key: 'deployId' },
    { title: '网关', dataIndex: 'gatewayId', key: 'gatewayId' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => <Tag color={getStatusColor(status)}>{status}</Tag>,
    },
    {
      title: '规则数',
      key: 'rules',
      render: (_, r) => `${r.successCount}/${r.totalRules}`,
    },
    {
      title: '部署时间',
      key: 'time',
      render: (_, r) => new Date(r.deployTime).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => record.status === 'SUCCESS' && (
        <Button size="small" danger icon={<RollbackOutlined />}
          onClick={() => { setSelectedDeploy(record); setRollbackModalVisible(true); }}>
          回滚
        </Button>
      ),
    },
  ];

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>自动限流部署</h2>

      <Alert
        message="自动部署到网关"
        description="将推荐的限流阈值自动应用到API网关，支持一键部署、回滚、逐服务部署。"
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card>
            <Statistic title="可用服务" value={services.length} prefix={<CloudUploadOutlined />} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="部署历史" value={history.length} prefix={<HistoryOutlined />} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="成功部署"
              value={history.filter(h => h.status === 'SUCCESS').length}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      <Card style={{ marginBottom: 24 }}>
        <Space>
          <Button
            type="primary"
            icon={<RocketOutlined />}
            size="large"
            loading={loading}
            onClick={deployToGateway}
          >
            一键部署全部到网关
          </Button>
          <span style={{ color: '#666' }}>将所有服务的推荐限流配置自动推送到API网关</span>
        </Space>
      </Card>

      <Card title="逐服务部署" style={{ marginBottom: 24 }}>
        <Table
          columns={[
            { title: '服务名称', dataIndex: 'serviceName', key: 'name' },
            { title: '当前QPS', dataIndex: ['metrics', 'avgQps'], key: 'qps',
              render: v => v?.toFixed(0) || '-' },
            { title: '版本', dataIndex: 'version', key: 'version' },
            {
              title: '操作',
              key: 'action',
              render: (_, record) => (
                <Button
                  type="primary"
                  size="small"
                  icon={<RocketOutlined />}
                  loading={loading}
                  onClick={() => deploySingleService(record.serviceId)}
                >
                  部署此服务
                </Button>
              ),
            },
          ]}
          dataSource={services}
          rowKey="serviceId"
          pagination={false}
        />
      </Card>

      {deployResult && (
        <Card title="最近部署结果" style={{ marginBottom: 24 }}>
          <Descriptions bordered column={3} style={{ marginBottom: 16 }}>
            <Descriptions.Item label="部署ID">{deployResult.deployId}</Descriptions.Item>
            <Descriptions.Item label="网关">{deployResult.gatewayId}</Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={getStatusColor(deployResult.status)}>{deployResult.status}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="成功/总数">{deployResult.successCount}/{deployResult.totalRules}</Descriptions.Item>
            <Descriptions.Item label="网关响应" span={2}>{deployResult.gatewayResponse}</Descriptions.Item>
          </Descriptions>
          <Table columns={columns} dataSource={deployResult.details} rowKey="ruleId" pagination={false} size="small" />
        </Card>
      )}

      <Card title="部署历史">
        <Table columns={historyColumns} dataSource={history} rowKey="deployId" pagination={{ pageSize: 5 }} />
      </Card>

      <Modal
        title="确认回滚"
        visible={rollbackModalVisible}
        onCancel={() => setRollbackModalVisible(false)}
        onOk={() => handleRollback(selectedDeploy?.deployId)}
        okText="确认回滚"
        okButtonProps={{ danger: true }}
      >
        <p>确定要回滚部署 <strong>{selectedDeploy?.deployId}</strong> 吗？</p>
        <p>回滚后网关将恢复到之前的限流配置。</p>
      </Modal>
    </div>
  );
}

export default AutoDeploy;

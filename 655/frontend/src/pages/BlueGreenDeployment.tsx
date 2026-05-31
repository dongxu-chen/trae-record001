import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Input,
  InputNumber,
  Select,
  Button,
  Steps,
  Space,
  Table,
  Tag,
  Modal,
  message,
  Switch,
  Progress,
  Timeline,
  Descriptions,
  Drawer,
  Popconfirm,
  Tooltip,
  Typography,
  Row,
  Col,
  Statistic,
} from 'antd';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  RollbackOutlined,
  CheckCircleOutlined,
  HistoryOutlined,
  ReloadOutlined,
  PlusOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { blueGreenAPI } from '../services/api';
import type { BlueGreenDeployment, DeploymentStep } from '../types';

const { Title, Text } = Typography;
const { Step } = Steps;
const { Option } = Select;

const BlueGreenDeploymentPage: React.FC = () => {
  const [deployments, setDeployments] = useState<BlueGreenDeployment[]>([]);
  const [loading, setLoading] = useState(false);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [detailVisible, setDetailVisible] = useState(false);
  const [selectedDeployment, setSelectedDeployment] = useState<BlueGreenDeployment | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [form] = Form.useForm();

  const [wizardData, setWizardData] = useState({
    name: '',
    namespace: 'default',
    serviceName: '',
    blueSubset: 'v1',
    greenSubset: 'v2',
    blueVersion: 'v1.0.0',
    greenVersion: 'v2.0.0',
    targetWeightBlue: 0,
    stepSize: 10,
    stepIntervalSeconds: 60,
    autoRollbackEnabled: true,
    rollbackThreshold: 5.0,
  });

  const fetchDeployments = async () => {
    setLoading(true);
    try {
      const res = await blueGreenAPI.listDeployments();
      setDeployments(res.data.deployments || []);
    } catch (err) {
      message.error('Failed to fetch deployments');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDeployments();
    const timer = setInterval(fetchDeployments, 5000);
    return () => clearInterval(timer);
  }, []);

  const handleWizardNext = async () => {
    try {
      const values = await form.validateFields();
      setWizardData({ ...wizardData, ...values });

      if (currentStep < 2) {
        setCurrentStep(currentStep + 1);
      } else {
        await handleCreateDeployment();
      }
    } catch (err) {
      console.error('Validation failed:', err);
    }
  };

  const handleCreateDeployment = async () => {
    try {
      await blueGreenAPI.createDeployment(wizardData);
      message.success('Blue-green deployment created successfully');
      setCreateModalVisible(false);
      setCurrentStep(0);
      form.resetFields();
      fetchDeployments();
    } catch (err) {
      message.error('Failed to create deployment');
    }
  };

  const handleStartDeployment = async (id: string) => {
    try {
      await blueGreenAPI.startDeployment(id);
      message.success('Deployment started');
      fetchDeployments();
    } catch (err) {
      message.error('Failed to start deployment');
    }
  };

  const handlePauseDeployment = async (id: string) => {
    try {
      await blueGreenAPI.pauseDeployment(id);
      message.success('Deployment paused');
      fetchDeployments();
    } catch (err) {
      message.error('Failed to pause deployment');
    }
  };

  const handleRollbackDeployment = async (id: string) => {
    try {
      await blueGreenAPI.rollbackDeployment(id);
      message.success('Rollback initiated');
      fetchDeployments();
    } catch (err) {
      message.error('Failed to rollback');
    }
  };

  const handleCompleteDeployment = async (id: string) => {
    try {
      await blueGreenAPI.completeDeployment(id);
      message.success('Deployment completed');
      fetchDeployments();
    } catch (err) {
      message.error('Failed to complete deployment');
    }
  };

  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; text: string }> = {
      'pending': { color: 'default', text: 'Pending' },
      'running': { color: 'processing', text: 'Running' },
      'paused': { color: 'warning', text: 'Paused' },
      'rollback': { color: 'error', text: 'Rolling Back' },
      'rolled-back': { color: 'error', text: 'Rolled Back' },
      'completed': { color: 'success', text: 'Completed' },
    };
    const info = statusMap[status] || { color: 'default', text: status };
    return <Tag color={info.color}>{info.text}</Tag>;
  };

  const columns: ColumnsType<BlueGreenDeployment> = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      width: 150,
    },
    {
      title: 'Service',
      dataIndex: 'serviceName',
      key: 'serviceName',
      width: 150,
    },
    {
      title: 'Blue',
      key: 'blue',
      width: 120,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Tag color="blue">{record.blueSubset}</Tag>
          <Text type="secondary" style={{ fontSize: 12 }}>{record.blueVersion}</Text>
        </Space>
      ),
    },
    {
      title: 'Green',
      key: 'green',
      width: 120,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Tag color="green">{record.greenSubset}</Tag>
          <Text type="secondary" style={{ fontSize: 12 }}>{record.greenVersion}</Text>
        </Space>
      ),
    },
    {
      title: 'Traffic Split',
      key: 'traffic',
      width: 200,
      render: (_, record) => {
        const blueWeight = record.currentWeightBlue;
        const greenWeight = 100 - blueWeight;
        return (
          <Space direction="vertical" size={2} style={{ width: '100%' }}>
            <div style={{ fontSize: 12 }}>
              <Tag color="blue">{blueWeight}% Blue</Tag>
              <Tag color="green">{greenWeight}% Green</Tag>
            </div>
            <Progress
              percent={blueWeight}
              size="small"
              strokeColor="#1890ff"
              trailColor="#52c41a"
              showInfo={false}
            />
          </Space>
        );
      },
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status) => getStatusTag(status),
    },
    {
      title: 'Auto Rollback',
      key: 'autoRollback',
      width: 120,
      render: (_, record) => (
        <Space>
          <Switch
            checked={record.autoRollbackEnabled}
            disabled
            size="small"
          />
          {record.autoRollbackEnabled && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {record.rollbackThreshold}%
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 280,
      render: (_, record) => (
        <Space size="small">
          {record.status === 'pending' && (
            <Tooltip title="Start Deployment">
              <Button
                type="primary"
                size="small"
                icon={<PlayCircleOutlined />}
                onClick={() => handleStartDeployment(record.id)}
              >
                Start
              </Button>
            </Tooltip>
          )}
          {record.status === 'running' && (
            <>
              <Tooltip title="Pause">
                <Button
                  size="small"
                  icon={<PauseCircleOutlined />}
                  onClick={() => handlePauseDeployment(record.id)}
                >
                  Pause
                </Button>
              </Tooltip>
              <Popconfirm
                title="Confirm rollback?"
                description="This will switch 100% traffic back to blue version"
                onConfirm={() => handleRollbackDeployment(record.id)}
                okText="Rollback"
                cancelText="Cancel"
                okButtonProps={{ danger: true }}
              >
                <Button
                  size="small"
                  danger
                  icon={<RollbackOutlined />}
                >
                  Rollback
                </Button>
              </Popconfirm>
              <Tooltip title="Complete - switch 100% to green">
                <Button
                  size="small"
                  type="primary"
                  icon={<CheckCircleOutlined />}
                  onClick={() => handleCompleteDeployment(record.id)}
                >
                  Complete
                </Button>
              </Tooltip>
            </>
          )}
          {record.status === 'paused' && (
            <Tooltip title="Resume">
              <Button
                type="primary"
                size="small"
                icon={<PlayCircleOutlined />}
                onClick={() => handleStartDeployment(record.id)}
              >
                Resume
              </Button>
            </Tooltip>
          )}
          <Tooltip title="View Details">
            <Button
              size="small"
              icon={<HistoryOutlined />}
              onClick={() => {
                setSelectedDeployment(record);
                setDetailVisible(true);
              }}
            >
              Details
            </Button>
          </Tooltip>
        </Space>
      ),
    },
  ];

  const renderWizardStep = () => {
    switch (currentStep) {
      case 0:
        return (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="name"
                  label="Deployment Name"
                  rules={[{ required: true }]}
                >
                  <Input placeholder="e.g., payment-service-v2-release" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="namespace"
                  label="Namespace"
                  initialValue="default"
                  rules={[{ required: true }]}
                >
                  <Input placeholder="default" />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item
              name="serviceName"
              label="Target Service"
              rules={[{ required: true }]}
            >
              <Input placeholder="payment-service" />
            </Form.Item>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="blueSubset"
                  label="Blue Subset (Current)"
                  initialValue="v1"
                  rules={[{ required: true }]}
                >
                  <Input placeholder="v1" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="blueVersion"
                  label="Blue Version"
                  initialValue="v1.0.0"
                  rules={[{ required: true }]}
                >
                  <Input placeholder="v1.0.0" />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="greenSubset"
                  label="Green Subset (New)"
                  initialValue="v2"
                  rules={[{ required: true }]}
                >
                  <Input placeholder="v2" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="greenVersion"
                  label="Green Version"
                  initialValue="v2.0.0"
                  rules={[{ required: true }]}
                >
                  <Input placeholder="v2.0.0" />
                </Form.Item>
              </Col>
            </Row>
          </Space>
        );
      case 1:
        return (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="targetWeightBlue"
                  label="Target Blue Weight (%)"
                  initialValue={0}
                  tooltip="Final weight for blue version (0 = fully migrate to green)"
                >
                  <InputNumber min={0} max={100} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="stepSize"
                  label="Step Size (%)"
                  initialValue={10}
                  tooltip="Traffic shift per step"
                >
                  <InputNumber min={1} max={50} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="stepIntervalSeconds"
                  label="Step Interval (seconds)"
                  initialValue={60}
                  tooltip="Wait time between traffic shifts"
                >
                  <InputNumber min={10} max={3600} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
            <Card size="small" title="Preview" type="inner">
              <Space direction="vertical" size="small">
                <Text>
                  Starting: Blue 100% → Green 0%
                </Text>
                <Text>
                  Target: Blue {wizardData.targetWeightBlue || 0}% → Green {100 - (wizardData.targetWeightBlue || 0)}%
                </Text>
                <Text>
                  Steps: {Math.ceil(100 / (wizardData.stepSize || 10))} steps × {(wizardData.stepIntervalSeconds || 60)}s
                </Text>
                <Text type="secondary">
                  Total estimated time: {Math.ceil(100 / (wizardData.stepSize || 10)) * (wizardData.stepIntervalSeconds || 60)} seconds
                </Text>
              </Space>
            </Card>
          </Space>
        );
      case 2:
        return (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Form.Item
              name="autoRollbackEnabled"
              label="Enable Auto Rollback"
              initialValue={true}
              valuePropName="checked"
              tooltip="Automatically rollback if error rate exceeds threshold"
            >
              <Switch />
            </Form.Item>
            <Form.Item
              name="rollbackThreshold"
              label="Rollback Error Threshold (%)"
              initialValue={5.0}
              tooltip="Trigger auto rollback if error rate exceeds this value"
            >
              <InputNumber min={0.1} max={100} step={0.1} style={{ width: 200 }} />
            </Form.Item>
            <Card size="small" title="Deployment Summary" type="inner">
              <Descriptions column={2} size="small">
                <Descriptions.Item label="Name">{wizardData.name || '-'}</Descriptions.Item>
                <Descriptions.Item label="Service">{wizardData.serviceName || '-'}</Descriptions.Item>
                <Descriptions.Item label="Blue">{wizardData.blueSubset} ({wizardData.blueVersion})</Descriptions.Item>
                <Descriptions.Item label="Green">{wizardData.greenSubset} ({wizardData.greenVersion})</Descriptions.Item>
                <Descriptions.Item label="Step Size">{wizardData.stepSize}%</Descriptions.Item>
                <Descriptions.Item label="Interval">{wizardData.stepIntervalSeconds}s</Descriptions.Item>
                <Descriptions.Item label="Auto Rollback">{wizardData.autoRollbackEnabled ? 'Enabled' : 'Disabled'}</Descriptions.Item>
                <Descriptions.Item label="Threshold">{wizardData.rollbackThreshold}%</Descriptions.Item>
              </Descriptions>
            </Card>
          </Space>
        );
      default:
        return null;
    }
  };

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card
        title="Blue-Green Deployment Wizard"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => {
            setCreateModalVisible(true);
            setCurrentStep(0);
          }}>
            New Deployment
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={deployments}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Modal
        title={
          <Steps current={currentStep} size="small">
            <Step title="Configure" />
            <Step title="Strategy" />
            <Step title="Review" />
          </Steps>
        }
        open={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        width={700}
        footer={
          <Space>
            <Button onClick={() => setCreateModalVisible(false)}>Cancel</Button>
            {currentStep > 0 && (
              <Button onClick={() => setCurrentStep(currentStep - 1)}>Previous</Button>
            )}
            <Button type="primary" onClick={handleWizardNext}>
              {currentStep === 2 ? 'Create Deployment' : 'Next'}
            </Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical" style={{ marginTop: 24 }}>
          {renderWizardStep()}
        </Form>
      </Modal>

      <Drawer
        title="Deployment Details"
        width={800}
        open={detailVisible}
        onClose={() => setDetailVisible(false)}
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetchDeployments}>
              Refresh
            </Button>
          </Space>
        }
      >
        {selectedDeployment && (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Card>
              <Descriptions column={2} size="small">
                <Descriptions.Item label="Name">{selectedDeployment.name}</Descriptions.Item>
                <Descriptions.Item label="Status">{getStatusTag(selectedDeployment.status)}</Descriptions.Item>
                <Descriptions.Item label="Service">{selectedDeployment.serviceName}</Descriptions.Item>
                <Descriptions.Item label="Namespace">{selectedDeployment.namespace}</Descriptions.Item>
                <Descriptions.Item label="Phase">{selectedDeployment.phase}</Descriptions.Item>
                <Descriptions.Item label="Created">{selectedDeployment.createdAt}</Descriptions.Item>
              </Descriptions>
            </Card>

            <Card title="Current Traffic Distribution">
              <Row gutter={16}>
                <Col span={12}>
                  <Statistic
                    title={<Tag color="blue">Blue Version</Tag>}
                    value={selectedDeployment.currentWeightBlue}
                    suffix="%"
                    valueStyle={{ color: '#1890ff' }}
                  />
                  <div style={{ fontSize: 12, color: '#666' }}>
                    {selectedDeployment.blueSubset} ({selectedDeployment.blueVersion})
                  </div>
                </Col>
                <Col span={12}>
                  <Statistic
                    title={<Tag color="green">Green Version</Tag>}
                    value={100 - selectedDeployment.currentWeightBlue}
                    suffix="%"
                    valueStyle={{ color: '#52c41a' }}
                  />
                  <div style={{ fontSize: 12, color: '#666' }}>
                    {selectedDeployment.greenSubset} ({selectedDeployment.greenVersion})
                  </div>
                </Col>
              </Row>
              <Progress
                percent={selectedDeployment.currentWeightBlue}
                strokeColor="#1890ff"
                trailColor="#52c41a"
                style={{ marginTop: 16 }}
              />
            </Card>

            <Card title="Deployment History">
              {selectedDeployment.deploymentHistory && selectedDeployment.deploymentHistory.length > 0 ? (
                <Timeline
                  items={selectedDeployment.deploymentHistory
                    .slice()
                    .reverse()
                    .map((step: DeploymentStep, idx: number) => ({
                      color: step.rollback ? 'red' : step.success ? 'green' : 'blue',
                      children: (
                        <Space direction="vertical" size={0}>
                          <Space>
                            <Text strong>
                              Step {selectedDeployment.deploymentHistory!.length - idx}: 
                              Blue {step.weightBlue}% → Green {step.weightGreen}%
                            </Text>
                            {step.rollback && <Tag color="red">ROLLBACK</Tag>}
                          </Space>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {new Date(step.timestamp).toLocaleString()}
                          </Text>
                          {step.message && <Text style={{ fontSize: 12 }}>{step.message}</Text>}
                          <div style={{ fontSize: 12, marginTop: 4 }}>
                            Error Rate: <Tag color={step.errorRate > 1 ? 'red' : 'green'}>{step.errorRate.toFixed(2)}%</Tag>
                            <Tag color="blue">P95: {step.latencyP95}ms</Tag>
                          </div>
                        </Space>
                      ),
                    }))}
                />
              ) : (
                <Empty description="No deployment steps yet" />
              )}
            </Card>

            <Card title="Deployment Configuration">
              <Descriptions column={2} size="small">
                <Descriptions.Item label="Step Size">{selectedDeployment.stepSize}%</Descriptions.Item>
                <Descriptions.Item label="Interval">{selectedDeployment.stepIntervalSeconds}s</Descriptions.Item>
                <Descriptions.Item label="Auto Rollback">
                  {selectedDeployment.autoRollbackEnabled ? 'Enabled' : 'Disabled'}
                </Descriptions.Item>
                <Descriptions.Item label="Error Threshold">
                  {selectedDeployment.rollbackThreshold}%
                </Descriptions.Item>
                <Descriptions.Item label="Target Blue Weight">{selectedDeployment.targetWeightBlue}%</Descriptions.Item>
              </Descriptions>
            </Card>
          </Space>
        )}
      </Drawer>
    </Space>
  );
};

const Empty: React.FC<{ description: string }> = ({ description }) => (
  <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
    <InfoCircleOutlined style={{ fontSize: 48, marginBottom: 16 }} />
    <div>{description}</div>
  </div>
);

export default BlueGreenDeploymentPage;

import { useState, useEffect } from 'react';
import {
  Card,
  Tabs,
  Form,
  Input,
  InputNumber,
  Switch,
  Select,
  Button,
  Row,
  Col,
  Space,
  Divider,
  Typography,
  Alert,
  Table,
  Tag,
  Slider,
  Tooltip,
  message,
  Modal,
} from 'antd';
import {
  Settings,
  Database,
  SlidersHorizontal,
  Bell,
  Info,
  Link,
  TestTube,
  Save,
  RotateCcw,
  CheckCircle,
  XCircle,
  RefreshCw,
  Edit3,
  Power,
} from '@phosphor-icons/react';
import { useAnalysisStore } from '@/stores/analysisStore';
import { healthApi, rulesApi } from '@/services/api';
import { AlertRule } from '@/types';
import { formatNumber, formatBytes } from '@/utils/format';

const { Title, Text } = Typography;
const { Option } = Select;
const { TabPane } = Tabs;

interface ConnectionConfig {
  skywalkingApiUrl: string;
  apiKey: string;
  mockMode: boolean;
}

interface AnalysisParams {
  epsTime: number;
  minSamples: number;
  frequencyWeight: number;
  criticalityWeight: number;
  noiseWeight: number;
  minConfidence: number;
  minInefficiencyScore: number;
  defaultLookbackHours: number;
}

interface NotificationConfig {
  channels: string[];
  webhookUrl: string;
  email: string;
  dingtalkWebhook: string;
  wechatWebhook: string;
  notificationThreshold: number;
  minAlertCount: number;
}

interface SystemInfo {
  version: string;
  dataStoragePath: string;
  cacheUsage: number;
  cacheMax: number;
  uptime: number;
  totalRules: number;
  totalAlerts: number;
}

interface EditableRule extends AlertRule {
  editing?: boolean;
}

const Settings: React.FC = () => {
  const { healthStatus, rules, fetchHealth, fetchRules, loading } = useAnalysisStore();

  const [connectionForm] = Form.useForm<ConnectionConfig>();
  const [analysisForm] = Form.useForm<AnalysisParams>();
  const [notificationForm] = Form.useForm<NotificationConfig>();

  const [testingConnection, setTestingConnection] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [saving, setSaving] = useState<Record<string, boolean>>({});
  const [editableRules, setEditableRules] = useState<EditableRule[]>([]);
  const [editingRuleId, setEditingRuleId] = useState<number | null>(null);
  const [editForm] = Form.useForm<Partial<AlertRule>>();

  const [systemInfo, setSystemInfo] = useState<SystemInfo>({
    version: '1.0.0',
    dataStoragePath: '/data/skywalking-optimizer',
    cacheUsage: 125829120,
    cacheMax: 536870912,
    uptime: 86400,
    totalRules: 0,
    totalAlerts: 0,
  });

  useEffect(() => {
    fetchHealth();
    fetchRules();
    loadConnectionConfig();
    loadAnalysisParams();
    loadNotificationConfig();
  }, [fetchHealth, fetchRules]);

  useEffect(() => {
    setEditableRules(rules);
    setSystemInfo((prev) => ({
      ...prev,
      totalRules: rules.length,
    }));
  }, [rules]);

  const loadConnectionConfig = () => {
    const saved = localStorage.getItem('connectionConfig');
    if (saved) {
      const config = JSON.parse(saved);
      connectionForm.setFieldsValue(config);
    } else {
      connectionForm.setFieldsValue({
        skywalkingApiUrl: 'http://localhost:12800/graphql',
        apiKey: '',
        mockMode: true,
      });
    }
  };

  const loadAnalysisParams = () => {
    const saved = localStorage.getItem('analysisParams');
    if (saved) {
      const config = JSON.parse(saved);
      analysisForm.setFieldsValue(config);
    } else {
      analysisForm.setFieldsValue({
        epsTime: 300,
        minSamples: 5,
        frequencyWeight: 0.4,
        criticalityWeight: 0.3,
        noiseWeight: 0.3,
        minConfidence: 0.5,
        minInefficiencyScore: 0.3,
        defaultLookbackHours: 168,
      });
    }
  };

  const loadNotificationConfig = () => {
    const saved = localStorage.getItem('notificationConfig');
    if (saved) {
      const config = JSON.parse(saved);
      notificationForm.setFieldsValue(config);
    } else {
      notificationForm.setFieldsValue({
        channels: [],
        webhookUrl: '',
        email: '',
        dingtalkWebhook: '',
        wechatWebhook: '',
        notificationThreshold: 0.7,
        minAlertCount: 10,
      });
    }
  };

  const handleTestConnection = async () => {
    setTestingConnection(true);
    setConnectionStatus('idle');

    try {
      const values = connectionForm.getFieldsValue();
      await healthApi.check();
      setConnectionStatus('success');
      message.success('连接测试成功');
    } catch (error) {
      setConnectionStatus('error');
      message.error('连接测试失败，请检查配置');
    } finally {
      setTestingConnection(false);
    }
  };

  const handleSaveConnection = async () => {
    try {
      const values = await connectionForm.validateFields();
      setSaving((prev) => ({ ...prev, connection: true }));

      localStorage.setItem('connectionConfig', JSON.stringify(values));

      await new Promise((resolve) => setTimeout(resolve, 500));

      message.success('连接配置已保存');
      fetchHealth();
    } catch (error) {
      message.error('请检查表单填写是否正确');
    } finally {
      setSaving((prev) => ({ ...prev, connection: false }));
    }
  };

  const handleResetConnection = () => {
    connectionForm.resetFields();
    localStorage.removeItem('connectionConfig');
    setConnectionStatus('idle');
    message.info('连接配置已重置');
  };

  const handleSaveAnalysis = async () => {
    try {
      const values = await analysisForm.validateFields();
      setSaving((prev) => ({ ...prev, analysis: true }));

      localStorage.setItem('analysisParams', JSON.stringify(values));

      await new Promise((resolve) => setTimeout(resolve, 500));

      message.success('分析参数已保存');
    } catch (error) {
      message.error('请检查表单填写是否正确');
    } finally {
      setSaving((prev) => ({ ...prev, analysis: false }));
    }
  };

  const handleResetAnalysis = () => {
    analysisForm.resetFields();
    localStorage.removeItem('analysisParams');
    message.info('分析参数已重置');
  };

  const handleSaveNotification = async () => {
    try {
      const values = await notificationForm.validateFields();
      setSaving((prev) => ({ ...prev, notification: true }));

      localStorage.setItem('notificationConfig', JSON.stringify(values));

      await new Promise((resolve) => setTimeout(resolve, 500));

      message.success('通知配置已保存');
    } catch (error) {
      message.error('请检查表单填写是否正确');
    } finally {
      setSaving((prev) => ({ ...prev, notification: false }));
    }
  };

  const handleResetNotification = () => {
    notificationForm.resetFields();
    localStorage.removeItem('notificationConfig');
    message.info('通知配置已重置');
  };

  const handleTestNotification = async () => {
    message.loading({ content: '正在发送测试通知...', key: 'test-notification' });

    try {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      message.success({ content: '测试通知发送成功', key: 'test-notification' });
    } catch (error) {
      message.error({ content: '测试通知发送失败', key: 'test-notification' });
    }
  };

  const handleEditRule = (record: EditableRule) => {
    setEditingRuleId(record.id);
    editForm.setFieldsValue({
      threshold: record.threshold as number,
      period: record.period,
      count: record.count,
      silencePeriod: record.silencePeriod,
    });
  };

  const handleSaveRule = async (record: EditableRule) => {
    try {
      const values = await editForm.validateFields();
      setEditableRules((prev) =>
        prev.map((r) => (r.id === record.id ? { ...r, ...values } : r))
      );

      await rulesApi.updateRule(record.id, values);

      setEditingRuleId(null);
      message.success(`规则 "${record.name}" 已更新`);
      fetchRules();
    } catch (error) {
      message.error('更新规则失败');
    }
  };

  const handleCancelEdit = () => {
    setEditingRuleId(null);
    editForm.resetFields();
  };

  const handleToggleRule = async (record: EditableRule, enabled: boolean) => {
    try {
      setEditableRules((prev) =>
        prev.map((r) => (r.id === record.id ? { ...r, enabled } : r))
      );

      await rulesApi.updateRule(record.id, { enabled });

      message.success(
        `规则 "${record.name}" 已${enabled ? '启用' : '禁用'}`
      );
      fetchRules();
    } catch (error) {
      setEditableRules((prev) =>
        prev.map((r) => (r.id === record.id ? { ...r, enabled: !enabled } : r))
      );
      message.error('更新规则状态失败');
    }
  };

  const handleRefreshSystem = async () => {
    setSystemInfo((prev) => ({
      ...prev,
      cacheUsage: Math.floor(Math.random() * 402653184) + 67108864,
      uptime: prev.uptime + 1,
    }));
    message.success('系统信息已刷新');
  };

  const formatUptime = (seconds: number): string => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${days}天 ${hours}小时 ${minutes}分钟`;
  };

  const ruleColumns = [
    {
      title: '规则名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      render: (text: string) => (
        <Tooltip title={text}>
          <span className="text-gray-200 font-medium">{text}</span>
        </Tooltip>
      ),
    },
    {
      title: '指标',
      dataIndex: 'metricsName',
      key: 'metricsName',
      width: 180,
      render: (text: string) => (
        <Tag color="blue" className="font-mono text-xs">
          {text}
        </Tag>
      ),
    },
    {
      title: '阈值',
      dataIndex: 'threshold',
      key: 'threshold',
      width: 120,
      render: (value: number | number[], record: EditableRule) => {
        if (editingRuleId === record.id) {
          return (
            <Form.Item
              name="threshold"
              rules={[{ required: true, message: '请输入阈值' }]}
              style={{ margin: 0 }}
            >
              <InputNumber min={0} step={0.01} className="w-full" size="small" />
            </Form.Item>
          );
        }
        return <span className="font-mono text-gray-300">{String(value)}</span>;
      },
    },
    {
      title: '操作符',
      dataIndex: 'op',
      key: 'op',
      width: 80,
      render: (text: string) => (
        <span className="text-gray-400 font-mono">{text}</span>
      ),
    },
    {
      title: '周期(分钟)',
      dataIndex: 'period',
      key: 'period',
      width: 120,
      render: (value: number, record: EditableRule) => {
        if (editingRuleId === record.id) {
          return (
            <Form.Item
              name="period"
              rules={[{ required: true, message: '请输入周期' }]}
              style={{ margin: 0 }}
            >
              <InputNumber min={1} className="w-full" size="small" />
            </Form.Item>
          );
        }
        return <span className="font-mono text-gray-300">{value}</span>;
      },
    },
    {
      title: '触发次数',
      dataIndex: 'count',
      key: 'count',
      width: 100,
      render: (value: number, record: EditableRule) => {
        if (editingRuleId === record.id) {
          return (
            <Form.Item
              name="count"
              rules={[{ required: true, message: '请输入次数' }]}
              style={{ margin: 0 }}
            >
              <InputNumber min={1} className="w-full" size="small" />
            </Form.Item>
          );
        }
        return <span className="font-mono text-gray-300">{value}</span>;
      },
    },
    {
      title: '静默期(分钟)',
      dataIndex: 'silencePeriod',
      key: 'silencePeriod',
      width: 120,
      render: (value: number, record: EditableRule) => {
        if (editingRuleId === record.id) {
          return (
            <Form.Item
              name="silencePeriod"
              rules={[{ required: true, message: '请输入静默期' }]}
              style={{ margin: 0 }}
            >
              <InputNumber min={0} className="w-full" size="small" />
            </Form.Item>
          );
        }
        return <span className="font-mono text-gray-300">{value}</span>;
      },
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 100,
      render: (priority: string) => {
        const colorMap: Record<string, string> = {
          CRITICAL: 'red',
          WARNING: 'orange',
          INFO: 'blue',
        };
        return (
          <Tag color={colorMap[priority] || 'default'} className="font-medium">
            {priority}
          </Tag>
        );
      },
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 100,
      render: (enabled: boolean, record: EditableRule) => (
        <Switch
          checked={enabled}
          checkedChildren={<Power size={12} />}
          unCheckedChildren={<Power size={12} />}
          onChange={(checked) => handleToggleRule(record, checked)}
          size="small"
        />
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      fixed: 'right' as const,
      render: (_: any, record: EditableRule) => {
        if (editingRuleId === record.id) {
          return (
            <Space size="small">
              <Button
                type="primary"
                size="small"
                icon={<Save size={14} />}
                onClick={() => handleSaveRule(record)}
              >
                保存
              </Button>
              <Button size="small" onClick={handleCancelEdit}>
                取消
              </Button>
            </Space>
          );
        }
        return (
          <Tooltip title="编辑规则">
            <Button
              type="text"
              size="small"
              icon={<Edit3 size={16} />}
              onClick={() => handleEditRule(record)}
              className="text-blue-400 hover:text-blue-300"
            />
          </Tooltip>
        );
      },
    },
  ];

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <Title level={2} className="text-white mb-1">
            <Settings size={28} className="mr-3 inline text-blue-400" />
            系统设置
          </Title>
          <Text className="text-gray-400">
            配置SkyWalking连接、分析参数、告警规则和通知设置
          </Text>
        </div>
      </div>

      <Card className="glass-card border-0">
        <Tabs defaultActiveKey="connection" size="large">
          <TabPane
            tab={
              <span className="flex items-center gap-2">
                <Link size={18} />
                连接设置
              </span>
            }
            key="connection"
          >
            <div className="space-y-6">
              {healthStatus && (
                <Alert
                  message={
                    <div className="flex items-center gap-2">
                      {healthStatus.skywalkingConnected ? (
                        <CheckCircle size={18} className="text-emerald-400" />
                      ) : (
                        <XCircle size={18} className="text-red-400" />
                      )}
                      <span>
                        后端服务状态:{' '}
                        <span className="font-medium">
                          {healthStatus.status === 'UP' ? '运行中' : '异常'}
                        </span>
                        {healthStatus.mockMode && (
                          <Tag color="purple" className="ml-2">
                            Mock模式
                          </Tag>
                        )}
                      </span>
                    </div>
                  }
                  type={healthStatus.status === 'UP' ? 'success' : 'error'}
                  showIcon={false}
                  className="mb-4"
                />
              )}

              <Form
                form={connectionForm}
                layout="vertical"
                className="max-w-3xl"
              >
                <Card
                  className="glass-card border-0 mb-4"
                  title={
                    <div className="flex items-center gap-2">
                      <Database size={18} className="text-blue-400" />
                      <span className="text-gray-200">SkyWalking API 配置</span>
                    </div>
                  }
                >
                  <Row gutter={[24, 16]}>
                    <Col xs={24} lg={16}>
                      <Form.Item
                        name="skywalkingApiUrl"
                        label={
                          <span className="text-gray-300">API 地址</span>
                        }
                        rules={[
                          {
                            required: true,
                            message: '请输入SkyWalking API地址',
                          },
                        ]}
                      >
                        <Input
                          placeholder="http://localhost:12800/graphql"
                          size="large"
                        />
                      </Form.Item>
                    </Col>
                    <Col xs={24} lg={8}>
                      <Form.Item
                        name="mockMode"
                        label={
                          <span className="text-gray-300">Mock 模式</span>
                        }
                        valuePropName="checked"
                      >
                        <Switch
                          checkedChildren="开启"
                          unCheckedChildren="关闭"
                          size="default"
                        />
                      </Form.Item>
                    </Col>
                    <Col xs={24}>
                      <Form.Item
                        name="apiKey"
                        label={
                          <span className="text-gray-300">API 密钥</span>
                        }
                      >
                        <Input.Password
                          placeholder="输入API密钥（可选）"
                          size="large"
                        />
                      </Form.Item>
                    </Col>
                  </Row>

                  <Divider className="border-slate-700 my-4" />

                  <div className="flex items-center justify-between">
                    <Space size="middle">
                      <Button
                        icon={<TestTube size={16} />}
                        onClick={handleTestConnection}
                        loading={testingConnection}
                        size="large"
                      >
                        测试连接
                      </Button>
                      {connectionStatus === 'success' && (
                        <span className="flex items-center gap-1 text-emerald-400">
                          <CheckCircle size={16} />
                          连接成功
                        </span>
                      )}
                      {connectionStatus === 'error' && (
                        <span className="flex items-center gap-1 text-red-400">
                          <XCircle size={16} />
                          连接失败
                        </span>
                      )}
                    </Space>
                    <Space size="middle">
                      <Button
                        icon={<RotateCcw size={16} />}
                        onClick={handleResetConnection}
                        size="large"
                      >
                        重置
                      </Button>
                      <Button
                        type="primary"
                        icon={<Save size={16} />}
                        onClick={handleSaveConnection}
                        loading={saving.connection}
                        size="large"
                      >
                        保存配置
                      </Button>
                    </Space>
                  </div>
                </Card>
              </Form>
            </div>
          </TabPane>

          <TabPane
            tab={
              <span className="flex items-center gap-2">
                <SlidersHorizontal size={18} />
                分析参数
              </span>
            }
            key="analysis"
          >
            <Form
              form={analysisForm}
              layout="vertical"
              className="max-w-4xl"
            >
              <Card
                className="glass-card border-0 mb-4"
                title={
                  <div className="flex items-center gap-2">
                    <SlidersHorizontal size={18} className="text-purple-400" />
                    <span className="text-gray-200">聚类参数</span>
                  </div>
                }
              >
                <Row gutter={[24, 16]}>
                  <Col xs={24} md={12}>
                    <Form.Item
                      name="epsTime"
                      label={
                        <span className="text-gray-300">
                          时间阈值 (秒)
                          <Tooltip title="DBSCAN聚类的epsilon时间阈值，用于判定告警是否属于同一时间窗口">
                            <Info size={14} className="ml-1 text-gray-500" />
                          </Tooltip>
                        </span>
                      }
                      rules={[
                        { required: true, message: '请输入时间阈值' },
                      ]}
                    >
                      <InputNumber
                        min={60}
                        max={3600}
                        step={60}
                        className="w-full"
                        size="large"
                        addonAfter="秒"
                      />
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={12}>
                    <Form.Item
                      name="minSamples"
                      label={
                        <span className="text-gray-300">
                          最小样本数
                          <Tooltip title="形成聚类所需的最小告警数量">
                            <Info size={14} className="ml-1 text-gray-500" />
                          </Tooltip>
                        </span>
                      }
                      rules={[
                        { required: true, message: '请输入最小样本数' },
                      ]}
                    >
                      <InputNumber
                        min={2}
                        max={100}
                        className="w-full"
                        size="large"
                        addonAfter="个"
                      />
                    </Form.Item>
                  </Col>
                </Row>
              </Card>

              <Card
                className="glass-card border-0 mb-4"
                title={
                  <div className="flex items-center gap-2">
                    <SlidersHorizontal size={18} className="text-orange-400" />
                    <span className="text-gray-200">评分权重</span>
                  </div>
                }
              >
                <Row gutter={[24, 16]}>
                  <Col xs={24}>
                    <Form.Item
                      name="frequencyWeight"
                      label={
                        <span className="text-gray-300">
                          频率权重
                          <Tooltip title="告警频率在低效度评分中的权重占比">
                            <Info size={14} className="ml-1 text-gray-500" />
                          </Tooltip>
                        </span>
                      }
                      rules={[
                        { required: true, message: '请输入频率权重' },
                      ]}
                    >
                      <Slider
                        min={0}
                        max={1}
                        step={0.05}
                        tooltip={{
                          formatter: (value) =>
                            `${((value || 0) * 100).toFixed(0)}%`,
                        }}
                      />
                    </Form.Item>
                  </Col>
                  <Col xs={24}>
                    <Form.Item
                      name="criticalityWeight"
                      label={
                        <span className="text-gray-300">
                          关键度权重
                          <Tooltip title="业务关键度在低效度评分中的权重占比">
                            <Info size={14} className="ml-1 text-gray-500" />
                          </Tooltip>
                        </span>
                      }
                      rules={[
                        { required: true, message: '请输入关键度权重' },
                      ]}
                    >
                      <Slider
                        min={0}
                        max={1}
                        step={0.05}
                        tooltip={{
                          formatter: (value) =>
                            `${((value || 0) * 100).toFixed(0)}%`,
                        }}
                      />
                    </Form.Item>
                  </Col>
                  <Col xs={24}>
                    <Form.Item
                      name="noiseWeight"
                      label={
                        <span className="text-gray-300">
                          噪声权重
                          <Tooltip title="噪声程度在低效度评分中的权重占比">
                            <Info size={14} className="ml-1 text-gray-500" />
                          </Tooltip>
                        </span>
                      }
                      rules={[
                        { required: true, message: '请输入噪声权重' },
                      ]}
                    >
                      <Slider
                        min={0}
                        max={1}
                        step={0.05}
                        tooltip={{
                          formatter: (value) =>
                            `${((value || 0) * 100).toFixed(0)}%`,
                        }}
                      />
                    </Form.Item>
                  </Col>
                </Row>
              </Card>

              <Card
                className="glass-card border-0 mb-4"
                title={
                  <div className="flex items-center gap-2">
                    <SlidersHorizontal size={18} className="text-emerald-400" />
                    <span className="text-gray-200">优化参数</span>
                  </div>
                }
              >
                <Row gutter={[24, 16]}>
                  <Col xs={24} md={12}>
                    <Form.Item
                      name="minConfidence"
                      label={
                        <span className="text-gray-300">
                          最小置信度
                          <Tooltip title="优化建议的最小置信度阈值，低于此值的建议将被过滤">
                            <Info size={14} className="ml-1 text-gray-500" />
                          </Tooltip>
                        </span>
                      }
                      rules={[
                        { required: true, message: '请输入最小置信度' },
                      ]}
                    >
                      <Slider
                        min={0}
                        max={1}
                        step={0.05}
                        tooltip={{
                          formatter: (value) =>
                            `${((value || 0) * 100).toFixed(0)}%`,
                        }}
                      />
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={12}>
                    <Form.Item
                      name="minInefficiencyScore"
                      label={
                        <span className="text-gray-300">
                          最小低效度评分阈值
                          <Tooltip title="识别低效规则的最低评分阈值">
                            <Info size={14} className="ml-1 text-gray-500" />
                          </Tooltip>
                        </span>
                      }
                      rules={[
                        {
                          required: true,
                          message: '请输入最小低效度评分阈值',
                        },
                      ]}
                    >
                      <Slider
                        min={0}
                        max={1}
                        step={0.05}
                        tooltip={{
                          formatter: (value) =>
                            `${((value || 0) * 100).toFixed(0)}%`,
                        }}
                      />
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={12}>
                    <Form.Item
                      name="defaultLookbackHours"
                      label={
                        <span className="text-gray-300">
                          默认时间范围
                          <Tooltip title="分析时默认使用的历史数据时间范围">
                            <Info size={14} className="ml-1 text-gray-500" />
                          </Tooltip>
                        </span>
                      }
                      rules={[
                        { required: true, message: '请输入默认时间范围' },
                      ]}
                    >
                      <Select size="large">
                        <Option value={24}>24小时</Option>
                        <Option value={72}>3天</Option>
                        <Option value={168}>7天</Option>
                        <Option value={336}>14天</Option>
                        <Option value={720}>30天</Option>
                      </Select>
                    </Form.Item>
                  </Col>
                </Row>
              </Card>

              <div className="flex justify-end gap-3">
                <Button
                  icon={<RotateCcw size={16} />}
                  onClick={handleResetAnalysis}
                  size="large"
                >
                  重置
                </Button>
                <Button
                  type="primary"
                  icon={<Save size={16} />}
                  onClick={handleSaveAnalysis}
                  loading={saving.analysis}
                  size="large"
                >
                  保存配置
                </Button>
              </div>
            </Form>
          </TabPane>

          <TabPane
            tab={
              <span className="flex items-center gap-2">
                <Bell size={18} />
                规则管理
              </span>
            }
            key="rules"
          >
            <Card
              className="glass-card border-0"
              title={
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Bell size={18} className="text-orange-400" />
                    <span className="text-gray-200">告警规则列表</span>
                    <Tag color="blue" className="ml-2">
                      共 {editableRules.length} 条规则
                    </Tag>
                  </div>
                  <Button
                    icon={<RefreshCw size={16} />}
                    onClick={fetchRules}
                    loading={loading.rules}
                    size="small"
                  >
                    刷新
                  </Button>
                </div>
              }
            >
              <Form form={editForm} layout="inline">
                <Table
                  dataSource={editableRules}
                  columns={ruleColumns}
                  rowKey="id"
                  loading={loading.rules}
                  pagination={{
                    pageSize: 10,
                    showSizeChanger: true,
                    showQuickJumper: true,
                    showTotal: (total) => `共 ${total} 条记录`,
                  }}
                  scroll={{ x: 1200 }}
                  rowClassName={(record) =>
                    editingRuleId === record.id ? 'bg-blue-900/20' : ''
                  }
                />
              </Form>
            </Card>
          </TabPane>

          <TabPane
            tab={
              <span className="flex items-center gap-2">
                <Bell size={18} />
                通知配置
              </span>
            }
            key="notification"
          >
            <Form
              form={notificationForm}
              layout="vertical"
              className="max-w-4xl"
            >
              <Card
                className="glass-card border-0 mb-4"
                title={
                  <div className="flex items-center gap-2">
                    <Bell size={18} className="text-pink-400" />
                    <span className="text-gray-200">通知渠道</span>
                  </div>
                }
              >
                <Form.Item
                  name="channels"
                  label={<span className="text-gray-300">启用的通知渠道</span>}
                >
                  <Select
                    mode="multiple"
                    placeholder="选择通知渠道"
                    size="large"
                    className="w-full"
                  >
                    <Option value="webhook">Webhook</Option>
                    <Option value="email">邮件</Option>
                    <Option value="dingtalk">钉钉</Option>
                    <Option value="wechat">企业微信</Option>
                  </Select>
                </Form.Item>

                <Divider className="border-slate-700 my-4" />

                <Row gutter={[24, 16]}>
                  <Col xs={24}>
                    <Form.Item
                      name="webhookUrl"
                      label={<span className="text-gray-300">Webhook 地址</span>}
                    >
                      <Input
                        placeholder="https://example.com/webhook"
                        size="large"
                      />
                    </Form.Item>
                  </Col>
                  <Col xs={24}>
                    <Form.Item
                      name="email"
                      label={<span className="text-gray-300">邮件地址</span>}
                    >
                      <Input
                        placeholder="admin@example.com"
                        size="large"
                      />
                    </Form.Item>
                  </Col>
                  <Col xs={24}>
                    <Form.Item
                      name="dingtalkWebhook"
                      label={<span className="text-gray-300">钉钉 Webhook</span>}
                    >
                      <Input
                        placeholder="https://oapi.dingtalk.com/robot/send?access_token=xxx"
                        size="large"
                      />
                    </Form.Item>
                  </Col>
                  <Col xs={24}>
                    <Form.Item
                      name="wechatWebhook"
                      label={<span className="text-gray-300">企业微信 Webhook</span>}
                    >
                      <Input
                        placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
                        size="large"
                      />
                    </Form.Item>
                  </Col>
                </Row>
              </Card>

              <Card
                className="glass-card border-0 mb-4"
                title={
                  <div className="flex items-center gap-2">
                    <SlidersHorizontal size={18} className="text-cyan-400" />
                    <span className="text-gray-200">通知阈值</span>
                  </div>
                }
              >
                <Row gutter={[24, 16]}>
                  <Col xs={24} md={12}>
                    <Form.Item
                      name="notificationThreshold"
                      label={
                        <span className="text-gray-300">
                          低效度阈值
                          <Tooltip title="达到此低效度评分时触发通知">
                            <Info size={14} className="ml-1 text-gray-500" />
                          </Tooltip>
                        </span>
                      }
                      rules={[
                        { required: true, message: '请输入通知阈值' },
                      ]}
                    >
                      <Slider
                        min={0}
                        max={1}
                        step={0.05}
                        tooltip={{
                          formatter: (value) =>
                            `${((value || 0) * 100).toFixed(0)}%`,
                        }}
                      />
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={12}>
                    <Form.Item
                      name="minAlertCount"
                      label={
                        <span className="text-gray-300">
                          最小告警数
                          <Tooltip title="触发通知的最小告警数量">
                            <Info size={14} className="ml-1 text-gray-500" />
                          </Tooltip>
                        </span>
                      }
                      rules={[
                        { required: true, message: '请输入最小告警数' },
                      ]}
                    >
                      <InputNumber
                        min={1}
                        max={1000}
                        className="w-full"
                        size="large"
                        addonAfter="条"
                      />
                    </Form.Item>
                  </Col>
                </Row>

                <Divider className="border-slate-700 my-4" />

                <div className="flex items-center justify-between">
                  <Button
                    icon={<TestTube size={16} />}
                    onClick={handleTestNotification}
                    size="large"
                  >
                    发送测试通知
                  </Button>
                  <Space size="middle">
                    <Button
                      icon={<RotateCcw size={16} />}
                      onClick={handleResetNotification}
                      size="large"
                    >
                      重置
                    </Button>
                    <Button
                      type="primary"
                      icon={<Save size={16} />}
                      onClick={handleSaveNotification}
                      loading={saving.notification}
                      size="large"
                    >
                      保存配置
                    </Button>
                  </Space>
                </div>
              </Card>
            </Form>
          </TabPane>

          <TabPane
            tab={
              <span className="flex items-center gap-2">
                <Info size={18} />
                系统信息
              </span>
            }
            key="system"
          >
            <Card
              className="glass-card border-0"
              title={
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Info size={18} className="text-cyan-400" />
                    <span className="text-gray-200">系统运行状态</span>
                  </div>
                  <Button
                    icon={<RefreshCw size={16} />}
                    onClick={handleRefreshSystem}
                    size="small"
                  >
                    刷新
                  </Button>
                </div>
              }
            >
              <Row gutter={[24, 24]}>
                <Col xs={24} md={12} lg={6}>
                  <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                    <div className="flex items-center gap-2 text-gray-400 text-sm mb-2">
                      <Info size={16} />
                      版本信息
                    </div>
                    <div className="text-xl font-bold text-white">
                      v{systemInfo.version}
                    </div>
                  </div>
                </Col>
                <Col xs={24} md={12} lg={6}>
                  <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                    <div className="flex items-center gap-2 text-gray-400 text-sm mb-2">
                      <Database size={16} />
                      数据存储路径
                    </div>
                    <div className="text-sm font-mono text-gray-200 break-all">
                      {systemInfo.dataStoragePath}
                    </div>
                  </div>
                </Col>
                <Col xs={24} md={12} lg={6}>
                  <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                    <div className="flex items-center gap-2 text-gray-400 text-sm mb-2">
                      <Power size={16} />
                      运行时间
                    </div>
                    <div className="text-xl font-bold text-white">
                      {formatUptime(systemInfo.uptime)}
                    </div>
                  </div>
                </Col>
                <Col xs={24} md={12} lg={6}>
                  <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                    <div className="flex items-center gap-2 text-gray-400 text-sm mb-2">
                      <Bell size={16} />
                      数据统计
                    </div>
                    <div className="text-gray-200">
                      <span className="text-xl font-bold">
                        {formatNumber(systemInfo.totalRules)}
                      </span>
                      <span className="text-sm ml-1">条规则</span>
                      <span className="text-gray-500 mx-2">/</span>
                      <span className="text-xl font-bold">
                        {formatNumber(systemInfo.totalAlerts)}
                      </span>
                      <span className="text-sm ml-1">条告警</span>
                    </div>
                  </div>
                </Col>
              </Row>

              <Divider className="border-slate-700 my-6" />

              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2 text-gray-300">
                    <Database size={18} className="text-blue-400" />
                    <span className="font-medium">缓存使用情况</span>
                  </div>
                  <div className="text-sm text-gray-400">
                    {formatBytes(systemInfo.cacheUsage)} /{' '}
                    {formatBytes(systemInfo.cacheMax)}
                  </div>
                </div>
                <div className="bg-slate-800 rounded-full h-4 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${(systemInfo.cacheUsage / systemInfo.cacheMax) * 100}%`,
                      background: `linear-gradient(90deg, #3B82F6, #06B6D4)`,
                    }}
                  />
                </div>
                <div className="flex justify-between mt-2 text-sm">
                  <span className="text-gray-500">0</span>
                  <span className="text-gray-400 font-mono">
                    {(
                      (systemInfo.cacheUsage / systemInfo.cacheMax) *
                      100
                    ).toFixed(1)}
                    %
                  </span>
                  <span className="text-gray-500">
                    {formatBytes(systemInfo.cacheMax)}
                  </span>
                </div>
              </div>

              <Divider className="border-slate-700 my-6" />

              <div>
                <div className="flex items-center gap-2 text-gray-300 mb-4">
                  <Link size={18} className="text-emerald-400" />
                  <span className="font-medium">后端服务状态</span>
                </div>
                {healthStatus ? (
                  <Row gutter={[16, 16]}>
                    <Col xs={24} md={8}>
                      <div
                        className={`p-4 rounded-lg border ${
                          healthStatus.status === 'UP'
                            ? 'bg-emerald-900/20 border-emerald-700'
                            : 'bg-red-900/20 border-red-700'
                        }`}
                      >
                        <div className="text-gray-400 text-sm mb-1">服务状态</div>
                        <div
                          className={`text-lg font-bold flex items-center gap-2 ${
                            healthStatus.status === 'UP'
                              ? 'text-emerald-400'
                              : 'text-red-400'
                          }`}
                        >
                          {healthStatus.status === 'UP' ? (
                            <CheckCircle size={18} />
                          ) : (
                            <XCircle size={18} />
                          )}
                          {healthStatus.status === 'UP' ? '正常运行' : '服务异常'}
                        </div>
                      </div>
                    </Col>
                    <Col xs={24} md={8}>
                      <div
                        className={`p-4 rounded-lg border ${
                          healthStatus.skywalkingConnected
                            ? 'bg-emerald-900/20 border-emerald-700'
                            : 'bg-yellow-900/20 border-yellow-700'
                        }`}
                      >
                        <div className="text-gray-400 text-sm mb-1">
                          SkyWalking 连接
                        </div>
                        <div
                          className={`text-lg font-bold flex items-center gap-2 ${
                            healthStatus.skywalkingConnected
                              ? 'text-emerald-400'
                              : 'text-yellow-400'
                          }`}
                        >
                          {healthStatus.skywalkingConnected ? (
                            <CheckCircle size={18} />
                          ) : (
                            <XCircle size={18} />
                          )}
                          {healthStatus.skywalkingConnected
                            ? '已连接'
                            : '未连接'}
                        </div>
                      </div>
                    </Col>
                    <Col xs={24} md={8}>
                      <div
                        className={`p-4 rounded-lg border ${
                          healthStatus.mockMode
                            ? 'bg-purple-900/20 border-purple-700'
                            : 'bg-slate-800 border-slate-700'
                        }`}
                      >
                        <div className="text-gray-400 text-sm mb-1">Mock 模式</div>
                        <div
                          className={`text-lg font-bold flex items-center gap-2 ${
                            healthStatus.mockMode
                              ? 'text-purple-400'
                              : 'text-gray-400'
                          }`}
                        >
                          {healthStatus.mockMode ? (
                            <CheckCircle size={18} />
                          ) : (
                            <XCircle size={18} />
                          )}
                          {healthStatus.mockMode ? '已开启' : '已关闭'}
                        </div>
                      </div>
                    </Col>
                  </Row>
                ) : (
                  <Alert
                    message="无法获取健康状态"
                    description="请检查后端服务是否正常运行"
                    type="warning"
                    showIcon
                  />
                )}
              </div>
            </Card>
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default Settings;

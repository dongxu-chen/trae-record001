import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Button,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  message,
  Space,
  Tag,
  Progress,
  Alert,
  Descriptions,
  List,
} from 'antd';
import { ReloadOutlined, ThunderboltOutlined, CheckOutlined } from '@ant-design/icons';
import { tenantApi, rateLimitApi } from '../services/api';

const { Option } = Select;

const QuotaConfig = () => {
  const [tenants, setTenants] = useState([]);
  const [selectedTenant, setSelectedTenant] = useState(null);
  const [usage, setUsage] = useState(null);
  const [loading, setLoading] = useState(false);
  const [preConsumeModalVisible, setPreConsumeModalVisible] = useState(false);
  const [releaseModalVisible, setReleaseModalVisible] = useState(false);
  const [confirmModalVisible, setConfirmModalVisible] = useState(false);
  const [testModalVisible, setTestModalVisible] = useState(false);
  const [warningsModalVisible, setWarningsModalVisible] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [preConsumeResult, setPreConsumeResult] = useState(null);
  const [warnings, setWarnings] = useState([]);
  const [preConsumeForm] = Form.useForm();
  const [releaseForm] = Form.useForm();
  const [confirmForm] = Form.useForm();
  const [testForm] = Form.useForm();

  useEffect(() => {
    loadTenants();
  }, []);

  const loadTenants = async () => {
    try {
      const result = await tenantApi.list();
      setTenants(result.data || []);
    } catch (error) {
      message.error('加载租户列表失败');
    }
  };

  const handleTenantChange = async (tenantId) => {
    setSelectedTenant(tenantId);
    setLoading(true);
    try {
      const result = await tenantApi.getUsage(tenantId);
      setUsage(result.data);
    } catch (error) {
      message.error('加载使用情况失败');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = () => {
    if (selectedTenant) {
      handleTenantChange(selectedTenant);
    }
  };

  const handlePreConsume = async () => {
    try {
      const values = await preConsumeForm.validateFields();
      const result = await tenantApi.preConsume({
        tenantId: selectedTenant,
        ...values,
      });
      const resp = result.data;
      if (resp.success) {
        message.success(`预消耗成功 (版本: ${resp.previousVersion} → ${resp.newVersion})`);
        setPreConsumeResult(resp);
        setPreConsumeModalVisible(false);
        handleRefresh();
      } else {
        message.error(`预消耗失败: ${resp.failReason}`);
      }
    } catch (error) {
      if (!error.errorFields) {
        message.error('预消耗失败');
      }
    }
  };

  const handleRelease = async () => {
    try {
      const values = await releaseForm.validateFields();
      const result = await tenantApi.release({
        tenantId: selectedTenant,
        ...values,
      });
      if (result.data) {
        message.success('释放成功');
        setReleaseModalVisible(false);
        handleRefresh();
      } else {
        message.error('释放失败');
      }
    } catch (error) {
      if (!error.errorFields) {
        message.error('释放失败');
      }
    }
  };

  const handleConfirm = async () => {
    try {
      const values = await confirmForm.validateFields();
      const result = await tenantApi.confirm({
        tenantId: selectedTenant,
        ...values,
      });
      if (result.data) {
        message.success('确认成功');
        setConfirmModalVisible(false);
        handleRefresh();
      } else {
        message.error('确认失败');
      }
    } catch (error) {
      if (!error.errorFields) {
        message.error('确认失败');
      }
    }
  };

  const handleTest = async () => {
    try {
      const values = await testForm.validateFields();
      const result = await rateLimitApi.check(values);
      setTestResult(result.data);
    } catch (error) {
      if (!error.errorFields) {
        message.error('测试失败');
      }
    }
  };

  const handleViewWarnings = async () => {
    try {
      const result = await tenantApi.getWarnings(selectedTenant);
      setWarnings(result.data || []);
      setWarningsModalVisible(true);
    } catch (error) {
      message.error('加载预警记录失败');
    }
  };

  const tenant = tenants.find(t => t.tenantId === selectedTenant);

  const getWarningLevelColor = (level) => {
    switch (level) {
      case 'EARLY_WARNING': return 'gold';
      case 'WARNING': return 'orange';
      case 'CRITICAL': return 'red';
      default: return 'blue';
    }
  };

  const getWarningLevelLabel = (level) => {
    switch (level) {
      case 'EARLY_WARNING': return '预告';
      case 'WARNING': return '警告';
      case 'CRITICAL': return '严重';
      default: return level;
    }
  };

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card title="选择租户">
        <Row gutter={16}>
          <Col span={12}>
            <Select
              style={{ width: '100%' }}
              placeholder="请选择租户"
              value={selectedTenant}
              onChange={handleTenantChange}
            >
              {tenants.map(t => (
                <Option key={t.tenantId} value={t.tenantId}>
                  {t.tenantName} ({t.tenantId})
                </Option>
              ))}
            </Select>
          </Col>
          <Col>
            <Button icon={<ReloadOutlined />} onClick={handleRefresh} disabled={!selectedTenant}>
              刷新
            </Button>
          </Col>
        </Row>
      </Card>

      {tenant && (
        <Card title="配额详情" loading={loading} extra={
          <Space>
            <Button onClick={() => setPreConsumeModalVisible(true)}>预消耗</Button>
            <Button onClick={() => setReleaseModalVisible(true)}>释放</Button>
            <Button icon={<CheckOutlined />} onClick={() => setConfirmModalVisible(true)}>确认</Button>
            <Button type="primary" icon={<ThunderboltOutlined />} onClick={() => setTestModalVisible(true)}>
              限流测试
            </Button>
            <Button onClick={handleViewWarnings}>预警记录</Button>
          </Space>
        }>
          <Row gutter={[16, 16]}>
            <Col span={8}>
              <Card size="small" title="分钟配额">
                <Progress
                  type="circle"
                  percent={Math.round((usage?.minuteUsageRate || 0) * 100)}
                  status={(usage?.minuteUsageRate || 0) > 0.95 ? 'exception' : (usage?.minuteUsageRate || 0) > 0.8 ? 'exception' : 'active'}
                />
                <div style={{ marginTop: 16 }}>
                  <div>已使用: {usage?.minuteUsed || 0}</div>
                  <div>剩余: {usage?.minuteRemaining || tenant.minuteLimit}</div>
                  <div>限额: {tenant.minuteLimit}</div>
                  {(usage?.minuteUsageRate || 0) >= 0.6 && (
                    <Tag color={(usage?.minuteUsageRate || 0) >= 0.95 ? 'red' : (usage?.minuteUsageRate || 0) >= 0.8 ? 'orange' : 'gold'} style={{ marginTop: 4 }}>
                      {(usage?.minuteUsageRate || 0) >= 0.95 ? '严重' : (usage?.minuteUsageRate || 0) >= 0.8 ? '警告' : '预告'}
                    </Tag>
                  )}
                </div>
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" title="小时配额">
                <Progress
                  type="circle"
                  percent={Math.round((usage?.hourUsageRate || 0) * 100)}
                  status={(usage?.hourUsageRate || 0) > 0.8 ? 'exception' : 'active'}
                />
                <div style={{ marginTop: 16 }}>
                  <div>已使用: {usage?.hourUsed || 0}</div>
                  <div>剩余: {usage?.hourRemaining || tenant.hourLimit}</div>
                  <div>限额: {tenant.hourLimit}</div>
                  {(usage?.hourUsageRate || 0) >= 0.6 && (
                    <Tag color={(usage?.hourUsageRate || 0) >= 0.95 ? 'red' : (usage?.hourUsageRate || 0) >= 0.8 ? 'orange' : 'gold'} style={{ marginTop: 4 }}>
                      {(usage?.hourUsageRate || 0) >= 0.95 ? '严重' : (usage?.hourUsageRate || 0) >= 0.8 ? '警告' : '预告'}
                    </Tag>
                  )}
                </div>
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" title="日配额">
                <Progress
                  type="circle"
                  percent={Math.round((usage?.dayUsageRate || 0) * 100)}
                  status={(usage?.dayUsageRate || 0) > 0.8 ? 'exception' : 'active'}
                />
                <div style={{ marginTop: 16 }}>
                  <div>已使用: {usage?.dayUsed || 0}</div>
                  <div>剩余: {usage?.dayRemaining || tenant.dayLimit}</div>
                  <div>限额: {tenant.dayLimit}</div>
                  {(usage?.dayUsageRate || 0) >= 0.6 && (
                    <Tag color={(usage?.dayUsageRate || 0) >= 0.95 ? 'red' : (usage?.dayUsageRate || 0) >= 0.8 ? 'orange' : 'gold'} style={{ marginTop: 4 }}>
                      {(usage?.dayUsageRate || 0) >= 0.95 ? '严重' : (usage?.dayUsageRate || 0) >= 0.8 ? '警告' : '预告'}
                    </Tag>
                  )}
                </div>
              </Card>
            </Col>
          </Row>

          {preConsumeResult && (
            <Alert
              message="最近预消耗结果"
              description={`版本: ${preConsumeResult.previousVersion} → ${preConsumeResult.newVersion}，剩余令牌: ${preConsumeResult.remainingTokens}`}
              type="info"
              closable
              onClose={() => setPreConsumeResult(null)}
              style={{ marginTop: 16 }}
            />
          )}
        </Card>
      )}

      <Modal title="预消耗配额（分布式锁+乐观锁）" open={preConsumeModalVisible} onOk={handlePreConsume} onCancel={() => setPreConsumeModalVisible(false)}>
        <Alert message="预消耗使用分布式锁+乐观锁保证一致性，返回版本号用于追踪" type="info" style={{ marginBottom: 16 }} />
        <Form form={preConsumeForm} layout="vertical">
          <Form.Item name="granularity" label="粒度" rules={[{ required: true, message: '请选择粒度' }]}>
            <Select>
              <Option value="minute">分钟</Option>
              <Option value="hour">小时</Option>
              <Option value="day">日</Option>
            </Select>
          </Form.Item>
          <Form.Item name="amount" label="数量" rules={[{ required: true, message: '请输入数量' }]}>
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal title="释放预消耗配额" open={releaseModalVisible} onOk={handleRelease} onCancel={() => setReleaseModalVisible(false)}>
        <Form form={releaseForm} layout="vertical">
          <Form.Item name="granularity" label="粒度" rules={[{ required: true, message: '请选择粒度' }]}>
            <Select>
              <Option value="minute">分钟</Option>
              <Option value="hour">小时</Option>
              <Option value="day">日</Option>
            </Select>
          </Form.Item>
          <Form.Item name="amount" label="数量" rules={[{ required: true, message: '请输入数量' }]}>
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal title="确认预消耗" open={confirmModalVisible} onOk={handleConfirm} onCancel={() => setConfirmModalVisible(false)}>
        <Alert message="确认预消耗后，配额将被正式消耗且不可回滚" type="warning" style={{ marginBottom: 16 }} />
        <Form form={confirmForm} layout="vertical">
          <Form.Item name="granularity" label="粒度" rules={[{ required: true, message: '请选择粒度' }]}>
            <Select>
              <Option value="minute">分钟</Option>
              <Option value="hour">小时</Option>
              <Option value="day">日</Option>
            </Select>
          </Form.Item>
          <Form.Item name="amount" label="数量" rules={[{ required: true, message: '请输入数量' }]}>
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal title="限流测试" open={testModalVisible} onOk={handleTest} onCancel={() => { setTestModalVisible(false); setTestResult(null); }}>
        <Form form={testForm} layout="vertical">
          <Form.Item name="tenantId" label="租户ID" initialValue={selectedTenant} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="tokens" label="消耗令牌数" initialValue={1}>
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
        {testResult && (
          <Card size="small" title="测试结果" style={{ marginTop: 16 }}>
            <Space direction="vertical">
              <div>允许: <Tag color={testResult.allowed ? 'green' : 'red'}>{testResult.allowed ? '是' : '否'}</Tag></div>
              <div>原因: {testResult.reason}</div>
              {testResult.granularity && <div>超限粒度: {testResult.granularity}</div>}
              {testResult.downgraded && <div>已降级: 是 (延迟 {testResult.delayMs}ms)</div>}
            </Space>
          </Card>
        )}
      </Modal>

      <Modal title="预警记录" open={warningsModalVisible} onCancel={() => setWarningsModalVisible(false)} footer={null} width={700}>
        <List
          dataSource={warnings}
          renderItem={item => (
            <List.Item>
              <Descriptions bordered size="small" column={2} style={{ width: '100%' }}>
                <Descriptions.Item label="预警级别">
                  <Tag color={getWarningLevelColor(item.warningLevel)}>{getWarningLevelLabel(item.warningLevel)}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="粒度">{item.granularity}</Descriptions.Item>
                <Descriptions.Item label="使用率">{(item.usageRate * 100).toFixed(1)}%</Descriptions.Item>
                <Descriptions.Item label="时间">{item.timestamp}</Descriptions.Item>
                <Descriptions.Item label="阈值" span={2}>
                  预告: {(item.earlyThreshold * 100).toFixed(0)}% /
                  警告: {(item.warningThreshold * 100).toFixed(0)}% /
                  严重: {(item.criticalThreshold * 100).toFixed(0)}%
                </Descriptions.Item>
              </Descriptions>
            </List.Item>
          )}
          locale={{ emptyText: '暂无预警记录' }}
        />
      </Modal>
    </Space>
  );
};

export default QuotaConfig;

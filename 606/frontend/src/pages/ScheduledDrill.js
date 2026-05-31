import React, { useState, useEffect } from 'react';
import {
  Card, Button, Table, Tag, Space, message, Modal, Form, Input,
  Select, Switch, Statistic, Row, Col, List, Tooltip, Badge, Alert,
  DatePicker, InputNumber, Descriptions
} from 'antd';
import {
  ClockCircleOutlined, PlayCircleOutlined, PauseCircleOutlined,
  PlusOutlined, DeleteOutlined, EditOutlined, HistoryOutlined,
  SettingOutlined, CheckCircleOutlined, CloseCircleOutlined
} from '@ant-design/icons';
import { scheduledApi, drillApi, strategyApi } from '../services/api';

const { Option } = Select;
const { TextArea } = Input;

const ScheduledDrill = () => {
  const [loading, setLoading] = useState(false);
  const [tasks, setTasks] = useState([]);
  const [stats, setStats] = useState({});
  const [modalVisible, setModalVisible] = useState(false);
  const [editingTask, setEditingTask] = useState(null);
  const [strategies, setStrategies] = useState([]);
  const [form] = Form.useForm();

  const frequencyOptions = [
    { label: '每小时', value: 'HOURLY' },
    { label: '每天', value: 'DAILY' },
    { label: '每周', value: 'WEEKLY' },
    { label: '每月', value: 'MONTHLY' },
    { label: '自定义', value: 'CUSTOM' },
  ];

  const patternOptions = [
    { label: '恒定流量', value: 'CONSTANT' },
    { label: '线性爬坡', value: 'LINEAR_RAMP' },
    { label: '突发脉冲', value: 'SPIKE' },
    { label: '波浪流量', value: 'WAVE' },
    { label: '阶梯流量', value: 'STEP' },
    { label: '指数陡峭', value: 'EXPONENTIAL_RAMP' },
    { label: '对数平缓', value: 'LOGARITHMIC_RAMP' },
    { label: 'S型曲线', value: 'SIGMOID_RAMP' },
  ];

  useEffect(() => {
    loadData();
    loadStrategies();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [tasksRes, statsRes] = await Promise.all([
        scheduledApi.listTasks(),
        scheduledApi.getStats()
      ]);
      setTasks(tasksRes.data?.data || []);
      setStats(statsRes.data?.data || {});
    } catch (e) {
      message.error('加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const loadStrategies = async () => {
    try {
      const res = await strategyApi.list();
      setStrategies(res.data?.data || []);
    } catch (e) {
      setStrategies([
        { id: '1', name: '默认限流策略' },
        { id: '2', name: '保守策略' },
        { id: '3', name: '激进策略' },
      ]);
    }
  };

  const handleCreate = () => {
    setEditingTask(null);
    form.resetFields();
    form.setFieldsValue({
      enabled: true,
      frequency: 'DAILY',
      autoPauseOnFailure: true,
      trafficPattern: 'LINEAR_RAMP',
      peakQps: 100,
      duration: 60,
    });
    setModalVisible(true);
  };

  const handleEdit = (task) => {
    setEditingTask(task);
    form.setFieldsValue({
      name: task.name,
      description: task.description,
      frequency: task.frequency,
      cronExpression: task.cronExpression,
      strategyId: task.strategyId,
      enabled: task.enabled,
      autoPauseOnFailure: task.autoPauseOnFailure,
      trafficPattern: task.trafficProfile?.pattern,
      peakQps: task.trafficProfile?.peakQps,
      duration: task.trafficProfile?.duration,
      notificationEmails: task.notificationEmails?.join(','),
    });
    setModalVisible(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const taskData = {
        name: values.name,
        description: values.description,
        frequency: values.frequency,
        cronExpression: values.cronExpression,
        strategyId: values.strategyId,
        enabled: values.enabled,
        autoPauseOnFailure: values.autoPauseOnFailure,
        trafficProfile: {
          pattern: values.trafficPattern,
          peakQps: values.peakQps,
          duration: values.duration,
        },
        notificationEmails: values.notificationEmails?.split(',').map(e => e.trim()).filter(Boolean),
      };

      if (editingTask) {
        await scheduledApi.updateTask(editingTask.id, taskData);
        message.success('更新成功');
      } else {
        await scheduledApi.createTask(taskData);
        message.success('创建成功');
      }

      setModalVisible(false);
      loadData();
    } catch (e) {
      message.error('保存失败');
    }
  };

  const handleDelete = async (id) => {
    try {
      await scheduledApi.deleteTask(id);
      message.success('删除成功');
      loadData();
    } catch (e) {
      message.error('删除失败');
    }
  };

  const handleToggle = async (task, enabled) => {
    try {
      await scheduledApi.toggleTask(task.id, enabled);
      message.success(enabled ? '已启用' : '已暂停');
      loadData();
    } catch (e) {
      message.error('操作失败');
    }
  };

  const handleTrigger = async (task) => {
    try {
      await scheduledApi.triggerTask(task.id);
      message.success('已触发执行');
      loadData();
    } catch (e) {
      message.error('触发失败');
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'ACTIVE': return 'success';
      case 'PAUSED': return 'default';
      case 'ERROR': return 'error';
      default: return 'default';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'ACTIVE': return '运行中';
      case 'PAUSED': return '已暂停';
      case 'ERROR': return '错误';
      default: return status;
    }
  };

  const columns = [
    { title: '任务名称', dataIndex: 'name', key: 'name', width: 150 },
    { 
      title: '状态', 
      dataIndex: 'status', 
      key: 'status', 
      width: 100,
      render: (v) => <Tag color={getStatusColor(v)}>{getStatusText(v)}</Tag>
    },
    { title: '执行频率', dataIndex: 'frequency', key: 'frequency', width: 100,
      render: (v) => {
        const map = { HOURLY: '每小时', DAILY: '每天', WEEKLY: '每周', MONTHLY: '每月', CUSTOM: '自定义' };
        return map[v] || v;
      }
    },
    { title: '流量模式', dataIndex: ['trafficProfile', 'pattern'], key: 'pattern', width: 120 },
    { title: '峰值QPS', dataIndex: ['trafficProfile', 'peakQps'], key: 'qps', width: 100 },
    { title: '执行次数', dataIndex: 'executionCount', key: 'count', width: 100 },
    { title: '成功次数', dataIndex: 'successCount', key: 'success', width: 100 },
    { title: '上次执行', dataIndex: 'lastExecutionTime', key: 'last', width: 170 },
    { title: '下次执行', dataIndex: 'nextExecutionTime', key: 'next', width: 170 },
    {
      title: '操作',
      key: 'action',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="立即执行">
            <Button 
              type="text" 
              icon={<PlayCircleOutlined />} 
              size="small"
              onClick={() => handleTrigger(record)}
            />
          </Tooltip>
          <Tooltip title={record.enabled ? '暂停' : '启用'}>
            <Button 
              type="text" 
              icon={record.enabled ? <PauseCircleOutlined /> : <PlayCircleOutlined />} 
              size="small"
              onClick={() => handleToggle(record, !record.enabled)}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button 
              type="text" 
              icon={<EditOutlined />} 
              size="small"
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Tooltip title="删除">
            <Button 
              type="text" 
              danger 
              icon={<DeleteOutlined />} 
              size="small"
              onClick={() => handleDelete(record.id)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card
        title={
          <Space>
            <ClockCircleOutlined />
            常态化演练
          </Space>
        }
        extra={
          <Space>
            <Button icon={<SettingOutlined />} onClick={loadData} loading={loading}>
              刷新
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              新建定时任务
            </Button>
          </Space>
        }
      >
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="定时任务总数"
                value={stats.totalScheduled || 0}
                suffix="个"
                prefix={<ClockCircleOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="运行中"
                value={stats.activeCount || 0}
                suffix="个"
                valueStyle={{ color: '#52c41a' }}
                prefix={<CheckCircleOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="总执行次数"
                value={stats.totalExecutions || 0}
                suffix="次"
                prefix={<HistoryOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="成功率"
                value={stats.successRate || 0}
                suffix="%"
                precision={1}
                valueStyle={{ color: (stats.successRate || 0) >= 90 ? '#52c41a' : '#faad14' }}
              />
            </Card>
          </Col>
        </Row>

        <Table
          columns={columns}
          dataSource={tasks}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1200 }}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Modal
        title={editingTask ? '编辑定时任务' : '新建定时任务'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleSubmit}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="任务名称" rules={[{ required: true }]}>
            <Input placeholder="请输入任务名称" />
          </Form.Item>

          <Form.Item name="description" label="任务描述">
            <TextArea rows={2} placeholder="请输入任务描述" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="frequency" label="执行频率" rules={[{ required: true }]}>
                <Select>
                  {frequencyOptions.map(opt => (
                    <Option key={opt.value} value={opt.value}>{opt.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="cronExpression" label="Cron表达式">
                <Input placeholder="例如: 0 0 2 * * ?" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="strategyId" label="限流策略" rules={[{ required: true }]}>
            <Select>
              {strategies.map(s => (
                <Option key={s.id} value={s.id}>{s.name}</Option>
              ))}
            </Select>
          </Form.Item>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="trafficPattern" label="流量模式">
                <Select>
                  {patternOptions.map(opt => (
                    <Option key={opt.value} value={opt.value}>{opt.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="peakQps" label="峰值QPS">
                <InputNumber min={1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="duration" label="持续时间(秒)">
                <InputNumber min={1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="notificationEmails" label="通知邮箱(逗号分隔)">
            <Input placeholder="a@example.com,b@example.com" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="enabled" label="立即启用" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="autoPauseOnFailure" label="连续失败自动暂停" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  );
};

export default ScheduledDrill;

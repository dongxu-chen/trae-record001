import React, { useState, useEffect } from 'react';
import {
  Card, Table, Button, Modal, Form, Input, InputNumber, Select, Tag, Space,
  message, Popconfirm, Progress, Descriptions, Row, Col, Alert, Spin
} from 'antd';
import {
  PlusOutlined, PlayCircleOutlined, PauseCircleOutlined,
  ReloadOutlined, ExperimentOutlined
} from '@ant-design/icons';
import { drillApi, strategyApi } from '../services/api';

const { Option } = Select;

const trafficPatterns = [
  { value: 'CONSTANT', label: '恒定流量', desc: '维持恒定QPS' },
  { value: 'LINEAR_RAMP', label: '线性爬坡', desc: '匀速上升' },
  { value: 'EXPONENTIAL_RAMP', label: '指数陡峭', desc: '慢启动后陡增' },
  { value: 'LOGARITHMIC_RAMP', label: '对数平缓', desc: '快启动后缓增' },
  { value: 'SIGMOID_RAMP', label: 'S型曲线', desc: '平滑过渡' },
  { value: 'SPIKE', label: '突发脉冲', desc: '瞬间峰值' },
  { value: 'WAVE', label: '波浪流量', desc: '周期性波动' },
  { value: 'STEP', label: '阶梯流量', desc: '分阶段上升' },
  { value: 'DOUBLE_STEP', label: '双阶流量', desc: '两阶段台阶' },
  { value: 'GRADUAL_STEP', label: '渐变阶梯', desc: '多阶平滑过渡' },
];

const Drill = () => {
  const [tasks, setTasks] = useState([]);
  const [strategies, setStrategies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [resultModalVisible, setResultModalVisible] = useState(false);
  const [selectedTask, setSelectedTask] = useState(null);
  const [form] = Form.useForm();

  useEffect(() => {
    loadData();
    const timer = setInterval(loadData, 5000);
    return () => clearInterval(timer);
  }, []);

  const loadData = async () => {
    try {
      const [tasksRes, strategiesRes] = await Promise.all([
        drillApi.listTasks(),
        strategyApi.list(),
      ]);
      setTasks(tasksRes.data?.data || []);
      setStrategies(strategiesRes.data?.data || []);
    } catch (e) {
      console.error('Failed to load data', e);
    }
  };

  const handleCreate = () => {
    form.resetFields();
    form.setFieldsValue({
      httpMethod: 'GET',
      baseQps: 10,
      peakQps: 100,
      rampUpSeconds: 10,
      sustainSeconds: 30,
      rampDownSeconds: 10,
      pattern: 'LINEAR_RAMP',
      concurrentUsers: 50,
      connectTimeoutMs: 5000,
      readTimeoutMs: 10000,
      targetUrl: 'http://localhost:8080/api/drill/target',
    });
    setCreateModalVisible(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const task = {
        name: values.name,
        description: values.description,
        strategyId: values.strategyId,
        trafficProfile: {
          baseQps: values.baseQps,
          peakQps: values.peakQps,
          rampUpSeconds: values.rampUpSeconds,
          sustainSeconds: values.sustainSeconds,
          rampDownSeconds: values.rampDownSeconds,
          pattern: values.pattern,
          concurrentUsers: values.concurrentUsers,
          targetUrl: values.targetUrl,
          httpMethod: values.httpMethod,
          requestBody: values.requestBody,
          connectTimeoutMs: values.connectTimeoutMs,
          readTimeoutMs: values.readTimeoutMs,
        },
      };

      const res = await drillApi.createTask(task);
      const taskId = res.data?.data?.id;
      if (taskId) {
        const mode = values.mode || 'simulator';
        await drillApi.startTask(taskId, mode);
        message.success('演练任务已创建并启动');
      }
      setCreateModalVisible(false);
      loadData();
    } catch (e) {
      if (e.errorFields) return;
      message.error('创建演练任务失败');
    }
  };

  const handleStart = async (taskId) => {
    try {
      await drillApi.startTask(taskId, 'simulator');
      message.success('演练已启动');
      loadData();
    } catch (e) {
      message.error('启动失败');
    }
  };

  const handleStop = async (taskId) => {
    try {
      await drillApi.stopTask(taskId);
      message.success('演练已停止');
      loadData();
    } catch (e) {
      message.error('停止失败');
    }
  };

  const handleDelete = async (taskId) => {
    try {
      await drillApi.deleteTask(taskId);
      message.success('删除成功');
      loadData();
    } catch (e) {
      message.error('删除失败');
    }
  };

  const showResult = (task) => {
    setSelectedTask(task);
    setResultModalVisible(true);
  };

  const statusColorMap = {
    CREATED: 'default',
    RUNNING: 'processing',
    COMPLETED: 'success',
    FAILED: 'error',
    CANCELLED: 'warning',
  };
  const statusLabelMap = {
    CREATED: '已创建',
    RUNNING: '运行中',
    COMPLETED: '已完成',
    FAILED: '失败',
    CANCELLED: '已取消',
  };

  const patternLabelMap = {};
  trafficPatterns.forEach(p => { patternLabelMap[p.value] = p.label; });

  const columns = [
    { title: '任务名称', dataIndex: 'name', key: 'name', ellipsis: true, width: 160 },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (s) => (
        <Tag color={statusColorMap[s]} icon={s === 'RUNNING' ? <Spin size="small" /> : null}>
          {statusLabelMap[s] || s}
        </Tag>
      ),
    },
    {
      title: '流量模式',
      key: 'pattern',
      width: 110,
      render: (_, r) => r.trafficProfile ? patternLabelMap[r.trafficProfile.pattern] || r.trafficProfile.pattern : '-',
    },
    {
      title: '峰值QPS',
      key: 'peakQps',
      width: 90,
      render: (_, r) => r.trafficProfile?.peakQps || '-',
    },
    {
      title: '评分',
      key: 'score',
      width: 80,
      render: (_, r) => {
        const score = r.result?.score;
        if (score == null) return '-';
        const color = score >= 80 ? '#52c41a' : score >= 60 ? '#faad14' : '#ff4d4f';
        return <span style={{ color, fontWeight: 'bold', fontSize: 16 }}>{score}</span>;
      },
    },
    { title: '创建时间', dataIndex: 'createTime', key: 'createTime', width: 170 },
    {
      title: '操作',
      key: 'action',
      width: 250,
      render: (_, record) => (
        <Space>
          {record.status === 'CREATED' && (
            <Button type="primary" size="small" icon={<PlayCircleOutlined />}
              onClick={() => handleStart(record.id)}>启动</Button>
          )}
          {record.status === 'RUNNING' && (
            <Button danger size="small" icon={<PauseCircleOutlined />}
              onClick={() => handleStop(record.id)}>停止</Button>
          )}
          {record.status === 'COMPLETED' && (
            <Button size="small" icon={<ExperimentOutlined />}
              onClick={() => showResult(record)}>结果</Button>
          )}
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const renderResultModal = () => {
    if (!selectedTask || !selectedTask.result) return null;
    const r = selectedTask.result;
    const scoreColor = r.score >= 80 ? '#52c41a' : r.score >= 60 ? '#faad14' : '#ff4d4f';

    return (
      <Modal
        title={`演练结果 - ${selectedTask.name}`}
        open={resultModalVisible}
        onCancel={() => setResultModalVisible(false)}
        footer={null}
        width={800}
        bodyStyle={{ maxHeight: '75vh', overflowY: 'auto' }}
      >
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6} style={{ textAlign: 'center' }}>
            <Progress
              type="dashboard"
              percent={r.score || 0}
              strokeColor={scoreColor}
              format={p => <span style={{ fontSize: 22, fontWeight: 'bold' }}>{p}</span>}
            />
            <div style={{ marginTop: 4, color: '#666' }}>综合评分</div>
          </Col>
          <Col span={18}>
            <Descriptions bordered size="small" column={3}>
              <Descriptions.Item label="总请求数">{r.totalRequests}</Descriptions.Item>
              <Descriptions.Item label="成功数">{r.successRequests}</Descriptions.Item>
              <Descriptions.Item label="拦截数">{r.blockedRequests}</Descriptions.Item>
              <Descriptions.Item label="失败数">{r.failedRequests}</Descriptions.Item>
              <Descriptions.Item label="降级数">{r.degradedRequests}</Descriptions.Item>
              <Descriptions.Item label="实际QPS">{r.actualQps?.toFixed(1)}</Descriptions.Item>
              <Descriptions.Item label="拦截率">{r.blockRate?.toFixed(1)}%</Descriptions.Item>
              <Descriptions.Item label="错误率">{r.errorRate?.toFixed(1)}%</Descriptions.Item>
              <Descriptions.Item label="峰值错误率">{r.peakErrorRate?.toFixed(1)}%</Descriptions.Item>
            </Descriptions>
          </Col>
        </Row>

        <Card title="恢复能力" size="small" style={{ marginBottom: 12 }}>
          <Descriptions bordered size="small" column={3}>
            <Descriptions.Item label="恢复时间">{r.recoveryTimeMs ? `${r.recoveryTimeMs}ms` : '未检测'}</Descriptions.Item>
            <Descriptions.Item label="错误抖动">{r.errorRateJitter?.toFixed(2)}</Descriptions.Item>
            <Descriptions.Item label="超阈值时长">{r.overThresholdSeconds || 0}秒</Descriptions.Item>
            <Descriptions.Item label="响应标准差">{r.responseTimeStdDev?.toFixed(1)}ms</Descriptions.Item>
            <Descriptions.Item label="峰值拦截率">{r.peakBlockRate?.toFixed(1)}%</Descriptions.Item>
            <Descriptions.Item label="自动恢复">{r.autoRecovered ? '是' : '否'}</Descriptions.Item>
          </Descriptions>
        </Card>

        <Card title="响应时间" size="small" style={{ marginBottom: 12 }}>
          <Descriptions bordered size="small" column={3}>
            <Descriptions.Item label="平均">{r.avgResponseTimeMs} ms</Descriptions.Item>
            <Descriptions.Item label="最小">{r.minResponseTimeMs} ms</Descriptions.Item>
            <Descriptions.Item label="最大">{r.maxResponseTimeMs} ms</Descriptions.Item>
            <Descriptions.Item label="P50">{r.p50ResponseTimeMs} ms</Descriptions.Item>
            <Descriptions.Item label="P90">{r.p90ResponseTimeMs} ms</Descriptions.Item>
            <Descriptions.Item label="P99">{r.p99ResponseTimeMs} ms</Descriptions.Item>
          </Descriptions>
        </Card>

        {r.scoreDetail && (
          <Card title="九维评分详情" size="small">
            <Row gutter={16}>
              <Col span={8}>
                <div style={{ marginBottom: 8 }}>
                  <span>可用性 ({r.scoreDetail.availabilityScore?.toFixed(1)})</span>
                  <Progress percent={r.scoreDetail.availabilityScore || 0} size="small" strokeColor="#1677ff" />
                </div>
                <div style={{ marginBottom: 8 }}>
                  <span>响应时间 ({r.scoreDetail.responseTimeScore?.toFixed(1)})</span>
                  <Progress percent={r.scoreDetail.responseTimeScore || 0} size="small" strokeColor="#52c41a" />
                </div>
                <div style={{ marginBottom: 8 }}>
                  <span>稳定性 ({r.scoreDetail.stabilityScore?.toFixed(1)})</span>
                  <Progress percent={r.scoreDetail.stabilityScore || 0} size="small" strokeColor="#faad14" />
                </div>
              </Col>
              <Col span={8}>
                <div style={{ marginBottom: 8 }}>
                  <span>降级效果 ({r.scoreDetail.degradationEffectScore?.toFixed(1)})</span>
                  <Progress percent={r.scoreDetail.degradationEffectScore || 0} size="small" strokeColor="#722ed1" />
                </div>
                <div style={{ marginBottom: 8 }}>
                  <span>恢复能力 ({r.scoreDetail.recoveryScore?.toFixed(1)})</span>
                  <Progress percent={r.scoreDetail.recoveryScore || 0} size="small" strokeColor="#13c2c2" />
                </div>
                <div style={{ marginBottom: 8 }}>
                  <span>恢复速度 ({r.scoreDetail.recoveryTimeScore?.toFixed(1)})</span>
                  <Progress percent={r.scoreDetail.recoveryTimeScore || 0} size="small" strokeColor="#eb2f96" />
                </div>
              </Col>
              <Col span={8}>
                <div style={{ marginBottom: 8 }}>
                  <span>抖动控制 ({r.scoreDetail.jitterScore?.toFixed(1)})</span>
                  <Progress percent={r.scoreDetail.jitterScore || 0} size="small" strokeColor="#fa8c16" />
                </div>
                <div style={{ marginBottom: 8 }}>
                  <span>阈值控制 ({r.scoreDetail.overThresholdScore?.toFixed(1)})</span>
                  <Progress percent={r.scoreDetail.overThresholdScore || 0} size="small" strokeColor="#a0d911" />
                </div>
                <div style={{ marginBottom: 8 }}>
                  <span>一致性 ({r.scoreDetail.consistencyScore?.toFixed(1)})</span>
                  <Progress percent={r.scoreDetail.consistencyScore || 0} size="small" strokeColor="#f5222d" />
                </div>
              </Col>
            </Row>
          </Card>
        )}
      </Modal>
    );
  };

  return (
    <div>
      <Alert
        message="限流降级演练"
        description="创建演练任务模拟突发流量，测试限流降级策略的防护效果。支持多种流量模式和策略组合。"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Card
        title="演练任务"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>创建演练</Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={tasks}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
          locale={{ emptyText: '暂无演练任务' }}
        />
      </Card>

      <Modal
        title="创建演练任务"
        open={createModalVisible}
        onOk={handleSubmit}
        onCancel={() => setCreateModalVisible(false)}
        width={700}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="name" label="任务名称" rules={[{ required: true, message: '请输入任务名称' }]}>
                <Input placeholder="输入演练任务名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="strategyId" label="限流策略">
                <Select allowClear placeholder="选择限流策略（可选）">
                  {strategies.map(s => (
                    <Option key={s.id} value={s.id}>{s.name}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="description" label="任务描述">
            <Input.TextArea rows={2} placeholder="描述本次演练目标" />
          </Form.Item>

          <Card title="流量配置" size="small" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="pattern" label="流量模式" rules={[{ required: true }]}>
                  <Select
                    optionLabelProp="label"
                    dropdownRender={menu => (
                      <div>
                        {menu}
                        <div style={{ padding: '8px', borderTop: '1px solid #f0f0f0', fontSize: '12px', color: '#999' }}>
                          提示：陡峭模式适合测试极限性能，平缓模式适合模拟真实业务增长
                        </div>
                      </div>
                    )}
                  >
                    {trafficPatterns.map(p => (
                      <Option key={p.value} value={p.value} label={p.label}>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <span style={{ fontWeight: 500 }}>{p.label}</span>
                          <span style={{ color: '#999', fontSize: '12px' }}>{p.desc}</span>
                        </div>
                      </Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="targetUrl" label="目标URL" rules={[{ required: true }]}>
                  <Input placeholder="http://localhost:8080/api/drill/target" />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name="baseQps" label="基础QPS" rules={[{ required: true }]}>
                  <InputNumber min={1} max={10000} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="peakQps" label="峰值QPS" rules={[{ required: true }]}>
                  <InputNumber min={1} max={100000} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="concurrentUsers" label="并发用户数" rules={[{ required: true }]}>
                  <InputNumber min={1} max={1000} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name="rampUpSeconds" label="爬坡时长(秒)">
                  <InputNumber min={1} max={300} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="sustainSeconds" label="持续时长(秒)">
                  <InputNumber min={1} max={600} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="rampDownSeconds" label="下降时长(秒)">
                  <InputNumber min={1} max={300} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name="httpMethod" label="HTTP方法">
                  <Select>
                    <Option value="GET">GET</Option>
                    <Option value="POST">POST</Option>
                    <Option value="PUT">PUT</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="connectTimeoutMs" label="连接超时(ms)">
                  <InputNumber min={100} max={30000} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="readTimeoutMs" label="读取超时(ms)">
                  <InputNumber min={100} max={60000} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          <Form.Item name="mode" label="执行模式">
            <Select defaultValue="simulator">
              <Option value="simulator">内置仿真器</Option>
              <Option value="jmeter">JMeter压测</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {renderResultModal()}
    </div>
  );
};

export default Drill;

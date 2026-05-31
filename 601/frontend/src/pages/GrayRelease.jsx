import React, { useState, useEffect } from 'react';
import { Card, Table, Tag, Button, Modal, Form, Input, InputNumber, Select, Switch, Row, Col, Steps, Progress, Empty, Space, message } from 'antd';
import { ExperimentOutlined, PlayCircleOutlined, PauseCircleOutlined, ForwardOutlined, ReloadOutlined } from '@ant-design/icons';
import { checkApi } from '../services/api';
import dayjs from 'dayjs';

const { Option } = Select;

const GrayRelease = () => {
  const [configs, setConfigs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    loadConfigs();
  }, []);

  const loadConfigs = async () => {
    setLoading(true);
    try {
      const data = await checkApi.getAllGrayConfigs();
      setConfigs(data || []);
    } catch (error) {
      console.error('Failed to load gray configs:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (values) => {
    try {
      const phases = [];
      const percentages = [10, 30, 60, 100];
      for (let i = 0; i < percentages.length; i++) {
        phases.push({
          phaseIndex: i,
          phaseName: `灰度阶段${i + 1} - ${percentages[i]}%`,
          percentage: percentages[i],
          durationMinutes: 30,
          autoAdvance: i < percentages.length - 1,
          status: 'PENDING'
        });
      }

      const config = {
        name: values.name,
        description: values.description || '',
        enabled: true,
        strategy: values.strategy || 'PERCENTAGE',
        phases: phases
      };

      await checkApi.createGrayConfig(config);
      message.success('灰度配置创建成功');
      setCreateModalVisible(false);
      form.resetFields();
      loadConfigs();
    } catch (error) {
      message.error('创建失败');
    }
  };

  const handleExecute = async (configId) => {
    try {
      await checkApi.executeGrayCheck(configId, {
        sourceType: 'MYSQL',
        tableName: 'default_table'
      });
      message.success('灰度校验已启动');
    } catch (error) {
      message.error('启动失败');
    }
  };

  const handleAdvance = async (configId) => {
    try {
      await checkApi.advanceGrayPhase(configId);
      message.success('已推进到下一阶段');
      loadConfigs();
    } catch (error) {
      message.error('推进失败');
    }
  };

  const handlePause = async (configId) => {
    try {
      await checkApi.pauseGrayRelease(configId);
      message.success('灰度已暂停');
      loadConfigs();
    } catch (error) {
      message.error('暂停失败');
    }
  };

  const handleResume = async (configId) => {
    try {
      await checkApi.resumeGrayRelease(configId);
      message.success('灰度已恢复');
      loadConfigs();
    } catch (error) {
      message.error('恢复失败');
    }
  };

  const getPhaseStatus = (status) => {
    const map = {
      PENDING: { color: 'default', text: '待执行' },
      RUNNING: { color: 'processing', text: '执行中' },
      COMPLETED: { color: 'success', text: '已完成' },
      FAILED: { color: 'error', text: '失败' },
      PAUSED: { color: 'warning', text: '已暂停' }
    };
    const cfg = map[status] || { color: 'default', text: status };
    return <Tag color={cfg.color}>{cfg.text}</Tag>;
  };

  const columns = [
    { title: '配置ID', dataIndex: 'id', key: 'id', width: 200, render: (t) => <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{t}</span> },
    { title: '名称', dataIndex: 'name', key: 'name', width: 150 },
    { title: '策略', dataIndex: 'strategy', key: 'strategy', width: 120,
      render: (s) => {
        const map = { PERCENTAGE: '百分比放量', TABLE_RANGE: '表范围', KEY_RANGE: 'Key范围' };
        return <Tag>{map[s] || s}</Tag>;
      }
    },
    { title: '当前阶段', key: 'currentPhase', width: 100,
      render: (_, r) => `${r.currentPhase + 1}/${r.phases?.length || 0}`
    },
    { title: '当前放量', key: 'percentage', width: 120,
      render: (_, r) => <Progress percent={r.phases?.[r.currentPhase]?.percentage || 0} size="small" />
    },
    { title: '状态', key: 'enabled', width: 80,
      render: (_, r) => r.enabled ? <Tag color="success">启用</Tag> : <Tag color="error">暂停</Tag>
    },
    { title: '操作', key: 'action', width: 280,
      render: (_, record) => (
        <Space size="small">
          <Button type="link" icon={<PlayCircleOutlined />} onClick={() => handleExecute(record.id)} size="small">执行</Button>
          <Button type="link" icon={<ForwardOutlined />} onClick={() => handleAdvance(record.id)} size="small">推进</Button>
          {record.enabled ? (
            <Button type="link" danger icon={<PauseCircleOutlined />} onClick={() => handlePause(record.id)} size="small">暂停</Button>
          ) : (
            <Button type="link" icon={<PlayCircleOutlined />} onClick={() => handleResume(record.id)} size="small">恢复</Button>
          )}
        </Space>
      )
    }
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0 }}>
          <ExperimentOutlined style={{ marginRight: 8 }} />
          校验灰度
        </h3>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadConfigs}>刷新</Button>
          <Button type="primary" icon={<ExperimentOutlined />} onClick={() => setCreateModalVisible(true)}>创建灰度配置</Button>
        </Space>
      </div>

      {configs.length > 0 ? (
        <>
          <Table columns={columns} dataSource={configs} rowKey="id" loading={loading} size="small" style={{ marginBottom: 16 }} />
          {configs.map(config => (
            <Card key={config.id} title={`灰度进度: ${config.name}`} size="small" style={{ marginBottom: 16 }}>
              <Steps
                current={config.currentPhase}
                items={(config.phases || []).map((phase, idx) => ({
                  title: phase.phaseName || `阶段${idx + 1}`,
                  description: (
                    <div>
                      <div>放量: {phase.percentage}%</div>
                      <div>{getPhaseStatus(phase.status)}</div>
                    </div>
                  )
                }))}
              />
            </Card>
          ))}
        </>
      ) : (
        <Empty description="暂无灰度配置" />
      )}

      <Modal title="创建灰度配置" open={createModalVisible} onCancel={() => setCreateModalVisible(false)} onOk={() => form.submit()}>
        <Form form={form} layout="vertical" onFinish={handleCreate} initialValues={{ strategy: 'PERCENTAGE' }}>
          <Form.Item name="name" label="配置名称" rules={[{ required: true }]}>
            <Input placeholder="输入灰度配置名称" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="描述灰度发布计划" />
          </Form.Item>
          <Form.Item name="strategy" label="灰度策略">
            <Select>
              <Option value="PERCENTAGE">百分比放量</Option>
              <Option value="TABLE_RANGE">表范围</Option>
              <Option value="KEY_RANGE">Key范围</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default GrayRelease;

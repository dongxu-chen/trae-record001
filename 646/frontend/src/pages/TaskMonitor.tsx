import React, { useEffect, useState, useRef, useCallback } from 'react';
import {
  Card, Progress, Button, Descriptions, Tag, Space, Typography, Table, Tooltip,
  Modal, Form, InputNumber, Switch, Select, Alert, List, message
} from 'antd';
import {
  ArrowLeftOutlined, PlayCircleOutlined, PauseCircleOutlined, ReloadOutlined, AimOutlined,
  SafetyCertificateOutlined, ThunderboltOutlined, RollbackOutlined, CheckCircleOutlined,
  CloseCircleOutlined, SettingOutlined
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import ReactECharts from 'echarts-for-react';
import { wsService } from '@/services/websocket';
import {
  taskApi, TaskStatus, TaskLog, PositionInfo, CheckpointRecord,
  ValidationResult, RollbackStatus
} from '@/services/api';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

const POSITION_TYPE_MAP: Record<string, string> = {
  row_offset: '行偏移',
  kafka_offset: 'Kafka位点',
  timestamp: '时间戳',
  file_offset: '文件偏移',
};

const ROLLBACK_STATUS_MAP: Record<string, string> = {
  BACKING_UP: '备份中',
  BACKUP_COMPLETED: '备份完成',
  BACKUP_FAILED: '备份失败',
  ROLLING_BACK: '回滚中',
  ROLLBACK_COMPLETED: '回滚完成',
  ROLLBACK_FAILED: '回滚失败',
};

const TaskMonitor: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);
  const [positionInfo, setPositionInfo] = useState<PositionInfo | null>(null);
  const [logs, setLogs] = useState<TaskLog[]>([]);
  const [checkpoints, setCheckpoints] = useState<CheckpointRecord[]>([]);
  const [rollbackStatus, setRollbackStatus] = useState<RollbackStatus | null>(null);
  const [throughputData, setThroughputData] = useState<number[]>([]);
  const [timeLabels, setTimeLabels] = useState<string[]>([]);
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [settingsModalVisible, setSettingsModalVisible] = useState(false);
  const [prevalidateLoading, setPrevalidateLoading] = useState(false);
  const [rollbackLoading, setRollbackLoading] = useState(false);
  const [form] = Form.useForm();
  const logContainerRef = useRef<HTMLDivElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchRealtimePosition = useCallback(async () => {
    if (!id) return;
    try {
      const response = await taskApi.getRealtimePosition(id);
      const data = response.data as PositionInfo;
      if (data.success) {
        setPositionInfo(data);
        setTaskStatus((prev) => ({
          ...prev!,
          progress: data.progress,
          processedRecords: data.processedRecords,
          totalRecords: data.totalRecords,
          positionType: data.positionType,
          positionValue: data.positionValue,
          throughput: data.throughput,
          batchSize: data.batchSize,
          rateLimit: data.rateLimit,
        }));
      }
    } catch {
      // backend not available
    }
  }, [id]);

  const fetchTaskStatus = useCallback(async () => {
    if (!id) return;
    try {
      const response = await taskApi.getStatus(id);
      const data = response.data as TaskStatus;
      setTaskStatus(data);
      if (data.rollbackStatus) {
        setRollbackStatus(data.rollbackStatus);
      }
    } catch {
      // backend not available
    }
  }, [id]);

  const fetchLogs = useCallback(async () => {
    if (!id) return;
    try {
      const response = await taskApi.getLogs(id, 100);
      setLogs(response.data);
    } catch {
      setLogs([
        { id: '1', level: 'INFO', message: '任务初始化完成，预校验已启用', createdAt: new Date().toISOString() },
        { id: '2', level: 'INFO', message: '限速控制配置已加载', createdAt: new Date().toISOString() },
        { id: '3', level: 'INFO', message: '回滚机制已就绪（需启用备份）', createdAt: new Date().toISOString() },
      ]);
    }
  }, [id]);

  const fetchCheckpoints = useCallback(async () => {
    if (!id) return;
    try {
      const response = await taskApi.getCheckpointHistory(id, 20);
      setCheckpoints(response.data);
    } catch {
      setCheckpoints([]);
    }
  }, [id]);

  const fetchRollbackStatus = useCallback(async () => {
    if (!id) return;
    try {
      const response = await taskApi.getRollbackStatus(id);
      const data = response.data as RollbackStatus;
      if (data.success) {
        setRollbackStatus(data);
      }
    } catch {
      // no rollback data
    }
  }, [id]);

  const handlePreValidate = async () => {
    if (!id) return;
    setPrevalidateLoading(true);
    try {
      const response = await taskApi.preValidate(id);
      setValidationResult(response.data);
      message.success('预校验完成');
    } catch (e: any) {
      message.error('预校验失败: ' + (e.message || '未知错误'));
    } finally {
      setPrevalidateLoading(false);
    }
  };

  const handleRollback = async () => {
    if (!id) return;
    Modal.confirm({
      title: '确认回滚',
      icon: <RollbackOutlined />,
      content: <Paragraph type="warning">回滚操作将停止当前迁移并从备份恢复数据。此操作不可撤销，确认继续吗？</Paragraph>,
      okText: '确认回滚',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        setRollbackLoading(true);
        try {
          await taskApi.rollback(id);
          message.success('回滚已触发');
          fetchRollbackStatus();
        } catch (e: any) {
          message.error('回滚失败: ' + (e.response?.data?.message || e.message || '未知错误'));
        } finally {
          setRollbackLoading(false);
        }
      },
    });
  };

  const handleSaveSettings = async (values: any) => {
    if (!id) return;
    try {
      const task = await taskApi.get(id);
      const currentConfig = task.data?.config || {};
      await taskApi.update(id, {
        ...task.data,
        config: {
          ...currentConfig,
          ...values,
        },
      });
      message.success('设置已保存');
      setSettingsModalVisible(false);
    } catch (e: any) {
      message.error('保存失败: ' + (e.message || '未知错误'));
    }
  };

  useEffect(() => {
    if (!id) return;

    fetchTaskStatus();
    fetchLogs();
    fetchCheckpoints();
    fetchRealtimePosition();
    fetchRollbackStatus();

    const connectWebSocket = async () => {
      try {
        await wsService.connect();
        wsService.subscribe(`/topic/tasks/${id}/progress`, (message: any) => {
          const newPos: PositionInfo = {
            success: true,
            progress: message.progress || 0,
            processedRecords: message.processedRecords || 0,
            totalRecords: message.totalRecords || 0,
            throughput: message.throughput || 0,
            batchSize: message.batchSize || 0,
            rateLimit: message.rateLimit,
            positionType: message.positionType || '',
            positionValue: message.positionValue || '',
          };
          setPositionInfo(newPos);
          setTaskStatus((prev) => ({
            ...prev!,
            progress: message.progress,
            processedRecords: message.processedRecords,
            totalRecords: message.totalRecords,
            positionType: message.positionType,
            positionValue: message.positionValue,
            throughput: message.throughput,
            batchSize: message.batchSize,
            rateLimit: message.rateLimit,
          }));
        });
        wsService.subscribe(`/topic/tasks/${id}/logs`, (message: any) => {
          setLogs((prev) => [...prev, message as TaskLog].slice(-100));
        });
      } catch {
        // WebSocket not available, fall back to polling
      }
    };

    connectWebSocket();

    pollRef.current = setInterval(() => {
      fetchRealtimePosition();

      const now = new Date();
      const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
      setTimeLabels((prev) => [...prev, timeStr].slice(-30));
      setThroughputData((prev) => {
        const lastThroughput = positionInfo?.throughput || Math.floor(Math.random() * 2000) + 500;
        return [...prev, Math.round(lastThroughput)].slice(-30);
      });
    }, 2000);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      wsService.unsubscribe(`/topic/tasks/${id}/progress`);
      wsService.unsubscribe(`/topic/tasks/${id}/logs`);
      wsService.disconnect();
    };
  }, [id, fetchTaskStatus, fetchLogs, fetchCheckpoints, fetchRealtimePosition, fetchRollbackStatus, positionInfo?.throughput]);

  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  const handleStart = async () => {
    if (!id) return;
    try {
      await taskApi.start(id);
      message.success('任务已启动');
      fetchTaskStatus();
      fetchRealtimePosition();
    } catch (e: any) {
      message.error('启动失败: ' + (e.message || '未知错误'));
    }
  };

  const handlePause = async () => {
    if (!id) return;
    try {
      await taskApi.pause(id);
      message.success('任务已暂停，当前位点已记录');
      fetchTaskStatus();
    } catch (e: any) {
      message.error('暂停失败: ' + (e.message || '未知错误'));
    }
  };

  const handleRefresh = () => {
    fetchTaskStatus();
    fetchRealtimePosition();
    fetchCheckpoints();
    fetchRollbackStatus();
  };

  const throughputChartOption = {
    tooltip: { trigger: 'axis', formatter: (params: any) => `${params[0].name}<br/>吞吐量: <b>${params[0].value}</b> 记录/秒` },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', boundaryGap: false, data: timeLabels },
    yAxis: { type: 'value', name: '记录/秒' },
    series: [{
      name: '吞吐量',
      type: 'line',
      smooth: true,
      data: throughputData,
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(16, 185, 129, 0.5)' },
            { offset: 1, color: 'rgba(16, 185, 129, 0.05)' },
          ],
        },
      },
      lineStyle: { color: '#10b981', width: 2 },
    }],
  };

  const statusColorMap: Record<string, string> = {
    running: 'processing', completed: 'success', pending: 'default', failed: 'error', paused: 'warning',
    rollback: 'processing', rollback_completed: 'success',
  };
  const statusTextMap: Record<string, string> = {
    running: '运行中', completed: '已完成', pending: '等待中', failed: '失败', paused: '已暂停',
    rollback: '回滚中', rollback_completed: '已回滚',
  };

  const checkpointColumns = [
    { title: '位点类型', dataIndex: 'positionType', key: 'positionType', width: 120, render: (v: string) => POSITION_TYPE_MAP[v] || v },
    { title: '位点值', dataIndex: 'positionValue', key: 'positionValue', width: 140, render: (v: string) => <Text code>{v}</Text> },
    { title: '已处理', dataIndex: 'processedRecords', key: 'processedRecords', width: 100, render: (v: number) => v?.toLocaleString() },
    { title: '时间', dataIndex: 'updatedAt', key: 'updatedAt', width: 160, render: (v: string) => v ? new Date(v).toLocaleString() : '-' },
  ];

  const displayPosition = positionInfo || {
    positionType: taskStatus?.livePositionType || taskStatus?.positionType,
    positionValue: taskStatus?.livePositionValue || taskStatus?.positionValue,
    throughput: taskStatus?.liveThroughput || taskStatus?.throughput || 0,
    batchSize: taskStatus?.liveBatchSize || taskStatus?.batchSize || 0,
    rateLimit: taskStatus?.liveRateLimit || taskStatus?.rateLimit || 0,
  };

  const hasBackup = rollbackStatus?.rollbackStatus === 'BACKUP_COMPLETED' ||
    rollbackStatus?.rollbackStatus === 'ROLLING_BACK' ||
    rollbackStatus?.rollbackStatus === 'ROLLBACK_COMPLETED';

  const rateLimitEnabled = (displayPosition.rateLimit ?? 0) > 0;

  return (
    <div>
      <div className="flex items-center mb-6">
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/task')} className="mr-4">返回</Button>
        <Title level={3} className="!mb-0">任务监控 - {taskStatus?.name || '加载中...'}</Title>
        <Space className="ml-4">
          <Button icon={<ReloadOutlined />} onClick={handleRefresh} size="small">刷新</Button>
          <Button icon={<SettingOutlined />} onClick={() => setSettingsModalVisible(true)} size="small">迁移配置</Button>
        </Space>
      </div>

      {validationResult && (
        <Alert
          type={validationResult.valid ? 'success' : 'error'}
          showIcon
          icon={validationResult.valid ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
          message={`预校验结果: ${validationResult.summary}`}
          description={
            <List
              size="small"
              dataSource={validationResult.items}
              renderItem={(item) => (
                <List.Item className={item.passed ? 'text-green-600' : 'text-red-600'}>
                  {item.passed ? <CheckCircleOutlined className="mr-2" /> : <CloseCircleOutlined className="mr-2" />}
                  <strong>{item.name}</strong>: {item.message}
                </List.Item>
              )}
            />
          }
          closable
          onClose={() => setValidationResult(null)}
          className="mb-6"
        />
      )}

      {rollbackStatus?.rollbackStatus?.includes('ROLLBACK') && !rollbackStatus.rollbackStatus.includes('COMPLETED') && (
        <Alert
          type="warning"
          showIcon
          message={`回滚状态: ${ROLLBACK_STATUS_MAP[rollbackStatus.rollbackStatus]}`}
          description={`备份表: ${rollbackStatus.backupTableName}, 备份记录: ${rollbackStatus.backupRecords?.toLocaleString()}`}
          className="mb-6"
        />
      )}

      <div className="grid grid-cols-6 gap-4 mb-6">
        <Card>
          <div className="text-gray-500 text-sm mb-2">状态</div>
          <Tag color={statusColorMap[taskStatus?.status || 'pending']} className="text-base">
            {statusTextMap[taskStatus?.status || 'pending']}
          </Tag>
        </Card>
        <Card>
          <div className="text-gray-500 text-sm mb-2">总记录数</div>
          <div className="text-2xl font-bold text-blue-600">
            {(positionInfo?.totalRecords || taskStatus?.totalRecords || 0).toLocaleString()}
          </div>
        </Card>
        <Card>
          <div className="text-gray-500 text-sm mb-2">已处理</div>
          <div className="text-2xl font-bold text-green-600">
            {(positionInfo?.processedRecords || taskStatus?.processedRecords || 0).toLocaleString()}
          </div>
        </Card>
        <Card>
          <div className="text-gray-500 text-sm mb-2">实时吞吐</div>
          <div className="text-2xl font-bold text-purple-600">
            {Math.round(displayPosition.throughput || 0).toLocaleString()}
            <span className="text-sm font-normal text-gray-400 ml-1">条/秒</span>
          </div>
        </Card>
        <Card>
          <div className="text-gray-500 text-sm mb-2">批量大小</div>
          <div className="text-2xl font-bold text-orange-600">
            {displayPosition.batchSize || 500}
            <span className="text-sm font-normal text-gray-400 ml-1">条/批</span>
          </div>
        </Card>
        <Card>
          <div className="text-gray-500 text-sm mb-2 flex items-center">
            <ThunderboltOutlined className={`mr-1 ${rateLimitEnabled ? 'text-yellow-500' : 'text-gray-300'}`} />
            限速控制
          </div>
          <div className="text-2xl font-bold" style={{ color: rateLimitEnabled ? '#eab308' : '#9ca3af' }}>
            {rateLimitEnabled ? (displayPosition.rateLimit || 0).toLocaleString() : '无限制'}
            <span className="text-sm font-normal text-gray-400 ml-1">{rateLimitEnabled ? '条/秒' : ''}</span>
          </div>
        </Card>
      </div>

      <Card title="迁移进度（位点精确追踪）" className="mb-6">
        <Progress
          percent={Math.round(positionInfo?.progress || taskStatus?.progress || 0)}
          strokeColor={{ '0%': '#108ee9', '100%': '#87d068' }}
          status={taskStatus?.status === 'failed' ? 'exception' : undefined}
        />
        <div className="mt-3 flex items-center text-sm">
          <AimOutlined className="mr-2 text-blue-500" />
          <span className="text-gray-500 mr-2">当前位点:</span>
          <Tag color="blue">{POSITION_TYPE_MAP[displayPosition.positionType] || displayPosition.positionType || '-'}</Tag>
          <Tooltip title="精确续传位点值，中断后从此位点恢复">
            <Text code className="text-base">{displayPosition.positionValue || '-'}</Text>
          </Tooltip>
          <span className="text-gray-400 ml-3">
            进度: {(positionInfo?.progress || taskStatus?.progress || 0).toFixed(2)}%
          </span>
          {hasBackup && (
            <Tag color="green" className="ml-3" icon={<SafetyCertificateOutlined />}>
              已备份: {rollbackStatus?.backupRecords?.toLocaleString() || 0} 条
            </Tag>
          )}
        </div>
        <div className="mt-4">
          <Space wrap>
            <Button
              icon={<SafetyCertificateOutlined />}
              onClick={handlePreValidate}
              loading={prevalidateLoading}
            >
              预校验
            </Button>
            {(taskStatus?.status === 'pending' || taskStatus?.status === 'paused' || taskStatus?.status === 'failed') && (
              <Button type="primary" icon={<PlayCircleOutlined />} onClick={handleStart}>
                {taskStatus?.status === 'paused' ? '从位点续传' : '启动任务'}
              </Button>
            )}
            {taskStatus?.status === 'running' && (
              <Button icon={<PauseCircleOutlined />} onClick={handlePause}>
                暂停并记录位点
              </Button>
            )}
            {(taskStatus?.status === 'failed' || taskStatus?.status === 'paused' || taskStatus?.status === 'running') && hasBackup && (
              <Button
                danger
                icon={<RollbackOutlined />}
                onClick={handleRollback}
                loading={rollbackLoading}
              >
                回滚迁移
              </Button>
            )}
          </Space>
        </div>
      </Card>

      <div className="grid grid-cols-2 gap-6 mb-6">
        <Card title="吞吐量监控">
          <ReactECharts option={throughputChartOption} style={{ height: 280 }} />
        </Card>
        <Card title="位点与任务信息">
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="任务ID">{id}</Descriptions.Item>
            <Descriptions.Item label="任务状态">
              <Tag color={statusColorMap[taskStatus?.status || 'pending']}>
                {statusTextMap[taskStatus?.status || 'pending']}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="位点类型">
              {POSITION_TYPE_MAP[displayPosition.positionType] || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="位点值">
              <Text code>{displayPosition.positionValue || '-'}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="批量大小">
              {displayPosition.batchSize || 500} 条/批
            </Descriptions.Item>
            <Descriptions.Item label="实时吞吐">
              {Math.round(displayPosition.throughput || 0).toLocaleString()} 条/秒
            </Descriptions.Item>
            <Descriptions.Item label="限速控制">
              {rateLimitEnabled ? `${displayPosition.rateLimit?.toLocaleString()} 条/秒` : '未启用'}
            </Descriptions.Item>
            <Descriptions.Item label="备份状态">
              {hasBackup ? (
                <Tag color="green">{ROLLBACK_STATUS_MAP[rollbackStatus?.rollbackStatus || '']}</Tag>
              ) : (
                <Tag color="default">未备份</Tag>
              )}
            </Descriptions.Item>
          </Descriptions>
        </Card>
      </div>

      <Card title="位点断点记录" className="mb-6">
        <Table
          dataSource={checkpoints}
          columns={checkpointColumns}
          rowKey="id"
          size="small"
          pagination={{ pageSize: 5 }}
          locale={{ emptyText: '暂无位点记录' }}
        />
      </Card>

      <Card title="运行日志">
        <div
          ref={logContainerRef}
          className="bg-gray-900 text-gray-100 p-4 rounded-lg h-64 overflow-y-auto font-mono text-sm"
        >
          {logs.map((log, index) => (
            <div key={log.id || index} className="mb-1">
              <span className={`mr-2 ${log.level === 'ERROR' ? 'text-red-400' : log.level === 'WARN' ? 'text-yellow-400' : 'text-green-400'}`}>
                [{log.level}]
              </span>
              <span className="text-gray-400 mr-2">{new Date(log.createdAt).toLocaleTimeString()}</span>
              <span>{log.message}</span>
            </div>
          ))}
        </div>
      </Card>

      <Modal
        title="迁移配置"
        open={settingsModalVisible}
        onCancel={() => setSettingsModalVisible(false)}
        footer={null}
        width={520}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSaveSettings}
          initialValues={{
            batchSize: 500,
            rateLimit: 0,
            enableBackup: false,
            autoRollback: true,
            rollbackStrategy: 'table_restore',
          }}
        >
          <Form.Item name="batchSize" label="批量大小" extra="每批处理的记录数量，更大的批量可以提升吞吐量">
            <InputNumber min={10} max={5000} step={50} style={{ width: '100%' }} addonAfter="条/批" />
          </Form.Item>
          <Form.Item name="rateLimit" label="速率限制" extra="每秒最大处理记录数，0表示无限制。用于降低对业务系统的影响。">
            <InputNumber min={0} max={100000} step={100} style={{ width: '100%' }} addonAfter="条/秒" />
          </Form.Item>
          <Form.Item name="enableBackup" label="启用备份" extra="迁移前备份目标表数据，用于迁移失败时回滚" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="autoRollback" label="自动回滚" extra="迁移失败时自动从备份恢复" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="rollbackStrategy" label="回滚策略">
            <Select>
              <Option value="table_restore">整表恢复（删除现有记录，从备份插入）</Option>
              <Option value="truncate_and_restore">清空后恢复（TRUNCATE + 恢复）</Option>
            </Select>
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">保存配置</Button>
              <Button onClick={() => setSettingsModalVisible(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default TaskMonitor;

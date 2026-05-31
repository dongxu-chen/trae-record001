import React, { useState, useEffect } from 'react';
import { Table, Button, Tag, Space, Modal, Select, message, Popconfirm, Empty, Row, Col } from 'antd';
import {
  PlayCircleOutlined,
  StopOutlined,
  ReloadOutlined,
  EyeOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { checkApi } from '../services/api';
import { wsService } from '../services/websocket';

const { Option } = Select;

const TaskList = () => {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedTask, setSelectedTask] = useState(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [resultModalVisible, setResultModalVisible] = useState(false);
  const [taskResult, setTaskResult] = useState(null);
  const [filterType, setFilterType] = useState(null);
  const [filterStatus, setFilterStatus] = useState(null);

  useEffect(() => {
    loadTasks();
    setupWebSocket();
    return () => {
      wsService.unsubscribe('/topic/tasks/*');
    };
  }, [filterType, filterStatus]);

  const loadTasks = async () => {
    setLoading(true);
    try {
      const params = {};
      if (filterType) params.sourceType = filterType;
      if (filterStatus) params.status = filterStatus;
      const data = await checkApi.getTasks(params);
      setTasks(data || []);
    } catch (error) {
      console.error('Failed to load tasks:', error);
      message.error('加载任务列表失败');
    } finally {
      setLoading(false);
    }
  };

  const setupWebSocket = () => {
    wsService.subscribe('/topic/results', (message) => {
      if (message.type === 'TASK_COMPLETE') {
        loadTasks();
      }
    });
  };

  const getStatusTag = (status) => {
    const statusMap = {
      RUNNING: { color: 'processing', text: '运行中', icon: <SyncOutlined spin /> },
      COMPLETED: { color: 'success', text: '已完成', icon: <CheckCircleOutlined /> },
      FAILED: { color: 'error', text: '失败', icon: <CloseCircleOutlined /> },
      PENDING: { color: 'warning', text: '等待中', icon: <ClockCircleOutlined /> },
      CANCELLED: { color: 'default', text: '已取消', icon: <CloseCircleOutlined /> }
    };
    const config = statusMap[status] || statusMap.PENDING;
    return <Tag icon={config.icon} color={config.color}>{config.text}</Tag>;
  };

  const handleStartTask = async (taskId) => {
    try {
      await checkApi.startTask(taskId);
      message.success('任务已启动');
      loadTasks();
    } catch (error) {
      console.error('Failed to start task:', error);
      message.error('启动任务失败');
    }
  };

  const handleCancelTask = async (taskId) => {
    try {
      await checkApi.cancelTask(taskId);
      message.success('任务已取消');
      loadTasks();
    } catch (error) {
      console.error('Failed to cancel task:', error);
      message.error('取消任务失败');
    }
  };

  const handleViewDetail = (task) => {
    setSelectedTask(task);
    setDetailModalVisible(true);
  };

  const handleViewResult = async (taskId) => {
    try {
      const result = await checkApi.getResult(taskId);
      setTaskResult(result);
      setResultModalVisible(true);
    } catch (error) {
      console.error('Failed to load result:', error);
      message.error('加载结果失败');
    }
  };

  const columns = [
    {
      title: '任务ID',
      dataIndex: 'id',
      key: 'id',
      width: 200,
      render: (text) => <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{text}</span>
    },
    {
      title: '数据源',
      dataIndex: 'sourceType',
      key: 'sourceType',
      width: 100,
      render: (text) => {
        const colorMap = { MYSQL: 'blue', REDIS: 'geekblue', ELASTICSEARCH: 'purple' };
        return <Tag color={colorMap[text] || 'default'}>{text}</Tag>;
      }
    },
    {
      title: '表名',
      dataIndex: 'tableName',
      key: 'tableName'
    },
    {
      title: '主键',
      dataIndex: 'primaryKey',
      key: 'primaryKey',
      width: 100,
      render: (text) => text || '-'
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status) => getStatusTag(status)
    },
    {
      title: '重要性',
      dataIndex: 'importanceLevel',
      key: 'importanceLevel',
      width: 100,
      render: (level) => {
        const levelMap = {
          'CRITICAL': { color: 'red', text: 'CRITICAL' },
          'HIGH': { color: 'orange', text: 'HIGH' },
          'MEDIUM': { color: 'blue', text: 'MEDIUM' },
          'LOW': { color: 'default', text: 'LOW' }
        };
        const config = levelMap[level] || { color: 'default', text: level || 'MEDIUM' };
        return <Tag color={config.color}>{config.text}</Tag>;
      }
    },
    {
      title: '自动修复',
      dataIndex: 'autoRepair',
      key: 'autoRepair',
      width: 90,
      render: (enabled) => enabled ?
        <Tag color="success">开启</Tag> : <Tag color="default">关闭</Tag>
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 170,
      render: (text) => text ? dayjs(text).format('YYYY-MM-DD HH:mm:ss') : '-'
    },
    {
      title: '完成时间',
      dataIndex: 'finishedAt',
      key: 'finishedAt',
      width: 170,
      render: (text) => text ? dayjs(text).format('YYYY-MM-DD HH:mm:ss') : '-'
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          {record.status === 'PENDING' && (
            <Button
              type="link"
              icon={<PlayCircleOutlined />}
              onClick={() => handleStartTask(record.id)}
            >
              启动
            </Button>
          )}
          {record.status === 'RUNNING' && (
            <Popconfirm
              title="确定要取消该任务吗？"
              onConfirm={() => handleCancelTask(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Button type="link" danger icon={<StopOutlined />}>
                取消
              </Button>
            </Popconfirm>
          )}
          {record.status === 'COMPLETED' && (
            <Button
              type="link"
              icon={<EyeOutlined />}
              onClick={() => handleViewResult(record.id)}
            >
              结果
            </Button>
          )}
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetail(record)}
          >
            详情
          </Button>
        </Space>
      )
    }
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', gap: 12, alignItems: 'center' }}>
        <Select
          placeholder="数据源类型"
          style={{ width: 150 }}
          allowClear
          value={filterType}
          onChange={setFilterType}
        >
          <Option value="MYSQL">MySQL</Option>
          <Option value="REDIS">Redis</Option>
          <Option value="ELASTICSEARCH">Elasticsearch</Option>
        </Select>
        <Select
          placeholder="任务状态"
          style={{ width: 150 }}
          allowClear
          value={filterStatus}
          onChange={setFilterStatus}
        >
          <Option value="PENDING">等待中</Option>
          <Option value="RUNNING">运行中</Option>
          <Option value="COMPLETED">已完成</Option>
          <Option value="FAILED">失败</Option>
          <Option value="CANCELLED">已取消</Option>
        </Select>
        <Button
          icon={<ReloadOutlined />}
          onClick={loadTasks}
          loading={loading}
        >
          刷新
        </Button>
      </div>

      {tasks.length > 0 ? (
        <Table
          columns={columns}
          dataSource={tasks}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1200 }}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条记录`
          }}
        />
      ) : (
        <Empty description="暂无任务，请先创建校验任务" />
      )}

      <Modal
        title="任务详情"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={null}
        width={600}
      >
        {selectedTask && (
          <div>
            <p><strong>任务ID:</strong> <span style={{ fontFamily: 'monospace' }}>{selectedTask.id}</span></p>
            <p><strong>数据源:</strong> {selectedTask.sourceType}</p>
            <p><strong>表名:</strong> {selectedTask.tableName}</p>
            <p><strong>主键:</strong> {selectedTask.primaryKey || '-'}</p>
            <p><strong>重要性级别:</strong> {selectedTask.importanceLevel || 'MEDIUM'}</p>
            <p><strong>比对字段:</strong> {selectedTask.compareFields?.join(', ') || '全部'}</p>
            <p><strong>排除字段:</strong> {selectedTask.excludeFields?.join(', ') || '-'}</p>
            <p><strong>查询条件:</strong> {selectedTask.whereCondition || '-'}</p>
            <p><strong>批次大小:</strong> {selectedTask.batchSize || '根据重要性级别自动配置'}</p>
            <p><strong>延迟阈值:</strong> {selectedTask.latencyThresholdMs ? `${selectedTask.latencyThresholdMs}ms` : '根据重要性级别自动配置'}</p>
            <p><strong>分层哈希校验:</strong> {selectedTask.stratifiedHashEnabled !== false ? '开启' : '关闭'}</p>
            <p><strong>分层数量:</strong> {selectedTask.stratumCount || 10}</p>
            <p><strong>自动修复:</strong> {selectedTask.autoRepair ? '开启' : '关闭'}</p>
            <p><strong>状态:</strong> {getStatusTag(selectedTask.status)}</p>
            <p><strong>创建时间:</strong> {selectedTask.createdAt ? dayjs(selectedTask.createdAt).format('YYYY-MM-DD HH:mm:ss') : '-'}</p>
            <p><strong>开始时间:</strong> {selectedTask.startedAt ? dayjs(selectedTask.startedAt).format('YYYY-MM-DD HH:mm:ss') : '-'}</p>
            <p><strong>完成时间:</strong> {selectedTask.finishedAt ? dayjs(selectedTask.finishedAt).format('YYYY-MM-DD HH:mm:ss') : '-'}</p>
          </div>
        )}
      </Modal>

      <Modal
        title="校验结果"
        open={resultModalVisible}
        onCancel={() => setResultModalVisible(false)}
        footer={null}
        width={800}
      >
        {taskResult && (
          <div>
            <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
              <Col span={6}>
                <Card size="small">
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 24, fontWeight: 'bold', color: '#1890ff' }}>
                      {taskResult.totalSourceRecords?.toLocaleString()}
                    </div>
                    <div style={{ fontSize: 12, color: '#8c8c8c' }}>源端记录</div>
                  </div>
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 24, fontWeight: 'bold', color: '#722ed1' }}>
                      {taskResult.totalTargetRecords?.toLocaleString()}
                    </div>
                    <div style={{ fontSize: 12, color: '#8c8c8c' }}>目标端记录</div>
                  </div>
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 24, fontWeight: 'bold', color: taskResult.diffCount > 0 ? '#ff4d4f' : '#52c41a' }}>
                      {taskResult.diffCount || 0}
                    </div>
                    <div style={{ fontSize: 12, color: '#8c8c8c' }}>差异数量</div>
                  </div>
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 24, fontWeight: 'bold', color: '#faad14' }}>
                      {taskResult.avgLatencyMs ? `${taskResult.avgLatencyMs.toFixed(0)}ms` : '-'}
                    </div>
                    <div style={{ fontSize: 12, color: '#8c8c8c' }}>平均延迟</div>
                  </div>
                </Card>
              </Col>
            </Row>
            <p><strong>最大延迟:</strong> {taskResult.maxLatencyMs ? `${taskResult.maxLatencyMs}ms` : '-'}</p>
            <p><strong>延迟异常数:</strong> {taskResult.latencyCount || 0}</p>
            <p><strong>开始时间:</strong> {taskResult.startTime ? dayjs(taskResult.startTime).format('YYYY-MM-DD HH:mm:ss') : '-'}</p>
            <p><strong>结束时间:</strong> {taskResult.endTime ? dayjs(taskResult.endTime).format('YYYY-MM-DD HH:mm:ss') : '-'}</p>
            {taskResult.metrics && (
              <div>
                <p><strong>校验模式:</strong> {taskResult.checkMode === 'STRATIFIED_HASH' ? '分层哈希校验' : '全量比对'}</p>
                <p><strong>处理记录数:</strong> {taskResult.metrics.processedRecords?.toLocaleString() || '-'}</p>
                {taskResult.checkMode === 'STRATIFIED_HASH' && (
                  <>
                    <p><strong>哈希跳过记录数:</strong> {taskResult.metrics.hashSkippedRecords?.toLocaleString() || 0}</p>
                    <p><strong>哈希校验记录数:</strong> {taskResult.metrics.hashVerifiedRecords?.toLocaleString() || 0}</p>
                    <p><strong>总分层数:</strong> {taskResult.metrics.totalStrata || 0}</p>
                    <p><strong>差异分层数:</strong> {taskResult.metrics.differentStrata || 0}</p>
                  </>
                )}
                <p><strong>耗时:</strong> {taskResult.metrics.durationMs ? `${taskResult.metrics.durationMs}ms` : '-'}</p>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default TaskList;

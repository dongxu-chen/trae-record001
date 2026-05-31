import React, { useState, useEffect } from 'react';
import { Table, Button, Tag, Space, Modal, Select, message, Popconfirm, Empty, Row, Col, Card } from 'antd';
import {
  ReloadOutlined,
  ToolOutlined,
  EyeOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  ArrowRightOutlined
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { checkApi } from '../services/api';
import { wsService } from '../services/websocket';

const { Option } = Select;

const DiffList = () => {
  const [allDiffs, setAllDiffs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedDiff, setSelectedDiff] = useState(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [filterType, setFilterType] = useState(null);
  const [filterDiffType, setFilterDiffType] = useState(null);
  const [filterRepairStatus, setFilterRepairStatus] = useState(null);
  const [stats, setStats] = useState({ total: 0, repaired: 0, failed: 0, pending: 0 });

  useEffect(() => {
    loadDiffs();
    setupWebSocket();
    return () => {
      wsService.unsubscribe('/topic/diffs');
      wsService.unsubscribe('/topic/repairs');
    };
  }, []);

  const loadDiffs = async () => {
    setLoading(true);
    try {
      const results = await checkApi.getRecentResults();
      const diffs = [];
      results.forEach(result => {
        if (result.diffs) {
          result.diffs.forEach(diff => {
            diffs.push({
              ...diff,
              taskId: result.taskId,
              sourceType: result.sourceType,
              tableName: result.tableName
            });
          });
        }
      });
      diffs.sort((a, b) => new Date(b.detectedAt) - new Date(a.detectedAt));
      setAllDiffs(diffs);
      updateStats(diffs);
    } catch (error) {
      console.error('Failed to load diffs:', error);
      message.error('加载差异列表失败');
    } finally {
      setLoading(false);
    }
  };

  const updateStats = (diffs) => {
    const stats = {
      total: diffs.length,
      repaired: diffs.filter(d => d.repairStatus === 'SUCCESS').length,
      failed: diffs.filter(d => d.repairStatus === 'FAILED').length,
      pending: diffs.filter(d => !d.repairStatus || d.repairStatus === 'PENDING' || d.repairStatus === 'IN_PROGRESS').length
    };
    setStats(stats);
  };

  const setupWebSocket = () => {
    wsService.subscribe('/topic/diffs', (message) => {
      if (message.type === 'DIFF' && message.payload) {
        const newDiff = message.payload;
        setAllDiffs(prev => [newDiff, ...prev]);
        setStats(prev => ({ ...prev, total: prev.total + 1, pending: prev.pending + 1 }));
      }
    });

    wsService.subscribe('/topic/repairs', (message) => {
      if (message.type === 'REPAIR_UPDATE' && message.payload) {
        const updatedDiff = message.payload;
        setAllDiffs(prev => prev.map(d =>
          d.id === updatedDiff.id ? { ...d, ...updatedDiff } : d
        ));
        updateStats(allDiffs.map(d =>
          d.id === updatedDiff.id ? { ...d, ...updatedDiff } : d
        ));
      }
    });
  };

  const getDiffTypeTag = (diffType) => {
    const typeMap = {
      MISSING_IN_TARGET: { color: 'orange', text: '目标缺失', icon: <CloseCircleOutlined /> },
      MISSING_IN_SOURCE: { color: 'warning', text: '源端缺失', icon: <CloseCircleOutlined /> },
      VALUE_MISMATCH: { color: 'red', text: '值不匹配', icon: <CloseCircleOutlined /> },
      LATENCY_EXCEEDED: { color: 'warning', text: '延迟过高', icon: <ClockCircleOutlined /> }
    };
    const config = typeMap[diffType] || { color: 'default', text: diffType };
    return <Tag icon={config.icon} color={config.color}>{config.text}</Tag>;
  };

  const getRepairStatusTag = (status) => {
    const statusMap = {
      PENDING: { color: 'processing', text: '待修复', icon: <ClockCircleOutlined /> },
      IN_PROGRESS: { color: 'warning', text: '修复中', icon: <SyncOutlined spin /> },
      SUCCESS: { color: 'success', text: '已修复', icon: <CheckCircleOutlined /> },
      FAILED: { color: 'error', text: '修复失败', icon: <CloseCircleOutlined /> }
    };
    const config = statusMap[status] || statusMap.PENDING;
    return <Tag icon={config.icon} color={config.color}>{config.text}</Tag>;
  };

  const handleRepair = async (diff) => {
    try {
      await checkApi.triggerRepair(diff.id, diff.taskId);
      message.success('修复任务已触发');
    } catch (error) {
      console.error('Failed to trigger repair:', error);
      message.error('触发修复失败');
    }
  };

  const handleViewDetail = (diff) => {
    setSelectedDiff(diff);
    setDetailModalVisible(true);
  };

  const filteredDiffs = allDiffs.filter(diff => {
    if (filterType && diff.sourceType !== filterType) return false;
    if (filterDiffType && diff.diffType !== filterDiffType) return false;
    if (filterRepairStatus && diff.repairStatus !== filterRepairStatus) return false;
    return true;
  });

  const renderDiffFields = (diffFields) => {
    if (!diffFields) return null;
    return Object.entries(diffFields).map(([field, values]) => (
      <div key={field} className="diff-field">
        <span className="field-name">{field}:</span>
        <span className="source-value">{JSON.stringify(values.source)}</span>
        <span className="arrow"><ArrowRightOutlined /></span>
        <span className="target-value">{JSON.stringify(values.target)}</span>
      </div>
    ));
  };

  const columns = [
    {
      title: '差异ID',
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
      key: 'tableName',
      width: 150
    },
    {
      title: '主键',
      dataIndex: 'key',
      key: 'key',
      width: 150
    },
    {
      title: '差异类型',
      dataIndex: 'diffType',
      key: 'diffType',
      width: 100,
      render: (type) => getDiffTypeTag(type)
    },
    {
      title: '延迟(ms)',
      dataIndex: 'latencyMs',
      key: 'latencyMs',
      width: 100,
      render: (val) => val > 0 ? val : '-'
    },
    {
      title: '修复状态',
      dataIndex: 'repairStatus',
      key: 'repairStatus',
      width: 100,
      render: (status) => getRepairStatusTag(status)
    },
    {
      title: '检测时间',
      dataIndex: 'detectedAt',
      key: 'detectedAt',
      width: 170,
      render: (text) => text ? dayjs(text).format('YYYY-MM-DD HH:mm:ss') : '-'
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          {(record.repairStatus === 'PENDING' || record.repairStatus === 'FAILED') && (
            <Button
              type="link"
              icon={<ToolOutlined />}
              onClick={() => handleRepair(record)}
            >
              修复
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
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}>
          <Card size="small">
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 24, fontWeight: 'bold', color: '#ff4d4f' }}>{stats.total}</div>
              <div style={{ fontSize: 12, color: '#8c8c8c' }}>总差异数</div>
            </div>
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 24, fontWeight: 'bold', color: '#1890ff' }}>{stats.pending}</div>
              <div style={{ fontSize: 12, color: '#8c8c8c' }}>待修复</div>
            </div>
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 24, fontWeight: 'bold', color: '#52c41a' }}>{stats.repaired}</div>
              <div style={{ fontSize: 12, color: '#8c8c8c' }}>已修复</div>
            </div>
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 24, fontWeight: 'bold', color: '#faad14' }}>
                {stats.total > 0 ? `${((stats.repaired / stats.total) * 100).toFixed(1)}%` : '0%'}
              </div>
              <div style={{ fontSize: 12, color: '#8c8c8c' }}>修复率</div>
            </div>
          </Card>
        </Col>
      </Row>

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
          placeholder="差异类型"
          style={{ width: 150 }}
          allowClear
          value={filterDiffType}
          onChange={setFilterDiffType}
        >
          <Option value="MISSING_IN_TARGET">目标缺失</Option>
          <Option value="MISSING_IN_SOURCE">源端缺失</Option>
          <Option value="VALUE_MISMATCH">值不匹配</Option>
          <Option value="LATENCY_EXCEEDED">延迟过高</Option>
        </Select>
        <Select
          placeholder="修复状态"
          style={{ width: 150 }}
          allowClear
          value={filterRepairStatus}
          onChange={setFilterRepairStatus}
        >
          <Option value="PENDING">待修复</Option>
          <Option value="IN_PROGRESS">修复中</Option>
          <Option value="SUCCESS">已修复</Option>
          <Option value="FAILED">修复失败</Option>
        </Select>
        <Button
          icon={<ReloadOutlined />}
          onClick={loadDiffs}
          loading={loading}
        >
          刷新
        </Button>
      </div>

      {filteredDiffs.length > 0 ? (
        <Table
          columns={columns}
          dataSource={filteredDiffs}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1200 }}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条记录`
          }}
        />
      ) : (
        <Empty description="暂无差异数据" />
      )}

      <Modal
        title="差异详情"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={null}
        width={700}
      >
        {selectedDiff && (
          <div>
            <p><strong>差异ID:</strong> <span style={{ fontFamily: 'monospace' }}>{selectedDiff.id}</span></p>
            <p><strong>数据源:</strong> {selectedDiff.sourceType}</p>
            <p><strong>表名:</strong> {selectedDiff.tableName}</p>
            <p><strong>主键:</strong> {selectedDiff.key}</p>
            <p><strong>差异类型:</strong> {getDiffTypeTag(selectedDiff.diffType)}</p>
            <p><strong>延迟:</strong> {selectedDiff.latencyMs > 0 ? `${selectedDiff.latencyMs}ms` : '-'}</p>
            <p><strong>修复状态:</strong> {getRepairStatusTag(selectedDiff.repairStatus)}</p>
            <p><strong>修复次数:</strong> {selectedDiff.repairAttempts || 0}</p>
            {selectedDiff.repairErrorMessage && (
              <p><strong>修复错误:</strong> <span style={{ color: '#ff4d4f' }}>{selectedDiff.repairErrorMessage}</span></p>
            )}
            <p><strong>检测时间:</strong> {selectedDiff.detectedAt ? dayjs(selectedDiff.detectedAt).format('YYYY-MM-DD HH:mm:ss') : '-'}</p>

            {selectedDiff.diffFields && Object.keys(selectedDiff.diffFields).length > 0 && (
              <div style={{ marginTop: 16 }}>
                <h4>差异字段:</h4>
                {renderDiffFields(selectedDiff.diffFields)}
              </div>
            )}

            {selectedDiff.sourceData && (
              <div style={{ marginTop: 16 }}>
                <h4>源端数据:</h4>
                <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 4, maxHeight: 200, overflow: 'auto' }}>
                  {JSON.stringify(selectedDiff.sourceData, null, 2)}
                </pre>
              </div>
            )}

            {selectedDiff.targetData && (
              <div style={{ marginTop: 16 }}>
                <h4>目标端数据:</h4>
                <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 4, maxHeight: 200, overflow: 'auto' }}>
                  {JSON.stringify(selectedDiff.targetData, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default DiffList;

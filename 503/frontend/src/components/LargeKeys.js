import React, { useState, useEffect } from 'react';
import { Table, Card, Tag, message, Button, Space, InputNumber, Progress, Switch, Tooltip } from 'antd';
import { WarningOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { slowLogAPI } from '../api/api';

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function getRiskColor(risk) {
  const colors = {
    critical: '#cf1322',
    high: '#ff4d4f',
    medium: '#faad14',
    low: '#1890ff',
    normal: '#52c41a'
  };
  return colors[risk] || '#666';
}

function getRiskLabel(risk) {
  const labels = {
    critical: '严重',
    high: '高',
    medium: '中',
    low: '低',
    normal: '正常'
  };
  return labels[risk] || risk;
}

function LargeKeys() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sizeThreshold, setSizeThreshold] = useState(10);
  const [elementThreshold, setElementThreshold] = useState(null);
  const [useComposite, setUseComposite] = useState(true);

  useEffect(() => {
    loadData();
  }, [sizeThreshold, elementThreshold, useComposite]);

  const loadData = async () => {
    try {
      setLoading(true);
      const response = await slowLogAPI.getLargeKeys(
        sizeThreshold * 1024,
        elementThreshold,
        useComposite
      );
      if (response.data.success) {
        setData(response.data.data);
      }
    } catch (error) {
      message.error('加载大Key数据失败，请确保Redis服务正常');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const getTypeColor = (type) => {
    const colors = {
      string: 'blue',
      hash: 'purple',
      list: 'green',
      set: 'orange',
      zset: 'red',
    };
    return colors[type] || 'default';
  };

  const maxSize = data.length > 0 ? Math.max(...data.map((k) => k.total_size)) : 1;

  const maxScore = data.length > 0 ? Math.max(...data.map((k) => k.composite_score || 0)) : 1;

  const columns = [
    {
      title: '排名',
      key: 'rank',
      width: 70,
      render: (_, __, index) => index + 1,
    },
    {
      title: '风险等级',
      dataIndex: 'risk_level',
      key: 'risk_level',
      width: 100,
      render: (risk) => (
        <Tag color={getRiskColor(risk)} style={{ fontWeight: 'bold' }}>
          {risk === 'critical' && <WarningOutlined />} {getRiskLabel(risk)}
        </Tag>
      ),
    },
    {
      title: '综合评分',
      dataIndex: 'composite_score',
      key: 'composite_score',
      width: 160,
      sorter: (a, b) => (a.composite_score || 0) - (b.composite_score || 0),
      render: (score) => (
        <Progress
          percent={Math.round((score / maxScore) * 100)}
          size="small"
          format={() => score?.toFixed(2) || '0'}
          strokeColor={{
            '0%': '#52c41a',
            '50%': '#faad14',
            '100%': '#cf1322',
          }}
        />
      ),
    },
    {
      title: 'Key',
      dataIndex: 'key',
      key: 'key',
      ellipsis: true,
      render: (text) => (
        <Tag color="magenta" style={{ maxWidth: 300 }}>
          {text}
        </Tag>
      ),
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 90,
      render: (type) => <Tag color={getTypeColor(type)}>{type.toUpperCase()}</Tag>,
    },
    {
      title: '大小',
      dataIndex: 'total_size',
      key: 'total_size',
      width: 180,
      sorter: (a, b) => a.total_size - b.total_size,
      render: (size, record) => (
        <Space direction="vertical" size={0} style={{ width: '100%' }}>
          <Space>
            <span>{formatSize(size)}</span>
            {record.size_exceeded && (
              <Tooltip title={`超过阈值 ${formatSize(record.size_threshold)}`}>
                <Tag color="red" style={{ margin: 0 }}>超</Tag>
              </Tooltip>
            )}
          </Space>
          {record.size_ratio && (
            <span style={{ fontSize: 12, color: '#999' }}>
              {record.size_ratio.toFixed(2)}x 阈值
            </span>
          )}
        </Space>
      ),
    },
    {
      title: '元素数量',
      dataIndex: 'elements',
      key: 'elements',
      width: 140,
      sorter: (a, b) => a.elements - b.elements,
      render: (val, record) => (
        <Space direction="vertical" size={0}>
          <Space>
            <span>{val.toLocaleString()}</span>
            {record.element_exceeded && (
              <Tooltip title={`超过阈值 ${record.element_threshold} 个`}>
                <Tag color="orange" style={{ margin: 0 }}>超</Tag>
              </Tooltip>
            )}
          </Space>
          {record.element_ratio && (
            <span style={{ fontSize: 12, color: '#999' }}>
              {record.element_ratio.toFixed(2)}x 阈值
            </span>
          )}
        </Space>
      ),
    },
    {
      title: '内存得分',
      dataIndex: 'size_score',
      key: 'size_score',
      width: 100,
      render: (val) => <Tag color="blue">{val?.toFixed(2)}</Tag>,
    },
    {
      title: '元素得分',
      dataIndex: 'element_score',
      key: 'element_score',
      width: 100,
      render: (val) => <Tag color="purple">{val?.toFixed(2)}</Tag>,
    },
  ];

  const riskCounts = data.reduce((acc, k) => {
    acc[k.risk_level] = (acc[k.risk_level] || 0) + 1;
    return acc;
  }, {});

  return (
    <div>
      <Card
        title="大Key分析"
        className="table-container"
        extra={
          <Space wrap>
            <Tooltip title="内存权重60% + 元素数权重40%">
              <Space>
                <span>综合评分:</span>
                <Switch
                  checked={useComposite}
                  onChange={setUseComposite}
                  checkedChildren="开启"
                  unCheckedChildren="关闭"
                />
              </Space>
            </Tooltip>
            <Space>
              <span>大小阈值(KB):</span>
              <InputNumber min={1} max={102400} value={sizeThreshold} onChange={setSizeThreshold} />
            </Space>
            <Space>
              <span>元素阈值:</span>
              <InputNumber
                min={1}
                max={1000000}
                value={elementThreshold}
                onChange={setElementThreshold}
                placeholder="自动"
                allowClear
              />
            </Space>
            <Button type="primary" onClick={loadData} loading={loading}>
              扫描大Key
            </Button>
          </Space>
        }
      >
        <p style={{ marginBottom: 16, color: '#666' }}>
          <strong>注意:</strong> 扫描大Key会遍历整个数据库，可能会对Redis性能产生影响，建议在低峰期执行。
          综合评分 = 内存得分(60%) + 元素得分(40%)
        </p>

        {data.length > 0 && (
          <Space style={{ marginBottom: 16 }} wrap>
            <Tag color="red">
              共发现 {data.length} 个大Key
            </Tag>
            <Tag color="orange">
              总大小: {formatSize(data.reduce((sum, k) => sum + k.total_size, 0))}
            </Tag>
            <Tag color="blue">
              平均大小: {formatSize(data.reduce((sum, k) => sum + k.total_size, 0) / data.length)}
            </Tag>
            {riskCounts.critical > 0 && (
              <Tag color={getRiskColor('critical')}>
                <WarningOutlined /> 严重: {riskCounts.critical}
              </Tag>
            )}
            {riskCounts.high > 0 && (
              <Tag color={getRiskColor('high')}>
                高风险: {riskCounts.high}
              </Tag>
            )}
            {riskCounts.medium > 0 && (
              <Tag color={getRiskColor('medium')}>
                中风险: {riskCounts.medium}
              </Tag>
            )}
            {riskCounts.low > 0 && (
              <Tag color={getRiskColor('low')}>
                低风险: {riskCounts.low}
              </Tag>
            )}
          </Space>
        )}

        <Table
          columns={columns}
          dataSource={data}
          rowKey="key"
          loading={loading}
          pagination={{
            pageSize: 15,
            showTotal: (total) => `共 ${total} 个大Key`,
          }}
          scroll={{ x: 1200 }}
        />
      </Card>
    </div>
  );
}

export default LargeKeys;

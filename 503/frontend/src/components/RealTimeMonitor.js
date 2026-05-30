import React, { useState, useEffect, useRef } from 'react';
import { Row, Col, Card, Statistic, Button, Space, Tag, Table, Progress } from 'antd';
import { PlayCircleOutlined, PauseCircleOutlined, ReloadOutlined, ThunderboltOutlined } from '@ant-design/icons';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
  ComposedChart,
  Bar,
} from 'recharts';
import { monitorAPI } from '../api/api';

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function RealTimeMonitor() {
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [aggregatedMetrics, setAggregatedMetrics] = useState(null);
  const [aggregatedHistory, setAggregatedHistory] = useState([]);
  const [slowLogs, setSlowLogs] = useState([]);
  const [streamStats, setStreamStats] = useState(null);
  const [stream_interval, setStreamInterval] = useState(100);
  const intervalRef = useRef(null);
  const slowLogIntervalRef = useRef(null);

  useEffect(() => {
    loadInitialData();
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      if (slowLogIntervalRef.current) {
        clearInterval(slowLogIntervalRef.current);
      }
    };
  }, []);

  const loadInitialData = async () => {
    try {
      const response = await monitorAPI.getMetrics();
      if (response.data.success) {
        setAggregatedMetrics(response.data.data);
      }
    } catch (error) {
      console.error('Load metrics error:', error);
    }
  };

  const startMonitoring = async () => {
    try {
      await monitorAPI.startStreamMonitor();
      setIsMonitoring(true);
      
      intervalRef.current = setInterval(async () => {
        try {
          const response = await monitorAPI.getAggregatedMetrics();
          if (response.data.success) {
            const data = response.data.data;
            setAggregatedMetrics(data);
            
            if (data) {
              setAggregatedHistory((prev) => {
                const updated = [...prev, {
                  time: data.timestamp,
                  avg_qps: data.commands_per_second?.avg || 0,
                  max_qps: data.commands_per_second?.max || 0,
                  min_qps: data.commands_per_second?.min || 0,
                  avg_connections: data.connected_clients?.avg || 0,
                  max_connections: data.connected_clients?.max || 0,
                  avg_hit_rate: data.hit_rate?.avg || 0,
                  avg_memory: data.used_memory?.avg || 0,
                  max_memory: data.used_memory?.max || 0,
                }];
                return updated.slice(-120);
              });

              if (data.stream_stats) {
                setStreamStats(data.stream_stats);
              }
            }
          }
        } catch (error) {
          console.error('Monitor update error:', error);
        }
      }, 1000);

      slowLogIntervalRef.current = setInterval(async () => {
        try {
          const slowLogResponse = await monitorAPI.getStreamSlowLogs();
          if (slowLogResponse.data.success && slowLogResponse.data.data.length > 0) {
            const newLogs = slowLogResponse.data.data;
            setSlowLogs((prev) => [...newLogs, ...prev].slice(0, 100));
          }
        } catch (error) {
          console.error('Slow log error:', error);
        }
      }, 2000);
    } catch (error) {
      console.error('Start monitor error:', error);
    }
  };

  const stopMonitoring = async () => {
    try {
      await monitorAPI.stopStreamMonitor();
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      if (slowLogIntervalRef.current) {
        clearInterval(slowLogIntervalRef.current);
        slowLogIntervalRef.current = null;
      }
      setIsMonitoring(false);
    } catch (error) {
      console.error('Stop monitor error:', error);
    }
  };

  const chartData = aggregatedHistory.map((m, idx) => ({
    time: m.time ? m.time.split(' ')[1] : `-${aggregatedHistory.length - idx}s`,
    avg_qps: m.avg_qps,
    max_qps: m.max_qps,
    min_qps: m.min_qps,
    connections: m.avg_connections,
    hitRate: m.avg_hit_rate,
    memory_mb: m.avg_memory ? Math.round(m.avg_memory / 1024 / 1024) : 0,
  }));

  const slowLogColumns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: '耗时(ms)',
      dataIndex: 'duration_ms',
      key: 'duration_ms',
      width: 100,
      render: (val) => <Tag color="red">{val.toFixed(3)}</Tag>,
    },
    {
      title: '命令',
      dataIndex: 'command',
      key: 'command',
      ellipsis: true,
    },
    {
      title: '时间',
      dataIndex: 'datetime',
      key: 'datetime',
      width: 160,
    },
  ];

  const isAggregated = aggregatedMetrics && typeof aggregatedMetrics.commands_per_second === 'object';
  const getValue = (field) => {
    if (!aggregatedMetrics) return 0;
    const val = aggregatedMetrics[field];
    return typeof val === 'object' ? val.last : val;
  };
  const getAvg = (field) => {
    if (!isAggregated) return null;
    return aggregatedMetrics[field]?.avg;
  };
  const getMax = (field) => {
    if (!isAggregated) return null;
    return aggregatedMetrics[field]?.max;
  };
  const getMin = (field) => {
    if (!isAggregated) return null;
    return aggregatedMetrics[field]?.min;
  };

  return (
    <div>
      {streamStats && (
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={24} sm={12} md={8}>
            <Card size="small" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: '#fff' }}>
              <Space direction="vertical" size={0} style={{ width: '100%' }}>
                <Space>
                  <ThunderboltOutlined style={{ fontSize: 18 }} />
                  <span style={{ fontWeight: 'bold' }}>流式采集状态</span>
                  {isMonitoring ? (
                    <Tag color="green" style={{ margin: 0 }}>运行中</Tag>
                  ) : (
                    <Tag color="default" style={{ margin: 0 }}>已停止</Tag>
                  )}
                </Space>
                <div style={{ marginTop: 8 }}>
                  采集间隔: {streamStats.stream_interval_ms}ms
                  <Tag color="blue" style={{ marginLeft: 8 }}>{1000 / streamStats.stream_interval_ms} 次/秒</Tag>
                </div>
              </Space>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Card size="small">
              <Statistic
                title="已采集样本数"
                value={streamStats.total_collected?.toLocaleString()}
                valueStyle={{ color: '#667eea', fontSize: 18 }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Card size="small">
              <Statistic
                title="队列利用率"
                value={Math.round((streamStats.queue_size / streamStats.queue_max) * 100)}
                suffix="%"
                valueStyle={{ color: streamStats.queue_size > streamStats.queue_max * 0.8 ? '#f5576c' : '#52c41a', fontSize: 18 }}
              />
              <Progress
                percent={Math.round((streamStats.queue_size / streamStats.queue_max) * 100)}
                size="small"
                showInfo={false}
                strokeColor={streamStats.queue_size > streamStats.queue_max * 0.8 ? '#f5576c' : '#52c41a'}
                style={{ marginTop: 4 }}
              />
            </Card>
          </Col>
        </Row>
      )}

      <Card
        className="monitor-card"
        title={
          <Space>
            {isMonitoring && <span className="live-indicator" />}
            实时监控
            {isMonitoring && <Tag color="green">100ms 流式采集</Tag>}
            {isAggregated && <Tag color="blue">秒级聚合</Tag>}
          </Space>
        }
        extra={
          <Space>
            {!isMonitoring ? (
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={startMonitoring}
              >
                开始监控
              </Button>
            ) : (
              <Button
                icon={<PauseCircleOutlined />}
                onClick={stopMonitoring}
                danger
              >
                停止监控
              </Button>
            )}
            <Button icon={<ReloadOutlined />} onClick={loadInitialData}>
              刷新
            </Button>
          </Space>
        }
      >
        {aggregatedMetrics && (
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={24} sm={12} md={6}>
              <Card className="stat-card">
                <Statistic
                  title="QPS"
                  value={getValue('commands_per_second')}
                  valueStyle={{ color: '#667eea' }}
                />
                {isAggregated && (
                  <Space direction="vertical" size={0} style={{ width: '100%', marginTop: 4 }}>
                    <span style={{ fontSize: 12, color: '#999' }}>
                      avg: {getAvg('commands_per_second')?.toFixed(2)} | max: {getMax('commands_per_second')?.toFixed(2)} | min: {getMin('commands_per_second')?.toFixed(2)}
                    </span>
                  </Space>
                )}
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card className="stat-card">
                <Statistic
                  title="连接数"
                  value={getValue('connected_clients')}
                  valueStyle={{ color: '#764ba2' }}
                />
                {isAggregated && (
                  <span style={{ fontSize: 12, color: '#999' }}>
                    avg: {Math.round(getAvg('connected_clients') || 0)} | max: {getMax('connected_clients')} | min: {getMin('connected_clients')}
                  </span>
                )}
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card className="stat-card">
                <Statistic
                  title="命中率"
                  value={getValue('hit_rate')}
                  suffix="%"
                  valueStyle={{ color: getValue('hit_rate') < 90 ? '#f5576c' : '#52c41a' }}
                />
                {isAggregated && (
                  <span style={{ fontSize: 12, color: '#999' }}>
                    avg: {getAvg('hit_rate')?.toFixed(1)}%
                  </span>
                )}
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card className="stat-card">
                <Statistic
                  title="内存使用"
                  value={formatSize(getValue('used_memory'))}
                  valueStyle={{ color: '#faad14' }}
                />
                {isAggregated && (
                  <span style={{ fontSize: 12, color: '#999' }}>
                    avg: {formatSize(Math.round(getAvg('used_memory') || 0))} | max: {formatSize(getMax('used_memory') || 0)}
                  </span>
                )}
              </Card>
            </Col>
          </Row>
        )}

        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={24} lg={12}>
            <Card title="QPS 趋势 (avg/max/min)" className="chart-container" style={{ height: 280 }}>
              <ResponsiveContainer width="100%" height="100%">
                {isAggregated && chartData.some(d => d.max_qps > 0) ? (
                  <ComposedChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Area type="monotone" dataKey="max_qps" fill="#667eea22" stroke="#667eea" strokeWidth={1} name="Max QPS" />
                    <Area type="monotone" dataKey="min_qps" fill="#ffffff" stroke="#aaaaaa" strokeWidth={1} name="Min QPS" />
                    <Line type="monotone" dataKey="avg_qps" stroke="#f5576c" strokeWidth={2} dot={false} name="Avg QPS" />
                  </ComposedChart>
                ) : (
                  <AreaChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time" />
                    <YAxis />
                    <Tooltip />
                    <Area
                      type="monotone"
                      dataKey="avg_qps"
                      stroke="#667eea"
                      fill="#667eea"
                      fillOpacity={0.3}
                      name="QPS"
                    />
                  </AreaChart>
                )}
              </ResponsiveContainer>
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card title="连接数 & 内存趋势" className="chart-container" style={{ height: 280 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis yAxisId="left" />
                  <YAxis yAxisId="right" orientation="right" />
                  <Tooltip />
                  <Legend />
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="connections"
                    stroke="#764ba2"
                    strokeWidth={2}
                    dot={false}
                    name="连接数"
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="memory_mb"
                    stroke="#faad14"
                    strokeWidth={2}
                    dot={false}
                    name="内存(MB)"
                  />
                </LineChart>
              </ResponsiveContainer>
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 16]}>
          <Col xs={24} lg={12}>
            <Card title="命中率趋势" className="chart-container" style={{ height: 280 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis domain={[0, 100]} />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="hitRate"
                    stroke="#52c41a"
                    strokeWidth={2}
                    dot={false}
                    name="命中率(%)"
                  />
                </LineChart>
              </ResponsiveContainer>
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card title="新产生的慢查询" className="table-container" style={{ height: 280, overflow: 'auto' }}>
              {slowLogs.length > 0 ? (
                <Table
                  columns={slowLogColumns}
                  dataSource={slowLogs}
                  rowKey="id"
                  size="small"
                  pagination={false}
                  scroll={{ y: 180 }}
                />
              ) : (
                <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
                  {isMonitoring ? '等待新的慢查询产生...' : '点击开始监控以捕获新的慢查询'}
                </div>
              )}
            </Card>
          </Col>
        </Row>

        {aggregatedMetrics && (
          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={24} sm={8}>
              <Card size="small">
                <Statistic
                  title="慢查询总数"
                  value={getValue('slowlog_length')}
                  valueStyle={{ color: '#f5576c', fontSize: 18 }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card size="small">
                <Statistic
                  title="已处理命令数"
                  value={getValue('total_commands_processed')?.toLocaleString()}
                  valueStyle={{ color: '#667eea', fontSize: 18 }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card size="small">
                <Statistic
                  title="阻塞客户端"
                  value={getValue('blocked_clients')}
                  valueStyle={{ color: getValue('blocked_clients') > 0 ? '#f5576c' : '#52c41a', fontSize: 18 }}
                />
              </Card>
            </Col>
          </Row>
        )}
      </Card>
    </div>
  );
}

export default RealTimeMonitor;

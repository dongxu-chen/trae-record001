import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Table, Tag, Progress, Statistic, Empty } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  ArrowUpOutlined
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import dayjs from 'dayjs';
import { checkApi } from '../services/api';
import { wsService } from '../services/websocket';

const Dashboard = () => {
  const [statistics, setStatistics] = useState(null);
  const [recentResults, setRecentResults] = useState([]);
  const [runningTasks, setRunningTasks] = useState([]);
  const [latencyHistory, setLatencyHistory] = useState([]);
  const [diffHistory, setDiffHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
    setupWebSocket();
    return () => {
      wsService.unsubscribe('/topic/diffs');
      wsService.unsubscribe('/topic/results');
    };
  }, []);

  const loadData = async () => {
    try {
      const [stats, results, tasks] = await Promise.all([
        checkApi.getStatistics(),
        checkApi.getRecentResults(),
        checkApi.getRunningTasks()
      ]);
      setStatistics(stats);
      setRecentResults(results || []);
      setRunningTasks(tasks || []);
      updateChartData(results || []);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const setupWebSocket = () => {
    wsService.subscribe('/topic/diffs', (message) => {
      if (message.type === 'DIFF' && message.payload) {
        const diff = message.payload;
        setStatistics(prev => prev ? {
          ...prev,
          totalDiffs: prev.totalDiffs + 1
        } : null);
      }
    });

    wsService.subscribe('/topic/results', (message) => {
      if (message.type === 'TASK_COMPLETE' && message.payload) {
        setRecentResults(prev => [message.payload, ...prev].slice(0, 10));
        updateChartData([message.payload, ...diffHistory].slice(0, 10));
      }
    });
  };

  const updateChartData = (results) => {
    const sorted = [...results].sort((a, b) =>
      new Date(a.startTime) - new Date(b.startTime)
    );

    const latencyData = sorted.map(r => ({
      time: dayjs(r.startTime).format('MM-DD HH:mm'),
      avg: r.avgLatencyMs || 0,
      max: r.maxLatencyMs || 0
    }));

    const diffData = sorted.map(r => ({
      time: dayjs(r.startTime).format('MM-DD HH:mm'),
      diffs: r.diffCount || 0,
      total: r.totalSourceRecords || 0
    }));

    setLatencyHistory(latencyData);
    setDiffHistory(diffData);
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

  const latencyChartOption = {
    title: { text: '同步延迟趋势', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    legend: { data: ['平均延迟', '最大延迟'], bottom: 0 },
    xAxis: {
      type: 'category',
      data: latencyHistory.map(d => d.time)
    },
    yAxis: {
      type: 'value',
      name: '毫秒',
      axisLabel: { formatter: '{value}ms' }
    },
    series: [
      {
        name: '平均延迟',
        type: 'line',
        smooth: true,
        data: latencyHistory.map(d => d.avg),
        itemStyle: { color: '#1890ff' },
        areaStyle: { color: 'rgba(24, 144, 255, 0.1)' }
      },
      {
        name: '最大延迟',
        type: 'line',
        smooth: true,
        data: latencyHistory.map(d => d.max),
        itemStyle: { color: '#faad14' }
      }
    ],
    grid: { left: 50, right: 20, top: 40, bottom: 40 }
  };

  const diffChartOption = {
    title: { text: '数据差异趋势', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    legend: { data: ['差异数量', '源端总数'], bottom: 0 },
    xAxis: {
      type: 'category',
      data: diffHistory.map(d => d.time)
    },
    yAxis: {
      type: 'value',
      name: '数量'
    },
    series: [
      {
        name: '差异数量',
        type: 'bar',
        data: diffHistory.map(d => d.diffs),
        itemStyle: { color: '#ff4d4f' }
      },
      {
        name: '源端总数',
        type: 'line',
        smooth: true,
        data: diffHistory.map(d => d.total),
        itemStyle: { color: '#52c41a' },
        yAxisIndex: 0
      }
    ],
    grid: { left: 50, right: 20, top: 40, bottom: 40 }
  };

  const resultColumns = [
    {
      title: '任务ID',
      dataIndex: 'taskId',
      key: 'taskId',
      width: 200,
      render: (text) => <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{text}</span>
    },
    {
      title: '数据源',
      dataIndex: 'sourceType',
      key: 'sourceType',
      width: 100
    },
    {
      title: '表名',
      dataIndex: 'tableName',
      key: 'tableName'
    },
    {
      title: '校验模式',
      dataIndex: 'checkMode',
      key: 'checkMode',
      width: 120,
      render: (text) => {
        const modeMap = {
          'FULL': { color: 'blue', text: '全量比对' },
          'STRATIFIED_HASH': { color: 'green', text: '分层哈希' }
        };
        const config = modeMap[text] || { color: 'default', text: text || '未知' };
        return <Tag color={config.color}>{config.text}</Tag>;
      }
    },
    {
      title: '源端数量',
      dataIndex: 'totalSourceRecords',
      key: 'totalSourceRecords',
      width: 100,
      render: (text) => text?.toLocaleString()
    },
    {
      title: '哈希跳过',
      key: 'hashSkipped',
      width: 100,
      render: (_, record) => {
        const skipped = record.metrics?.hashSkippedRecords;
        return skipped != null ? skipped.toLocaleString() : '-';
      }
    },
    {
      title: '差异数量',
      dataIndex: 'diffCount',
      key: 'diffCount',
      width: 100,
      render: (text) => (
        <span style={{ color: text > 0 ? '#ff4d4f' : '#52c41a', fontWeight: 'bold' }}>
          {text || 0}
        </span>
      )
    },
    {
      title: '平均延迟',
      dataIndex: 'avgLatencyMs',
      key: 'avgLatencyMs',
      width: 100,
      render: (text) => text ? `${text.toFixed(0)}ms` : '-'
    },
    {
      title: '完成时间',
      dataIndex: 'endTime',
      key: 'endTime',
      width: 170,
      render: (text) => text ? dayjs(text).format('YYYY-MM-DD HH:mm:ss') : '-'
    }
  ];

  const statCards = statistics ? [
    {
      title: '总任务数',
      value: statistics.totalTasks,
      icon: <SyncOutlined style={{ color: '#1890ff', fontSize: 24 }} />,
      color: '#1890ff'
    },
    {
      title: '已完成',
      value: statistics.completedTasks,
      icon: <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 24 }} />,
      color: '#52c41a'
    },
    {
      title: '运行中',
      value: statistics.runningTasks,
      icon: <SyncOutlined spin style={{ color: '#1890ff', fontSize: 24 }} />,
      color: '#1890ff'
    },
    {
      title: '总差异数',
      value: statistics.totalDiffs,
      icon: <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 24 }} />,
      color: '#ff4d4f'
    },
    {
      title: '已修复',
      value: statistics.totalRepaired,
      icon: <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 24 }} />,
      color: '#52c41a'
    },
    {
      title: '待修复',
      value: statistics.pendingRepair,
      icon: <ClockCircleOutlined style={{ color: '#faad14', fontSize: 24 }} />,
      color: '#faad14'
    }
  ] : [];

  if (loading) {
    return <div style={{ textAlign: 'center', padding: 50 }}>加载中...</div>;
  }

  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        {statCards.map((stat, index) => (
          <Col xs={12} sm={8} md={4} key={index}>
            <Card>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                {stat.icon}
                <div>
                  <Statistic
                    title={stat.title}
                    value={stat.value}
                    valueStyle={{ color: stat.color, fontSize: 24 }}
                  />
                </div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      {runningTasks.length > 0 && (
        <Card title="运行中的任务" style={{ marginBottom: 16 }}>
          <Row gutter={[16, 16]}>
            {runningTasks.map(task => (
              <Col xs={24} sm={12} md={8} key={task.id}>
                <Card size="small">
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <span style={{ fontWeight: 'bold' }}>{task.tableName}</span>
                    {getStatusTag(task.status)}
                  </div>
                  <div style={{ fontSize: 12, color: '#8c8c8c', marginBottom: 8 }}>
                    {task.sourceType} · {task.id.substring(0, 8)}...
                  </div>
                  <Progress percent={30} showInfo={false} status="active" />
                </Card>
              </Col>
            ))}
          </Row>
        </Card>
      )}

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} md={12}>
          <div className="chart-container">
            {latencyHistory.length > 0 ? (
              <ReactECharts option={latencyChartOption} style={{ height: 300 }} />
            ) : (
              <Empty description="暂无延迟数据" style={{ height: 300, padding: 100 }} />
            )}
          </div>
        </Col>
        <Col xs={24} md={12}>
          <div className="chart-container">
            {diffHistory.length > 0 ? (
              <ReactECharts option={diffChartOption} style={{ height: 300 }} />
            ) : (
              <Empty description="暂无差异数据" style={{ height: 300, padding: 100 }} />
            )}
          </div>
        </Col>
      </Row>

      <Card title="最近校验结果">
        {recentResults.length > 0 ? (
          <Table
            columns={resultColumns}
            dataSource={recentResults}
            rowKey="taskId"
            size="small"
            pagination={{ pageSize: 5 }}
          />
        ) : (
          <Empty description="暂无校验结果" />
        )}
      </Card>
    </div>
  );
};

export default Dashboard;

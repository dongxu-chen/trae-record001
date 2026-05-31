import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Tag, Table, Progress, Spin } from 'antd';
import {
  ThunderboltOutlined,
  SafetyCertificateOutlined,
  CheckCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { drillApi, strategyApi, reportApi } from '../services/api';

const Dashboard = () => {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalTasks: 0,
    runningTasks: 0,
    totalStrategies: 0,
    totalReports: 0,
    avgScore: 0,
  });
  const [recentTasks, setRecentTasks] = useState([]);

  useEffect(() => {
    loadData();
    const timer = setInterval(loadData, 10000);
    return () => clearInterval(timer);
  }, []);

  const loadData = async () => {
    try {
      const [tasksRes, strategiesRes, reportsRes] = await Promise.all([
        drillApi.listTasks(),
        strategyApi.list(),
        reportApi.list(),
      ]);

      const tasks = tasksRes.data?.data || [];
      const strategies = strategiesRes.data?.data || [];
      const reports = reportsRes.data?.data || [];

      const running = tasks.filter(t => t.status === 'RUNNING').length;
      const scores = reports.map(r => r.result?.score || 0).filter(s => s > 0);
      const avgScore = scores.length > 0
        ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1)
        : 0;

      setStats({
        totalTasks: tasks.length,
        runningTasks: running,
        totalStrategies: strategies.length,
        totalReports: reports.length,
        avgScore,
      });

      setRecentTasks(tasks.slice(0, 10).map(t => ({
        key: t.id,
        id: t.id,
        name: t.name,
        status: t.status,
        createTime: t.createTime,
        score: t.result?.score,
      })));
    } catch (e) {
      console.error('Failed to load dashboard data', e);
    } finally {
      setLoading(false);
    }
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

  const columns = [
    { title: '任务名称', dataIndex: 'name', key: 'name', ellipsis: true },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => <Tag color={statusColorMap[status]}>{statusLabelMap[status] || status}</Tag>,
    },
    {
      title: '评分',
      dataIndex: 'score',
      key: 'score',
      render: (score) => score != null ? (
        <span style={{ color: score >= 80 ? '#52c41a' : score >= 60 ? '#faad14' : '#ff4d4f', fontWeight: 'bold' }}>
          {score}
        </span>
      ) : '-',
    },
    { title: '创建时间', dataIndex: 'createTime', key: 'createTime', width: 180 },
  ];

  const scoreColor = stats.avgScore >= 80 ? '#52c41a' : stats.avgScore >= 60 ? '#faad14' : '#ff4d4f';

  return (
    <Spin spinning={loading}>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            <Statistic
              title="演练任务总数"
              value={stats.totalTasks}
              prefix={<ThunderboltOutlined style={{ color: '#1677ff' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            <Statistic
              title="运行中任务"
              value={stats.runningTasks}
              prefix={<WarningOutlined style={{ color: '#faad14' }} />}
              valueStyle={{ color: stats.runningTasks > 0 ? '#faad14' : '#333' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            <Statistic
              title="限流策略数"
              value={stats.totalStrategies}
              prefix={<SafetyCertificateOutlined style={{ color: '#52c41a' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            <Statistic
              title="平均评分"
              value={stats.avgScore}
              suffix="/ 100"
              prefix={<CheckCircleOutlined style={{ color: scoreColor }} />}
              valueStyle={{ color: scoreColor }}
            />
          </Card>
        </Col>
      </Row>

      <Card title="系统健康度" style={{ marginTop: 16 }}>
        <Row gutter={16}>
          <Col span={12}>
            <div style={{ textAlign: 'center' }}>
              <Progress
                type="dashboard"
                percent={parseFloat(stats.avgScore) || 0}
                strokeColor={scoreColor}
                format={percent => <span style={{ fontSize: 24, fontWeight: 'bold' }}>{percent}</span>}
              />
              <div style={{ marginTop: 8, color: '#666' }}>系统综合评分</div>
            </div>
          </Col>
          <Col span={12}>
            <Row gutter={[8, 8]}>
              <Col span={12}>
                <Card size="small">
                  <Statistic title="报告总数" value={stats.totalReports} />
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small">
                  <Statistic title="活跃策略" value={stats.totalStrategies} />
                </Card>
              </Col>
            </Row>
          </Col>
        </Row>
      </Card>

      <Card title="最近演练任务" style={{ marginTop: 16 }}>
        <Table
          columns={columns}
          dataSource={recentTasks}
          pagination={false}
          size="small"
          locale={{ emptyText: '暂无演练任务' }}
        />
      </Card>
    </Spin>
  );
};

export default Dashboard;

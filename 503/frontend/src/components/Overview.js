import React from 'react';
import { Row, Col, Card, Statistic, Button, Space, Table, Tag } from 'antd';
import { ReloadOutlined, ThunderboltOutlined, FireOutlined, DatabaseOutlined, RocketOutlined } from '@ant-design/icons';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

const COLORS = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#00f2fe'];

function Overview({ data, loading, onRefresh }) {
  if (!data) return null;

  const { summary, command_patterns, hot_keys, large_keys, metrics, database_stats } = data;

  const commandChartData = command_patterns.slice(0, 8).map((item) => ({
    name: item.command,
    count: item.count,
    avgTime: parseFloat(item.avg_time.toFixed(2)),
  }));

  const pieChartData = command_patterns.slice(0, 6).map((item) => ({
    name: item.command,
    value: item.count,
  }));

  const slowLogColumns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '耗时(ms)',
      dataIndex: 'duration_ms',
      key: 'duration_ms',
      width: 100,
      render: (val) => <Tag color="red">{val.toFixed(2)}</Tag>,
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
      width: 180,
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, textAlign: 'right' }}>
        <Button icon={<ReloadOutlined />} onClick={onRefresh} loading={loading}>
          刷新数据
        </Button>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card className="stat-card">
            <Statistic
              title={<span><RocketOutlined /> 慢查询总数</span>}
              value={summary.total_slow_logs}
              valueStyle={{ color: '#667eea' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="stat-card">
            <Statistic
              title={<span><ThunderboltOutlined /> 命令类型数</span>}
              value={summary.total_commands}
              valueStyle={{ color: '#764ba2' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="stat-card">
            <Statistic
              title={<span><FireOutlined /> 热点Key数</span>}
              value={summary.hot_keys_count}
              valueStyle={{ color: '#f5576c' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="stat-card">
            <Statistic
              title={<span><DatabaseOutlined /> 大Key数</span>}
              value={summary.large_keys_count}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={16}>
          <Card title="命令执行次数分布" className="chart-container" style={{ height: 320 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={commandChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#667eea" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="命令占比" className="chart-container" style={{ height: 320 }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieChartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={40}
                  outerRadius={80}
                  paddingAngle={2}
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                >
                  {pieChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={12}>
          <Card title="热点Key Top 10" className="table-container">
            <Table
              dataSource={hot_keys.slice(0, 10)}
              rowKey="key"
              size="small"
              pagination={false}
              columns={[
                { title: 'Key', dataIndex: 'key', key: 'key', ellipsis: true },
                { title: '访问次数', dataIndex: 'count', key: 'count', width: 100 },
                { title: '总耗时(ms)', dataIndex: 'total_time', key: 'total_time', width: 100, render: (v) => v.toFixed(2) },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="最近慢查询" className="table-container">
            <Table
              dataSource={data.slow_logs?.slice(0, 10) || []}
              rowKey="id"
              size="small"
              pagination={false}
              columns={slowLogColumns}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="数据库统计" className="table-container">
            <Table
              dataSource={database_stats}
              rowKey="database"
              size="small"
              pagination={false}
              columns={[
                { title: '数据库', dataIndex: 'database', key: 'database', width: 100 },
                { title: 'Key数量', dataIndex: 'keys', key: 'keys' },
                { title: '过期Key', dataIndex: 'expires', key: 'expires' },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="大Key列表" className="table-container">
            <Table
              dataSource={large_keys.slice(0, 10)}
              rowKey="key"
              size="small"
              pagination={false}
              columns={[
                { title: 'Key', dataIndex: 'key', key: 'key', ellipsis: true },
                { title: '类型', dataIndex: 'type', key: 'type', width: 80, render: (v) => <Tag>{v}</Tag> },
                { title: '大小(KB)', dataIndex: 'total_size', key: 'total_size', width: 100, render: (v) => (v / 1024).toFixed(2) },
              ]}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}

export default Overview;

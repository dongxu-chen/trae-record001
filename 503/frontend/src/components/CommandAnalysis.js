import React, { useState, useEffect } from 'react';
import { Table, Card, Row, Col, Statistic, message, Switch, Space, Button, Tag, Tooltip } from 'antd';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { slowLogAPI } from '../api/api';

function CommandAnalysis() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [normalize, setNormalize] = useState(true);
  const [expandedRowKeys, setExpandedRowKeys] = useState([]);

  useEffect(() => {
    loadData();
  }, [normalize]);

  const loadData = async () => {
    try {
      setLoading(true);
      const response = await slowLogAPI.getCommandAnalysis(1000, normalize);
      if (response.data.success) {
        setData(response.data.data);
      }
    } catch (error) {
      message.error('加载命令分析数据失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const chartData = data.slice(0, 10).map((item) => ({
    name: item.command,
    count: item.count,
    avgTime: parseFloat(item.avg_time.toFixed(2)),
    maxTime: parseFloat(item.max_time.toFixed(2)),
  }));

  const totalCount = data.reduce((sum, item) => sum + item.count, 0);
  const totalTime = data.reduce((sum, item) => sum + item.total_time, 0);

  const columns = [
    {
      title: '归一化命令',
      dataIndex: 'command',
      key: 'command',
      width: 200,
      render: (text, record) => (
        <Space>
          <strong style={{ color: '#667eea' }}>{text}</strong>
          {record.base_command && record.base_command !== text && (
            <Tag color="purple">{record.base_command}</Tag>
          )}
        </Space>
      ),
    },
    {
      title: '执行次数',
      dataIndex: 'count',
      key: 'count',
      width: 120,
      sorter: (a, b) => a.count - b.count,
    },
    {
      title: '占比',
      key: 'ratio',
      width: 100,
      render: (_, record) => `${((record.count / totalCount) * 100).toFixed(2)}%`,
    },
    {
      title: '总耗时(ms)',
      dataIndex: 'total_time',
      key: 'total_time',
      sorter: (a, b) => a.total_time - b.total_time,
      render: (val) => val.toFixed(2),
    },
    {
      title: '平均耗时(ms)',
      dataIndex: 'avg_time',
      key: 'avg_time',
      sorter: (a, b) => a.avg_time - b.avg_time,
      render: (val) => val.toFixed(3),
    },
    {
      title: '最大耗时(ms)',
      dataIndex: 'max_time',
      key: 'max_time',
      sorter: (a, b) => a.max_time - b.max_time,
      render: (val) => val.toFixed(3),
    },
    {
      title: '最小耗时(ms)',
      dataIndex: 'min_time',
      key: 'min_time',
      sorter: (a, b) => a.min_time - b.min_time,
      render: (val) => val.toFixed(3),
    },
  ];

  const expandedRowRender = (record) => {
    if (!record.sample_commands || record.sample_commands.length === 0) {
      return <p style={{ padding: 16, color: '#999' }}>暂无示例命令</p>;
    }
    return (
      <div style={{ padding: 16, background: '#fafafa' }}>
        <p style={{ marginBottom: 8, fontWeight: 'bold' }}>示例命令：</p>
        {record.sample_commands.map((cmd, idx) => (
          <code key={idx} style={{
            display: 'block',
            padding: '8px 12px',
            marginBottom: 4,
            background: '#f5f5f5',
            borderRadius: 4,
            fontFamily: 'monospace'
          }}>
            {cmd}
          </code>
        ))}
      </div>
    );
  };

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space>
          <Tooltip title="将相同命令的不同参数归为一类统计">
            <span>参数归一化:</span>
          </Tooltip>
          <Switch
            checked={normalize}
            onChange={setNormalize}
            checkedChildren="开启"
            unCheckedChildren="关闭"
          />
          {normalize && (
            <Tag color="purple">
              ? 表示参数占位符, ?* 表示多个参数
            </Tag>
          )}
        </Space>
        <Button onClick={loadData} loading={loading}>
          刷新
        </Button>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={8}>
          <Card className="stat-card">
            <Statistic
              title="命令总执行次数"
              value={totalCount}
              valueStyle={{ color: '#667eea' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card className="stat-card">
            <Statistic
              title="总耗时(ms)"
              value={totalTime.toFixed(2)}
              valueStyle={{ color: '#764ba2' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card className="stat-card">
            <Statistic
              title="命令类型数"
              value={data.length}
              valueStyle={{ color: '#f5576c' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="命令执行次数" className="chart-container" style={{ height: 350 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="count" fill="#667eea" name="执行次数" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="平均耗时对比(ms)" className="chart-container" style={{ height: 350 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="avgTime" fill="#764ba2" name="平均耗时" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      <Card title="命令详情" className="table-container">
        <Table
          columns={columns}
          dataSource={data}
          rowKey="command"
          loading={loading}
          pagination={{
            pageSize: 15,
            showTotal: (total) => `共 ${total} 种命令`,
          }}
          expandable={{
            expandedRowRender,
            expandedRowKeys,
            onExpandedRowsChange: setExpandedRowKeys,
          }}
        />
      </Card>
    </div>
  );
}

export default CommandAnalysis;

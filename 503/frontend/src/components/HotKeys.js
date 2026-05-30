import React, { useState, useEffect } from 'react';
import { Table, Card, Tag, message, Button, Space, InputNumber } from 'antd';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { slowLogAPI } from '../api/api';

function HotKeys() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [topN, setTopN] = useState(20);

  useEffect(() => {
    loadData();
  }, [topN]);

  const loadData = async () => {
    try {
      setLoading(true);
      const response = await slowLogAPI.getHotKeys(1000, topN);
      if (response.data.success) {
        setData(response.data.data);
      }
    } catch (error) {
      message.error('加载热点Key失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const chartData = data.slice(0, 10).map((item) => ({
    name: item.key.length > 20 ? item.key.substring(0, 20) + '...' : item.key,
    fullName: item.key,
    count: item.count,
    totalTime: parseFloat(item.total_time.toFixed(2)),
  }));

  const columns = [
    {
      title: '排名',
      key: 'rank',
      width: 80,
      render: (_, __, index) => index + 1,
    },
    {
      title: 'Key',
      dataIndex: 'key',
      key: 'key',
      ellipsis: true,
      render: (text) => (
        <Tag color="purple" style={{ maxWidth: 300 }}>
          {text}
        </Tag>
      ),
    },
    {
      title: '访问次数',
      dataIndex: 'count',
      key: 'count',
      width: 120,
      sorter: (a, b) => a.count - b.count,
    },
    {
      title: '总耗时(ms)',
      dataIndex: 'total_time',
      key: 'total_time',
      width: 140,
      sorter: (a, b) => a.total_time - b.total_time,
      render: (val) => val.toFixed(2),
    },
    {
      title: '平均耗时(ms)',
      dataIndex: 'avg_time',
      key: 'avg_time',
      width: 140,
      sorter: (a, b) => a.avg_time - b.avg_time,
      render: (val) => val.toFixed(3),
    },
    {
      title: '相关命令',
      dataIndex: 'commands',
      key: 'commands',
      render: (commands) => (
        <Space wrap>
          {commands?.map((cmd, idx) => (
            <Tag key={idx} color="blue">
              {cmd}
            </Tag>
          ))}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card
        title="热点Key分析"
        className="table-container"
        extra={
          <Space>
            <span>显示Top:</span>
            <InputNumber min={5} max={100} value={topN} onChange={setTopN} />
            <Button onClick={loadData} loading={loading}>
              刷新
            </Button>
          </Space>
        }
      >
        <div style={{ height: 300, marginBottom: 16 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip
                formatter={(value, name, props) => {
                  if (name === 'count') return [value, '访问次数'];
                  return [value, '总耗时(ms)'];
                }}
                labelFormatter={(label) => props.payload?.[0]?.payload?.fullName || label}
              />
              <Bar dataKey="count" fill="#f5576c" name="访问次数" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <Table
          columns={columns}
          dataSource={data}
          rowKey="key"
          loading={loading}
          pagination={{
            pageSize: 15,
            showTotal: (total) => `共 ${total} 个热点Key`,
          }}
        />
      </Card>
    </div>
  );
}

export default HotKeys;

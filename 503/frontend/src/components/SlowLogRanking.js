import React, { useState, useEffect } from 'react';
import { Table, Tag, Space, Input, Select, Button, Card, message } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { slowLogAPI } from '../api/api';

const { Search } = Input;
const { Option } = Select;

function SlowLogRanking() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filteredData, setFilteredData] = useState([]);
  const [searchText, setSearchText] = useState('');
  const [sortBy, setSortBy] = useState('duration');

  useEffect(() => {
    loadData();
  }, [sortBy]);

  useEffect(() => {
    if (searchText) {
      const filtered = data.filter(
        (item) => item.command.toLowerCase().includes(searchText.toLowerCase())
      );
      setFilteredData(filtered);
    } else {
      setFilteredData(data);
    }
  }, [searchText, data]);

  const loadData = async () => {
    try {
      setLoading(true);
      const response = await slowLogAPI.getSlowQueriesRanking(1000, 100, sortBy);
      if (response.data.success) {
        setData(response.data.data);
        setFilteredData(response.data.data);
      }
    } catch (error) {
      message.error('加载慢查询排行失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    {
      title: '排名',
      key: 'rank',
      width: 80,
      render: (_, __, index) => index + 1,
    },
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
      width: 120,
      sorter: (a, b) => a.duration_ms - b.duration_ms,
      render: (val) => (
        <Tag color={val > 100 ? 'red' : val > 50 ? 'orange' : 'blue'}>
          {val.toFixed(3)}
        </Tag>
      ),
    },
    {
      title: '命令',
      dataIndex: 'command',
      key: 'command',
      ellipsis: true,
      render: (text) => <code style={{ background: '#f5f5f5', padding: '2px 6px', borderRadius: 4 }}>{text}</code>,
    },
    {
      title: '客户端IP',
      dataIndex: 'client_ip',
      key: 'client_ip',
      width: 140,
      render: (val) => val || '-',
    },
    {
      title: '执行时间',
      dataIndex: 'datetime',
      key: 'datetime',
      width: 180,
      sorter: (a, b) => a.timestamp - b.timestamp,
    },
  ];

  return (
    <Card className="table-container" title="慢查询排行榜">
      <Space style={{ marginBottom: 16 }} wrap>
        <Search
          placeholder="搜索命令..."
          allowClear
          enterButton={<SearchOutlined />}
          size="middle"
          style={{ width: 300 }}
          onSearch={setSearchText}
          onChange={(e) => setSearchText(e.target.value)}
        />
        <Select
          value={sortBy}
          onChange={setSortBy}
          style={{ width: 150 }}
        >
          <Option value="duration">按耗时排序</Option>
          <Option value="count">按频次排序</Option>
        </Select>
        <Button onClick={loadData} loading={loading}>
          刷新
        </Button>
      </Space>

      <Table
        columns={columns}
        dataSource={filteredData}
        rowKey="id"
        loading={loading}
        pagination={{
          pageSize: 20,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条记录`,
        }}
        scroll={{ x: 800 }}
      />
    </Card>
  );
}

export default SlowLogRanking;

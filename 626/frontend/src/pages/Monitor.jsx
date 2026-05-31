import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Table, Tag, Space } from 'antd';
import { WarningOutlined, CheckCircleOutlined, CloseCircleOutlined, AlertOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { tenantApi } from '../services/api';

const Monitor = () => {
  const [tenants, setTenants] = useState([]);
  const [usageData, setUsageData] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 3000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const result = await tenantApi.list();
      const tenantList = result.data || [];
      setTenants(tenantList);

      const usageMap = {};
      for (const tenant of tenantList) {
        try {
          const usageResult = await tenantApi.getUsage(tenant.tenantId);
          usageMap[tenant.tenantId] = { ...usageResult.data, tenant };
        } catch (e) {
          console.error('Failed to load usage for', tenant.tenantId);
        }
      }
      setUsageData(usageMap);
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (rate) => {
    if (rate >= 0.95) return 'red';
    if (rate >= 0.8) return 'orange';
    if (rate >= 0.6) return 'gold';
    return 'green';
  };

  const getStatusIcon = (rate) => {
    if (rate >= 0.95) return <CloseCircleOutlined style={{ color: '#f5222d' }} />;
    if (rate >= 0.8) return <WarningOutlined style={{ color: '#faad14' }} />;
    if (rate >= 0.6) return <AlertOutlined style={{ color: '#faad14' }} />;
    return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
  };

  const getStatusLabel = (rate) => {
    if (rate >= 1) return '超限';
    if (rate >= 0.95) return '严重';
    if (rate >= 0.8) return '警告';
    if (rate >= 0.6) return '预告';
    return '正常';
  };

  const getPieChartOption = () => {
    const normalCount = Object.values(usageData).filter(u => (u.dayUsageRate || 0) < 0.6).length;
    const earlyCount = Object.values(usageData).filter(u => (u.dayUsageRate || 0) >= 0.6 && (u.dayUsageRate || 0) < 0.8).length;
    const warningCount = Object.values(usageData).filter(u => (u.dayUsageRate || 0) >= 0.8 && (u.dayUsageRate || 0) < 0.95).length;
    const criticalCount = Object.values(usageData).filter(u => (u.dayUsageRate || 0) >= 0.95).length;

    return {
      tooltip: { trigger: 'item' },
      legend: { orient: 'vertical', left: 'left' },
      series: [{
        name: '租户状态',
        type: 'pie',
        radius: '50%',
        data: [
          { value: normalCount, name: '正常', itemStyle: { color: '#52c41a' } },
          { value: earlyCount, name: '预告', itemStyle: { color: '#fadb14' } },
          { value: warningCount, name: '警告', itemStyle: { color: '#faad14' } },
          { value: criticalCount, name: '严重', itemStyle: { color: '#f5222d' } },
        ],
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)',
          },
        },
      }],
    };
  };

  const getUsageChartOption = () => {
    const sortedTenants = Object.values(usageData)
      .sort((a, b) => (b.dayUsageRate || 0) - (a.dayUsageRate || 0))
      .slice(0, 10);

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
      },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: {
        type: 'value',
        max: 1,
        axisLabel: { formatter: (value) => `${value * 100}%` },
      },
      yAxis: {
        type: 'category',
        data: sortedTenants.map(u => u.tenant?.tenantName || u.tenantId),
      },
      series: [{
        name: '日使用率',
        type: 'bar',
        data: sortedTenants.map(u => ({
          value: u.dayUsageRate || 0,
          itemStyle: {
            color: getStatusColor(u.dayUsageRate || 0),
          },
        })),
      }],
    };
  };

  const columns = [
    {
      title: '租户',
      dataIndex: 'tenantId',
      key: 'tenantId',
      render: (_, record) => record.tenant?.tenantName || record.tenantId,
    },
    {
      title: '状态',
      key: 'status',
      render: (_, record) => (
        <Space>
          {getStatusIcon(record.dayUsageRate || 0)}
          <Tag color={getStatusColor(record.dayUsageRate || 0)}>
            {getStatusLabel(record.dayUsageRate || 0)}
          </Tag>
        </Space>
      ),
    },
    {
      title: '分钟使用率',
      dataIndex: 'minuteUsageRate',
      key: 'minuteUsageRate',
      render: (rate) => (
        <Tag color={getStatusColor(rate || 0)}>
          {((rate || 0) * 100).toFixed(1)}%
        </Tag>
      ),
      sorter: (a, b) => (a.minuteUsageRate || 0) - (b.minuteUsageRate || 0),
    },
    {
      title: '小时使用率',
      dataIndex: 'hourUsageRate',
      key: 'hourUsageRate',
      render: (rate) => (
        <Tag color={getStatusColor(rate || 0)}>
          {((rate || 0) * 100).toFixed(1)}%
        </Tag>
      ),
      sorter: (a, b) => (a.hourUsageRate || 0) - (b.hourUsageRate || 0),
    },
    {
      title: '日使用率',
      dataIndex: 'dayUsageRate',
      key: 'dayUsageRate',
      render: (rate) => (
        <Tag color={getStatusColor(rate || 0)}>
          {((rate || 0) * 100).toFixed(1)}%
        </Tag>
      ),
      sorter: (a, b) => (a.dayUsageRate || 0) - (b.dayUsageRate || 0),
    },
  ];

  const normalCount = Object.values(usageData).filter(u => (u.dayUsageRate || 0) < 0.6).length;
  const earlyCount = Object.values(usageData).filter(u => (u.dayUsageRate || 0) >= 0.6 && (u.dayUsageRate || 0) < 0.8).length;
  const warningCount = Object.values(usageData).filter(u => (u.dayUsageRate || 0) >= 0.8 && (u.dayUsageRate || 0) < 0.95).length;
  const criticalCount = Object.values(usageData).filter(u => (u.dayUsageRate || 0) >= 0.95).length;

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic
              title="正常租户"
              value={normalCount}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic
              title="预告租户"
              value={earlyCount}
              valueStyle={{ color: '#fadb14' }}
              prefix={<AlertOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic
              title="警告租户"
              value={warningCount}
              valueStyle={{ color: '#faad14' }}
              prefix={<WarningOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic
              title="严重租户"
              value={criticalCount}
              valueStyle={{ color: '#f5222d' }}
              prefix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col span={8}>
          <Card title="租户状态分布" loading={loading}>
            <ReactECharts option={getPieChartOption()} style={{ height: 300 }} />
          </Card>
        </Col>
        <Col span={16}>
          <Card title="配额使用率排行 (日)" loading={loading}>
            <ReactECharts option={getUsageChartOption()} style={{ height: 300 }} />
          </Card>
        </Col>
      </Row>

      <Card title="租户使用详情" loading={loading}>
        <Table
          columns={columns}
          dataSource={Object.values(usageData)}
          rowKey="tenantId"
          pagination={{ pageSize: 10 }}
        />
      </Card>
    </Space>
  );
};

export default Monitor;

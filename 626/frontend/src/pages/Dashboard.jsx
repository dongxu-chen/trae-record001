import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Statistic, Progress, Space } from 'antd';
import { ArrowUpOutlined, WarningOutlined, CheckCircleOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { tenantApi } from '../services/api';

const Dashboard = () => {
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [usageData, setUsageData] = useState({});

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const result = await tenantApi.list();
      const tenantList = result.data || [];
      setTenants(tenantList);

      const usageMap = {};
      for (const tenant of tenantList.slice(0, 5)) {
        try {
          const usageResult = await tenantApi.getUsage(tenant.tenantId);
          usageMap[tenant.tenantId] = usageResult.data;
        } catch (e) {
          console.error('Failed to load usage for', tenant.tenantId);
        }
      }
      setUsageData(usageMap);
    } catch (error) {
      console.error('Failed to load tenants:', error);
    } finally {
      setLoading(false);
    }
  };

  const getChartOption = () => ({
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow',
      },
    },
    legend: {
      data: ['分钟限额', '小时限额', '日限额'],
    },
    xAxis: {
      type: 'category',
      data: tenants.slice(0, 5).map(t => t.tenantName || t.tenantId),
    },
    yAxis: {
      type: 'value',
      name: '已使用',
    },
    series: [
      {
        name: '分钟限额',
        type: 'bar',
        data: tenants.slice(0, 5).map(t => usageData[t.tenantId]?.minuteUsed || 0),
        itemStyle: { color: '#1890ff' },
      },
      {
        name: '小时限额',
        type: 'bar',
        data: tenants.slice(0, 5).map(t => usageData[t.tenantId]?.hourUsed || 0),
        itemStyle: { color: '#52c41a' },
      },
      {
        name: '日限额',
        type: 'bar',
        data: tenants.slice(0, 5).map(t => usageData[t.tenantId]?.dayUsed || 0),
        itemStyle: { color: '#faad14' },
      },
    ],
  });

  const warningCount = Object.values(usageData).filter(u =>
    (u.minuteUsageRate || 0) > 0.8 ||
    (u.hourUsageRate || 0) > 0.8 ||
    (u.dayUsageRate || 0) > 0.8
  ).length;

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic
              title="租户总数"
              value={tenants.length}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic
              title="活跃租户"
              value={tenants.filter(t => t.enabled).length}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
              suffix={`/ ${tenants.length}`}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic
              title="预警租户"
              value={warningCount}
              prefix={<WarningOutlined />}
              valueStyle={{ color: warningCount > 0 ? '#faad14' : '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic
              title="总API调用"
              value={Object.values(usageData).reduce((sum, u) => sum + (u.dayUsed || 0), 0)}
              prefix={<ArrowUpOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      <Card title="配额使用概览" loading={loading}>
        <Row gutter={[16, 16]}>
          {tenants.slice(0, 4).map(tenant => {
            const usage = usageData[tenant.tenantId];
            return (
              <Col span={12} key={tenant.tenantId}>
                <Card size="small" title={tenant.tenantName || tenant.tenantId}>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <div>
                      <div style={{ marginBottom: 8 }}>分钟配额 ({usage?.minuteUsed || 0}/{tenant.minuteLimit})</div>
                      <Progress
                        percent={Math.round((usage?.minuteUsageRate || 0) * 100)}
                        status={(usage?.minuteUsageRate || 0) > 0.8 ? 'exception' : 'active'}
                      />
                    </div>
                    <div>
                      <div style={{ marginBottom: 8 }}>小时配额 ({usage?.hourUsed || 0}/{tenant.hourLimit})</div>
                      <Progress
                        percent={Math.round((usage?.hourUsageRate || 0) * 100)}
                        status={(usage?.hourUsageRate || 0) > 0.8 ? 'exception' : 'active'}
                      />
                    </div>
                    <div>
                      <div style={{ marginBottom: 8 }}>日配额 ({usage?.dayUsed || 0}/{tenant.dayLimit})</div>
                      <Progress
                        percent={Math.round((usage?.dayUsageRate || 0) * 100)}
                        status={(usage?.dayUsageRate || 0) > 0.8 ? 'exception' : 'active'}
                      />
                    </div>
                  </Space>
                </Card>
              </Col>
            );
          })}
        </Row>
      </Card>

      <Card title="配额使用统计" loading={loading}>
        <ReactECharts option={getChartOption()} style={{ height: 400 }} />
      </Card>
    </Space>
  );
};

export default Dashboard;

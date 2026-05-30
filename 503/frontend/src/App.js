import React, { useState, useEffect } from 'react';
import { Layout, Tabs, message, Spin, Row, Col, Statistic, Card } from 'antd';
import {
  DashboardOutlined,
  BarChartOutlined,
  ThunderboltOutlined,
  BulbOutlined,
  MonitorOutlined,
  LineChartOutlined,
  CodeOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import Overview from './components/Overview';
import SlowLogRanking from './components/SlowLogRanking';
import CommandAnalysis from './components/CommandAnalysis';
import HotKeys from './components/HotKeys';
import LargeKeys from './components/LargeKeys';
import Optimizations from './components/Optimizations';
import RealTimeMonitor from './components/RealTimeMonitor';
import Prediction from './components/Prediction';
import AutoOptimization from './components/AutoOptimization';
import AuditLog from './components/AuditLog';
import { slowLogAPI, monitorAPI } from './api/api';

const { Header, Content } = Layout;

function App() {
  const [loading, setLoading] = useState(true);
  const [overviewData, setOverviewData] = useState(null);
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    loadOverviewData();
    loadMetrics();
    
    const interval = setInterval(loadMetrics, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadOverviewData = async () => {
    try {
      setLoading(true);
      const response = await slowLogAPI.getFullAnalysis();
      if (response.data.success) {
        setOverviewData(response.data.data);
      }
    } catch (error) {
      message.error('加载数据失败，请确保后端服务正常运行');
      console.error('Load overview data error:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadMetrics = async () => {
    try {
      const response = await monitorAPI.getMetrics();
      if (response.data.success) {
        setMetrics(response.data.data);
      }
    } catch (error) {
      console.error('Load metrics error:', error);
    }
  };

  const tabItems = [
    {
      key: 'overview',
      label: (
        <span>
          <DashboardOutlined />
          总览
        </span>
      ),
      children: <Overview data={overviewData} loading={loading} onRefresh={loadOverviewData} />,
    },
    {
      key: 'ranking',
      label: (
        <span>
          <BarChartOutlined />
          慢查询排行
        </span>
      ),
      children: <SlowLogRanking />,
    },
    {
      key: 'commands',
      label: (
        <span>
          <ThunderboltOutlined />
          命令分析
        </span>
      ),
      children: <CommandAnalysis />,
    },
    {
      key: 'hotkeys',
      label: (
        <span>
          🔥 热点Key
        </span>
      ),
      children: <HotKeys />,
    },
    {
      key: 'largekeys',
      label: (
        <span>
          📦 大Key分析
        </span>
      ),
      children: <LargeKeys />,
    },
    {
      key: 'optimizations',
      label: (
        <span>
          <BulbOutlined />
          优化建议
        </span>
      ),
      children: <Optimizations />,
    },
    {
      key: 'monitor',
      label: (
        <span>
          <MonitorOutlined />
          实时监控
        </span>
      ),
      children: <RealTimeMonitor />,
    },
    {
      key: 'prediction',
      label: (
        <span>
          <LineChartOutlined />
          慢查预测
        </span>
      ),
      children: <Prediction />,
    },
    {
      key: 'auto-optimization',
      label: (
        <span>
          <CodeOutlined />
          自动优化
        </span>
      ),
      children: <AutoOptimization />,
    },
    {
      key: 'audit-log',
      label: (
        <span>
          <FileTextOutlined />
          审计日志
        </span>
      ),
      children: <AuditLog />,
    },
  ];

  return (
    <Layout className="app-container">
      <Header className="app-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h1 className="app-title">🔍 Redis 慢查询分析工具</h1>
        {metrics && (
          <Row gutter={16} style={{ color: 'white' }}>
            <Col>
              <Statistic
                title={<span style={{ color: 'rgba(255,255,255,0.8)' }}>QPS</span>}
                value={metrics.commands_per_second}
                valueStyle={{ color: 'white', fontSize: '16px' }}
              />
            </Col>
            <Col>
              <Statistic
                title={<span style={{ color: 'rgba(255,255,255,0.8)' }}>连接数</span>}
                value={metrics.connected_clients}
                valueStyle={{ color: 'white', fontSize: '16px' }}
              />
            </Col>
            <Col>
              <Statistic
                title={<span style={{ color: 'rgba(255,255,255,0.8)' }}>命中率</span>}
                value={metrics.hit_rate}
                suffix="%"
                valueStyle={{ color: 'white', fontSize: '16px' }}
              />
            </Col>
            <Col>
              <Statistic
                title={<span style={{ color: 'rgba(255,255,255,0.8)' }}>内存</span>}
                value={metrics.used_memory_human}
                valueStyle={{ color: 'white', fontSize: '16px' }}
              />
            </Col>
          </Row>
        )}
      </Header>
      <Content className="app-content">
        {loading && !overviewData ? (
          <div style={{ textAlign: 'center', padding: '100px' }}>
            <Spin size="large" />
            <p style={{ marginTop: 16 }}>正在加载数据...</p>
          </div>
        ) : (
          <Tabs items={tabItems} defaultActiveKey="overview" size="large" />
        )}
      </Content>
    </Layout>
  );
}

export default App;

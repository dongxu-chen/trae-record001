import React, { useState, useEffect } from 'react';
import { Layout, Menu, Breadcrumb } from 'antd';
import {
  DashboardOutlined,
  ApartmentOutlined,
  SettingOutlined,
  LineChartOutlined,
  ExperimentOutlined,
  ThunderboltOutlined,
  RocketOutlined,
  SafetyCertificateOutlined,
  AimOutlined,
} from '@ant-design/icons';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Topology from './pages/Topology';
import Recommendations from './pages/Recommendations';
import Configurations from './pages/Configurations';
import Simulation from './pages/Simulation';
import RealtimeWaterLevel from './pages/RealtimeWaterLevel';
import AutoDeploy from './pages/AutoDeploy';
import EffectivenessEval from './pages/EffectivenessEval';
import DrillPage from './pages/DrillPage';

const { Header, Content, Sider } = Layout;

function App() {
  const location = useLocation();
  const [selectedKey, setSelectedKey] = useState('/');

  useEffect(() => {
    setSelectedKey(location.pathname);
  }, [location.pathname]);

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: <Link to="/">仪表盘</Link>,
    },
    {
      key: '/realtime',
      icon: <ThunderboltOutlined />,
      label: <Link to="/realtime">实时监控</Link>,
    },
    {
      key: '/topology',
      icon: <ApartmentOutlined />,
      label: <Link to="/topology">服务拓扑</Link>,
    },
    {
      key: '/recommendations',
      icon: <LineChartOutlined />,
      label: <Link to="/recommendations">限流推荐</Link>,
    },
    {
      key: '/auto-deploy',
      icon: <RocketOutlined />,
      label: <Link to="/auto-deploy">自动部署</Link>,
    },
    {
      key: '/evaluation',
      icon: <SafetyCertificateOutlined />,
      label: <Link to="/evaluation">效果评估</Link>,
    },
    {
      key: '/drill',
      icon: <AimOutlined />,
      label: <Link to="/drill">限流演练</Link>,
    },
    {
      key: '/configurations',
      icon: <SettingOutlined />,
      label: <Link to="/configurations">配置管理</Link>,
    },
    {
      key: '/simulation',
      icon: <ExperimentOutlined />,
      label: <Link to="/simulation">过载模拟</Link>,
    },
  ];

  const getBreadcrumb = () => {
    const pathMap = {
      '/': '仪表盘',
      '/realtime': '实时监控',
      '/topology': '服务拓扑',
      '/recommendations': '限流推荐',
      '/auto-deploy': '自动部署',
      '/evaluation': '效果评估',
      '/drill': '限流演练',
      '/configurations': '配置管理',
      '/simulation': '过载模拟',
    };
    return pathMap[location.pathname] || '首页';
  };

  return (
    <Layout className="app-layout">
      <Header className="app-header">
        <div className="app-logo">🔒 限流配置推荐工具</div>
        <div style={{ color: '#666' }}>自动部署 · 效果评估 · 限流演练</div>
      </Header>
      <Layout>
        <Sider width={200} style={{ background: '#fff' }}>
          <Menu
            mode="inline"
            selectedKeys={[selectedKey]}
            style={{ height: '100%', borderRight: 0 }}
            items={menuItems}
          />
        </Sider>
        <Layout style={{ padding: '0 24px 24px' }}>
          <Breadcrumb style={{ margin: '16px 0' }}>
            <Breadcrumb.Item>首页</Breadcrumb.Item>
            <Breadcrumb.Item>{getBreadcrumb()}</Breadcrumb.Item>
          </Breadcrumb>
          <Content
            className="app-content"
            style={{
              padding: 24,
              margin: 0,
              minHeight: 280,
              background: '#fff',
              borderRadius: 8,
            }}
          >
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/realtime" element={<RealtimeWaterLevel />} />
              <Route path="/topology" element={<Topology />} />
              <Route path="/recommendations" element={<Recommendations />} />
              <Route path="/auto-deploy" element={<AutoDeploy />} />
              <Route path="/evaluation" element={<EffectivenessEval />} />
              <Route path="/drill" element={<DrillPage />} />
              <Route path="/configurations" element={<Configurations />} />
              <Route path="/simulation" element={<Simulation />} />
            </Routes>
          </Content>
        </Layout>
      </Layout>
    </Layout>
  );
}

export default App;

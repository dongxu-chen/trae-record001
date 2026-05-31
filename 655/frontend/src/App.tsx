import React, { useState } from 'react';
import {
  DashboardOutlined,
  BranchesOutlined,
  BarChartOutlined,
  SettingOutlined,
  CloudServerOutlined,
  SwapOutlined,
  SafetyOutlined,
  CalculatorOutlined,
} from '@ant-design/icons';
import { Layout, Menu, theme } from 'antd';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';

import Dashboard from './pages/Dashboard';
import Topology from './pages/Topology';
import RoutingRules from './pages/RoutingRules';
import TrafficAnalysis from './pages/TrafficAnalysis';
import IstioResources from './pages/IstioResources';
import BlueGreenDeployment from './pages/BlueGreenDeployment';
import AccessControl from './pages/AccessControl';
import CostEstimator from './pages/CostEstimator';

const { Header, Content, Sider } = Layout;

const App: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();

  const menuItems = [
    {
      key: '1',
      icon: <DashboardOutlined />,
      label: <Link to="/">仪表盘</Link>,
    },
    {
      key: '2',
      icon: <CloudServerOutlined />,
      label: <Link to="/topology">流量拓扑</Link>,
    },
    {
      key: '3',
      icon: <BranchesOutlined />,
      label: <Link to="/routing">路由规则</Link>,
    },
    {
      key: '4',
      icon: <SwapOutlined />,
      label: <Link to="/bluegreen">蓝绿部署</Link>,
    },
    {
      key: '5',
      icon: <SafetyOutlined />,
      label: <Link to="/access-control">访问控制</Link>,
    },
    {
      key: '6',
      icon: <CalculatorOutlined />,
      label: <Link to="/cost">费用估算</Link>,
    },
    {
      key: '7',
      icon: <BarChartOutlined />,
      label: <Link to="/analysis">流量分析</Link>,
    },
    {
      key: '8',
      icon: <SettingOutlined />,
      label: <Link to="/istio">Istio资源</Link>,
    },
  ];

  return (
    <Router>
      <Layout style={{ minHeight: '100vh' }}>
        <Sider
          collapsible
          collapsed={collapsed}
          onCollapse={(value) => setCollapsed(value)}
        >
          <div
            style={{
              height: 64,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              fontSize: collapsed ? 14 : 18,
              fontWeight: 'bold',
            }}
          >
            {collapsed ? 'SMG' : '服务网格治理平台'}
          </div>
          <Menu
            theme="dark"
            defaultSelectedKeys={['1']}
            mode="inline"
            items={menuItems}
          />
        </Sider>
        <Layout>
          <Header
            style={{
              padding: '0 24px',
              background: colorBgContainer,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <h2 style={{ margin: 0 }}>服务网格流量治理平台</h2>
          </Header>
          <Content style={{ margin: '24px' }}>
            <div
              style={{
                padding: 24,
                minHeight: 360,
                background: colorBgContainer,
                borderRadius: borderRadiusLG,
              }}
            >
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/topology" element={<Topology />} />
                <Route path="/routing" element={<RoutingRules />} />
                <Route path="/bluegreen" element={<BlueGreenDeployment />} />
                <Route path="/access-control" element={<AccessControl />} />
                <Route path="/cost" element={<CostEstimator />} />
                <Route path="/analysis" element={<TrafficAnalysis />} />
                <Route path="/istio" element={<IstioResources />} />
              </Routes>
            </div>
          </Content>
        </Layout>
      </Layout>
    </Router>
  );
};

export default App;

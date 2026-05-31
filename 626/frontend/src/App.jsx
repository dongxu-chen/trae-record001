import React, { useState } from 'react';
import { Layout, Menu } from 'antd';
import {
  DashboardOutlined,
  TeamOutlined,
  SettingOutlined,
  BarChartOutlined,
  ShopOutlined,
  UserOutlined,
  NodeIndexOutlined,
} from '@ant-design/icons';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import TenantManagement from './pages/TenantManagement';
import QuotaConfig from './pages/QuotaConfig';
import Monitor from './pages/Monitor';
import QuotaPoolManagement from './pages/QuotaPoolManagement';
import QuotaMarket from './pages/QuotaMarket';
import QuotaProfile from './pages/QuotaProfile';

const { Header, Content, Sider } = Layout;

function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: '仪表盘',
      onClick: () => navigate('/'),
    },
    {
      key: '/tenants',
      icon: <TeamOutlined />,
      label: '租户管理',
      onClick: () => navigate('/tenants'),
    },
    {
      key: '/quota-config',
      icon: <SettingOutlined />,
      label: '配额配置',
      onClick: () => navigate('/quota-config'),
    },
    {
      key: '/pool',
      icon: <NodeIndexOutlined />,
      label: '配额共享池',
      onClick: () => navigate('/pool'),
    },
    {
      key: '/market',
      icon: <ShopOutlined />,
      label: '配额市场',
      onClick: () => navigate('/market'),
    },
    {
      key: '/profile',
      icon: <UserOutlined />,
      label: '配额画像',
      onClick: () => navigate('/profile'),
    },
    {
      key: '/monitor',
      icon: <BarChartOutlined />,
      label: '监控中心',
      onClick: () => navigate('/monitor'),
    },
  ];

  return (
    <Layout className="layout">
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed}>
        <div style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontSize: collapsed ? 12 : 18, fontWeight: 'bold' }}>
          {collapsed ? '配额' : 'API配额管理'}
        </div>
        <Menu
          theme="dark"
          selectedKeys={[location.pathname]}
          mode="inline"
          items={menuItems}
        />
      </Sider>
      <Layout>
        <Header className="site-layout-background" style={{ padding: '0 24px', fontSize: 18, fontWeight: 'bold' }}>
          API配额管理平台
        </Header>
        <Content style={{ margin: '24px', minHeight: 280 }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/tenants" element={<TenantManagement />} />
            <Route path="/quota-config" element={<QuotaConfig />} />
            <Route path="/pool" element={<QuotaPoolManagement />} />
            <Route path="/market" element={<QuotaMarket />} />
            <Route path="/profile" element={<QuotaProfile />} />
            <Route path="/monitor" element={<Monitor />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
}

export default App;

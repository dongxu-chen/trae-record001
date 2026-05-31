import React, { useState } from 'react';
import { Layout, Menu, theme } from 'antd';
import {
  DashboardOutlined,
  UnorderedListOutlined,
  BellOutlined,
  InboxOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';

const { Header, Content, Sider } = Layout;

interface MenuItem {
  key: string;
  icon: React.ReactNode;
  label: string;
  path: string;
}

const menuItems: MenuItem[] = [
  {
    key: '/dashboard',
    icon: <DashboardOutlined />,
    label: '概览',
    path: '/dashboard',
  },
  {
    key: '/analytics',
    icon: <BarChartOutlined />,
    label: '智能分析',
    path: '/analytics',
  },
  {
    key: '/dead-letters',
    icon: <UnorderedListOutlined />,
    label: '死信列表',
    path: '/dead-letters',
  },
  {
    key: '/alert-rules',
    icon: <BellOutlined />,
    label: '告警规则',
    path: '/alert-rules',
  },
  {
    key: '/archives',
    icon: <InboxOutlined />,
    label: '归档管理',
    path: '/archives',
  },
];

const MainLayout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const {
    token: { colorBgContainer },
  } = theme.useToken();

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key);
  };

  const selectedKey = menuItems.find(
    (item) => location.pathname.startsWith(item.key)
  )?.key || '/dashboard';

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={(value) => setCollapsed(value)}
        theme="dark"
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
            background: 'rgba(255, 255, 255, 0.1)',
          }}
        >
          {collapsed ? 'DLQ' : '死信队列管理平台'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={handleMenuClick}
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
            borderBottom: '1px solid #f0f0f0',
          }}
        >
          <div style={{ fontSize: 16, fontWeight: 500 }}>
            {menuItems.find((item) => item.key === selectedKey)?.label}
          </div>
          <div style={{ color: '#666' }}>欢迎使用死信队列管理平台</div>
        </Header>
        <Content
          style={{
            margin: '24px',
            padding: '24px',
            background: colorBgContainer,
            borderRadius: 8,
            minHeight: 'calc(100vh - 64px - 48px)',
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default MainLayout;

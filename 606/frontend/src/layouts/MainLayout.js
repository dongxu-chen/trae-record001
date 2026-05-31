import React, { useState } from 'react';
import { Layout, Menu } from 'antd';
import {
  DashboardOutlined,
  SafetyCertificateOutlined,
  ThunderboltOutlined,
  FileTextOutlined,
  BulbOutlined,
  ClockCircleOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';

const { Header, Sider, Content } = Layout;

const menuItems = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: '仪表盘' },
  { key: '/strategy', icon: <SafetyCertificateOutlined />, label: '策略配置' },
  { key: '/drill', icon: <ThunderboltOutlined />, label: '演练管理' },
  { key: '/report', icon: <FileTextOutlined />, label: '演练报告' },
  {
    type: 'group',
    label: '智能分析',
    children: [
      { key: '/recommendation', icon: <BulbOutlined />, label: '策略推荐' },
      { key: '/scheduled', icon: <ClockCircleOutlined />, label: '常态化演练' },
      { key: '/capacity', icon: <BarChartOutlined />, label: '容量预测' },
    ]
  },
];

const MainLayout = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="dark"
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
        }}
      >
        <div style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#fff',
          fontSize: collapsed ? 16 : 18,
          fontWeight: 'bold',
          borderBottom: '1px solid rgba(255,255,255,0.1)',
        }}>
          {collapsed ? '限流' : '限流降级演练'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout style={{ marginLeft: collapsed ? 80 : 200, transition: 'all 0.2s' }}>
        <Header style={{
          padding: '0 24px',
          background: '#fff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
          position: 'sticky',
          top: 0,
          zIndex: 1,
        }}>
          <h2 style={{ margin: 0, fontSize: 18, color: '#333' }}>
            限流降级演练平台
          </h2>
          <span style={{ color: '#999', fontSize: 13 }}>
            Rate Limit Drill Platform v1.0
          </span>
        </Header>
        <Content style={{ margin: 24, minHeight: 280 }}>
          {children}
        </Content>
      </Layout>
    </Layout>
  );
};

export default MainLayout;

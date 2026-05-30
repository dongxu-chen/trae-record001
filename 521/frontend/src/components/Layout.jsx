import React, { useState } from 'react';
import { Layout as AntLayout, Menu, theme } from 'antd';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  ProjectOutlined,
  RocketOutlined,
  ClockCircleOutlined,
  ApiOutlined
} from '@ant-design/icons';

const { Header, Sider, Content } = AntLayout;

const Layout = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();

  const menuItems = [
    {
      key: '/workflows',
      icon: <ProjectOutlined />,
      label: '工作流管理',
    },
    {
      key: '/executions',
      icon: <RocketOutlined />,
      label: '执行监控',
    },
    {
      key: '/triggers',
      icon: <ClockCircleOutlined />,
      label: '触发策略',
    }
  ];

  const getSelectedKey = () => {
    const path = location.pathname;
    if (path.startsWith('/workflows')) return '/workflows';
    if (path.startsWith('/executions')) return '/executions';
    if (path.startsWith('/triggers')) return '/triggers';
    return '/workflows';
  };

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed}>
        <div style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white',
          fontSize: collapsed ? 14 : 18,
          fontWeight: 'bold',
          background: 'rgba(24, 144, 255, 0.3)'
        }}>
          {collapsed ? 'TF' : 'TaskFlow'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[getSelectedKey()]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <AntLayout>
        <Header style={{
          padding: '0 24px',
          background: colorBgContainer,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid #f0f0f0'
        }}>
          <h2 style={{ margin: 0, fontSize: 18 }}>分布式任务流平台</h2>
          <ApiOutlined style={{ fontSize: 20, color: '#1890ff' }} />
        </Header>
        <Content style={{
          margin: '24px',
          padding: 24,
          minHeight: 'calc(100vh - 112px)',
          background: colorBgContainer,
          borderRadius: borderRadiusLG,
        }}>
          {children}
        </Content>
      </AntLayout>
    </AntLayout>
  );
};

export default Layout;

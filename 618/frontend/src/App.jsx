import React from 'react'
import { Layout, Menu, theme } from 'antd'
import { Routes, Route, Link, useLocation } from 'react-router-dom'
import {
  HistoryOutlined,
  DiffOutlined,
  SettingOutlined,
  SafetyOutlined,
  BellOutlined,
  DashboardOutlined,
  AppstoreOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import AuditLogList from './pages/AuditLogList'
import AuditLogDetail from './pages/AuditLogDetail'
import NamespaceConfig from './pages/NamespaceConfig'
import ComplianceRules from './pages/ComplianceRules'
import ListenerConfig from './pages/ListenerConfig'
import Dashboard from './pages/Dashboard'
import ServiceRegistry from './pages/ServiceRegistry'
import RollbackPolicy from './pages/RollbackPolicy'

const { Header, Content, Sider } = Layout

function App() {
  const {
    token: { colorBgContainer },
  } = theme.useToken()

  const location = useLocation()

  const menuItems = [
    {
      key: '/dashboard',
      icon: <DashboardOutlined />,
      label: <Link to="/dashboard">审计大盘</Link>,
    },
    {
      key: '/',
      icon: <HistoryOutlined />,
      label: <Link to="/">变更历史</Link>,
    },
    {
      key: '/services',
      icon: <AppstoreOutlined />,
      label: <Link to="/services">服务注册</Link>,
    },
    {
      key: '/rollback-policy',
      icon: <ThunderboltOutlined />,
      label: <Link to="/rollback-policy">回滚策略</Link>,
    },
    {
      key: '/namespaces',
      icon: <SettingOutlined />,
      label: <Link to="/namespaces">命名空间配置</Link>,
    },
    {
      key: '/compliance',
      icon: <SafetyOutlined />,
      label: <Link to="/compliance">合规规则</Link>,
    },
    {
      key: '/listener',
      icon: <BellOutlined />,
      label: <Link to="/listener">监听配置</Link>,
    },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          background: '#001529',
          padding: '0 24px',
        }}
      >
        <div style={{ color: 'white', fontSize: '20px', fontWeight: 'bold' }}>
          <DiffOutlined style={{ marginRight: '12px' }} />
          Nacos 配置变更审计工具
        </div>
      </Header>
      <Layout>
        <Sider width={200} style={{ background: colorBgContainer }}>
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
            style={{ height: '100%', borderRight: 0 }}
            items={menuItems}
          />
        </Sider>
        <Layout style={{ padding: '24px' }}>
          <Content
            style={{
              padding: 24,
              margin: 0,
              minHeight: 280,
              background: colorBgContainer,
              borderRadius: '8px',
            }}
          >
            <Routes>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/" element={<AuditLogList />} />
              <Route path="/logs/:id" element={<AuditLogDetail />} />
              <Route path="/services" element={<ServiceRegistry />} />
              <Route path="/rollback-policy" element={<RollbackPolicy />} />
              <Route path="/namespaces" element={<NamespaceConfig />} />
              <Route path="/compliance" element={<ComplianceRules />} />
              <Route path="/listener" element={<ListenerConfig />} />
            </Routes>
          </Content>
        </Layout>
      </Layout>
    </Layout>
  )
}

export default App

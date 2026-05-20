import React, { useState } from 'react'
import { Routes, Route, Link, useLocation } from 'react-router-dom'
import { Layout, Menu, Button, theme } from 'antd'
import {
  AlertOutlined,
  AppstoreOutlined,
  PlayCircleOutlined,
  DatabaseOutlined,
  ThunderboltOutlined,
  ImportOutlined,
  ExportOutlined,
} from '@ant-design/icons'

import RulesPage from './pages/RulesPage'
import GroupsPage from './pages/GroupsPage'
import SimulatePage from './pages/SimulatePage'
import PrometheusPage from './pages/PrometheusPage'
import ImportExportPage from './pages/ImportExportPage'

const { Header, Sider, Content } = Layout

function App() {
  const [collapsed, setCollapsed] = useState(false)
  const location = useLocation()
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken()

  const menuItems = [
    {
      key: '/',
      icon: <AlertOutlined />,
      label: <Link to="/">告警规则</Link>,
    },
    {
      key: '/groups',
      icon: <AppstoreOutlined />,
      label: <Link to="/groups">规则分组</Link>,
    },
    {
      key: '/templates',
      icon: <ShopOutlined />,
      label: <Link to="/templates">模板市场</Link>,
    },
    {
      key: '/simulate',
      icon: <PlayCircleOutlined />,
      label: <Link to="/simulate">模拟测试</Link>,
    },
    {
      key: '/performance',
      icon: <RocketOutlined />,
      label: <Link to="/performance">性能分析</Link>,
    },
    {
      key: '/dependencies',
      icon: <LinkOutlined />,
      label: <Link to="/dependencies">依赖分析</Link>,
    },
    {
      key: '/prometheus',
      icon: <DatabaseOutlined />,
      label: <Link to="/prometheus">Prometheus</Link>,
    },
    {
      key: '/import-export',
      icon: <ImportOutlined />,
      label: <Link to="/import-export">导入导出</Link>,
    },
  ]

  return (
    <Layout className="main-layout">
      <Sider trigger={null} collapsible collapsed={collapsed}>
        <div
          style={{
            height: 64,
            margin: 16,
            background: 'rgba(255, 255, 255, 0.2)',
            borderRadius: borderRadiusLG,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            fontSize: collapsed ? 16 : 18,
            fontWeight: 'bold',
          }}
        >
          <ThunderboltOutlined />
          {!collapsed && <span style={{ marginLeft: 8 }}>Alert Manager</span>}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
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
          <Button
            type="text"
            icon={collapsed ? <span>»</span> : <span>«</span>}
            onClick={() => setCollapsed(!collapsed)}
            style={{ fontSize: '16px', width: 64, height: 64 }}
          />
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <span style={{ color: '#666' }}>Prometheus 告警规则管理系统</span>
          </div>
        </Header>
        <Content
          className="content"
          style={{
            background: colorBgContainer,
            borderRadius: borderRadiusLG,
          }}
        >
          <Routes>
            <Route path="/" element={<RulesPage />} />
            <Route path="/groups" element={<GroupsPage />} />
            <Route path="/simulate" element={<SimulatePage />} />
            <Route path="/prometheus" element={<PrometheusPage />} />
            <Route path="/import-export" element={<ImportExportPage />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  )
}

export default App

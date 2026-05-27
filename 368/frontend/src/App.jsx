import React, { useState } from 'react'
import { Layout, Menu, theme } from 'antd'
import {
  DashboardOutlined,
  GlobalOutlined,
  SafetyCertificateOutlined,
  AlertOutlined,
  FileTextOutlined,
  ShareAltOutlined,
  SettingOutlined,
  DnsOutlined,
} from '@ant-design/icons'
import Dashboard from './components/Dashboard.jsx'
import DomainList from './components/DomainList.jsx'
import CertList from './components/CertList.jsx'
import AlertLogs from './components/AlertLogs.jsx'
import Report from './components/Report.jsx'
import SubdomainDiscovery from './components/SubdomainDiscovery.jsx'
import RuleLibrary from './components/RuleLibrary.jsx'
import ScanSettings from './components/ScanSettings.jsx'

const { Header, Content, Sider } = Layout

function App() {
  const [collapsed, setCollapsed] = useState(false)
  const [selectedKey, setSelectedKey] = useState('dashboard')
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken()

  const menuItems = [
    { key: 'dashboard', icon: <DashboardOutlined />, label: '仪表盘' },
    { key: 'domains', icon: <GlobalOutlined />, label: '域名管理' },
    { key: 'subdomains', icon: <ShareAltOutlined />, label: '子域名发现' },
    { key: 'certs', icon: <SafetyCertificateOutlined />, label: '证书列表' },
    { key: 'alerts', icon: <AlertOutlined />, label: '告警记录' },
    { key: 'report', icon: <FileTextOutlined />, label: '报告中心' },
    { key: 'rules', icon: <SettingOutlined />, label: '规则库管理' },
    { key: 'settings', icon: <DnsOutlined />, label: '扫描设置' },
  ]

  const renderContent = () => {
    switch (selectedKey) {
      case 'dashboard':
        return <Dashboard />
      case 'domains':
        return <DomainList />
      case 'subdomains':
        return <SubdomainDiscovery />
      case 'certs':
        return <CertList />
      case 'alerts':
        return <AlertLogs />
      case 'report':
        return <Report />
      case 'rules':
        return <RuleLibrary />
      case 'settings':
        return <ScanSettings />
      default:
        return <Dashboard />
    }
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider collapsible collapsed={collapsed} onCollapse={(value) => setCollapsed(value)}>
        <div style={{
          height: 32,
          margin: 16,
          background: 'rgba(255, 255, 255, 0.2)',
          borderRadius: 6,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#fff',
          fontWeight: 600,
          fontSize: collapsed ? 14 : 16,
        }}>
          SSL监控
        </div>
        <Menu
          theme="dark"
          selectedKeys={[selectedKey]}
          mode="inline"
          items={menuItems}
          onClick={({ key }) => setSelectedKey(key)}
        />
      </Sider>
      <Layout>
        <Header style={{ padding: 0, background: colorBgContainer }}>
          <div className="app-header">
            <h1>SSL证书过期监控工具</h1>
          </div>
        </Header>
        <Content style={{ margin: '16px' }}>
          <div
            style={{
              padding: 24,
              minHeight: 360,
              background: colorBgContainer,
              borderRadius: borderRadiusLG,
            }}
          >
            {renderContent()}
          </div>
        </Content>
      </Layout>
    </Layout>
  )
}

export default App

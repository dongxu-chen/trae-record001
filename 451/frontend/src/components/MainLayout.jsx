import { useState } from 'react'
import { Layout, Menu } from 'antd'
import {
  DashboardOutlined,
  SafetyOutlined,
  AppstoreOutlined,
  ThunderboltOutlined,
  BarChartOutlined,
  WarningOutlined,
  ExperimentOutlined,
  LineChartOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'

const { Header, Sider, Content: AntContent } = Layout

const menuItems = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: '控制台' },
  { key: '/rules', icon: <SafetyOutlined />, label: '规则管理' },
  { key: '/rules/visual', icon: <AppstoreOutlined />, label: '可视化编排' },
  { key: '/simulate', icon: <ThunderboltOutlined />, label: '模拟测试' },
  { key: '/analysis', icon: <BarChartOutlined />, label: '命中率分析' },
  { key: '/conflicts', icon: <WarningOutlined />, label: '冲突检测' },
  { key: '/abtest', icon: <ExperimentOutlined />, label: 'A/B 测试' },
  { key: '/evaluation', icon: <LineChartOutlined />, label: '效果评估' },
]

export default function MainLayout({ children }) {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  const selectedKey = menuItems.find(item => location.pathname.startsWith(item.key))?.key || '/dashboard'

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
          {collapsed ? '风控' : '🛡️ 风控引擎'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
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
          zIndex: 10,
        }}>
          <span style={{ fontSize: 16, fontWeight: 500 }}>
            实时风控规则引擎
          </span>
          <span style={{ color: '#999', fontSize: 13 }}>
            Rule Engine v1.0
          </span>
        </Header>
        <AntContent style={{ margin: 16, padding: 0, minHeight: 280 }}>
          {children}
        </AntContent>
      </Layout>
    </Layout>
  )
}

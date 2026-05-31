import { useState } from 'react'
import { Layout, Menu, theme } from 'antd'
import {
  DashboardOutlined,
  AlertOutlined,
  BarChartOutlined,
  TrendingUpOutlined,
  BulbOutlined,
  HeartOutlined,
  ClockCircleOutlined,
  FireOutlined,
} from '@ant-design/icons'
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import PathStats from './pages/PathStats'
import Trends from './pages/Trends'
import Alerts from './pages/Alerts'
import Recommendations from './pages/Recommendations'
import Health from './pages/Health'
import TTLManager from './pages/TTLManager'
import Hotness from './pages/Hotness'

const { Header, Content, Sider } = Layout

function App() {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken()

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: '总览',
    },
    {
      key: '/health',
      icon: <HeartOutlined />,
      label: '健康评分',
    },
    {
      key: '/paths',
      icon: <BarChartOutlined />,
      label: '路径统计',
    },
    {
      key: '/trends',
      icon: <TrendingUpOutlined />,
      label: '趋势预测',
    },
    {
      key: '/ttl',
      icon: <ClockCircleOutlined />,
      label: 'TTL管理',
    },
    {
      key: '/hotness',
      icon: <FireOutlined />,
      label: '热度分析',
    },
    {
      key: '/alerts',
      icon: <AlertOutlined />,
      label: '预警中心',
    },
    {
      key: '/recommendations',
      icon: <BulbOutlined />,
      label: '优化建议',
    },
  ]

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key)
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        style={{ background: '#001529' }}
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
          {collapsed ? 'ZK' : 'ZooKeeper 巡检'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
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
          }}
        >
          <h2 style={{ margin: 0 }}>ZooKeeper 节点数据量巡检工具</h2>
        </Header>
        <Content
          style={{
            margin: '24px 16px',
            padding: 24,
            minHeight: 280,
            background: colorBgContainer,
            borderRadius: borderRadiusLG,
          }}
        >
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/health" element={<Health />} />
            <Route path="/paths" element={<PathStats />} />
            <Route path="/trends" element={<Trends />} />
            <Route path="/ttl" element={<TTLManager />} />
            <Route path="/hotness" element={<Hotness />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/recommendations" element={<Recommendations />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  )
}

export default App

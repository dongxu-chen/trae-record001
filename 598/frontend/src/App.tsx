import React, { useState, useEffect } from 'react'
import { Layout, Menu, Button, Badge } from 'antd'
import {
  DatabaseOutlined,
  TableOutlined,
  PartitionOutlined,
  FileTextOutlined,
  ThunderboltOutlined,
  DisconnectOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import { Routes, Route, Link, useNavigate, useLocation } from 'react-router-dom'
import { connectionApi } from './services/api'
import ConnectionPage from './pages/ConnectionPage'
import TablesPage from './pages/TablesPage'
import TableDetailPage from './pages/TableDetailPage'
import RecommendationPage from './pages/RecommendationPage'
import QueryRewritePage from './pages/QueryRewritePage'
import AdvancedPartitionPage from './pages/AdvancedPartitionPage'
import type { DBConfig } from './types'

const { Header, Sider, Content } = Layout

const App: React.FC = () => {
  const [connected, setConnected] = useState(false)
  const [connectionConfig, setConnectionConfig] = useState<DBConfig | null>(null)
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    checkConnectionStatus()
  }, [])

  const checkConnectionStatus = async () => {
    try {
      const response = await connectionApi.getStatus()
      setConnected(response.data?.connected || false)
    } catch (error) {
      setConnected(false)
    }
  }

  const handleConnect = async (config: DBConfig) => {
    try {
      await connectionApi.connect(config)
      setConnected(true)
      setConnectionConfig(config)
      navigate('/tables')
    } catch (error: any) {
      throw error
    }
  }

  const handleDisconnect = async () => {
    try {
      await connectionApi.disconnect()
      setConnected(false)
      setConnectionConfig(null)
      navigate('/connection')
    } catch (error) {
      console.error('Disconnect error:', error)
    }
  }

  const menuItems = [
    {
      key: '/connection',
      icon: <DatabaseOutlined />,
      label: '连接配置',
    },
    {
      key: '/tables',
      icon: <TableOutlined />,
      label: '表列表',
      disabled: !connected,
    },
    {
      key: '/recommendations',
      icon: <PartitionOutlined />,
      label: '分区推荐',
      disabled: !connected,
    },
    {
      key: '/advanced',
      icon: <SettingOutlined />,
      label: '分区管理',
      disabled: !connected,
    },
    {
      key: '/query-rewrite',
      icon: <ThunderboltOutlined />,
      label: '查询优化',
      disabled: !connected,
    },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: '#001529',
          padding: '0 24px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <DatabaseOutlined style={{ fontSize: 24, color: '#fff' }} />
          <h1 style={{ color: '#fff', margin: 0, fontSize: 20, fontWeight: 600 }}>
            MySQL 自动分区工具
          </h1>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          {connected && connectionConfig && (
            <Badge status="processing" text={`${connectionConfig.user}@${connectionConfig.host}:${connectionConfig.port}/${connectionConfig.database}`} />
          )}
          {connected && (
            <Button
              type="primary"
              danger
              icon={<DisconnectOutlined />}
              onClick={handleDisconnect}
            >
              断开连接
            </Button>
          )}
        </div>
      </Header>
      <Layout>
        <Sider
          width={220}
          theme="light"
          collapsible
          collapsed={collapsed}
          onCollapse={setCollapsed}
        >
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
            style={{ height: '100%', borderRight: 0 }}
            items={menuItems.map((item) => ({
              ...item,
              label: item.disabled ? item.label : <Link to={item.key}>{item.label}</Link>,
            }))}
          />
        </Sider>
        <Layout style={{ padding: '0' }}>
          <Content
            style={{
              background: '#f0f2f5',
              minHeight: 'calc(100vh - 64px)',
            }}
          >
            <Routes>
              <Route
                path="/"
                element={
                  <ConnectionPage
                    onConnect={handleConnect}
                    connected={connected}
                  />
                }
              />
              <Route
                path="/connection"
                element={
                  <ConnectionPage
                    onConnect={handleConnect}
                    connected={connected}
                  />
                }
              />
              <Route
                path="/tables"
                element={<TablesPage />}
              />
              <Route
                path="/tables/:tableName"
                element={<TableDetailPage />}
              />
              <Route
                path="/recommendations"
                element={<RecommendationPage />}
              />
              <Route
                path="/query-rewrite"
                element={<QueryRewritePage />}
              />
              <Route
                path="/advanced"
                element={<AdvancedPartitionPage />}
              />
            </Routes>
          </Content>
        </Layout>
      </Layout>
    </Layout>
  )
}

export default App

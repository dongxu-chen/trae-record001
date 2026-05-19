import { Routes, Route } from 'react-router-dom'
import { Layout, Menu, theme } from 'antd'
import {
  ProjectOutlined, DatabaseOutlined, BarChartOutlined, SettingOutlined } from '@ant-design/icons'
import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import PipelineList from './pages/PipelineList'
import PipelineDesigner from './pages/PipelineDesigner'
import ExecutionMonitor from './pages/ExecutionMonitor'
import './App.css'

const { Header, Sider, Content } = Layout

function App() {
  const [collapsed, setCollapsed] = useState(false)
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken()
  const location = useLocation()

  const menuItems = [
    {
      key: '/pipelines',
      icon: <ProjectOutlined />,
      label: <Link to="/pipelines">管道管理</Link>,
    },
    {
      key: '/designer',
      icon: <DatabaseOutlined />,
      label: <Link to="/designer">可视化设计</Link>,
    },
    {
      key: '/monitor',
      icon: <BarChartOutlined />,
      label: <Link to="/monitor">执行监控</Link>,
    },
  ]

  return (
    <Layout style={{ height: '100vh' }}>
      <Sider collapsible collapsed={collapsed} onCollapse={(value) => setCollapsed(value)}>
        <div style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white',
          fontSize: collapsed ? 16 : 20,
          fontWeight: 'bold'
        }}>
          {collapsed ? 'ETL' : '低代码ETL'}
        </div>
        <Menu
          theme="dark"
          selectedKeys={[location.pathname]}
          mode="inline"
          items={menuItems}
        />
      </Sider>
      <Layout>
        <Header style={{
          padding: '0 24px',
          background: colorBgContainer,
          display: 'flex',
          alignItems: 'center',
          borderBottom: '1px solid #f0f0f0'
        }}>
          <h2 style={{ margin: 0 }}>低代码数据ETL平台</h2>
        </Header>
        <Content style={{
          margin: '24px 16px',
          padding: 24,
          minHeight: 280,
          background: colorBgContainer,
          borderRadius: borderRadiusLG,
          overflow: 'auto'
        }}>
          <Routes>
            <Route path="/" element={<PipelineList />} />
            <Route path="/pipelines" element={<PipelineList />} />
            <Route path="/designer" element={<PipelineDesigner />} />
            <Route path="/designer/:id" element={<PipelineDesigner />} />
            <Route path="/monitor" element={<ExecutionMonitor />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  )
}

export default App

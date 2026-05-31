import React, { useState, useEffect } from 'react';
import { Layout, Menu, theme } from 'antd';
import {
  DashboardOutlined,
  TableOutlined,
  DiffOutlined,
  SettingOutlined,
  DatabaseOutlined,
  FileTextOutlined,
  ExperimentOutlined,
  LineChartOutlined
} from '@ant-design/icons';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import TaskList from './pages/TaskList';
import DiffList from './pages/DiffList';
import CreateTask from './pages/CreateTask';
import ReportPage from './pages/ReportPage';
import GrayRelease from './pages/GrayRelease';
import PredictiveCheck from './pages/PredictiveCheck';
import './index.css';

const { Header, Sider, Content } = Layout;

const menuItems = [
  {
    key: '/',
    icon: <DashboardOutlined />,
    label: '数据看板'
  },
  {
    key: '/tasks',
    icon: <TableOutlined />,
    label: '校验任务'
  },
  {
    key: '/diffs',
    icon: <DiffOutlined />,
    label: '差异列表'
  },
  {
    key: '/create',
    icon: <DatabaseOutlined />,
    label: '创建任务'
  },
  {
    key: '/report',
    icon: <FileTextOutlined />,
    label: '校验报告'
  },
  {
    key: '/gray',
    icon: <ExperimentOutlined />,
    label: '灰度发布'
  },
  {
    key: '/predictive',
    icon: <LineChartOutlined />,
    label: '预测校验'
  }
];

function App() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const {
    token: { colorBgContainer, borderRadiusLG }
  } = theme.useToken();

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
            margin: 16,
            background: 'rgba(255, 255, 255, 0.2)',
            borderRadius: 8,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontSize: collapsed ? 12 : 16,
            fontWeight: 'bold'
          }}
        >
          {collapsed ? 'DSC' : '数据同步校验'}
        </div>
        <Menu
          theme="dark"
          selectedKeys={[location.pathname]}
          mode="inline"
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            padding: '0 24px',
            background: colorBgContainer,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}
        >
          <h2 style={{ margin: 0, fontSize: 18 }}>
            {menuItems.find(m => m.key === location.pathname)?.label || '实时数据同步校验工具'}
          </h2>
          <div className="live-indicator">
            <span className="live-dot"></span>
            实时监控中
          </div>
        </Header>
        <Content
          style={{
            margin: '24px 16px',
            padding: 24,
            minHeight: 280,
            background: colorBgContainer,
            borderRadius: borderRadiusLG
          }}
        >
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/tasks" element={<TaskList />} />
            <Route path="/diffs" element={<DiffList />} />
            <Route path="/create" element={<CreateTask />} />
            <Route path="/report" element={<ReportPage />} />
            <Route path="/gray" element={<GrayRelease />} />
            <Route path="/predictive" element={<PredictiveCheck />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
}

export default App;

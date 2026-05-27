import React from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { Layout, Menu, theme } from 'antd';
import {
  DashboardOutlined,
  SearchOutlined,
  LineChartOutlined,
  BarChartOutlined,
  FileTextOutlined,
  AppstoreOutlined,
  BugOutlined,
  EditOutlined,
  ThunderboltOutlined,
  ExperimentOutlined,
  BulbOutlined,
} from '@ant-design/icons';
import Dashboard from '@/pages/Dashboard';
import SearchEvaluation from '@/pages/SearchEvaluation';
import Annotation from '@/pages/Annotation';
import ConfusionMatrixPage from '@/pages/ConfusionMatrixPage';
import ModelComparison from '@/pages/ModelComparison';
import FailureCases from '@/pages/FailureCases';
import DataManagement from '@/pages/DataManagement';
import AutoAnnotation from '@/pages/AutoAnnotation';
import ABTesting from '@/pages/ABTesting';
import FeedbackLearning from '@/pages/FeedbackLearning';

const { Header, Sider, Content } = Layout;

const App: React.FC = () => {
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();
  const location = useLocation();

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: <Link to="/">数据仪表盘</Link>,
    },
    {
      key: '/search',
      icon: <SearchOutlined />,
      label: <Link to="/search">搜索评估</Link>,
    },
    {
      key: '/annotation',
      icon: <EditOutlined />,
      label: <Link to="/annotation">人工标注</Link>,
    },
    {
      key: '/auto-annotation',
      icon: <ThunderboltOutlined />,
      label: <Link to="/auto-annotation">自动标注</Link>,
    },
    {
      key: '/confusion-matrix',
      icon: <BarChartOutlined />,
      label: <Link to="/confusion-matrix">混淆矩阵</Link>,
    },
    {
      key: '/model-comparison',
      icon: <LineChartOutlined />,
      label: <Link to="/model-comparison">模型对比</Link>,
    },
    {
      key: '/ab-testing',
      icon: <ExperimentOutlined />,
      label: <Link to="/ab-testing">A/B测试</Link>,
    },
    {
      key: '/failure-cases',
      icon: <BugOutlined />,
      label: <Link to="/failure-cases">失败案例</Link>,
    },
    {
      key: '/feedback-learning',
      icon: <BulbOutlined />,
      label: <Link to="/feedback-learning">反馈学习</Link>,
    },
    {
      key: '/data',
      icon: <AppstoreOutlined />,
      label: <Link to="/data">数据管理</Link>,
    },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header className="app-header">
        <div className="app-logo">
          <FileTextOutlined />
          召回率分析平台
        </div>
        <div style={{ color: '#666', fontSize: '14px' }}>
          Recall Analysis Platform v1.0
        </div>
      </Header>
      <Layout>
        <Sider
          width={220}
          style={{ background: colorBgContainer }}
          breakpoint="lg"
          collapsedWidth="0"
        >
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
            items={menuItems}
            style={{ height: '100%', borderRight: 0 }}
          />
        </Sider>
        <Layout style={{ padding: '24px', background: '#f0f2f5' }}>
          <Content
            style={{
              padding: 24,
              margin: 0,
              minHeight: 280,
              background: colorBgContainer,
              borderRadius: borderRadiusLG,
            }}
          >
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/search" element={<SearchEvaluation />} />
              <Route path="/annotation" element={<Annotation />} />
              <Route path="/auto-annotation" element={<AutoAnnotation />} />
              <Route path="/confusion-matrix" element={<ConfusionMatrixPage />} />
              <Route path="/model-comparison" element={<ModelComparison />} />
              <Route path="/ab-testing" element={<ABTesting />} />
              <Route path="/failure-cases" element={<FailureCases />} />
              <Route path="/feedback-learning" element={<FeedbackLearning />} />
              <Route path="/data" element={<DataManagement />} />
            </Routes>
          </Content>
        </Layout>
      </Layout>
    </Layout>
  );
};

export default App;

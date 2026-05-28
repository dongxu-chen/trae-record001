import { Routes, Route, Link } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import {
  DashboardOutlined,
  AppstoreOutlined,
  TagOutlined,
  WarningOutlined,
  ThunderboltOutlined,
  LineChartOutlined,
  FireOutlined,
  DollarOutlined,
  SettingOutlined,
  CalculatorOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import Dashboard from './pages/Dashboard';
import NamespaceCostPage from './pages/NamespaceCostPage';
import ProjectCostPage from './pages/ProjectCostPage';
import LabelCostPage from './pages/LabelCostPage';
import IdleResourcesPage from './pages/IdleResourcesPage';
import OptimizationsPage from './pages/OptimizationsPage';
import PredictionsPage from './pages/PredictionsPage';
import ContentionPage from './pages/ContentionPage';
import BudgetAlertsPage from './pages/BudgetAlertsPage';
import BudgetManagementPage from './pages/BudgetManagementPage';
import PricingSimulatorPage from './pages/PricingSimulatorPage';
import SpotRecommendationsPage from './pages/SpotRecommendationsPage';

const { Header, Sider, Content } = Layout;

function App() {
  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: <Link to="/">Dashboard</Link>,
    },
    {
      key: '/namespaces',
      icon: <AppstoreOutlined />,
      label: <Link to="/namespaces">Namespace Costs</Link>,
    },
    {
      key: '/projects',
      icon: <AppstoreOutlined />,
      label: <Link to="/projects">Project Costs</Link>,
    },
    {
      key: '/labels',
      icon: <TagOutlined />,
      label: <Link to="/labels">Label Costs</Link>,
    },
    {
      key: '/contention',
      icon: <FireOutlined />,
      label: <Link to="/contention">Resource Contention</Link>,
    },
    {
      key: '/idle',
      icon: <WarningOutlined />,
      label: <Link to="/idle">Idle Resources</Link>,
    },
    {
      key: '/optimizations',
      icon: <ThunderboltOutlined />,
      label: <Link to="/optimizations">Optimizations</Link>,
    },
    {
      key: '/predictions',
      icon: <LineChartOutlined />,
      label: <Link to="/predictions">Predictions</Link>,
    },
    {
      key: 'budget-group',
      icon: <DollarOutlined />,
      label: 'Budget Management',
      children: [
        {
          key: '/budgets/alerts',
          label: <Link to="/budgets/alerts">Budget Alerts</Link>,
        },
        {
          key: '/budgets/manage',
          label: <Link to="/budgets/manage">Manage Budgets</Link>,
        },
      ],
    },
    {
      key: 'pricing-group',
      icon: <CalculatorOutlined />,
      label: 'Pricing Tools',
      children: [
        {
          key: '/pricing/simulator',
          label: <Link to="/pricing/simulator">Price Simulator</Link>,
        },
        {
          key: '/pricing/spot',
          label: <Link to="/pricing/spot">Spot Recommendations</Link>,
        },
      ],
    },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#001529', padding: '0 24px' }}>
        <h1 style={{ color: 'white', margin: 0, lineHeight: '64px' }}>
          Kubernetes Cost Allocation
        </h1>
      </Header>
      <Layout>
        <Sider width={280} style={{ background: '#fff' }}>
          <Menu
            mode="inline"
            defaultSelectedKeys={['/']}
            items={menuItems}
            style={{ height: '100%', borderRight: 0 }}
          />
        </Sider>
        <Layout style={{ padding: '24px' }}>
          <Content
          style={{
            padding: 24,
            margin: 0,
            minHeight: 280,
            background: '#f0f2f5',
            borderRadius: '8px',
          }}
        >
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/namespaces" element={<NamespaceCostPage />} />
            <Route path="/projects" element={<ProjectCostPage />} />
            <Route path="/labels" element={<LabelCostPage />} />
            <Route path="/contention" element={<ContentionPage />} />
            <Route path="/idle" element={<IdleResourcesPage />} />
            <Route path="/optimizations" element={<OptimizationsPage />} />
            <Route path="/predictions" element={<PredictionsPage />} />
            <Route path="/budgets/alerts" element={<BudgetAlertsPage />} />
            <Route path="/budgets/manage" element={<BudgetManagementPage />} />
            <Route path="/pricing/simulator" element={<PricingSimulatorPage />} />
            <Route path="/pricing/spot" element={<SpotRecommendationsPage />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
}

export default App;

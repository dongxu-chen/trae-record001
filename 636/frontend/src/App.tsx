import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import Layout from './components/Layout';
import ConfigPage from './pages/ConfigPage';
import MonitorPage from './pages/MonitorPage';
import ReportPage from './pages/ReportPage';
import StabilityPage from './pages/StabilityPage';
import BaselinePage from './pages/BaselinePage';
import TuningPage from './pages/TuningPage';
import './index.css';

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<ConfigPage />} />
            <Route path="/monitor" element={<MonitorPage />} />
            <Route path="/report" element={<ReportPage />} />
            <Route path="/stability" element={<StabilityPage />} />
            <Route path="/baseline" element={<BaselinePage />} />
            <Route path="/tuning" element={<TuningPage />} />
          </Routes>
        </Layout>
      </Router>
    </ConfigProvider>
  );
}

export default App;

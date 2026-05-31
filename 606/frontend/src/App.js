import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import MainLayout from './layouts/MainLayout';
import Dashboard from './pages/Dashboard';
import Strategy from './pages/Strategy';
import Drill from './pages/Drill';
import Report from './pages/Report';
import Recommendation from './pages/Recommendation';
import ScheduledDrill from './pages/ScheduledDrill';
import CapacityPrediction from './pages/CapacityPrediction';

const App = () => {
  return (
    <ConfigProvider locale={zhCN} theme={{
      token: {
        colorPrimary: '#1677ff',
        borderRadius: 6,
      },
    }}>
      <Router>
        <MainLayout>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/strategy" element={<Strategy />} />
            <Route path="/drill" element={<Drill />} />
            <Route path="/report" element={<Report />} />
            <Route path="/recommendation" element={<Recommendation />} />
            <Route path="/scheduled" element={<ScheduledDrill />} />
            <Route path="/capacity" element={<CapacityPrediction />} />
          </Routes>
        </MainLayout>
      </Router>
    </ConfigProvider>
  );
};

export default App;

import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Box } from '@mui/material';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import JobAnalysis from './pages/JobAnalysis';
import Recommendation from './pages/Recommendation';
import CostEstimator from './pages/CostEstimator';
import HealthMonitor from './pages/HealthMonitor';
import JobComparison from './pages/JobComparison';
import AutoAdjust from './pages/AutoAdjust';

function App() {
  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <Navbar />
      <Box component="main" sx={{ flexGrow: 1, p: 3, ml: 24 }}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/jobs/:jobId/analysis" element={<JobAnalysis />} />
          <Route path="/jobs/:jobId/recommendation" element={<Recommendation />} />
          <Route path="/cost-estimator" element={<CostEstimator />} />
          <Route path="/jobs/:jobId/health" element={<HealthMonitor />} />
          <Route path="/jobs/comparison" element={<JobComparison />} />
          <Route path="/jobs/:jobId/auto-adjust" element={<AutoAdjust />} />
        </Routes>
      </Box>
    </Box>
  );
}

export default App;

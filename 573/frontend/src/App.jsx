import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Scan from './pages/Scan';
import Jobs from './pages/Jobs';
import JobDetail from './pages/JobDetail';
import Reports from './pages/Reports';
import Rules from './pages/Rules';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="scan" element={<Scan />} />
        <Route path="jobs" element={<Jobs />} />
        <Route path="jobs/:jobId" element={<JobDetail />} />
        <Route path="reports" element={<Reports />} />
        <Route path="rules" element={<Rules />} />
      </Route>
    </Routes>
  );
}

export default App;

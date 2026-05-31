import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import Dashboard from './pages/Dashboard';
import DeadLetterList from './pages/DeadLetterList';
import DeadLetterDetail from './pages/DeadLetterDetail';
import AlertRule from './pages/AlertRule';
import Archive from './pages/Archive';
import Analytics from './pages/Analytics';

const App: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route element={<MainLayout />}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/dead-letters" element={<DeadLetterList />} />
        <Route path="/dead-letter/:id" element={<DeadLetterDetail />} />
        <Route path="/alert-rules" element={<AlertRule />} />
        <Route path="/archives" element={<Archive />} />
      </Route>
    </Routes>
  );
};

export default App;

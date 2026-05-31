import React, { useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import ServiceGraph from './pages/ServiceGraph';
import Policies from './pages/Policies';
import Conflicts from './pages/Conflicts';
import Simulator from './pages/Simulator';
import Compliance from './pages/Compliance';
import Deployment from './pages/Deployment';
import Effectiveness from './pages/Effectiveness';
import Visualization from './pages/Visualization';

function App() {
  const [activePage, setActivePage] = useState('dashboard');

  return (
    <div className="app-container">
      <Sidebar activePage={activePage} setActivePage={setActivePage} />
      <div className="main-content">
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard setActivePage={setActivePage} />} />
          <Route path="/service-graph" element={<ServiceGraph />} />
          <Route path="/policies" element={<Policies />} />
          <Route path="/conflicts" element={<Conflicts />} />
          <Route path="/simulator" element={<Simulator />} />
          <Route path="/compliance" element={<Compliance />} />
          <Route path="/deployment" element={<Deployment />} />
          <Route path="/effectiveness" element={<Effectiveness />} />
          <Route path="/visualization" element={<Visualization />} />
        </Routes>
      </div>
    </div>
  );
}

export default App;

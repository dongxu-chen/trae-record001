import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Box, Toolbar } from '@mui/material';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import Faults from './pages/Faults';
import Scenarios from './pages/Scenarios';
import Services from './pages/Services';
import Executions from './pages/Executions';
import Presets from './pages/Presets';
import Resilience from './pages/Resilience';

function App() {
  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <Navbar />
      <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
        <Toolbar />
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/faults" element={<Faults />} />
          <Route path="/scenarios" element={<Scenarios />} />
          <Route path="/services" element={<Services />} />
          <Route path="/executions" element={<Executions />} />
          <Route path="/presets" element={<Presets />} />
          <Route path="/resilience" element={<Resilience />} />
        </Routes>
      </Box>
    </Box>
  );
}

export default App;

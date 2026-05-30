import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Box } from '@mui/material';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import Secrets from './pages/Secrets';
import SecretDetail from './pages/SecretDetail';
import AuditLogs from './pages/AuditLogs';

const App: React.FC = () => {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Navbar />
      <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/secrets" element={<Secrets />} />
          <Route path="/secrets/:id" element={<SecretDetail />} />
          <Route path="/audit" element={<AuditLogs />} />
        </Routes>
      </Box>
    </Box>
  );
};

export default App;

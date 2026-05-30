import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';

import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Policies from './pages/Policies';
import PolicyDetail from './pages/PolicyDetail';
import PolicyEditor from './pages/PolicyEditor';
import Analysis from './pages/Analysis';
import Recommendations from './pages/Recommendations';
import CanaryDeployments from './pages/CanaryDeployments';
import Topology from './pages/Topology';
import OPAPolicies from './pages/OPAPolicies';
import Simulation from './pages/Simulation';
import Compliance from './pages/Compliance';
import AutoFix from './pages/AutoFix';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
    background: {
      default: '#f5f5f5',
    },
  },
});

const App: React.FC = () => {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/policies" element={<Policies />} />
            <Route path="/policies/:id" element={<PolicyDetail />} />
            <Route path="/policies/new" element={<PolicyEditor />} />
            <Route path="/policies/edit/:id" element={<PolicyEditor />} />
            <Route path="/analysis" element={<Analysis />} />
            <Route path="/recommendations" element={<Recommendations />} />
            <Route path="/canary" element={<CanaryDeployments />} />
            <Route path="/topology" element={<Topology />} />
            <Route path="/opa" element={<OPAPolicies />} />
            <Route path="/simulation" element={<Simulation />} />
            <Route path="/compliance" element={<Compliance />} />
            <Route path="/autofix" element={<AutoFix />} />
          </Routes>
        </Layout>
      </Router>
    </ThemeProvider>
  );
};

export default App;

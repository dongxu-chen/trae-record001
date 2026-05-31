import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Box, Toolbar } from '@mui/material';
import Navbar from './components/Navbar';
import SchemaList from './components/SchemaList';
import SchemaDetail from './components/SchemaDetail';
import CompatibilityChecker from './components/CompatibilityChecker';
import SchemaDiffViewer from './components/SchemaDiffViewer';
import EvolutionRecommendation from './components/EvolutionRecommendation';
import AutoEvolve from './components/AutoEvolve';
import CodeGeneration from './components/CodeGeneration';
import AuditLog from './components/AuditLog';

function App() {
  return (
    <Box sx={{ display: 'flex' }}>
      <Navbar />
      <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
        <Toolbar />
        <Routes>
          <Route path="/" element={<SchemaList />} />
          <Route path="/schema/:subject" element={<SchemaDetail />} />
          <Route path="/compatibility" element={<CompatibilityChecker />} />
          <Route path="/diff" element={<SchemaDiffViewer />} />
          <Route path="/evolution" element={<EvolutionRecommendation />} />
          <Route path="/auto-evolve" element={<AutoEvolve />} />
          <Route path="/code-gen" element={<CodeGeneration />} />
          <Route path="/audit" element={<AuditLog />} />
        </Routes>
      </Box>
    </Box>
  );
}

export default App;

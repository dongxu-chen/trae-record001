import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Box, Container } from '@mui/material';
import Header from './components/Header';
import SearchPage from './pages/SearchPage';
import CaseDetailPage from './pages/CaseDetailPage';
import ApiService from './services/api';

function App() {
  const [apiService] = useState(() => new ApiService());

  return (
    <Router>
      <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <Header />
        <Container component="main" sx={{ flexGrow: 1, py: 4 }}>
          <Routes>
            <Route path="/" element={<SearchPage apiService={apiService} />} />
            <Route path="/case/:id" element={<CaseDetailPage apiService={apiService} />} />
          </Routes>
        </Container>
      </Box>
    </Router>
  );
}

export default App;

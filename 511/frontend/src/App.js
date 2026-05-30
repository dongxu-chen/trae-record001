import React from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { Box, AppBar, Toolbar, Typography, Container, Button } from '@mui/material';
import HomePage from './pages/HomePage';
import LineagePage from './pages/LineagePage';
import GraphPage from './pages/GraphPage';
import AnalyticsPage from './pages/AnalyticsPage';

function App() {
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'SQL解析' },
    { path: '/lineage', label: '血缘查询' },
    { path: '/graph', label: '血缘图谱' },
    { path: '/analytics', label: '数据分析' },
  ];

  return (
    <Box sx={{ flexGrow: 1 }}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            数据血缘解析工具
          </Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            {navItems.map((item) => (
              <Button
                key={item.path}
                color="inherit"
                component={Link}
                to={item.path}
                sx={{
                  fontWeight: location.pathname === item.path ? 'bold' : 'normal',
                  backgroundColor: location.pathname === item.path ? 'rgba(255,255,255,0.1)' : 'transparent',
                }}
              >
                {item.label}
              </Button>
            ))}
          </Box>
        </Toolbar>
      </AppBar>
      <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/lineage" element={<LineagePage />} />
          <Route path="/graph" element={<GraphPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
        </Routes>
      </Container>
    </Box>
  );
}

export default App;

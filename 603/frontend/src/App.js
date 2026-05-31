import React, { useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  List,
  Typography,
  Divider,
  IconButton,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  ShowChart as ChartIcon,
  Settings as SettingsIcon,
  History as HistoryIcon,
  Timeline as PredictionIcon,
  ReportProblem as DLQIcon,
  Schedule as DelayIcon,
} from '@mui/icons-material';

import Dashboard from './pages/Dashboard';
import Strategies from './pages/Strategies';
import AuditLog from './pages/AuditLog';
import Predictions from './pages/Predictions';
import DLQReplay from './pages/DLQReplay';
import DelayProcess from './pages/DelayProcess';

const drawerWidth = 240;

function App() {
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const menuItems = [
    { text: '监控面板', icon: <DashboardIcon />, path: '/' },
    { text: '积压预测', icon: <PredictionIcon />, path: '/predictions' },
    { text: '死信 & 重放', icon: <DLQIcon />, path: '/dlq-replay' },
    { text: '延迟处理', icon: <DelayIcon />, path: '/delay' },
    { text: '策略配置', icon: <SettingsIcon />, path: '/strategies' },
    { text: '执行审计', icon: <HistoryIcon />, path: '/audit' },
  ];

  const drawer = (
    <div>
      <Toolbar>
        <Typography variant="h6" noWrap component="div">
          Pulsar 积压管理
        </Typography>
      </Toolbar>
      <Divider />
      <List>
        {menuItems.map((item) => (
          <ListItem key={item.text} disablePadding>
            <ListItemButton
              component="a"
              href={item.path}
              selected={window.location.pathname === item.path}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </div>
  );

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar
        position="fixed"
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div">
            Pulsar 消息积压处理工具
          </Typography>
        </Toolbar>
      </AppBar>

      <Box
        component="nav"
        sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: drawerWidth,
            },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: drawerWidth,
            },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${drawerWidth}px)` },
        }}
      >
        <Toolbar />
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/predictions" element={<Predictions />} />
          <Route path="/dlq-replay" element={<DLQReplay />} />
          <Route path="/delay" element={<DelayProcess />} />
          <Route path="/strategies" element={<Strategies />} />
          <Route path="/audit" element={<AuditLog />} />
        </Routes>
      </Box>
    </Box>
  );
}

export default App;

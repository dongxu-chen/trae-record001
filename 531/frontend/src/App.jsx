import React, { useState, useEffect } from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  Typography,
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Box,
  CssBaseline,
  IconButton,
  Badge,
  Divider,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Compare as CompareIcon,
  Warning as WarningIcon,
  Grade as GradeIcon,
  Rule as RuleIcon,
  Menu as MenuIcon,
  AttachMoney as AttachMoneyIcon,
  Memory as MemoryIcon,
  AccountTree as AccountTreeIcon,
} from '@mui/icons-material';
import Dashboard from './components/Dashboard';
import ServiceComparison from './components/ServiceComparison';
import AlertPanel from './components/AlertPanel';
import ServiceDetail from './components/ServiceDetail';
import SlaTierConfig from './components/SlaTierConfig';
import RootCauseRuleBase from './components/RootCauseRuleBase';
import CompensationPanel from './components/CompensationPanel';
import CapacityPlanning from './components/CapacityPlanning';
import DependencyGraph from './components/DependencyGraph';
import { alertApi } from './services/api';

const drawerWidth = 240;

function App() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [activeAlerts, setActiveAlerts] = useState([]);

  useEffect(() => {
    fetchActiveAlerts();
    const interval = setInterval(fetchActiveAlerts, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchActiveAlerts = async () => {
    try {
      const response = await alertApi.getActive();
      setActiveAlerts(response.data);
    } catch (error) {
      console.error('Failed to fetch alerts:', error);
    }
  };

  const drawer = (
    <div>
      <Toolbar />
      <List>
        <ListItem component={Link} to="/" button onClick={() => setMobileOpen(false)}>
          <ListItemIcon>
            <DashboardIcon />
          </ListItemIcon>
          <ListItemText primary="仪表板" />
        </ListItem>
        <ListItem component={Link} to="/comparison" button onClick={() => setMobileOpen(false)}>
          <ListItemIcon>
            <CompareIcon />
          </ListItemIcon>
          <ListItemText primary="服务对比" />
        </ListItem>
        <ListItem component={Link} to="/alerts" button onClick={() => setMobileOpen(false)}>
          <ListItemIcon>
            <Badge badgeContent={activeAlerts.length} color="error">
              <WarningIcon />
            </Badge>
          </ListItemIcon>
          <ListItemText primary="告警中心" />
        </ListItem>
      </List>
      <Divider />
      <List>
        <ListItem component={Link} to="/sla-tiers" button onClick={() => setMobileOpen(false)}>
          <ListItemIcon>
            <GradeIcon />
          </ListItemIcon>
          <ListItemText primary="SLA等级配置" />
        </ListItem>
        <ListItem component={Link} to="/rules" button onClick={() => setMobileOpen(false)}>
          <ListItemIcon>
            <RuleIcon />
          </ListItemIcon>
          <ListItemText primary="根因规则库" />
        </ListItem>
      </List>
      <Divider />
      <List>
        <ListItem component={Link} to="/compensations" button onClick={() => setMobileOpen(false)}>
          <ListItemIcon>
            <AttachMoneyIcon />
          </ListItemIcon>
          <ListItemText primary="SLA补偿建议" />
        </ListItem>
        <ListItem component={Link} to="/capacity" button onClick={() => setMobileOpen(false)}>
          <ListItemIcon>
            <MemoryIcon />
          </ListItemIcon>
          <ListItemText primary="容量规划" />
        </ListItem>
        <ListItem component={Link} to="/dependencies" button onClick={() => setMobileOpen(false)}>
          <ListItemIcon>
            <AccountTreeIcon />
          </ListItemIcon>
          <ListItemText primary="服务依赖" />
        </ListItem>
      </List>
    </div>
  );

  return (
    <Box sx={{ display: 'flex' }}>
      <CssBaseline />
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
            edge="start"
            onClick={() => setMobileOpen(!mobileOpen)}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            SLA 监控平台
          </Typography>
          <Badge badgeContent={activeAlerts.length} color="error">
            <WarningIcon />
          </Badge>
        </Toolbar>
      </AppBar>

      <Box
        component="nav"
        sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
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
          <Route path="/comparison" element={<ServiceComparison />} />
          <Route path="/alerts" element={<AlertPanel />} />
          <Route path="/service/:name" element={<ServiceDetail />} />
          <Route path="/sla-tiers" element={<SlaTierConfig />} />
          <Route path="/rules" element={<RootCauseRuleBase />} />
          <Route path="/compensations" element={<CompensationPanel />} />
          <Route path="/capacity" element={<CapacityPlanning />} />
          <Route path="/dependencies" element={<DependencyGraph />} />
        </Routes>
      </Box>
    </Box>
  );
}

export default App;

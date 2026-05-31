import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
  Box,
  Divider,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  BugReport as FaultIcon,
  PlaylistPlay as ScenarioIcon,
  Apps as ServiceIcon,
  Timeline as ExecutionIcon,
  LibraryBooks as PresetIcon,
  Shield as ResilienceIcon,
} from '@mui/icons-material';

const drawerWidth = 240;

const menuItems = [
  { text: '仪表盘', icon: <DashboardIcon />, path: '/' },
  { text: '故障管理', icon: <FaultIcon />, path: '/faults' },
  { text: '场景编排', icon: <ScenarioIcon />, path: '/scenarios' },
  { text: '服务监控', icon: <ServiceIcon />, path: '/services' },
  { text: '执行记录', icon: <ExecutionIcon />, path: '/executions' },
];

const advancedMenuItems = [
  { text: '场景库', icon: <PresetIcon />, path: '/presets' },
  { text: '韧性评分', icon: <ResilienceIcon />, path: '/resilience' },
];

function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();

  const renderMenuItem = (item) => (
    <ListItem
      button
      key={item.text}
      onClick={() => navigate(item.path)}
      selected={location.pathname === item.path}
      sx={{
        '&.Mui-selected': {
          backgroundColor: '#3949ab',
          '&:hover': {
            backgroundColor: '#3949ab',
          },
        },
        '&:hover': {
          backgroundColor: '#283593',
        },
      }}
    >
      <ListItemIcon sx={{ color: 'white' }}>{item.icon}</ListItemIcon>
      <ListItemText primary={item.text} />
    </ListItem>
  );

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: drawerWidth,
          boxSizing: 'border-box',
          backgroundColor: '#1a237e',
          color: 'white',
        },
      }}
    >
      <Toolbar>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <FaultIcon sx={{ color: '#64b5f6' }} />
          <Typography variant="h6" noWrap component="div" sx={{ color: 'white' }}>
            故障注入平台
          </Typography>
        </Box>
      </Toolbar>
      <List>
        {menuItems.map(renderMenuItem)}
      </List>
      <Divider sx={{ bgcolor: 'rgba(255,255,255,0.2)', my: 1 }} />
      <List>
        <ListItem sx={{ py: 0 }}>
          <ListItemText
            primary="高级功能"
            primaryTypographyProps={{ variant: 'caption', color: 'rgba(255,255,255,0.6)' }}
          />
        </ListItem>
        {advancedMenuItems.map(renderMenuItem)}
      </List>
    </Drawer>
  );
}

export default Navbar;

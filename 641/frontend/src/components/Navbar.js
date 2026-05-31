import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
  Box,
} from '@mui/material';
import {
  List as ListIcon,
  CompareArrows,
  Diff,
  TrendingUp,
  AutoAwesome,
  Code,
  History,
} from '@mui/icons-material';

const drawerWidth = 240;

const menuItems = [
  { text: 'Schema List', icon: <ListIcon />, path: '/' },
  { text: 'Compatibility Check', icon: <CompareArrows />, path: '/compatibility' },
  { text: 'Schema Diff', icon: <Diff />, path: '/diff' },
  { text: 'Evolution Recommendation', icon: <TrendingUp />, path: '/evolution' },
  { text: 'Auto Evolve', icon: <AutoAwesome />, path: '/auto-evolve' },
  { text: 'Code Generation', icon: <Code />, path: '/code-gen' },
  { text: 'Audit Log', icon: <History />, path: '/audit' },
];

function Navbar() {
  const location = useLocation();

  return (
    <Drawer
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: drawerWidth,
          boxSizing: 'border-box',
        },
      }}
      variant="permanent"
      anchor="left"
    >
      <Toolbar>
        <Typography variant="h6" noWrap component="div">
          Schema Registry
        </Typography>
      </Toolbar>
      <Box sx={{ overflow: 'auto' }}>
        <List>
          {menuItems.map((item) => (
            <ListItem
              button
              key={item.text}
              component={Link}
              to={item.path}
              selected={location.pathname === item.path}
              sx={{
                backgroundColor: location.pathname === item.path ? 'action.selected' : 'inherit',
              }}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItem>
          ))}
        </List>
      </Box>
    </Drawer>
  );
}

export default Navbar;

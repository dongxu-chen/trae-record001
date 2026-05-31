import React from 'react';
import { Drawer, List, ListItem, ListItemIcon, ListItemText, Typography, Box, Divider } from '@mui/material';
import { Dashboard, Analytics, TrendingUp, AttachMoney, Home, Favorite, Compare, AutoFixHigh } from '@mui/icons-material';
import { Link, useLocation } from 'react-router-dom';

const Navbar = () => {
  const location = useLocation();

  const menuItems = [
    { text: 'Dashboard', icon: <Dashboard />, path: '/' },
    { text: 'Job Analysis', icon: <Analytics />, path: '/jobs/demo/analysis' },
    { text: 'Recommendation', icon: <TrendingUp />, path: '/jobs/demo/recommendation' },
    { text: 'Cost Estimator', icon: <AttachMoney />, path: '/cost-estimator' },
    { text: 'Health Monitor', icon: <Favorite />, path: '/jobs/demo/health' },
    { text: 'Job Comparison', icon: <Compare />, path: '/jobs/comparison' },
    { text: 'Auto Adjust', icon: <AutoFixHigh />, path: '/jobs/demo/auto-adjust' },
  ];

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: 240,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: 240,
          boxSizing: 'border-box',
          background: 'linear-gradient(180deg, #1976d2 0%, #1565c0 100%)',
          color: 'white',
        },
      }}
    >
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="h6" sx={{ color: 'white', fontWeight: 'bold' }}>
          Flink Resource
        </Typography>
        <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.8)' }}>
          Recommender
        </Typography>
      </Box>
      <Divider sx={{ bgcolor: 'rgba(255,255,255,0.2)' }} />
      <List>
        {menuItems.map((item) => (
          <ListItem
            button
            key={item.text}
            component={Link}
            to={item.path}
            sx={{
              bgcolor: location.pathname === item.path ? 'rgba(255,255,255,0.2)' : 'transparent',
              '&:hover': {
                bgcolor: 'rgba(255,255,255,0.15)',
              },
              my: 0.5,
              mx: 1,
              borderRadius: 1,
            }}
          >
            <ListItemIcon sx={{ color: 'white', minWidth: 40 }}>
              {item.icon}
            </ListItemIcon>
            <ListItemText
              primary={item.text}
              sx={{
                '& .MuiListItemText-primary': {
                  fontSize: '0.9rem',
                  fontWeight: 500,
                },
              }}
            />
          </ListItem>
        ))}
      </List>
    </Drawer>
  );
};

export default Navbar;

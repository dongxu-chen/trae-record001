import React from 'react';
import { AppBar, Toolbar, Typography, Button, Box } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import LockIcon from '@mui/icons-material/Lock';
import DashboardIcon from '@mui/icons-material/Dashboard';
import VpnKeyIcon from '@mui/icons-material/VpnKey';
import AssessmentIcon from '@mui/icons-material/Assessment';

const Navbar: React.FC = () => {
  return (
    <AppBar position="static">
      <Toolbar>
        <LockIcon sx={{ mr: 2 }} />
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          Key Management Service
        </Typography>
        <Box>
          <Button
            color="inherit"
            component={RouterLink}
            to="/"
            startIcon={<DashboardIcon />}
          >
            Dashboard
          </Button>
          <Button
            color="inherit"
            component={RouterLink}
            to="/secrets"
            startIcon={<VpnKeyIcon />}
          >
            Secrets
          </Button>
          <Button
            color="inherit"
            component={RouterLink}
            to="/audit"
            startIcon={<AssessmentIcon />}
          >
            Audit Logs
          </Button>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Navbar;

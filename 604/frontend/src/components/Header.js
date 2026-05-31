import React from 'react';
import { AppBar, Toolbar, Typography, Box } from '@mui/material';
import { Link } from 'react-router-dom';
import GavelIcon from '@mui/icons-material/Gavel';

function Header() {
  return (
    <AppBar position="static" elevation={0}>
      <Toolbar>
        <Box
          component={Link}
          to="/"
          sx={{
            display: 'flex',
            alignItems: 'center',
            textDecoration: 'none',
            color: 'inherit',
          }}
        >
          <GavelIcon sx={{ mr: 2 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            法律文书相似案例检索系统
          </Typography>
        </Box>
      </Toolbar>
    </AppBar>
  );
}

export default Header;

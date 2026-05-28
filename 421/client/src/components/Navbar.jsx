import React from 'react';
import { AppBar, Toolbar, Typography, Button, Box, Avatar, Menu, MenuItem } from '@mui/material';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import NotificationCenter from './NotificationCenter';
import AssignmentIcon from '@mui/icons-material/Assignment';
import BarChartIcon from '@mui/icons-material/BarChart';
import PlaylistAddCheckIcon from '@mui/icons-material/PlaylistAddCheck';

const Navbar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [anchorEl, setAnchorEl] = React.useState(null);

  const handleMenu = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
    handleClose();
  };

  return (
    <AppBar position="static">
      <Toolbar>
        <Typography 
          variant="h6" 
          component={Link} 
          to="/"
          sx={{ flexGrow: 1, textDecoration: 'none', color: 'inherit' }}
        >
          文档协作审核系统
        </Typography>
        
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <Button color="inherit" component={Link} to="/">
            我的文档
          </Button>
          {user?.role === 'reviewer' || user?.role === 'admin' ? (
            <Button color="inherit" component={Link} to="/reviews" startIcon={<AssignmentIcon />}>
              待审核
            </Button>
          ) : null}
          
          <Button color="inherit" component={Link} to="/templates" startIcon={<PlaylistAddCheckIcon />}>
            审核模板
          </Button>
          
          {user?.role === 'reviewer' || user?.role === 'admin' ? (
            <Button color="inherit" component={Link} to="/stats" startIcon={<BarChartIcon />}>
              统计
            </Button>
          ) : null}
          
          <NotificationCenter userId={user?.id} />
          
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Avatar 
              onClick={handleMenu}
              sx={{ cursor: 'pointer', bgcolor: 'secondary.main' }}
            >
              {user?.username?.charAt(0).toUpperCase()}
            </Avatar>
            <Menu
              anchorEl={anchorEl}
              open={Boolean(anchorEl)}
              onClose={handleClose}
            >
              <MenuItem disabled>
                <Typography variant="body2">{user?.username}</Typography>
              </MenuItem>
              <MenuItem disabled>
                <Typography variant="body2" color="textSecondary">
                  {user?.role === 'admin' ? '管理员' : 
                   user?.role === 'reviewer' ? '审核人' : '编辑者'}
                </Typography>
              </MenuItem>
              <MenuItem onClick={handleLogout}>退出登录</MenuItem>
            </Menu>
          </Box>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Navbar;

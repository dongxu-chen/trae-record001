import React, { useState } from 'react'
import { Routes, Route, useNavigate } from 'react-router-dom'
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
  IconButton
} from '@mui/material'
import {
  Dashboard as DashboardIcon,
  Storage as StorageIcon,
  Backup as BackupIcon,
  Restore as RestoreIcon,
  Schedule as ScheduleIcon,
  VpnKey as VpnKeyIcon,
  SyncAlt as SyncAltIcon,
  FactCheck as FactCheckIcon,
  AccountBalance as AccountBalanceIcon,
  Menu as MenuIcon
} from '@mui/icons-material'
import Dashboard from './pages/Dashboard'
import Clusters from './pages/Clusters'
import Backups from './pages/Backups'
import Restores from './pages/Restores'
import Schedules from './pages/Schedules'
import KMS from './pages/KMS'
import Replication from './pages/Replication'
import Drills from './pages/Drills'
import CostAnalysis from './pages/CostAnalysis'

const drawerWidth = 240

function App() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const navigate = useNavigate()

  const menuItems = [
    { text: '仪表盘', icon: <DashboardIcon />, path: '/' },
    { text: '集群管理', icon: <StorageIcon />, path: '/clusters' },
    { text: '备份管理', icon: <BackupIcon />, path: '/backups' },
    { text: '恢复任务', icon: <RestoreIcon />, path: '/restores' },
    { text: '定时任务', icon: <ScheduleIcon />, path: '/schedules' },
    { text: '跨集群复制', icon: <SyncAltIcon />, path: '/replication' },
    { text: '恢复演练', icon: <FactCheckIcon />, path: '/drills' },
    { text: '成本分析', icon: <AccountBalanceIcon />, path: '/cost' },
    { text: 'KMS 密钥管理', icon: <VpnKeyIcon />, path: '/kms' }
  ]

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen)
  }

  const drawer = (
    <Box>
      <Toolbar>
        <Typography variant="h6" noWrap component="div">
          ETCD 备份管理器
        </Typography>
      </Toolbar>
      <List>
        {menuItems.map((item) => (
          <ListItem
            button
            key={item.text}
            onClick={() => {
              navigate(item.path)
              setMobileOpen(false)
            }}
          >
            <ListItemIcon>{item.icon}</ListItemIcon>
            <ListItemText primary={item.text} />
          </ListItem>
        ))}
      </List>
    </Box>
  )

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
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div">
            ETCD 集群备份恢复管理系统
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
          ModalProps={{
            keepMounted: true,
          }}
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
          mt: 8
        }}
      >
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/clusters" element={<Clusters />} />
          <Route path="/backups" element={<Backups />} />
          <Route path="/restores" element={<Restores />} />
          <Route path="/schedules" element={<Schedules />} />
          <Route path="/replication" element={<Replication />} />
          <Route path="/drills" element={<Drills />} />
          <Route path="/cost" element={<CostAnalysis />} />
          <Route path="/kms" element={<KMS />} />
        </Routes>
      </Box>
    </Box>
  )
}

export default App

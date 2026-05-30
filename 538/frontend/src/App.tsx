import { useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import { Box, Drawer, AppBar, Toolbar, Typography, List, ListItem, ListItemIcon, ListItemText } from '@mui/material'
import {
  AccountTree as TopologyIcon,
  Policy as PolicyIcon,
  Warning as ConflictIcon,
  Speed as SimulationIcon,
  SettingsBackupRestore as ManagementIcon,
} from '@mui/icons-material'
import TopologyView from './components/TopologyView'
import PolicyRecommendations from './components/PolicyRecommendations'
import ConflictDetection from './components/ConflictDetection'
import PolicySimulator from './components/PolicySimulator'
import PolicyManagement from './components/PolicyManagement'

const drawerWidth = 240

export default function App() {
  const [namespace, setNamespace] = useState('default')

  const menuItems = [
    { text: 'Network Topology', icon: <TopologyIcon />, path: '/' },
    { text: 'Policy Recommendations', icon: <PolicyIcon />, path: '/policies' },
    { text: 'Conflict Detection', icon: <ConflictIcon />, path: '/conflicts' },
    { text: 'Policy Simulator', icon: <SimulationIcon />, path: '/simulator' },
    { text: 'Policy Management', icon: <ManagementIcon />, path: '/management' },
  ]

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Toolbar>
          <Typography variant="h6" noWrap component="div">
            K8s Network Policy Recommender
          </Typography>
          <Box sx={{ flexGrow: 1 }} />
          <Typography variant="body1">
            Namespace: {namespace}
          </Typography>
        </Toolbar>
      </AppBar>
      
      <Drawer
        variant="permanent"
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          [`& .MuiDrawer-paper`]: { width: drawerWidth, boxSizing: 'border-box' },
        }}
      >
        <Toolbar />
        <Box sx={{ overflow: 'auto' }}>
          <List>
            {menuItems.map((item) => (
              <ListItem
                button
                component="a"
                href={item.path}
                key={item.text}
              >
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText primary={item.text} />
              </ListItem>
            ))}
          </List>
        </Box>
      </Drawer>
      
      <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
        <Toolbar />
        <Routes>
          <Route path="/" element={<TopologyView namespace={namespace} onNamespaceChange={setNamespace} />} />
          <Route path="/policies" element={<PolicyRecommendations namespace={namespace} onNamespaceChange={setNamespace} />} />
          <Route path="/conflicts" element={<ConflictDetection namespace={namespace} onNamespaceChange={setNamespace} />} />
          <Route path="/simulator" element={<PolicySimulator namespace={namespace} onNamespaceChange={setNamespace} />} />
          <Route path="/management" element={<PolicyManagement namespace={namespace} onNamespaceChange={setNamespace} />} />
        </Routes>
      </Box>
    </Box>
  )
}

import React, { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Chip,
  LinearProgress
} from '@mui/material'
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon
} from '@mui/icons-material'
import { clusterApi } from '../api/client'

function Clusters() {
  const [loading, setLoading] = useState(true)
  const [clusters, setClusters] = useState([])
  const [statuses, setStatuses] = useState({})
  const [openDialog, setOpenDialog] = useState(false)
  const [editingCluster, setEditingCluster] = useState(null)
  const [formData, setFormData] = useState({
    name: '',
    endpoints: '',
    username: '',
    password: '',
    tls: false
  })

  useEffect(() => {
    loadClusters()
  }, [])

  const loadClusters = async () => {
    try {
      const res = await clusterApi.list()
      setClusters(res.data || [])
      
      res.data?.forEach(cluster => {
        loadClusterStatus(cluster.id)
      })
    } catch (error) {
      console.error('Failed to load clusters:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadClusterStatus = async (clusterId) => {
    try {
      const res = await clusterApi.getStatus(clusterId)
      setStatuses(prev => ({ ...prev, [clusterId]: res.data }))
    } catch (error) {
      console.error(`Failed to load status for cluster ${clusterId}:`, error)
    }
  }

  const handleOpenDialog = (cluster = null) => {
    if (cluster) {
      setEditingCluster(cluster)
      setFormData({
        name: cluster.name,
        endpoints: cluster.endpoints?.join(', ') || '',
        username: cluster.username || '',
        password: cluster.password || '',
        tls: cluster.tls || false
      })
    } else {
      setEditingCluster(null)
      setFormData({
        name: '',
        endpoints: '',
        username: '',
        password: '',
        tls: false
      })
    }
    setOpenDialog(true)
  }

  const handleCloseDialog = () => {
    setOpenDialog(false)
    setEditingCluster(null)
  }

  const handleSubmit = async () => {
    try {
      const endpoints = formData.endpoints.split(',').map(e => e.trim()).filter(e => e)
      
      if (editingCluster) {
        await clusterApi.update(editingCluster.id, {
          ...formData,
          endpoints
        })
      } else {
        await clusterApi.create({
          ...formData,
          endpoints
        })
      }
      
      handleCloseDialog()
      loadClusters()
    } catch (error) {
      console.error('Failed to save cluster:', error)
    }
  }

  const handleDelete = async (clusterId) => {
    if (window.confirm('确定要删除这个集群吗？')) {
      try {
        await clusterApi.delete(clusterId)
        loadClusters()
      } catch (error) {
        console.error('Failed to delete cluster:', error)
      }
    }
  }

  if (loading) {
    return <LinearProgress />
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">集群管理</Typography>
        <Box>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadClusters}
            sx={{ mr: 1 }}
          >
            刷新
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => handleOpenDialog()}
          >
            添加集群
          </Button>
        </Box>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>集群名称</TableCell>
              <TableCell>端点</TableCell>
              <TableCell>状态</TableCell>
              <TableCell>版本</TableCell>
              <TableCell>节点数</TableCell>
              <TableCell>数据大小</TableCell>
              <TableCell>操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {clusters.map((cluster) => {
              const status = statuses[cluster.id]
              return (
                <TableRow key={cluster.id}>
                  <TableCell>{cluster.name}</TableCell>
                  <TableCell>
                    <Typography variant="body2" noWrap sx={{ maxWidth: 200 }}>
                      {cluster.endpoints?.join(', ')}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {status ? (
                      status.healthy ? (
                        <Chip
                          icon={<CheckCircleIcon />}
                          label="健康"
                          color="success"
                          size="small"
                        />
                      ) : (
                        <Chip
                          icon={<ErrorIcon />}
                          label="异常"
                          color="error"
                          size="small"
                        />
                      )
                    ) : (
                      <LinearProgress size="small" />
                    )}
                  </TableCell>
                  <TableCell>{status?.version || '-'}</TableCell>
                  <TableCell>{status?.members?.length || '-'}</TableCell>
                  <TableCell>
                    {status?.dbSize 
                      ? (status.dbSize / 1024 / 1024).toFixed(2) + ' MB'
                      : '-'}
                  </TableCell>
                  <TableCell>
                    <IconButton
                      size="small"
                      onClick={() => loadClusterStatus(cluster.id)}
                      title="刷新状态"
                    >
                      <RefreshIcon fontSize="small" />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => handleOpenDialog(cluster)}
                      title="编辑"
                    >
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => handleDelete(cluster.id)}
                      title="删除"
                      color="error"
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              )
            })}
            {clusters.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  <Typography variant="body2" color="text.secondary" py={3}>
                    暂无集群，请点击"添加集群"按钮添加
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingCluster ? '编辑集群' : '添加集群'}
        </DialogTitle>
        <DialogContent>
          <Box pt={1}>
            <TextField
              fullWidth
              label="集群名称"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              margin="normal"
            />
            <TextField
              fullWidth
              label="端点地址（多个用逗号分隔）"
              placeholder="http://localhost:2379"
              value={formData.endpoints}
              onChange={(e) => setFormData({ ...formData, endpoints: e.target.value })}
              margin="normal"
            />
            <TextField
              fullWidth
              label="用户名"
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              margin="normal"
            />
            <TextField
              fullWidth
              label="密码"
              type="password"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              margin="normal"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>取消</Button>
          <Button onClick={handleSubmit} variant="contained">
            {editingCluster ? '保存' : '添加'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default Clusters

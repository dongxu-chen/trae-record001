import React, { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  LinearProgress,
  MenuItem,
  Select,
  FormControl,
  InputLabel
} from '@mui/material'
import {
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  PlayArrow as PlayArrowIcon
} from '@mui/icons-material'
import { clusterApi, restoreApi } from '../api/client'

function Restores() {
  const [loading, setLoading] = useState(true)
  const [clusters, setClusters] = useState([])
  const [restores, setRestores] = useState([])
  const [selectedCluster, setSelectedCluster] = useState('')

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [clusterRes, restoreRes] = await Promise.all([
        clusterApi.list(),
        restoreApi.list()
      ])
      
      setClusters(clusterRes.data || [])
      setRestores(restoreRes.data || [])
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleClusterChange = async (clusterId) => {
    setSelectedCluster(clusterId)
    try {
      const res = await restoreApi.list(clusterId)
      setRestores(res.data || [])
    } catch (error) {
      console.error('Failed to load restores:', error)
    }
  }

  if (loading) {
    return <LinearProgress />
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">恢复任务</Typography>
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>选择集群</InputLabel>
          <Select
            value={selectedCluster}
            label="选择集群"
            onChange={(e) => handleClusterChange(e.target.value)}
          >
            <MenuItem value="">全部集群</MenuItem>
            {clusters.map((cluster) => (
              <MenuItem key={cluster.id} value={cluster.id}>
                {cluster.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>任务ID</TableCell>
              <TableCell>备份ID</TableCell>
              <TableCell>目标集群</TableCell>
              <TableCell>类型</TableCell>
              <TableCell>状态</TableCell>
              <TableCell>恢复时间点</TableCell>
              <TableCell>创建时间</TableCell>
              <TableCell>完成时间</TableCell>
              <TableCell>消息</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {restores.map((restore) => (
              <TableRow key={restore.id}>
                <TableCell sx={{ maxWidth: 100 }}>
                  <Typography variant="body2" noWrap>
                    {restore.id.substring(0, 8)}...
                  </Typography>
                </TableCell>
                <TableCell sx={{ maxWidth: 100 }}>
                  <Typography variant="body2" noWrap>
                    {restore.backupId?.substring(0, 8)}...
                  </Typography>
                </TableCell>
                <TableCell>{restore.targetCluster || '-'}</TableCell>
                <TableCell>
                  <Chip
                    size="small"
                    label={restore.type === 'dryrun' ? '演练' : '恢复'}
                    color={restore.type === 'dryrun' ? 'default' : 'primary'}
                  />
                </TableCell>
                <TableCell>
                  {restore.status === 'completed' ? (
                    <Chip
                      icon={<CheckCircleIcon />}
                      label="成功"
                      color="success"
                      size="small"
                    />
                  ) : restore.status === 'failed' ? (
                    <Chip
                      icon={<ErrorIcon />}
                      label="失败"
                      color="error"
                      size="small"
                    />
                  ) : (
                    <Chip
                      icon={<PlayArrowIcon />}
                      label="进行中"
                      color="info"
                      size="small"
                    />
                  )}
                </TableCell>
                <TableCell>
                  {restore.pointInTime 
                    ? new Date(restore.pointInTime).toLocaleString()
                    : '-'}
                </TableCell>
                <TableCell>
                  {new Date(restore.createdAt).toLocaleString()}
                </TableCell>
                <TableCell>
                  {restore.completedAt 
                    ? new Date(restore.completedAt).toLocaleString()
                    : '-'}
                </TableCell>
                <TableCell>
                  <Typography variant="body2" color="text.secondary">
                    {restore.message || '-'}
                  </Typography>
                </TableCell>
              </TableRow>
            ))}
            {restores.length === 0 && (
              <TableRow>
                <TableCell colSpan={9} align="center">
                  <Typography variant="body2" color="text.secondary" py={3}>
                    暂无恢复任务
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  )
}

export default Restores

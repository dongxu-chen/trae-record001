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
  Chip,
  LinearProgress,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Tabs,
  Tab,
  Tooltip
} from '@mui/material'
import {
  Add as AddIcon,
  Refresh as RefreshIcon,
  Verify as VerifyIcon,
  Restore as RestoreIcon,
  PlayArrow as PlayArrowIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  VpnKey as VpnKeyIcon,
  Schedule as ScheduleIcon
} from '@mui/icons-material'
import { clusterApi, backupApi, restoreApi } from '../api/client'

function Backups() {
  const [loading, setLoading] = useState(true)
  const [clusters, setClusters] = useState([])
  const [backups, setBackups] = useState([])
  const [selectedCluster, setSelectedCluster] = useState('')
  const [verifyResult, setVerifyResult] = useState(null)
  const [openRestoreDialog, setOpenRestoreDialog] = useState(false)
  const [selectedBackup, setSelectedBackup] = useState(null)
  const [restoreTab, setRestoreTab] = useState(0)
  const [timePoints, setTimePoints] = useState([])
  const [restoreData, setRestoreData] = useState({
    targetClusterId: '',
    pointInTime: '',
    walIndex: ''
  })

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [clusterRes, backupRes] = await Promise.all([
        clusterApi.list(),
        backupApi.list()
      ])

      setClusters(clusterRes.data || [])
      setBackups(backupRes.data || [])
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleClusterChange = async (clusterId) => {
    setSelectedCluster(clusterId)
    try {
      const backupRes = await backupApi.list(clusterId)
      setBackups(backupRes.data || [])

      if (clusterId) {
        const tpRes = await backupApi.listTimePoints(clusterId)
        setTimePoints(tpRes.data || [])
      }
    } catch (error) {
      console.error('Failed to load backups:', error)
    }
  }

  const handleCreateFullBackup = async () => {
    if (!selectedCluster) {
      alert('请先选择集群')
      return
    }
    try {
      await backupApi.createFull(selectedCluster)
      setTimeout(loadData, 2000)
    } catch (error) {
      console.error('Failed to create backup:', error)
    }
  }

  const handleCreateIncrementalBackup = async () => {
    if (!selectedCluster) {
      alert('请先选择集群')
      return
    }
    try {
      await backupApi.createIncremental(selectedCluster)
      setTimeout(loadData, 2000)
    } catch (error) {
      console.error('Failed to create incremental backup:', error)
    }
  }

  const handleVerify = async (backupId) => {
    try {
      const res = await backupApi.verify(backupId)
      setVerifyResult(res.data)
    } catch (error) {
      console.error('Failed to verify backup:', error)
    }
  }

  const handleOpenRestoreDialog = async (backup) => {
    setSelectedBackup(backup)
    setRestoreData({
      targetClusterId: backup.clusterId,
      pointInTime: '',
      walIndex: ''
    })
    setRestoreTab(0)
    setOpenRestoreDialog(true)

    try {
      const tpRes = await backupApi.listTimePoints(backup.clusterId)
      setTimePoints(tpRes.data || [])
    } catch (error) {
      console.error('Failed to load time points:', error)
    }
  }

  const handleRestore = async () => {
    try {
      if (restoreTab === 2 && restoreData.walIndex) {
        await restoreApi.restoreByWALIndex(
          selectedBackup.id,
          restoreData.targetClusterId,
          parseInt(restoreData.walIndex)
        )
      } else {
        await restoreApi.create(
          selectedBackup.id,
          restoreData.targetClusterId,
          restoreData.pointInTime || null
        )
      }
      setOpenRestoreDialog(false)
    } catch (error) {
      console.error('Failed to restore:', error)
    }
  }

  const handleDryRun = async (backupId) => {
    try {
      const res = await backupApi.dryRun(backupId)
      alert(`恢复演练结果: ${res.data.message}`)
    } catch (error) {
      console.error('Failed to dry run:', error)
    }
  }

  if (loading) {
    return <LinearProgress />
  }

  const formatSize = (bytes) => {
    if (!bytes) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">备份管理</Typography>
        <Box display="flex" alignItems="center">
          <FormControl size="small" sx={{ mr: 2, minWidth: 200 }}>
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
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadData}
            sx={{ mr: 1 }}
          >
            刷新
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleCreateFullBackup}
            sx={{ mr: 1 }}
          >
            完整备份
          </Button>
          <Button
            variant="outlined"
            startIcon={<AddIcon />}
            onClick={handleCreateIncrementalBackup}
          >
            WAL增量备份
          </Button>
        </Box>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>备份ID</TableCell>
              <TableCell>集群名称</TableCell>
              <TableCell>类型</TableCell>
              <TableCell>状态</TableCell>
              <TableCell>大小</TableCell>
              <TableCell>密钥数量</TableCell>
              <TableCell>WAL区间</TableCell>
              <TableCell>版本</TableCell>
              <TableCell>加密</TableCell>
              <TableCell>创建时间</TableCell>
              <TableCell>操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {backups.map((backup) => (
              <TableRow key={backup.id}>
                <TableCell sx={{ maxWidth: 100 }}>
                  <Typography variant="body2" noWrap>
                    {backup.id.substring(0, 8)}...
                  </Typography>
                </TableCell>
                <TableCell>{backup.clusterName}</TableCell>
                <TableCell>
                  <Chip
                    size="small"
                    label={backup.type === 'full' ? '完整备份' : 'WAL增量'}
                    color={backup.type === 'full' ? 'primary' : 'secondary'}
                  />
                </TableCell>
                <TableCell>
                  {backup.status === 'completed' ? (
                    <Chip icon={<CheckCircleIcon />} label="成功" color="success" size="small" />
                  ) : backup.status === 'failed' ? (
                    <Chip icon={<ErrorIcon />} label="失败" color="error" size="small" />
                  ) : (
                    <Chip icon={<PlayArrowIcon />} label="进行中" color="info" size="small" />
                  )}
                </TableCell>
                <TableCell>{formatSize(backup.size)}</TableCell>
                <TableCell>{backup.keysCount || '-'}</TableCell>
                <TableCell>
                  <Tooltip title={`WAL: ${backup.snapshotMeta?.walStartIndex || 0} → ${backup.snapshotMeta?.walEndIndex || '-'}`}>
                    <Typography variant="body2" fontFamily="monospace">
                      {backup.snapshotMeta?.walStartIndex || 0} → {backup.snapshotMeta?.walEndIndex || '-'}
                    </Typography>
                  </Tooltip>
                </TableCell>
                <TableCell>
                  <Chip size="small" label={`v${backup.snapshotMeta?.version || '1.0'}`} variant="outlined" />
                </TableCell>
                <TableCell>
                  {backup.encrypted ? (
                    <Tooltip title={backup.kmsKeyId ? `KMS: ${backup.kmsKeyId}` : '静态密钥加密'}>
                      <Chip
                        icon={<VpnKeyIcon />}
                        label={backup.kmsKeyId ? 'KMS' : '已加密'}
                        size="small"
                        color="primary"
                      />
                    </Tooltip>
                  ) : (
                    <Chip label="未加密" size="small" />
                  )}
                </TableCell>
                <TableCell>
                  {new Date(backup.createdAt).toLocaleString()}
                </TableCell>
                <TableCell>
                  <IconButton size="small" onClick={() => handleVerify(backup.id)} title="校验备份">
                    <VerifyIcon fontSize="small" />
                  </IconButton>
                  <IconButton size="small" onClick={() => handleDryRun(backup.id)} title="恢复演练">
                    <PlayArrowIcon fontSize="small" />
                  </IconButton>
                  <IconButton size="small" onClick={() => handleOpenRestoreDialog(backup)} title="恢复" color="primary">
                    <RestoreIcon fontSize="small" />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
            {backups.length === 0 && (
              <TableRow>
                <TableCell colSpan={11} align="center">
                  <Typography variant="body2" color="text.secondary" py={3}>
                    暂无备份记录
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {verifyResult && (
        <Dialog open={!!verifyResult} onClose={() => setVerifyResult(null)} maxWidth="sm" fullWidth>
          <DialogTitle>备份校验结果</DialogTitle>
          <DialogContent>
            <Box py={2}>
              <Typography variant="body1" gutterBottom>
                状态: {verifyResult.status === 'passed' ? '✅ 通过' : '❌ 失败'}
              </Typography>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                {verifyResult.message}
              </Typography>
              <Typography variant="body2" gutterBottom>
                密钥数量: {verifyResult.keysCount}
              </Typography>
              <Typography variant="body2">
                校验和: {verifyResult.checksum}
              </Typography>
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setVerifyResult(null)}>关闭</Button>
          </DialogActions>
        </Dialog>
      )}

      <Dialog open={openRestoreDialog} onClose={() => setOpenRestoreDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>恢复备份</DialogTitle>
        <DialogContent>
          <Box py={2}>
            <Typography variant="body2" gutterBottom>
              备份: {selectedBackup?.id?.substring(0, 8)}... | 类型: {selectedBackup?.type === 'full' ? '完整备份' : 'WAL增量'}
            </Typography>
            {selectedBackup?.snapshotMeta && (
              <Typography variant="body2" color="text.secondary" gutterBottom>
                版本: {selectedBackup.snapshotMeta.version} | WAL区间: {selectedBackup.snapshotMeta.walStartIndex} → {selectedBackup.snapshotMeta.walEndIndex} | 修订号: {selectedBackup.snapshotMeta.revision}
              </Typography>
            )}

            <FormControl fullWidth margin="normal">
              <InputLabel>目标集群</InputLabel>
              <Select
                value={restoreData.targetClusterId}
                label="目标集群"
                onChange={(e) => setRestoreData({ ...restoreData, targetClusterId: e.target.value })}
              >
                {clusters.map((cluster) => (
                  <MenuItem key={cluster.id} value={cluster.id}>
                    {cluster.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <Box sx={{ borderBottom: 1, borderColor: 'divider', mt: 2 }}>
              <Tabs value={restoreTab} onChange={(e, v) => setRestoreTab(v)}>
                <Tab label="直接恢复" />
                <Tab label="时间点恢复" />
                <Tab label="WAL索引恢复" />
              </Tabs>
            </Box>

            {restoreTab === 0 && (
              <Box mt={2}>
                <Typography variant="body2" color="text.secondary">
                  将直接恢复选中备份的数据到目标集群
                </Typography>
              </Box>
            )}

            {restoreTab === 1 && (
              <Box mt={2}>
                <TextField
                  fullWidth
                  label="恢复时间点"
                  type="datetime-local"
                  value={restoreData.pointInTime}
                  onChange={(e) => setRestoreData({ ...restoreData, pointInTime: e.target.value })}
                  margin="normal"
                  InputLabelProps={{ shrink: true }}
                  helperText="选择一个历史时间点，将重放WAL日志到该时间点"
                />
                {timePoints.length > 0 && (
                  <Box mt={1}>
                    <Typography variant="caption" color="text.secondary">
                      可用恢复时间点:
                    </Typography>
                    {timePoints.map((tp, i) => (
                      <Chip
                        key={i}
                        size="small"
                        label={`${new Date(tp.endTime).toLocaleString()} (WAL:${tp.walEndIndex})`}
                        onClick={() => setRestoreData({ ...restoreData, pointInTime: tp.endTime })}
                        sx={{ mr: 0.5, mt: 0.5 }}
                        icon={<ScheduleIcon />}
                      />
                    ))}
                  </Box>
                )}
              </Box>
            )}

            {restoreTab === 2 && (
              <Box mt={2}>
                <TextField
                  fullWidth
                  label="WAL 索引号"
                  type="number"
                  value={restoreData.walIndex}
                  onChange={(e) => setRestoreData({ ...restoreData, walIndex: e.target.value })}
                  margin="normal"
                  helperText={`WAL区间: ${selectedBackup?.snapshotMeta?.walStartIndex || 0} → ${selectedBackup?.snapshotMeta?.walEndIndex || '-'}`}
                />
                <Typography variant="body2" color="text.secondary" mt={1}>
                  输入WAL索引号，系统将重放WAL日志到该索引位置
                </Typography>
              </Box>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenRestoreDialog(false)}>取消</Button>
          <Button onClick={handleRestore} variant="contained" color="primary">
            开始恢复
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default Backups

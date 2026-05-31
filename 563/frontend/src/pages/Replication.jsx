import React, { useState, useEffect } from 'react'
import {
  Box, Typography, Button, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Paper, IconButton,
  Chip, LinearProgress, Dialog, DialogTitle, DialogContent,
  DialogActions, TextField, MenuItem, Select, FormControl,
  InputLabel, Switch, FormControlLabel, Card, CardContent, Grid,
  Tooltip
} from '@mui/material'
import {
  Add as AddIcon, Refresh as RefreshIcon, Delete as DeleteIcon,
  Edit as EditIcon, Sync as SyncIcon, CheckCircle as CheckCircleIcon,
  Error as ErrorIcon, Schedule as ScheduleIcon, Speed as SpeedIcon,
  CloudSync as CloudSyncIcon
} from '@mui/icons-material'
import { replicationApi, clusterApi } from '../api/client'

function Replication() {
  const [loading, setLoading] = useState(true)
  const [clusters, setClusters] = useState([])
  const [configs, setConfigs] = useState([])
  const [tasks, setTasks] = useState([])
  const [openDialog, setOpenDialog] = useState(false)
  const [editingConfig, setEditingConfig] = useState(null)
  const [formData, setFormData] = useState({
    name: '',
    sourceClusterId: '',
    targetClusterId: '',
    targetStorageType: 's3',
    targetS3Endpoint: '',
    targetS3Bucket: '',
    targetS3Region: '',
    targetS3AccessKey: '',
    targetS3SecretKey: '',
    mode: 'async',
    cronExpr: '0 0 3 * * *',
    bandwidthLimitMb: 0,
    compress: true,
    encrypted: true,
    enabled: true
  })

  useEffect(() => { loadData() }, [])

  const loadData = async () => {
    try {
      const [clusterRes, configRes, taskRes] = await Promise.all([
        clusterApi.list(),
        replicationApi.list(),
        replicationApi.listTasks()
      ])
      setClusters(clusterRes.data || [])
      setConfigs(configRes.data || [])
      setTasks(taskRes.data || [])
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  const handleOpenDialog = (config = null) => {
    if (config) {
      setEditingConfig(config)
      setFormData({
        name: config.name,
        sourceClusterId: config.sourceClusterId,
        targetClusterId: config.targetClusterId,
        targetStorageType: config.targetStorage?.type || 's3',
        targetS3Endpoint: config.targetStorage?.s3Endpoint || '',
        targetS3Bucket: config.targetStorage?.s3Bucket || '',
        targetS3Region: config.targetStorage?.s3Region || '',
        targetS3AccessKey: config.targetStorage?.accessKey || '',
        targetS3SecretKey: config.targetStorage?.secretKey || '',
        mode: config.mode,
        cronExpr: config.cronExpr,
        bandwidthLimitMb: config.bandwidthLimitMb || 0,
        compress: config.compress,
        encrypted: config.encrypted,
        enabled: config.enabled
      })
    } else {
      setEditingConfig(null)
      setFormData({
        name: '', sourceClusterId: clusters[0]?.id || '', targetClusterId: '',
        targetStorageType: 's3', targetS3Endpoint: '', targetS3Bucket: '',
        targetS3Region: '', targetS3AccessKey: '', targetS3SecretKey: '',
        mode: 'async', cronExpr: '0 0 3 * * *', bandwidthLimitMb: 0,
        compress: true, encrypted: true, enabled: true
      })
    }
    setOpenDialog(true)
  }

  const handleSubmit = async () => {
    const payload = {
      name: formData.name,
      sourceClusterId: formData.sourceClusterId,
      targetClusterId: formData.targetClusterId,
      targetStorage: {
        type: formData.targetStorageType,
        s3Endpoint: formData.targetS3Endpoint,
        s3Bucket: formData.targetS3Bucket,
        s3Region: formData.targetS3Region,
        accessKey: formData.targetS3AccessKey,
        secretKey: formData.targetS3SecretKey,
        useSSL: true
      },
      mode: formData.mode,
      cronExpr: formData.cronExpr,
      bandwidthLimitMb: formData.bandwidthLimitMb,
      compress: formData.compress,
      encrypted: formData.encrypted,
      enabled: formData.enabled
    }
    try {
      if (editingConfig) {
        await replicationApi.update(editingConfig.id, payload)
      } else {
        await replicationApi.create(payload)
      }
      setOpenDialog(false)
      loadData()
    } catch (e) { console.error(e) }
  }

  const handleDelete = async (id) => {
    if (window.confirm('确定删除此复制配置？')) {
      try { await replicationApi.delete(id); loadData() } catch (e) { console.error(e) }
    }
  }

  const handleSync = async (id) => {
    try {
      await replicationApi.replicateLatest(id)
      setTimeout(loadData, 2000)
    } catch (e) { console.error(e) }
  }

  const handleCheckHealth = async (id) => {
    try {
      const res = await replicationApi.checkHealth(id)
      alert(res.data.healthy ? '✅ 目标存储健康' : '❌ 目标存储异常: ' + res.data.error)
    } catch (e) { console.error(e) }
  }

  const getClusterName = (id) => clusters.find(c => c.id === id)?.name || id

  if (loading) return <LinearProgress />

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">跨集群复制</Typography>
        <Box>
          <Button variant="outlined" startIcon={<RefreshIcon />} onClick={loadData} sx={{ mr: 1 }}>刷新</Button>
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => handleOpenDialog()}>添加复制</Button>
        </Box>
      </Box>

      <Grid container spacing={3} mb={3}>
        {configs.map((config) => (
          <Grid item xs={12} md={6} key={config.id}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                  <Typography variant="h6">{config.name}</Typography>
                  <Box>
                    <Chip
                      size="small"
                      label={config.mode === 'async' ? '异步' : '同步'}
                      color={config.mode === 'async' ? 'default' : 'primary'}
                    />
                    <Chip
                      size="small"
                      label={config.enabled ? '启用' : '禁用'}
                      color={config.enabled ? 'success' : 'default'}
                      sx={{ ml: 0.5 }}
                    />
                  </Box>
                </Box>

                <Box display="flex" alignItems="center" mb={1}>
                  <CloudSyncIcon fontSize="small" color="primary" sx={{ mr: 1 }} />
                  <Typography variant="body2">
                    {getClusterName(config.sourceClusterId)} → {getClusterName(config.targetClusterId)}
                  </Typography>
                </Box>

                <Box display="flex" alignItems="center" mb={1}>
                  <ScheduleIcon fontSize="small" sx={{ mr: 1 }} />
                  <Typography variant="body2" fontFamily="monospace">
                    {config.cronExpr}
                  </Typography>
                </Box>

                <Box display="flex" gap={1} mb={1}>
                  {config.compress && <Chip size="small" label="压缩" variant="outlined" />}
                  {config.encrypted && <Chip size="small" label="加密" color="primary" variant="outlined" />}
                  <Chip size="small" label={config.targetStorage?.type?.toUpperCase() || 'S3'} variant="outlined" />
                </Box>

                {config.lastSyncAt && (
                  <Typography variant="caption" color="text.secondary">
                    最近同步: {new Date(config.lastSyncAt).toLocaleString()}
                    {config.lastSyncSize ? ` | ${(config.lastSyncSize / 1024 / 1024).toFixed(2)} MB` : ''}
                  </Typography>
                )}

                <Box mt={2} display="flex" gap={1}>
                  <Tooltip title="立即同步">
                    <IconButton size="small" onClick={() => handleSync(config.id)} color="primary">
                      <SyncIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="健康检查">
                    <IconButton size="small" onClick={() => handleCheckHealth(config.id)}>
                      <SpeedIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="编辑">
                    <IconButton size="small" onClick={() => handleOpenDialog(config)}>
                      <EditIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="删除">
                    <IconButton size="small" onClick={() => handleDelete(config.id)} color="error">
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
        {configs.length === 0 && (
          <Grid item xs={12}>
            <Typography variant="body2" color="text.secondary" textAlign="center" py={4}>
              暂无复制配置，点击"添加复制"配置异地容灾
            </Typography>
          </Grid>
        )}
      </Grid>

      <Typography variant="h6" gutterBottom>复制任务记录</Typography>
      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>任务ID</TableCell>
              <TableCell>配置</TableCell>
              <TableCell>备份</TableCell>
              <TableCell>状态</TableCell>
              <TableCell>源大小</TableCell>
              <TableCell>目标大小</TableCell>
              <TableCell>耗时</TableCell>
              <TableCell>时间</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {tasks.map((task) => (
              <TableRow key={task.id}>
                <TableCell><Typography variant="body2" noWrap>{task.id?.substring(0, 8)}...</Typography></TableCell>
                <TableCell>{task.configId?.substring(0, 8)}...</TableCell>
                <TableCell>{task.backupId?.substring(0, 8)}...</TableCell>
                <TableCell>
                  {task.status === 'completed' ? <Chip icon={<CheckCircleIcon />} label="完成" color="success" size="small" />
                    : task.status === 'failed' ? <Chip icon={<ErrorIcon />} label="失败" color="error" size="small" />
                    : <Chip label="进行中" color="info" size="small" />}
                </TableCell>
                <TableCell>{(task.sourceSize / 1024 / 1024).toFixed(2)} MB</TableCell>
                <TableCell>{(task.targetSize / 1024 / 1024).toFixed(2)} MB</TableCell>
                <TableCell>{task.duration ? `${task.duration}s` : '-'}</TableCell>
                <TableCell>{new Date(task.createdAt).toLocaleString()}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editingConfig ? '编辑复制配置' : '添加复制配置'}</DialogTitle>
        <DialogContent>
          <Box pt={1}>
            <TextField fullWidth label="配置名称" value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })} margin="normal" />
            <FormControl fullWidth margin="normal">
              <InputLabel>源集群</InputLabel>
              <Select value={formData.sourceClusterId} label="源集群"
                onChange={(e) => setFormData({ ...formData, sourceClusterId: e.target.value })}>
                {clusters.map((c) => <MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>)}
              </Select>
            </FormControl>
            <FormControl fullWidth margin="normal">
              <InputLabel>目标集群</InputLabel>
              <Select value={formData.targetClusterId} label="目标集群"
                onChange={(e) => setFormData({ ...formData, targetClusterId: e.target.value })}>
                {clusters.map((c) => <MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>)}
              </Select>
            </FormControl>
            <FormControl fullWidth margin="normal">
              <InputLabel>复制模式</InputLabel>
              <Select value={formData.mode} label="复制模式"
                onChange={(e) => setFormData({ ...formData, mode: e.target.value })}>
                <MenuItem value="async">异步（推荐）</MenuItem>
                <MenuItem value="sync">同步</MenuItem>
              </Select>
            </FormControl>
            <TextField fullWidth label="Cron 表达式" value={formData.cronExpr}
              onChange={(e) => setFormData({ ...formData, cronExpr: e.target.value })} margin="normal"
              helperText="默认每天凌晨3点同步" />
            <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>目标存储配置</Typography>
            <FormControl fullWidth margin="normal">
              <InputLabel>存储类型</InputLabel>
              <Select value={formData.targetStorageType} label="存储类型"
                onChange={(e) => setFormData({ ...formData, targetStorageType: e.target.value })}>
                <MenuItem value="s3">S3 兼容</MenuItem>
                <MenuItem value="local">本地存储</MenuItem>
              </Select>
            </FormControl>
            {formData.targetStorageType === 's3' && (
              <>
                <TextField fullWidth label="S3 Endpoint" value={formData.targetS3Endpoint}
                  onChange={(e) => setFormData({ ...formData, targetS3Endpoint: e.target.value })} margin="normal" />
                <TextField fullWidth label="S3 Bucket" value={formData.targetS3Bucket}
                  onChange={(e) => setFormData({ ...formData, targetS3Bucket: e.target.value })} margin="normal" />
                <TextField fullWidth label="S3 Region" value={formData.targetS3Region}
                  onChange={(e) => setFormData({ ...formData, targetS3Region: e.target.value })} margin="normal" />
                <TextField fullWidth label="Access Key" value={formData.targetS3AccessKey}
                  onChange={(e) => setFormData({ ...formData, targetS3AccessKey: e.target.value })} margin="normal" />
                <TextField fullWidth label="Secret Key" type="password" value={formData.targetS3SecretKey}
                  onChange={(e) => setFormData({ ...formData, targetS3SecretKey: e.target.value })} margin="normal" />
              </>
            )}
            <TextField fullWidth label="带宽限制 (MB/s，0=不限)" type="number" value={formData.bandwidthLimitMb}
              onChange={(e) => setFormData({ ...formData, bandwidthLimitMb: parseInt(e.target.value) })} margin="normal" />
            <Box mt={2}>
              <FormControlLabel control={<Switch checked={formData.compress}
                onChange={(e) => setFormData({ ...formData, compress: e.target.checked })} />} label="启用压缩传输" />
            </Box>
            <Box>
              <FormControlLabel control={<Switch checked={formData.encrypted}
                onChange={(e) => setFormData({ ...formData, encrypted: e.target.checked })} />} label="启用加密传输" />
            </Box>
            <Box>
              <FormControlLabel control={<Switch checked={formData.enabled}
                onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })} />} label="启用复制" />
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>取消</Button>
          <Button onClick={handleSubmit} variant="contained">{editingConfig ? '保存' : '添加'}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default Replication

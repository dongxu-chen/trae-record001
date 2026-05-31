import React, { useState, useEffect } from 'react'
import {
  Box, Typography, Button, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Paper, IconButton,
  Chip, LinearProgress, Dialog, DialogTitle, DialogContent,
  DialogActions, TextField, MenuItem, Select, FormControl,
  InputLabel, Switch, FormControlLabel, Card, CardContent, Grid,
  Alert
} from '@mui/material'
import {
  Add as AddIcon, Refresh as RefreshIcon, Delete as DeleteIcon,
  Edit as EditIcon, PlayArrow as PlayArrowIcon,
  CheckCircle as CheckCircleIcon, Error as ErrorIcon,
  Speed as SpeedIcon, FactCheck as FactCheckIcon
} from '@mui/icons-material'
import { drillApi, clusterApi } from '../api/client'

function Drills() {
  const [loading, setLoading] = useState(true)
  const [clusters, setClusters] = useState([])
  const [configs, setConfigs] = useState([])
  const [results, setResults] = useState([])
  const [stats, setStats] = useState(null)
  const [openDialog, setOpenDialog] = useState(false)
  const [editingConfig, setEditingConfig] = useState(null)
  const [formData, setFormData] = useState({
    name: '', clusterId: '', cronExpr: '0 0 4 * * 0',
    targetClusterId: '', autoCleanup: true, cleanupDelayMin: 30,
    verifyChecksum: true, maxDataSizeMb: 0, notifyOnFailure: true, enabled: true
  })

  useEffect(() => { loadData() }, [])

  const loadData = async () => {
    try {
      const [clusterRes, configRes, resultRes, statsRes] = await Promise.all([
        clusterApi.list(),
        drillApi.list(),
        drillApi.listResults(),
        drillApi.getStats()
      ])
      setClusters(clusterRes.data || [])
      setConfigs(configRes.data || [])
      setResults(resultRes.data || [])
      setStats(statsRes.data || null)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  const handleOpenDialog = (config = null) => {
    if (config) {
      setEditingConfig(config)
      setFormData({
        name: config.name, clusterId: config.clusterId,
        cronExpr: config.cronExpr, targetClusterId: config.targetClusterId || '',
        autoCleanup: config.autoCleanup, cleanupDelayMin: config.cleanupDelayMin,
        verifyChecksum: config.verifyChecksum, maxDataSizeMb: config.maxDataSizeMb || 0,
        notifyOnFailure: config.notifyOnFailure, enabled: config.enabled
      })
    } else {
      setEditingConfig(null)
      setFormData({
        name: '', clusterId: clusters[0]?.id || '', cronExpr: '0 0 4 * * 0',
        targetClusterId: '', autoCleanup: true, cleanupDelayMin: 30,
        verifyChecksum: true, maxDataSizeMb: 0, notifyOnFailure: true, enabled: true
      })
    }
    setOpenDialog(true)
  }

  const handleSubmit = async () => {
    try {
      if (editingConfig) {
        await drillApi.update(editingConfig.id, formData)
      } else {
        await drillApi.create(formData)
      }
      setOpenDialog(false)
      loadData()
    } catch (e) { console.error(e) }
  }

  const handleDelete = async (id) => {
    if (window.confirm('确定删除此演练配置？')) {
      try { await drillApi.delete(id); loadData() } catch (e) { console.error(e) }
    }
  }

  const handleRunNow = async (id) => {
    try {
      await drillApi.runNow(id)
      setTimeout(loadData, 3000)
    } catch (e) { console.error(e) }
  }

  const getClusterName = (id) => clusters.find(c => c.id === id)?.name || id

  if (loading) return <LinearProgress />

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">恢复演练</Typography>
        <Box>
          <Button variant="outlined" startIcon={<RefreshIcon />} onClick={loadData} sx={{ mr: 1 }}>刷新</Button>
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => handleOpenDialog()}>添加演练</Button>
        </Box>
      </Box>

      {stats && (
        <Grid container spacing={3} mb={3}>
          <Grid item xs={12} sm={3}>
            <Card><CardContent>
              <Typography variant="body2" color="text.secondary">总演练次数</Typography>
              <Typography variant="h4">{stats.totalDrills}</Typography>
            </CardContent></Card>
          </Grid>
          <Grid item xs={12} sm={3}>
            <Card><CardContent>
              <Typography variant="body2" color="text.secondary">通过次数</Typography>
              <Typography variant="h4" color="success.main">{stats.passedDrills}</Typography>
            </CardContent></Card>
          </Grid>
          <Grid item xs={12} sm={3}>
            <Card><CardContent>
              <Typography variant="body2" color="text.secondary">失败次数</Typography>
              <Typography variant="h4" color="error.main">{stats.failedDrills}</Typography>
            </CardContent></Card>
          </Grid>
          <Grid item xs={12} sm={3}>
            <Card><CardContent>
              <Typography variant="body2" color="text.secondary">通过率</Typography>
              <Typography variant="h4">{stats.passRate?.toFixed(1) || 0}%</Typography>
              <LinearProgress variant="determinate" value={stats.passRate || 0} sx={{ mt: 1 }} />
            </CardContent></Card>
          </Grid>
        </Grid>
      )}

      <Typography variant="h6" gutterBottom>演练配置</Typography>
      <TableContainer component={Paper} sx={{ mb: 3 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>名称</TableCell>
              <TableCell>集群</TableCell>
              <TableCell>Cron</TableCell>
              <TableCell>自动清理</TableCell>
              <TableCell>校验和</TableCell>
              <TableCell>上次结果</TableCell>
              <TableCell>连续失败</TableCell>
              <TableCell>状态</TableCell>
              <TableCell>操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {configs.map((config) => (
              <TableRow key={config.id}>
                <TableCell>{config.name}</TableCell>
                <TableCell>{getClusterName(config.clusterId)}</TableCell>
                <TableCell><Typography variant="body2" fontFamily="monospace">{config.cronExpr}</Typography></TableCell>
                <TableCell>
                  <Chip size="small" label={config.autoCleanup ? `${config.cleanupDelayMin}分钟后` : '手动'} />
                </TableCell>
                <TableCell><Chip size="small" label={config.verifyChecksum ? '是' : '否'} /></TableCell>
                <TableCell>
                  {config.lastResult === 'passed' ? <Chip icon={<CheckCircleIcon />} label="通过" color="success" size="small" />
                    : config.lastResult === 'failed' ? <Chip icon={<ErrorIcon />} label="失败" color="error" size="small" />
                    : <Chip label="未运行" size="small" />}
                </TableCell>
                <TableCell>
                  {config.consecutiveFail > 0 && (
                    <Chip size="small" label={`${config.consecutiveFail}次`} color="error" />
                  )}
                  {(!config.consecutiveFail || config.consecutiveFail === 0) && '-'}
                </TableCell>
                <TableCell><Chip size="small" label={config.enabled ? '启用' : '禁用'} color={config.enabled ? 'success' : 'default'} /></TableCell>
                <TableCell>
                  <IconButton size="small" onClick={() => handleRunNow(config.id)} title="立即执行" color="primary">
                    <PlayArrowIcon fontSize="small" />
                  </IconButton>
                  <IconButton size="small" onClick={() => handleOpenDialog(config)} title="编辑">
                    <EditIcon fontSize="small" />
                  </IconButton>
                  <IconButton size="small" onClick={() => handleDelete(config.id)} title="删除" color="error">
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Typography variant="h6" gutterBottom>演练记录</Typography>
      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>演练ID</TableCell>
              <TableCell>集群</TableCell>
              <TableCell>备份</TableCell>
              <TableCell>备份有效</TableCell>
              <TableCell>恢复成功</TableCell>
              <TableCell>数据完整</TableCell>
              <TableCell>恢复耗时</TableCell>
              <TableCell>清理</TableCell>
              <TableCell>状态</TableCell>
              <TableCell>时间</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {results.map((r) => (
              <TableRow key={r.id}>
                <TableCell><Typography variant="body2" noWrap>{r.id?.substring(0, 8)}...</Typography></TableCell>
                <TableCell>{getClusterName(r.clusterId)}</TableCell>
                <TableCell><Typography variant="body2" noWrap>{r.backupId?.substring(0, 8)}...</Typography></TableCell>
                <TableCell>{r.backupValid ? <CheckCircleIcon color="success" fontSize="small" /> : <ErrorIcon color="error" fontSize="small" />}</TableCell>
                <TableCell>{r.restoreSuccess ? <CheckCircleIcon color="success" fontSize="small" /> : <ErrorIcon color="error" fontSize="small" />}</TableCell>
                <TableCell>{r.dataIntegrity ? <CheckCircleIcon color="success" fontSize="small" /> : <ErrorIcon color="error" fontSize="small" />}</TableCell>
                <TableCell>{r.restoreDuration ? `${r.restoreDuration}ms` : '-'}</TableCell>
                <TableCell>{r.cleanupDone ? '✓' : '-'}</TableCell>
                <TableCell>
                  {r.status === 'completed' && r.dataIntegrity ? <Chip label="通过" color="success" size="small" />
                    : r.status === 'completed' ? <Chip label="失败" color="error" size="small" />
                    : r.status === 'running' ? <Chip label="运行中" color="info" size="small" />
                    : <Chip label={r.status} size="small" />}
                </TableCell>
                <TableCell>{new Date(r.createdAt).toLocaleString()}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {results.length === 0 && (
        <Alert severity="info" sx={{ mt: 2 }}>
          暂无演练记录。建议配置定期自动演练，确保备份数据的可用性。
        </Alert>
      )}

      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editingConfig ? '编辑演练配置' : '添加演练配置'}</DialogTitle>
        <DialogContent>
          <Box pt={1}>
            <TextField fullWidth label="演练名称" value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })} margin="normal" />
            <FormControl fullWidth margin="normal">
              <InputLabel>源集群</InputLabel>
              <Select value={formData.clusterId} label="源集群"
                onChange={(e) => setFormData({ ...formData, clusterId: e.target.value })}>
                {clusters.map((c) => <MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>)}
              </Select>
            </FormControl>
            <TextField fullWidth label="Cron 表达式" value={formData.cronExpr}
              onChange={(e) => setFormData({ ...formData, cronExpr: e.target.value })} margin="normal"
              helperText="默认每周日凌晨4点执行演练" />
            <TextField fullWidth label="最大数据量限制 (MB，0=不限)" type="number" value={formData.maxDataSizeMb}
              onChange={(e) => setFormData({ ...formData, maxDataSizeMb: parseInt(e.target.value) })} margin="normal" />
            <Box mt={2}>
              <FormControlLabel control={<Switch checked={formData.autoCleanup}
                onChange={(e) => setFormData({ ...formData, autoCleanup: e.target.checked })} />} label="自动清理演练数据" />
            </Box>
            {formData.autoCleanup && (
              <TextField fullWidth label="清理延迟 (分钟)" type="number" value={formData.cleanupDelayMin}
                onChange={(e) => setFormData({ ...formData, cleanupDelayMin: parseInt(e.target.value) })} margin="normal" />
            )}
            <Box>
              <FormControlLabel control={<Switch checked={formData.verifyChecksum}
                onChange={(e) => setFormData({ ...formData, verifyChecksum: e.target.checked })} />} label="校验备份数据和校验和" />
            </Box>
            <Box>
              <FormControlLabel control={<Switch checked={formData.notifyOnFailure}
                onChange={(e) => setFormData({ ...formData, notifyOnFailure: e.target.checked })} />} label="失败时发送通知" />
            </Box>
            <Box>
              <FormControlLabel control={<Switch checked={formData.enabled}
                onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })} />} label="启用自动演练" />
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

export default Drills

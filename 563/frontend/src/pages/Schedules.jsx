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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Switch,
  FormControlLabel
} from '@mui/material'
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material'
import { clusterApi, scheduleApi } from '../api/client'

function Schedules() {
  const [loading, setLoading] = useState(true)
  const [clusters, setClusters] = useState([])
  const [schedules, setSchedules] = useState([])
  const [openDialog, setOpenDialog] = useState(false)
  const [editingSchedule, setEditingSchedule] = useState(null)
  const [formData, setFormData] = useState({
    clusterId: '',
    name: '',
    cronExpr: '0 0 2 * * *',
    backupType: 'full',
    retentionDays: 30,
    encrypted: false,
    kmsKeyId: '',
    enabled: true
  })

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [clusterRes, scheduleRes] = await Promise.all([
        clusterApi.list(),
        scheduleApi.list()
      ])
      
      setClusters(clusterRes.data || [])
      setSchedules(scheduleRes.data || [])
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleOpenDialog = (schedule = null) => {
    if (schedule) {
      setEditingSchedule(schedule)
      setFormData({
        clusterId: schedule.clusterId,
        name: schedule.name,
        cronExpr: schedule.cronExpr,
        backupType: schedule.backupType,
        retentionDays: schedule.retentionDays,
        encrypted: schedule.encrypted,
        kmsKeyId: schedule.kmsKeyId || '',
        enabled: schedule.enabled
      })
    } else {
      setEditingSchedule(null)
      setFormData({
        clusterId: clusters[0]?.id || '',
        name: '',
        cronExpr: '0 0 2 * * *',
        backupType: 'full',
        retentionDays: 30,
        encrypted: false,
        kmsKeyId: '',
        enabled: true
      })
    }
    setOpenDialog(true)
  }

  const handleCloseDialog = () => {
    setOpenDialog(false)
    setEditingSchedule(null)
  }

  const handleSubmit = async () => {
    try {
      if (editingSchedule) {
        await scheduleApi.update(editingSchedule.id, formData)
      } else {
        await scheduleApi.create(formData)
      }
      
      handleCloseDialog()
      loadData()
    } catch (error) {
      console.error('Failed to save schedule:', error)
    }
  }

  const handleDelete = async (scheduleId) => {
    if (window.confirm('确定要删除这个定时任务吗？')) {
      try {
        await scheduleApi.delete(scheduleId)
        loadData()
      } catch (error) {
        console.error('Failed to delete schedule:', error)
      }
    }
  }

  if (loading) {
    return <LinearProgress />
  }

  const getClusterName = (clusterId) => {
    const cluster = clusters.find(c => c.id === clusterId)
    return cluster?.name || clusterId
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">定时任务</Typography>
        <Box>
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
            onClick={() => handleOpenDialog()}
          >
            添加任务
          </Button>
        </Box>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>任务名称</TableCell>
              <TableCell>集群</TableCell>
              <TableCell>备份类型</TableCell>
              <TableCell>Cron 表达式</TableCell>
              <TableCell>保留天数</TableCell>
              <TableCell>加密</TableCell>
              <TableCell>状态</TableCell>
              <TableCell>创建时间</TableCell>
              <TableCell>操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {schedules.map((schedule) => (
              <TableRow key={schedule.id}>
                <TableCell>{schedule.name}</TableCell>
                <TableCell>{getClusterName(schedule.clusterId)}</TableCell>
                <TableCell>
                  <Chip
                    size="small"
                    label={schedule.backupType === 'full' ? '完整备份' : '增量备份'}
                    color={schedule.backupType === 'full' ? 'primary' : 'default'}
                  />
                </TableCell>
                <TableCell>
                  <Typography variant="body2" fontFamily="monospace">
                    {schedule.cronExpr}
                  </Typography>
                </TableCell>
                <TableCell>{schedule.retentionDays} 天</TableCell>
                <TableCell>
                  {schedule.encrypted ? (
                    <Chip label="加密" size="small" color="primary" />
                  ) : (
                    <Chip label="不加密" size="small" />
                  )}
                </TableCell>
                <TableCell>
                  {schedule.enabled ? (
                    <Chip label="启用" size="small" color="success" />
                  ) : (
                    <Chip label="禁用" size="small" />
                  )}
                </TableCell>
                <TableCell>
                  {new Date(schedule.createdAt).toLocaleString()}
                </TableCell>
                <TableCell>
                  <IconButton
                    size="small"
                    onClick={() => handleOpenDialog(schedule)}
                    title="编辑"
                  >
                    <EditIcon fontSize="small" />
                  </IconButton>
                  <IconButton
                    size="small"
                    onClick={() => handleDelete(schedule.id)}
                    title="删除"
                    color="error"
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
            {schedules.length === 0 && (
              <TableRow>
                <TableCell colSpan={9} align="center">
                  <Typography variant="body2" color="text.secondary" py={3}>
                    暂无定时任务，请点击"添加任务"按钮添加
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingSchedule ? '编辑定时任务' : '添加定时任务'}
        </DialogTitle>
        <DialogContent>
          <Box py={1}>
            <TextField
              fullWidth
              label="任务名称"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              margin="normal"
            />
            <FormControl fullWidth margin="normal">
              <InputLabel>选择集群</InputLabel>
              <Select
                value={formData.clusterId}
                label="选择集群"
                onChange={(e) => setFormData({ ...formData, clusterId: e.target.value })}
              >
                {clusters.map((cluster) => (
                  <MenuItem key={cluster.id} value={cluster.id}>
                    {cluster.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl fullWidth margin="normal">
              <InputLabel>备份类型</InputLabel>
              <Select
                value={formData.backupType}
                label="备份类型"
                onChange={(e) => setFormData({ ...formData, backupType: e.target.value })}
              >
                <MenuItem value="full">完整备份</MenuItem>
                <MenuItem value="incremental">增量备份</MenuItem>
              </Select>
            </FormControl>
            <TextField
              fullWidth
              label="Cron 表达式"
              value={formData.cronExpr}
              onChange={(e) => setFormData({ ...formData, cronExpr: e.target.value })}
              margin="normal"
              helperText="例如: 0 0 2 * * * 表示每天凌晨2点执行"
            />
            <TextField
              fullWidth
              label="保留天数"
              type="number"
              value={formData.retentionDays}
              onChange={(e) => setFormData({ ...formData, retentionDays: parseInt(e.target.value) })}
              margin="normal"
            />
            <Box mt={2}>
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.encrypted}
                    onChange={(e) => setFormData({ ...formData, encrypted: e.target.checked })}
                  />
                }
                label="启用备份加密"
              />
            </Box>
            {formData.encrypted && (
              <TextField
                fullWidth
                label="KMS 密钥ID（可选）"
                value={formData.kmsKeyId}
                onChange={(e) => setFormData({ ...formData, kmsKeyId: e.target.value })}
                margin="normal"
                helperText="留空使用默认KMS密钥，或指定特定密钥ID"
              />
            )}
            <Box>
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.enabled}
                    onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
                  />
                }
                label="启用任务"
              />
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>取消</Button>
          <Button onClick={handleSubmit} variant="contained">
            {editingSchedule ? '保存' : '添加'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default Schedules

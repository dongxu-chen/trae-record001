import React, { useState, useEffect } from 'react';
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
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Grid,
  CircularProgress,
  Alert,
  Tooltip,
  Switch,
  FormControlLabel,
  Divider,
} from '@mui/material';
import {
  Add as AddIcon,
  PlayArrow as StartIcon,
  Stop as StopIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Language as LanguageIcon,
  Shield as ShieldIcon,
} from '@mui/icons-material';
import { faultApi, serviceApi, rollbackApi } from '../services/api';
import ServiceTopologySelector from '../components/ServiceTopologySelector';

const FaultTypeLabels = {
  delay: '延迟故障',
  abort: '中断故障',
  error: '错误故障',
};

const StatusLabels = {
  pending: '待执行',
  running: '运行中',
  completed: '已完成',
  failed: '失败',
};

const StatusColors = {
  pending: 'default',
  running: 'warning',
  completed: 'success',
  failed: 'error',
};

function Faults() {
  const [faults, setFaults] = useState([]);
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [topologyOpen, setTopologyOpen] = useState(false);
  const [editingFault, setEditingFault] = useState(null);
  const [defaultRollbackConfig, setDefaultRollbackConfig] = useState({
    enabled: true,
    max_latency_threshold_ms: 5000,
    max_error_rate_threshold_pct: 20,
    min_request_count: 10,
    consecutive_failures_trigger: 3,
    check_interval_seconds: 10,
  });
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    type: 'delay',
    target_service: '',
    target_port: 80,
    percentage: 100,
    duration: 60,
    delay_config: { fixed_delay_ms: 1000 },
    abort_config: { http_status: 500 },
    error_config: { error_rate: 0.1 },
    rollback_config: {
      enabled: true,
      max_latency_threshold_ms: 5000,
      max_error_rate_threshold_pct: 20,
      min_request_count: 10,
      consecutive_failures_trigger: 3,
      check_interval_seconds: 10,
    },
  });

  useEffect(() => {
    loadData();
    loadDefaultRollbackConfig();
  }, []);

  const loadDefaultRollbackConfig = async () => {
    try {
      const config = await rollbackApi.getDefaultConfig();
      setDefaultRollbackConfig(config);
    } catch (error) {
      console.error('Failed to load default rollback config:', error);
    }
  };

  const loadData = async () => {
    try {
      setLoading(true);
      const [faultsData, servicesData] = await Promise.all([
        faultApi.list(),
        serviceApi.list().catch(() => []),
      ]);
      setFaults(faultsData);
      setServices(servicesData);
    } catch (err) {
      setError('加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (fault = null) => {
    if (fault) {
      setEditingFault(fault);
      const defaultDelayConfig = {
        distribution: 'fixed',
        fixed_delay_ms: 1000,
        mean_delay_ms: 1000,
        std_dev_ms: 300,
        min_delay_ms: 100,
        max_delay_ms: 5000,
      };
      setFormData({
        name: fault.name,
        description: fault.description,
        type: fault.type,
        target_service: fault.target_service,
        target_port: fault.target_port || 80,
        percentage: fault.percentage,
        duration: fault.duration || 60,
        delay_config: fault.delay_config || defaultDelayConfig,
        abort_config: fault.abort_config || { http_status: 500 },
        error_config: fault.error_config || { error_rate: 0.1 },
        rollback_config: fault.rollback_config || defaultRollbackConfig,
      });
    } else {
      setEditingFault(null);
      setFormData({
        name: '',
        description: '',
        type: 'delay',
        target_service: '',
        target_port: 80,
        percentage: 100,
        duration: 60,
        delay_config: {
          distribution: 'fixed',
          fixed_delay_ms: 1000,
          mean_delay_ms: 1000,
          std_dev_ms: 300,
          min_delay_ms: 100,
          max_delay_ms: 5000,
        },
        abort_config: { http_status: 500 },
        error_config: { error_rate: 0.1 },
        rollback_config: { ...defaultRollbackConfig },
      });
    }
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingFault(null);
  };

  const handleSubmit = async () => {
    try {
      if (editingFault) {
        await faultApi.update(editingFault.id, formData);
      } else {
        await faultApi.create(formData);
      }
      handleCloseDialog();
      loadData();
    } catch (err) {
      setError('保存失败');
    }
  };

  const handleStart = async (id) => {
    try {
      await faultApi.start(id);
      loadData();
    } catch (err) {
      setError('启动故障失败');
    }
  };

  const handleStop = async (id) => {
    try {
      await faultApi.stop(id);
      loadData();
    } catch (err) {
      setError('停止故障失败');
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('确定要删除此故障吗？')) {
      try {
        await faultApi.delete(id);
        loadData();
      } catch (err) {
        setError('删除失败');
      }
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">故障管理</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => handleOpenDialog()}
        >
          创建故障
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>名称</TableCell>
              <TableCell>类型</TableCell>
              <TableCell>目标服务</TableCell>
              <TableCell>影响比例</TableCell>
              <TableCell>状态</TableCell>
              <TableCell>回滚保护</TableCell>
              <TableCell>创建时间</TableCell>
              <TableCell>操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {faults.map((fault) => (
              <TableRow key={fault.id}>
                <TableCell>
                  <Typography variant="body2" fontWeight="bold">
                    {fault.name}
                  </Typography>
                  {fault.description && (
                    <Typography variant="caption" color="text.secondary">
                      {fault.description}
                    </Typography>
                  )}
                </TableCell>
                <TableCell>
                  <Chip label={FaultTypeLabels[fault.type]} size="small" />
                </TableCell>
                <TableCell>{fault.target_service}</TableCell>
                <TableCell>{fault.percentage}%</TableCell>
                <TableCell>
                  <Chip
                    label={StatusLabels[fault.status]}
                    color={StatusColors[fault.status]}
                    size="small"
                  />
                </TableCell>
                <TableCell>
                  {fault.rollback_config?.enabled ? (
                    <Chip
                      label="已启用"
                      color="success"
                      size="small"
                      icon={<ShieldIcon fontSize="small" />}
                    />
                  ) : (
                    <Chip label="未启用" color="default" size="small" />
                  )}
                </TableCell>
                <TableCell>
                  {new Date(fault.created_at).toLocaleString()}
                </TableCell>
                <TableCell>
                  <Tooltip title="编辑">
                    <IconButton
                      size="small"
                      onClick={() => handleOpenDialog(fault)}
                      disabled={fault.status === 'running'}
                    >
                      <EditIcon />
                    </IconButton>
                  </Tooltip>
                  {fault.status === 'running' ? (
                    <Tooltip title="停止">
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => handleStop(fault.id)}
                      >
                        <StopIcon />
                      </IconButton>
                    </Tooltip>
                  ) : (
                    <Tooltip title="启动">
                      <IconButton
                        size="small"
                        color="success"
                        onClick={() => handleStart(fault.id)}
                        disabled={fault.status === 'completed'}
                      >
                        <StartIcon />
                      </IconButton>
                    </Tooltip>
                  )}
                  <Tooltip title="删除">
                    <IconButton
                      size="small"
                      onClick={() => handleDelete(fault.id)}
                      disabled={fault.status === 'running'}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
            {faults.length === 0 && (
              <TableRow>
                <TableCell colSpan={8} align="center">
                  <Typography color="text.secondary">暂无故障记录</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingFault ? '编辑故障' : '创建故障'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="故障名称"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth required>
                <InputLabel>故障类型</InputLabel>
                <Select
                  value={formData.type}
                  onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                  label="故障类型"
                >
                  <MenuItem value="delay">延迟故障</MenuItem>
                  <MenuItem value="abort">中断故障</MenuItem>
                  <MenuItem value="error">错误故障</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="描述"
                multiline
                rows={2}
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth required>
                <InputLabel>目标服务</InputLabel>
                <Select
                  value={formData.target_service}
                  onChange={(e) => setFormData({ ...formData, target_service: e.target.value })}
                  label="目标服务"
                  endAdornment={
                    <IconButton
                      size="small"
                      sx={{ mr: 2 }}
                      onClick={() => setTopologyOpen(true)}
                      title="从拓扑图选择"
                    >
                      <LanguageIcon fontSize="small" />
                    </IconButton>
                  }
                >
                  {services.map((s) => (
                    <MenuItem key={s} value={s}>
                      {s}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="目标端口"
                type="number"
                value={formData.target_port}
                onChange={(e) => setFormData({ ...formData, target_port: parseInt(e.target.value) })}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="影响比例 (%)"
                type="number"
                inputProps={{ min: 1, max: 100 }}
                value={formData.percentage}
                onChange={(e) => setFormData({ ...formData, percentage: parseInt(e.target.value) })}
                required
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="持续时间 (秒)"
                type="number"
                value={formData.duration}
                onChange={(e) => setFormData({ ...formData, duration: parseInt(e.target.value) })}
              />
            </Grid>

            {formData.type === 'delay' && (
              <>
                <Grid item xs={12}>
                  <FormControl fullWidth>
                    <InputLabel>延迟分布模式</InputLabel>
                    <Select
                      value={formData.delay_config.distribution || 'fixed'}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          delay_config: {
                            ...formData.delay_config,
                            distribution: e.target.value,
                          },
                        })
                      }
                      label="延迟分布模式"
                    >
                      <MenuItem value="fixed">
                        <Box display="flex" alignItems="center" gap={2}>
                          <Box
                            sx={{
                              width: 60,
                              height: 30,
                              backgroundColor: '#e3f2fd',
                              borderRadius: 1,
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                            }}
                          >
                            <Box sx={{ width: 40, height: 4, backgroundColor: '#1976d2' }} />
                          </Box>
                          <Box>
                            <Typography variant="body2">固定延迟</Typography>
                            <Typography variant="caption" color="text.secondary">
                              所有请求使用相同延迟
                            </Typography>
                          </Box>
                        </Box>
                      </MenuItem>
                      <MenuItem value="normal">
                        <Box display="flex" alignItems="center" gap={2}>
                          <Box
                            sx={{
                              width: 60,
                              height: 30,
                              backgroundColor: '#e8f5e9',
                              borderRadius: 1,
                              display: 'flex',
                              alignItems: 'flex-end',
                              justifyContent: 'center',
                              gap: 0.5,
                              pb: 0.5,
                            }}
                          >
                            <Box sx={{ width: 4, height: 8, backgroundColor: '#4caf50' }} />
                            <Box sx={{ width: 4, height: 16, backgroundColor: '#4caf50' }} />
                            <Box sx={{ width: 4, height: 22, backgroundColor: '#4caf50' }} />
                            <Box sx={{ width: 4, height: 16, backgroundColor: '#4caf50' }} />
                            <Box sx={{ width: 4, height: 8, backgroundColor: '#4caf50' }} />
                          </Box>
                          <Box>
                            <Typography variant="body2">正态分布</Typography>
                            <Typography variant="caption" color="text.secondary">
                              模拟真实网络波动，延迟围绕均值分布
                            </Typography>
                          </Box>
                        </Box>
                      </MenuItem>
                      <MenuItem value="exponential">
                        <Box display="flex" alignItems="center" gap={2}>
                          <Box
                            sx={{
                              width: 60,
                              height: 30,
                              backgroundColor: '#fff3e0',
                              borderRadius: 1,
                              display: 'flex',
                              alignItems: 'flex-end',
                              justifyContent: 'center',
                              gap: 0.5,
                              pb: 0.5,
                            }}
                          >
                            <Box sx={{ width: 4, height: 22, backgroundColor: '#ff9800' }} />
                            <Box sx={{ width: 4, height: 14, backgroundColor: '#ff9800' }} />
                            <Box sx={{ width: 4, height: 10, backgroundColor: '#ff9800' }} />
                            <Box sx={{ width: 4, height: 6, backgroundColor: '#ff9800' }} />
                            <Box sx={{ width: 4, height: 4, backgroundColor: '#ff9800' }} />
                          </Box>
                          <Box>
                            <Typography variant="body2">指数分布</Typography>
                            <Typography variant="caption" color="text.secondary">
                              模拟长尾延迟，大部分延迟较小，少数延迟很大
                            </Typography>
                          </Box>
                        </Box>
                      </MenuItem>
                    </Select>
                  </FormControl>
                </Grid>

                {formData.delay_config.distribution === 'fixed' && (
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="固定延迟 (毫秒)"
                      type="number"
                      value={formData.delay_config.fixed_delay_ms}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          delay_config: {
                            ...formData.delay_config,
                            fixed_delay_ms: parseInt(e.target.value) || 0,
                          },
                        })
                      }
                    />
                  </Grid>
                )}

                {formData.delay_config.distribution === 'normal' && (
                  <>
                    <Grid item xs={12} sm={6}>
                      <TextField
                        fullWidth
                        label="平均延迟 (毫秒)"
                        type="number"
                        value={formData.delay_config.mean_delay_ms}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            delay_config: {
                              ...formData.delay_config,
                              mean_delay_ms: parseInt(e.target.value) || 0,
                            },
                          })
                        }
                      />
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <TextField
                        fullWidth
                        label="标准差 (毫秒)"
                        type="number"
                        value={formData.delay_config.std_dev_ms}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            delay_config: {
                              ...formData.delay_config,
                              std_dev_ms: parseInt(e.target.value) || 0,
                            },
                          })
                        }
                      />
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <TextField
                        fullWidth
                        label="最小延迟 (毫秒)"
                        type="number"
                        value={formData.delay_config.min_delay_ms}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            delay_config: {
                              ...formData.delay_config,
                              min_delay_ms: parseInt(e.target.value) || 0,
                            },
                          })
                        }
                      />
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <TextField
                        fullWidth
                        label="最大延迟 (毫秒)"
                        type="number"
                        value={formData.delay_config.max_delay_ms}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            delay_config: {
                              ...formData.delay_config,
                              max_delay_ms: parseInt(e.target.value) || 0,
                            },
                          })
                        }
                      />
                    </Grid>
                  </>
                )}

                {formData.delay_config.distribution === 'exponential' && (
                  <>
                    <Grid item xs={12} sm={6}>
                      <TextField
                        fullWidth
                        label="平均延迟 (毫秒)"
                        type="number"
                        value={formData.delay_config.mean_delay_ms}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            delay_config: {
                              ...formData.delay_config,
                              mean_delay_ms: parseInt(e.target.value) || 0,
                            },
                          })
                        }
                      />
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <TextField
                        fullWidth
                        label="最小延迟 (毫秒)"
                        type="number"
                        value={formData.delay_config.min_delay_ms}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            delay_config: {
                              ...formData.delay_config,
                              min_delay_ms: parseInt(e.target.value) || 0,
                            },
                          })
                        }
                      />
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <TextField
                        fullWidth
                        label="最大延迟 (毫秒)"
                        type="number"
                        value={formData.delay_config.max_delay_ms}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            delay_config: {
                              ...formData.delay_config,
                              max_delay_ms: parseInt(e.target.value) || 0,
                            },
                          })
                        }
                      />
                    </Grid>
                  </>
                )}
              </>
            )}

            {formData.type === 'abort' && (
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="HTTP 状态码"
                  type="number"
                  value={formData.abort_config.http_status}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      abort_config: { http_status: parseInt(e.target.value) },
                    })
                  }
                />
              </Grid>
            )}

            {formData.type === 'error' && (
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="错误率 (0-1)"
                  type="number"
                  inputProps={{ step: 0.1, min: 0, max: 1 }}
                  value={formData.error_config.error_rate}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      error_config: { error_rate: parseFloat(e.target.value) },
                    })
                  }
                />
              </Grid>
            )}

            <Grid item xs={12}>
              <Divider sx={{ my: 2 }} />
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <ShieldIcon sx={{ mr: 1, color: 'primary.main' }} />
                <Typography variant="h6">智能回滚保护</Typography>
              </Box>
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.rollback_config?.enabled ?? true}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        rollback_config: {
                          ...formData.rollback_config,
                          enabled: e.target.checked,
                        },
                      })
                    }
                  />
                }
                label="启用智能回滚（系统异常时自动停止故障注入）"
              />

              {formData.rollback_config?.enabled && (
                <Grid container spacing={2} sx={{ mt: 1 }}>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="最大延迟阈值 (毫秒)"
                      type="number"
                      value={formData.rollback_config?.max_latency_threshold_ms ?? 5000}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          rollback_config: {
                            ...formData.rollback_config,
                            max_latency_threshold_ms: parseInt(e.target.value) || 5000,
                          },
                        })
                      }
                      helperText="P99延迟超过此值触发回滚"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="最大错误率阈值 (%)"
                      type="number"
                      inputProps={{ min: 0, max: 100 }}
                      value={formData.rollback_config?.max_error_rate_threshold_pct ?? 20}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          rollback_config: {
                            ...formData.rollback_config,
                            max_error_rate_threshold_pct: parseInt(e.target.value) || 20,
                          },
                        })
                      }
                      helperText="错误率超过此值触发回滚"
                    />
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <TextField
                      fullWidth
                      label="最小请求数"
                      type="number"
                      inputProps={{ min: 1 }}
                      value={formData.rollback_config?.min_request_count ?? 10}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          rollback_config: {
                            ...formData.rollback_config,
                            min_request_count: parseInt(e.target.value) || 10,
                          },
                        })
                      }
                      helperText="检测所需最小样本量"
                    />
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <TextField
                      fullWidth
                      label="连续失败次数"
                      type="number"
                      inputProps={{ min: 1 }}
                      value={formData.rollback_config?.consecutive_failures_trigger ?? 3}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          rollback_config: {
                            ...formData.rollback_config,
                            consecutive_failures_trigger: parseInt(e.target.value) || 3,
                          },
                        })
                      }
                      helperText="连续失败次数触发回滚"
                    />
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <TextField
                      fullWidth
                      label="检测间隔 (秒)"
                      type="number"
                      inputProps={{ min: 5, max: 300 }}
                      value={formData.rollback_config?.check_interval_seconds ?? 10}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          rollback_config: {
                            ...formData.rollback_config,
                            check_interval_seconds: parseInt(e.target.value) || 10,
                          },
                        })
                      }
                      helperText="指标检测频率"
                    />
                  </Grid>
                </Grid>
              )}
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>取消</Button>
          <Button onClick={handleSubmit} variant="contained">
            {editingFault ? '保存' : '创建'}
          </Button>
        </DialogActions>
      </Dialog>

      <ServiceTopologySelector
        open={topologyOpen}
        onClose={() => setTopologyOpen(false)}
        selectedService={formData.target_service}
        onSelect={(selection) => {
          setFormData({
            ...formData,
            target_service: selection.service,
            scope: {
              ...formData.scope,
              labels: selection.version
                ? { ...formData.scope?.labels, version: selection.version }
                : formData.scope?.labels,
            },
          });
        }}
      />
    </Box>
  );
}

export default Faults;

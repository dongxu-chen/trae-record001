import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Switch,
  FormControlLabel,
  Grid,
  Box,
} from '@mui/material';
import { Add as AddIcon, Edit as EditIcon, Delete as DeleteIcon } from '@mui/icons-material';
import { getStrategies, setStrategy, deleteStrategy } from '../services/api';

function Strategies() {
  const [strategies, setStrategies] = useState({});
  const [openDialog, setOpenDialog] = useState(false);
  const [editStrategy, setEditStrategy] = useState(null);

  const fetchStrategies = async () => {
    try {
      const res = await getStrategies();
      setStrategies(res.data.strategies || {});
    } catch (error) {
      console.error('Failed to fetch strategies:', error);
    }
  };

  useEffect(() => {
    fetchStrategies();
  }, []);

  const handleOpenAdd = () => {
    setEditStrategy({
      TopicName: '',
      AutoScale: {
        Enabled: true,
        MinConsumers: 1,
        MaxConsumers: 20,
        ScaleUpThreshold: 10000,
        ScaleDownThreshold: 1000,
      },
      Partition: {
        Enabled: true,
        MinPartitions: 1,
        MaxPartitions: 32,
        ScaleUpThreshold: 50000,
        ScaleDownThreshold: 5000,
      },
      RateLimit: {
        Enabled: true,
        MaxRate: 1000,
        BacklogThreshold: 100000,
        RecoveryThreshold: 10000,
        TopicBacklogThreshold: 50000,
      },
      Prediction: {
        Enabled: true,
        AlertThreshold: 100000,
      },
      DeadLetter: {
        Enabled: true,
        MaxRedeliveries: 3,
        DLQTopic: '',
        RetryTopic: '',
      },
      Replay: {
        Enabled: true,
        MaxMessages: 1000,
        TargetTopic: '',
      },
      DelayProcess: {
        Enabled: true,
        BacklogThreshold: 50000,
        RecoveryThreshold: 25000,
        CoreSubscriptions: [],
        NonCoreSubscriptions: [],
      },
      Priority: 0,
    });
    setOpenDialog(true);
  };

  const handleOpenEdit = (topic) => {
    setEditStrategy(JSON.parse(JSON.stringify(strategies[topic])));
    setOpenDialog(true);
  };

  const handleSave = async () => {
    try {
      await setStrategy(editStrategy);
      setOpenDialog(false);
      fetchStrategies();
    } catch (error) {
      console.error('Failed to save strategy:', error);
    }
  };

  const handleDelete = async (topic) => {
    if (topic === 'default') return;
    try {
      await deleteStrategy(topic);
      fetchStrategies();
    } catch (error) {
      console.error('Failed to delete strategy:', error);
    }
  };

  return (
    <div>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">策略配置</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={handleOpenAdd}>
          添加策略
        </Button>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Topic</TableCell>
              <TableCell align="center">自动伸缩</TableCell>
              <TableCell align="center">限流</TableCell>
              <TableCell align="center">死信</TableCell>
              <TableCell align="center">重放</TableCell>
              <TableCell align="center">延迟降级</TableCell>
              <TableCell align="center">操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {Object.keys(strategies).map((topic) => {
              const s = strategies[topic];
              return (
                <TableRow key={topic}>
                  <TableCell component="th" scope="row">
                    {topic}
                    {topic === 'default' && (
                      <Typography variant="caption" color="textSecondary" display="block">(默认策略)</Typography>
                    )}
                  </TableCell>
                  <TableCell align="center"><Switch checked={s.AutoScale?.Enabled} disabled size="small" /></TableCell>
                  <TableCell align="center"><Switch checked={s.RateLimit?.Enabled} disabled size="small" /></TableCell>
                  <TableCell align="center"><Switch checked={s.DeadLetter?.Enabled} disabled size="small" /></TableCell>
                  <TableCell align="center"><Switch checked={s.Replay?.Enabled} disabled size="small" /></TableCell>
                  <TableCell align="center"><Switch checked={s.DelayProcess?.Enabled} disabled size="small" /></TableCell>
                  <TableCell align="center">
                    <Button size="small" startIcon={<EditIcon />} onClick={() => handleOpenEdit(topic)}>编辑</Button>
                    {topic !== 'default' && (
                      <Button size="small" color="error" startIcon={<DeleteIcon />} onClick={() => handleDelete(topic)}>删除</Button>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog
        open={openDialog}
        onClose={() => setOpenDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {editStrategy?.TopicName ? '编辑策略' : '添加策略'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                label="Topic 名称"
                fullWidth
                value={editStrategy?.TopicName || ''}
                onChange={(e) =>
                  setEditStrategy({ ...editStrategy, TopicName: e.target.value })
                }
                disabled={editStrategy?.TopicName === 'default'}
              />
            </Grid>

            <Grid item xs={12}>
              <Card variant="outlined">
                <CardContent>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={editStrategy?.AutoScale?.Enabled}
                        onChange={(e) =>
                          setEditStrategy({
                            ...editStrategy,
                            AutoScale: { ...editStrategy.AutoScale, Enabled: e.target.checked },
                          })
                        }
                      />
                    }
                    label="自动伸缩 (消费者)"
                  />
                  <Grid container spacing={2} sx={{ mt: 1 }}>
                    <Grid item xs={6}>
                      <TextField
                        label="最小消费者数"
                        type="number"
                        fullWidth
                        size="small"
                        value={editStrategy?.AutoScale?.MinConsumers}
                        onChange={(e) =>
                          setEditStrategy({
                            ...editStrategy,
                            AutoScale: {
                              ...editStrategy.AutoScale,
                              MinConsumers: parseInt(e.target.value),
                            },
                          })
                        }
                      />
                    </Grid>
                    <Grid item xs={6}>
                      <TextField
                        label="最大消费者数"
                        type="number"
                        fullWidth
                        size="small"
                        value={editStrategy?.AutoScale?.MaxConsumers}
                        onChange={(e) =>
                          setEditStrategy({
                            ...editStrategy,
                            AutoScale: {
                              ...editStrategy.AutoScale,
                              MaxConsumers: parseInt(e.target.value),
                            },
                          })
                        }
                      />
                    </Grid>
                    <Grid item xs={6}>
                      <TextField
                        label="扩容阈值"
                        type="number"
                        fullWidth
                        size="small"
                        value={editStrategy?.AutoScale?.ScaleUpThreshold}
                        onChange={(e) =>
                          setEditStrategy({
                            ...editStrategy,
                            AutoScale: {
                              ...editStrategy.AutoScale,
                              ScaleUpThreshold: parseInt(e.target.value),
                            },
                          })
                        }
                      />
                    </Grid>
                    <Grid item xs={6}>
                      <TextField
                        label="缩容阈值"
                        type="number"
                        fullWidth
                        size="small"
                        value={editStrategy?.AutoScale?.ScaleDownThreshold}
                        onChange={(e) =>
                          setEditStrategy({
                            ...editStrategy,
                            AutoScale: {
                              ...editStrategy.AutoScale,
                              ScaleDownThreshold: parseInt(e.target.value),
                            },
                          })
                        }
                      />
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12}>
              <Card variant="outlined">
                <CardContent>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={editStrategy?.Partition?.Enabled}
                        onChange={(e) =>
                          setEditStrategy({
                            ...editStrategy,
                            Partition: { ...editStrategy.Partition, Enabled: e.target.checked },
                          })
                        }
                      />
                    }
                    label="分区管理"
                  />
                  <Grid container spacing={2} sx={{ mt: 1 }}>
                    <Grid item xs={6}>
                      <TextField
                        label="最小分区数"
                        type="number"
                        fullWidth
                        size="small"
                        value={editStrategy?.Partition?.MinPartitions}
                        onChange={(e) =>
                          setEditStrategy({
                            ...editStrategy,
                            Partition: {
                              ...editStrategy.Partition,
                              MinPartitions: parseInt(e.target.value),
                            },
                          })
                        }
                      />
                    </Grid>
                    <Grid item xs={6}>
                      <TextField
                        label="最大分区数"
                        type="number"
                        fullWidth
                        size="small"
                        value={editStrategy?.Partition?.MaxPartitions}
                        onChange={(e) =>
                          setEditStrategy({
                            ...editStrategy,
                            Partition: {
                              ...editStrategy.Partition,
                              MaxPartitions: parseInt(e.target.value),
                            },
                          })
                        }
                      />
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12}>
              <Card variant="outlined">
                <CardContent>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={editStrategy?.RateLimit?.Enabled}
                        onChange={(e) =>
                          setEditStrategy({
                            ...editStrategy,
                            RateLimit: { ...editStrategy.RateLimit, Enabled: e.target.checked },
                          })
                        }
                      />
                    }
                    label="分级限流 (Topic级 + 订阅级)"
                  />
                  <Typography variant="caption" color="textSecondary" sx={{ display: 'block', mb: 1 }}>
                    优先对积压严重的订阅独立限流，仅当多订阅同时积压时升级到Topic级限流
                  </Typography>
                  <Grid container spacing={2} sx={{ mt: 1 }}>
                    <Grid item xs={4}>
                      <TextField
                        label="基础速率 (msg/s)"
                        type="number"
                        fullWidth
                        size="small"
                        value={editStrategy?.RateLimit?.MaxRate}
                        onChange={(e) =>
                          setEditStrategy({
                            ...editStrategy,
                            RateLimit: {
                              ...editStrategy.RateLimit,
                              MaxRate: parseInt(e.target.value),
                            },
                          })
                        }
                      />
                    </Grid>
                    <Grid item xs={4}>
                      <TextField
                        label="订阅限流阈值"
                        type="number"
                        fullWidth
                        size="small"
                        value={editStrategy?.RateLimit?.BacklogThreshold}
                        onChange={(e) =>
                          setEditStrategy({
                            ...editStrategy,
                            RateLimit: {
                              ...editStrategy.RateLimit,
                              BacklogThreshold: parseInt(e.target.value),
                            },
                          })
                        }
                      />
                    </Grid>
                    <Grid item xs={4}>
                      <TextField
                        label="订阅恢复阈值"
                        type="number"
                        fullWidth
                        size="small"
                        value={editStrategy?.RateLimit?.RecoveryThreshold}
                        onChange={(e) =>
                          setEditStrategy({
                            ...editStrategy,
                            RateLimit: {
                              ...editStrategy.RateLimit,
                              RecoveryThreshold: parseInt(e.target.value),
                            },
                          })
                        }
                      />
                    </Grid>
                    <Grid item xs={12}>
                      <TextField
                        label="Topic级限流阈值 (多订阅同时积压触发)"
                        type="number"
                        fullWidth
                        size="small"
                        value={editStrategy?.RateLimit?.TopicBacklogThreshold}
                        onChange={(e) =>
                          setEditStrategy({
                            ...editStrategy,
                            RateLimit: {
                              ...editStrategy.RateLimit,
                              TopicBacklogThreshold: parseInt(e.target.value),
                            },
                          })
                        }
                      />
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12}>
              <Card variant="outlined">
                <CardContent>
                  <FormControlLabel
                    control={<Switch checked={editStrategy?.Prediction?.Enabled} onChange={(e) => setEditStrategy({ ...editStrategy, Prediction: { ...editStrategy.Prediction, Enabled: e.target.checked } })} />}
                    label="积压预测"
                  />
                  <Grid container spacing={2} sx={{ mt: 1 }}>
                    <Grid item xs={12}>
                      <TextField label="告警阈值" type="number" fullWidth size="small"
                        value={editStrategy?.Prediction?.AlertThreshold || 100000}
                        onChange={(e) => setEditStrategy({ ...editStrategy, Prediction: { ...editStrategy.Prediction, AlertThreshold: parseInt(e.target.value) } })}
                      />
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12}>
              <Card variant="outlined">
                <CardContent>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={editStrategy?.DeadLetter?.Enabled}
                        onChange={(e) =>
                          setEditStrategy({
                            ...editStrategy,
                            DeadLetter: { ...editStrategy.DeadLetter, Enabled: e.target.checked },
                          })
                        }
                      />
                    }
                    label="死信处理"
                  />
                  <Typography variant="caption" color="textSecondary" sx={{ display: 'block', mb: 1 }}>
                    消费失败达最大重投递次数后自动进入死信队列
                  </Typography>
                  <Grid container spacing={2} sx={{ mt: 1 }}>
                    <Grid item xs={4}>
                      <TextField
                        label="最大重投递次数" type="number" fullWidth size="small"
                        value={editStrategy?.DeadLetter?.MaxRedeliveries || 3}
                        onChange={(e) =>
                          setEditStrategy({ ...editStrategy, DeadLetter: { ...editStrategy.DeadLetter, MaxRedeliveries: parseInt(e.target.value) } })
                        }
                      />
                    </Grid>
                    <Grid item xs={4}>
                      <TextField
                        label="死信Topic (留空默认)" fullWidth size="small"
                        value={editStrategy?.DeadLetter?.DLQTopic || ''}
                        onChange={(e) =>
                          setEditStrategy({ ...editStrategy, DeadLetter: { ...editStrategy.DeadLetter, DLQTopic: e.target.value } })
                        }
                      />
                    </Grid>
                    <Grid item xs={4}>
                      <TextField
                        label="重试Topic (留空默认)" fullWidth size="small"
                        value={editStrategy?.DeadLetter?.RetryTopic || ''}
                        onChange={(e) =>
                          setEditStrategy({ ...editStrategy, DeadLetter: { ...editStrategy.DeadLetter, RetryTopic: e.target.value } })
                        }
                      />
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12}>
              <Card variant="outlined">
                <CardContent>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={editStrategy?.Replay?.Enabled}
                        onChange={(e) =>
                          setEditStrategy({ ...editStrategy, Replay: { ...editStrategy.Replay, Enabled: e.target.checked } })
                        }
                      />
                    }
                    label="消息重放"
                  />
                  <Grid container spacing={2} sx={{ mt: 1 }}>
                    <Grid item xs={6}>
                      <TextField
                        label="默认重放条数" type="number" fullWidth size="small"
                        value={editStrategy?.Replay?.MaxMessages || 1000}
                        onChange={(e) =>
                          setEditStrategy({ ...editStrategy, Replay: { ...editStrategy.Replay, MaxMessages: parseInt(e.target.value) } })
                        }
                      />
                    </Grid>
                    <Grid item xs={6}>
                      <TextField
                        label="重放目标Topic (留空默认)" fullWidth size="small"
                        value={editStrategy?.Replay?.TargetTopic || ''}
                        onChange={(e) =>
                          setEditStrategy({ ...editStrategy, Replay: { ...editStrategy.Replay, TargetTopic: e.target.value } })
                        }
                      />
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12}>
              <Card variant="outlined">
                <CardContent>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={editStrategy?.DelayProcess?.Enabled}
                        onChange={(e) =>
                          setEditStrategy({ ...editStrategy, DelayProcess: { ...editStrategy.DelayProcess, Enabled: e.target.checked } })
                        }
                      />
                    }
                    label="延迟处理 (积压降级)"
                  />
                  <Typography variant="caption" color="textSecondary" sx={{ display: 'block', mb: 1 }}>
                    积压超阈值时自动暂停非核心订阅，恢复后自动恢复
                  </Typography>
                  <Grid container spacing={2} sx={{ mt: 1 }}>
                    <Grid item xs={6}>
                      <TextField
                        label="降级阈值" type="number" fullWidth size="small"
                        value={editStrategy?.DelayProcess?.BacklogThreshold || 50000}
                        onChange={(e) =>
                          setEditStrategy({ ...editStrategy, DelayProcess: { ...editStrategy.DelayProcess, BacklogThreshold: parseInt(e.target.value) } })
                        }
                      />
                    </Grid>
                    <Grid item xs={6}>
                      <TextField
                        label="恢复阈值" type="number" fullWidth size="small"
                        value={editStrategy?.DelayProcess?.RecoveryThreshold || 25000}
                        onChange={(e) =>
                          setEditStrategy({ ...editStrategy, DelayProcess: { ...editStrategy.DelayProcess, RecoveryThreshold: parseInt(e.target.value) } })
                        }
                      />
                    </Grid>
                    <Grid item xs={6}>
                      <TextField
                        label="核心订阅 (逗号分隔)" fullWidth size="small"
                        value={(editStrategy?.DelayProcess?.CoreSubscriptions || []).join(',')}
                        onChange={(e) =>
                          setEditStrategy({ ...editStrategy, DelayProcess: { ...editStrategy.DelayProcess, CoreSubscriptions: e.target.value.split(',').filter(Boolean) } })
                        }
                        placeholder="sub-core-1,sub-core-2"
                      />
                    </Grid>
                    <Grid item xs={6}>
                      <TextField
                        label="非核心订阅 (逗号分隔)" fullWidth size="small"
                        value={(editStrategy?.DelayProcess?.NonCoreSubscriptions || []).join(',')}
                        onChange={(e) =>
                          setEditStrategy({ ...editStrategy, DelayProcess: { ...editStrategy.DelayProcess, NonCoreSubscriptions: e.target.value.split(',').filter(Boolean) } })
                        }
                        placeholder="sub-analytics,sub-log"
                      />
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>取消</Button>
          <Button onClick={handleSave} variant="contained">
            保存
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
}

export default Strategies;

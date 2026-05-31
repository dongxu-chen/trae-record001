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
  Chip,
  Grid,
  Box,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import {
  getDelayAllStats,
  getDelayStats,
  registerSubscription,
  pauseSubscription,
  resumeSubscription,
  getTopics,
} from '../services/api';

function DelayProcess() {
  const [delayStats, setDelayStats] = useState([]);
  const [topics, setTopics] = useState([]);
  const [registerDialog, setRegisterDialog] = useState({ open: false });
  const [registerForm, setRegisterForm] = useState({ topic: '', subscription: '', priority: 'normal' });

  const fetchData = async () => {
    try {
      const [delayRes, topicsRes] = await Promise.all([
        getDelayAllStats(),
        getTopics(),
      ]);
      setDelayStats(delayRes.data.stats || []);
      setTopics(topicsRes.data.topics || []);
    } catch (e) {
      console.error('Failed to fetch data:', e);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleRegister = async () => {
    await registerSubscription(registerForm.topic, registerForm.subscription, registerForm.priority);
    setRegisterDialog({ open: false });
    setRegisterForm({ topic: '', subscription: '', priority: 'normal' });
    fetchData();
  };

  const totalPauses = delayStats.reduce((sum, s) => sum + (s.total_pauses || 0), 0);
  const totalResumes = delayStats.reduce((sum, s) => sum + (s.total_resumes || 0), 0);
  const degradedCount = delayStats.filter((s) => s.is_degraded).length;

  return (
    <div>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">延迟处理</Typography>
        <Button variant="contained" onClick={() => setRegisterDialog({ open: true })}>
          注册订阅
        </Button>
      </Box>

      <Typography variant="body2" color="textSecondary" paragraph>
        积压时自动降级非核心订阅的消费，核心订阅不受影响。积压恢复后自动恢复非核心订阅。
      </Typography>

      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>降级中 Topic</Typography>
              <Typography variant="h4" color={degradedCount > 0 ? 'warning' : 'success'}>
                {degradedCount}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>累计暂停次数</Typography>
              <Typography variant="h4">{totalPauses}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>累计恢复次数</Typography>
              <Typography variant="h4">{totalResumes}</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {delayStats.map((stat, idx) => (
        <Card key={idx} sx={{ mb: 3 }}>
          <CardContent>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
              <Box display="flex" alignItems="center" gap={1}>
                <Typography variant="h6">{stat.topic}</Typography>
                <Chip
                  label={stat.is_degraded ? '降级中' : '正常'}
                  color={stat.is_degraded ? 'warning' : 'success'}
                  size="small"
                />
              </Box>
              <Typography variant="body2" color="textSecondary">
                阈值: {stat.threshold?.toLocaleString()} / 恢复: {stat.recovery_threshold?.toLocaleString()}
              </Typography>
            </Box>

            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>订阅名称</TableCell>
                    <TableCell align="center">状态</TableCell>
                    <TableCell align="center">操作</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {stat.paused_subscriptions?.map((sub) => (
                    <TableRow key={sub}>
                      <TableCell>{sub}</TableCell>
                      <TableCell align="center">
                        <Chip label="已暂停" color="error" size="small" />
                      </TableCell>
                      <TableCell align="center">
                        <Button size="small" color="success" onClick={async () => {
                          await resumeSubscription(stat.topic, sub);
                          fetchData();
                        }}>恢复</Button>
                      </TableCell>
                    </TableRow>
                  ))}
                  {stat.active_subscriptions?.map((sub) => (
                    <TableRow key={sub}>
                      <TableCell>{sub}</TableCell>
                      <TableCell align="center">
                        <Chip label="活跃" color="success" size="small" />
                      </TableCell>
                      <TableCell align="center">
                        <Button size="small" color="warning" onClick={async () => {
                          await pauseSubscription(stat.topic, sub);
                          fetchData();
                        }}>暂停</Button>
                      </TableCell>
                    </TableRow>
                  ))}
                  {(!stat.paused_subscriptions?.length && !stat.active_subscriptions?.length) && (
                    <TableRow>
                      <TableCell colSpan={3} align="center">
                        <Typography variant="body2" color="textSecondary">未注册订阅</Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      ))}

      {delayStats.length === 0 && (
        <Card>
          <CardContent>
            <Typography color="textSecondary" align="center" py={3}>
              暂无延迟处理配置，请先注册订阅并设置优先级
            </Typography>
          </CardContent>
        </Card>
      )}

      <Box mt={3}>
        <Card variant="outlined">
          <CardContent>
            <Typography variant="h6" gutterBottom>优先级说明</Typography>
            <Grid container spacing={2}>
              <Grid item xs={4}>
                <Chip label="核心 (core)" color="error" size="small" sx={{ mr: 1 }} />
                <Typography variant="body2">积压时永不暂停，确保核心业务不受影响</Typography>
              </Grid>
              <Grid item xs={4}>
                <Chip label="普通 (normal)" color="info" size="small" sx={{ mr: 1 }} />
                <Typography variant="body2">默认优先级，不受自动降级影响</Typography>
              </Grid>
              <Grid item xs={4}>
                <Chip label="非核心 (non_core)" color="default" size="small" sx={{ mr: 1 }} />
                <Typography variant="body2">积压超阈值时自动暂停，恢复后自动恢复</Typography>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      </Box>

      <Dialog open={registerDialog.open} onClose={() => setRegisterDialog({ open: false })}>
        <DialogTitle>注册订阅</DialogTitle>
        <DialogContent>
          <FormControl fullWidth margin="dense">
            <InputLabel>Topic</InputLabel>
            <Select
              value={registerForm.topic}
              label="Topic"
              onChange={(e) => setRegisterForm({ ...registerForm, topic: e.target.value })}
            >
              {topics.map((t) => (
                <MenuItem key={t} value={t}>{t}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            label="订阅名称" fullWidth margin="dense"
            value={registerForm.subscription}
            onChange={(e) => setRegisterForm({ ...registerForm, subscription: e.target.value })}
          />
          <FormControl fullWidth margin="dense">
            <InputLabel>优先级</InputLabel>
            <Select
              value={registerForm.priority}
              label="优先级"
              onChange={(e) => setRegisterForm({ ...registerForm, priority: e.target.value })}
            >
              <MenuItem value="core">核心 (core) - 永不暂停</MenuItem>
              <MenuItem value="normal">普通 (normal) - 默认</MenuItem>
              <MenuItem value="non_core">非核心 (non_core) - 积压时暂停</MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRegisterDialog({ open: false })}>取消</Button>
          <Button onClick={handleRegister} variant="contained"
            disabled={!registerForm.topic || !registerForm.subscription}>
            注册
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
}

export default DelayProcess;

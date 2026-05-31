import React, { useState, useEffect } from 'react';
import {
  Grid,
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
  IconButton,
  Chip,
  Box,
  LinearProgress,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import {
  getTopics,
  addTopic,
  removeTopic,
  getBacklogs,
  getBacklogHistory,
  setConsumerCount,
  setPartitionCount,
  setRateLimit,
  setSubscriptionRateLimit,
  getThrottleStatus,
} from '../services/api';

function Dashboard() {
  const [topics, setTopics] = useState([]);
  const [backlogs, setBacklogs] = useState({});
  const [historyData, setHistoryData] = useState([]);
  const [openAddDialog, setOpenAddDialog] = useState(false);
  const [newTopic, setNewTopic] = useState('');
  const [selectedTopic, setSelectedTopic] = useState(null);
  const [throttleStatuses, setThrottleStatuses] = useState({});
  const [actionDialog, setActionDialog] = useState({ open: false, type: '', topic: '', subscription: '' });
  const [actionValue, setActionValue] = useState('');

  const fetchData = async () => {
    try {
      const topicsRes = await getTopics();
      setTopics(topicsRes.data.topics || []);

      const backlogsRes = await getBacklogs();
      setBacklogs(backlogsRes.data.backlogs || {});

      const statuses = {};
      for (const topic of topicsRes.data.topics || []) {
        try {
          const res = await getThrottleStatus(topic);
          statuses[topic] = res.data;
        } catch (e) {}
      }
      setThrottleStatuses(statuses);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleAddTopic = async () => {
    if (newTopic) {
      await addTopic(newTopic);
      setNewTopic('');
      setOpenAddDialog(false);
      fetchData();
    }
  };

  const handleRemoveTopic = async (topic) => {
    await removeTopic(topic);
    fetchData();
  };

  const handleViewHistory = async (topic) => {
    try {
      const res = await getBacklogHistory(topic);
      const history = res.data.history || [];
      setHistoryData(
        history.map((h) => ({
          time: new Date(h.Timestamp).toLocaleTimeString(),
          backlog: h.BacklogSize,
          effectiveBacklog: h.EffectiveBacklog || h.BacklogSize,
        }))
      );
      setSelectedTopic(topic);
    } catch (error) {
      console.error('Failed to fetch history:', error);
    }
  };

  const handleOpenActionDialog = (type, topic, currentValue, subscription) => {
    setActionDialog({ open: true, type, topic, subscription: subscription || '' });
    setActionValue(currentValue?.toString() || '');
  };

  const handleExecuteAction = async () => {
    const { type, topic, subscription } = actionDialog;
    try {
      if (type === 'consumer') {
        await setConsumerCount(topic, 'default', parseInt(actionValue));
      } else if (type === 'partition') {
        await setPartitionCount(topic, parseInt(actionValue));
      } else if (type === 'ratelimit') {
        await setRateLimit(topic, parseFloat(actionValue));
      } else if (type === 'subRatelimit') {
        await setSubscriptionRateLimit(topic, subscription || 'default', parseFloat(actionValue));
      }
      setActionDialog({ open: false, type: '', topic: '', subscription: '' });
      fetchData();
    } catch (error) {
      console.error('Failed to execute action:', error);
    }
  };

  const getBacklogStatus = (backlog, effectiveBacklog) => {
    const val = effectiveBacklog || backlog;
    if (val > 50000) return { color: 'error', label: '严重' };
    if (val > 10000) return { color: 'warning', label: '警告' };
    return { color: 'success', label: '正常' };
  };

  const getThrottleLabel = (level) => {
    if (level === 10) return { label: '重度(10%)', color: 'error' };
    if (level === 40) return { label: '中度(40%)', color: 'warning' };
    if (level === 70) return { label: '轻度(70%)', color: 'info' };
    return { label: '正常', color: 'success' };
  };

  return (
    <div>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">监控面板</Typography>
        <Box>
          <Button variant="outlined" startIcon={<RefreshIcon />} onClick={fetchData} sx={{ mr: 2 }}>
            刷新
          </Button>
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => setOpenAddDialog(true)}>
            添加 Topic
          </Button>
        </Box>
      </Box>

      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>监控 Topic 数</Typography>
              <Typography variant="h4">{topics.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>总积压消息数</Typography>
              <Typography variant="h4">
                {Object.values(backlogs).reduce((sum, b) => sum + (b.BacklogSize || 0), 0).toLocaleString()}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>有效积压 (KB等价)</Typography>
              <Typography variant="h4">
                {Object.values(backlogs).reduce((sum, b) => sum + (b.EffectiveBacklog || 0), 0).toLocaleString()}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>高负载 Topic</Typography>
              <Typography variant="h4">
                {Object.values(backlogs).filter((b) => (b.EffectiveBacklog || b.BacklogSize || 0) > 10000).length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {selectedTopic && (
        <Card sx={{ mb: 4 }}>
          <CardContent>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
              <Typography variant="h6">积压趋势 - {selectedTopic}</Typography>
              <Button size="small" onClick={() => setSelectedTopic(null)}>关闭</Button>
            </Box>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={historyData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="backlog" stroke="#1976d2" strokeWidth={2} name="消息积压" />
                <Line type="monotone" dataKey="effectiveBacklog" stroke="#ff6f00" strokeWidth={2} name="有效积压(KB等价)" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Topic</TableCell>
              <TableCell align="right">积压消息</TableCell>
              <TableCell align="right">有效积压</TableCell>
              <TableCell align="right">状态</TableCell>
              <TableCell align="center">限流状态</TableCell>
              <TableCell align="center">操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {topics.map((topic) => {
              const backlog = backlogs[`${topic}-default`] || {};
              const status = getBacklogStatus(backlog.BacklogSize || 0, backlog.EffectiveBacklog || 0);
              const throttle = throttleStatuses[topic];
              const topicThrottle = getThrottleLabel(throttle?.topic_level || 0);
              return (
                <TableRow key={topic}>
                  <TableCell component="th" scope="row">{topic}</TableCell>
                  <TableCell align="right">{(backlog.BacklogSize || 0).toLocaleString()}</TableCell>
                  <TableCell align="right">{(backlog.EffectiveBacklog || 0).toLocaleString()}</TableCell>
                  <TableCell align="right">
                    <Chip label={status.label} color={status.color} size="small" />
                  </TableCell>
                  <TableCell align="center">
                    <Chip label={topicThrottle.label} color={topicThrottle.color} size="small" />
                    {throttle?.subscriptions && Object.entries(throttle.subscriptions).map(([sub, info]) => {
                      const subThrottle = getThrottleLabel(info.level || 0);
                      return (
                        <Chip key={sub} label={`${sub}: ${subThrottle.label}`} color={subThrottle.color} size="small" sx={{ ml: 0.5 }} />
                      );
                    })}
                  </TableCell>
                  <TableCell align="center">
                    <Button size="small" onClick={() => handleViewHistory(topic)}>趋势</Button>
                    <Button size="small" onClick={() => handleOpenActionDialog('consumer', topic, backlog.ConsumerCount || 1)}>
                      消费者
                    </Button>
                    <Button size="small" onClick={() => handleOpenActionDialog('partition', topic, 1)}>
                      分区
                    </Button>
                    <Button size="small" onClick={() => handleOpenActionDialog('ratelimit', topic, throttle?.topic_rate || 1000)}>
                      Topic限流
                    </Button>
                    <Button size="small" onClick={() => handleOpenActionDialog('subRatelimit', topic, 1000, 'default')}>
                      订阅限流
                    </Button>
                    <IconButton size="small" color="error" onClick={() => handleRemoveTopic(topic)}>
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={openAddDialog} onClose={() => setOpenAddDialog(false)}>
        <DialogTitle>添加 Topic</DialogTitle>
        <DialogContent>
          <TextField autoFocus margin="dense" label="Topic 名称" fullWidth value={newTopic} onChange={(e) => setNewTopic(e.target.value)} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenAddDialog(false)}>取消</Button>
          <Button onClick={handleAddTopic} variant="contained">添加</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={actionDialog.open} onClose={() => setActionDialog({ open: false, type: '', topic: '', subscription: '' })}>
        <DialogTitle>
          {actionDialog.type === 'consumer' && '调整消费者数量'}
          {actionDialog.type === 'partition' && '调整分区数量'}
          {actionDialog.type === 'ratelimit' && '设置 Topic 级限流速率'}
          {actionDialog.type === 'subRatelimit' && `设置订阅 [${actionDialog.subscription}] 限流速率`}
        </DialogTitle>
        <DialogContent>
          <TextField
            autoFocus margin="dense"
            label={actionDialog.type.includes('ratelimit') ? '限流速率 (msg/s)' : '数量'}
            type="number" fullWidth
            value={actionValue}
            onChange={(e) => setActionValue(e.target.value)}
          />
          {actionDialog.type === 'subRatelimit' && (
            <Typography variant="caption" color="textSecondary" sx={{ mt: 1, display: 'block' }}>
              订阅级别限流仅影响该订阅的消费速率，不影响同Topic下其他订阅
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setActionDialog({ open: false, type: '', topic: '', subscription: '' })}>取消</Button>
          <Button onClick={handleExecuteAction} variant="contained">确认</Button>
        </DialogActions>
      </Dialog>
    </div>
  );
}

export default Dashboard;

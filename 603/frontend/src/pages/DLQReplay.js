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
  Switch,
  FormControlLabel,
  Tabs,
  Tab,
} from '@mui/material';
import {
  getDLQAllStats,
  configureDLQ,
  retryFromDLQ,
  enableDLQ,
  disableDLQ,
  replayMessages,
  replayLastN,
  getReplayStatus,
  getReplayHistory,
  cancelReplay,
  getTopics,
} from '../services/api';

function DLQReplay() {
  const [tab, setTab] = useState(0);
  const [dlqStats, setDlqStats] = useState([]);
  const [replayHistory, setReplayHistory] = useState([]);
  const [topics, setTopics] = useState([]);
  const [configDialog, setConfigDialog] = useState({ open: false, topic: '', subscription: '' });
  const [configForm, setConfigForm] = useState({ max_redeliveries: 3, dlq_topic: '', retry_topic: '' });
  const [replayDialog, setReplayDialog] = useState({ open: false, topic: '' });
  const [replayForm, setReplayForm] = useState({ count: 100, target_topic: '', start_time: '', end_time: '' });
  const [retryDialog, setRetryDialog] = useState({ open: false, topic: '', subscription: '' });
  const [retryCount, setRetryCount] = useState(100);

  const fetchData = async () => {
    try {
      const [dlqRes, historyRes, topicsRes] = await Promise.all([
        getDLQAllStats(),
        getReplayHistory(),
        getTopics(),
      ]);
      setDlqStats(dlqRes.data.stats || []);
      setReplayHistory(historyRes.data.history || []);
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

  const handleConfigureDLQ = async () => {
    await configureDLQ(configDialog.topic, configDialog.subscription, configForm);
    setConfigDialog({ open: false, topic: '', subscription: '' });
    fetchData();
  };

  const handleRetryFromDLQ = async () => {
    await retryFromDLQ(retryDialog.topic, retryDialog.subscription, retryCount);
    setRetryDialog({ open: false, topic: '', subscription: '' });
    fetchData();
  };

  const handleReplayLastN = async () => {
    await replayLastN(replayDialog.topic, parseInt(replayForm.count), replayForm.target_topic);
    setReplayDialog({ open: false, topic: '' });
    fetchData();
  };

  const handleReplayByTime = async () => {
    const req = {
      topic: replayDialog.topic,
      subscription: 'default',
      max_messages: parseInt(replayForm.count) || 1000,
      target_topic: replayForm.target_topic,
    };
    if (replayForm.start_time) req.start_time = replayForm.start_time;
    if (replayForm.end_time) req.end_time = replayForm.end_time;
    await replayMessages(req);
    setReplayDialog({ open: false, topic: '' });
    fetchData();
  };

  const totalSentToDLQ = dlqStats.reduce((sum, s) => sum + (s.total_sent_to_dlq || 0), 0);
  const totalRetried = dlqStats.reduce((sum, s) => sum + (s.total_retried || 0), 0);

  return (
    <div>
      <Typography variant="h4" gutterBottom>死信处理 & 消息重放</Typography>

      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={tab} onChange={(_, v) => setTab(v)}>
          <Tab label="死信队列" />
          <Tab label="消息重放" />
        </Tabs>
      </Box>

      {tab === 0 && (
        <div>
          <Grid container spacing={3} mb={3}>
            <Grid item xs={12} sm={4}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>DLQ Topic 数</Typography>
                  <Typography variant="h4">{dlqStats.length}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={4}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>累计入死信</Typography>
                  <Typography variant="h4">{totalSentToDLQ.toLocaleString()}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={4}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>累计重试成功</Typography>
                  <Typography variant="h4">{totalRetried.toLocaleString()}</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Topic</TableCell>
                  <TableCell>Subscription</TableCell>
                  <TableCell align="right">入死信数</TableCell>
                  <TableCell align="right">重试成功</TableCell>
                  <TableCell align="center">最大重投递</TableCell>
                  <TableCell align="center">状态</TableCell>
                  <TableCell align="center">操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {dlqStats.map((stat, idx) => (
                  <TableRow key={idx}>
                    <TableCell>{stat.topic}</TableCell>
                    <TableCell>{stat.subscription}</TableCell>
                    <TableCell align="right">{stat.total_sent_to_dlq?.toLocaleString()}</TableCell>
                    <TableCell align="right">{stat.total_retried?.toLocaleString()}</TableCell>
                    <TableCell align="center">{stat.max_redeliveries}</TableCell>
                    <TableCell align="center">
                      <Chip
                        label={stat.enabled ? '启用' : '禁用'}
                        color={stat.enabled ? 'success' : 'default'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell align="center">
                      <Button size="small" onClick={() => {
                        setConfigDialog({ open: true, topic: stat.topic, subscription: stat.subscription });
                        setConfigForm({
                          max_redeliveries: stat.max_redeliveries || 3,
                          dlq_topic: stat.dlq_topic || '',
                          retry_topic: stat.retry_topic || '',
                        });
                      }}>配置</Button>
                      <Button size="small" onClick={() => setRetryDialog({ open: true, topic: stat.topic, subscription: stat.subscription })}>
                        重试
                      </Button>
                      <Button size="small" color={stat.enabled ? 'error' : 'success'}
                        onClick={async () => {
                          if (stat.enabled) await disableDLQ(stat.topic, stat.subscription);
                          else await enableDLQ(stat.topic, stat.subscription);
                          fetchData();
                        }}>
                        {stat.enabled ? '禁用' : '启用'}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {dlqStats.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} align="center">
                      <Typography color="textSecondary" py={2}>暂无死信队列配置</Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>

          <Box mt={3}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="h6" gutterBottom>死信处理流程</Typography>
                <Typography variant="body2" color="textSecondary">
                  1. 消费者处理消息失败 → 消息重新投递<br/>
                  2. 重新投递次数达到 max_redeliveries → 自动发送到死信队列 (DLQ Topic)<br/>
                  3. 死信消息可手动重试 → 从DLQ Topic读取并转发到重试Topic<br/>
                  4. 重试Topic的消费者重新消费
                </Typography>
              </CardContent>
            </Card>
          </Box>
        </div>
      )}

      {tab === 1 && (
        <div>
          <Box mb={3}>
            <Grid container spacing={2}>
              {topics.map((topic) => (
                <Grid item key={topic}>
                  <Button variant="outlined" onClick={() => {
                    setReplayDialog({ open: true, topic });
                    setReplayForm({ count: 100, target_topic: '', start_time: '', end_time: '' });
                  }}>
                    重放 {topic}
                  </Button>
                </Grid>
              ))}
            </Grid>
          </Box>

          <Typography variant="h6" gutterBottom>重放历史</Typography>
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>源 Topic</TableCell>
                  <TableCell>目标 Topic</TableCell>
                  <TableCell align="right">重放成功</TableCell>
                  <TableCell align="right">重放失败</TableCell>
                  <TableCell>完成时间</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {replayHistory.map((h, idx) => (
                  <TableRow key={idx}>
                    <TableCell>{h.topic}</TableCell>
                    <TableCell>{h.target_topic}</TableCell>
                    <TableCell align="right">{h.replayed}</TableCell>
                    <TableCell align="right">{h.failed}</TableCell>
                    <TableCell>{h.completed_at ? new Date(h.completed_at).toLocaleString() : '-'}</TableCell>
                  </TableRow>
                ))}
                {replayHistory.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} align="center">
                      <Typography color="textSecondary" py={2}>暂无重放记录</Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>

          <Box mt={3}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="h6" gutterBottom>消息重放说明</Typography>
                <Typography variant="body2" color="textSecondary">
                  • 重放最近N条：从Topic最早的消息开始，重新发送指定数量的消息到目标Topic<br/>
                  • 按时间范围重放：重放指定时间范围内的已消费消息<br/>
                  • 重放的消息会附加元数据（原始Topic、原始发布时间等）<br/>
                  • 同一Topic同一时间只允许一个重放任务
                </Typography>
              </CardContent>
            </Card>
          </Box>
        </div>
      )}

      <Dialog open={configDialog.open} onClose={() => setConfigDialog({ open: false, topic: '', subscription: '' })}>
        <DialogTitle>配置死信队列</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
            Topic: {configDialog.topic} / Subscription: {configDialog.subscription}
          </Typography>
          <TextField
            label="最大重投递次数" type="number" fullWidth margin="dense"
            value={configForm.max_redeliveries}
            onChange={(e) => setConfigForm({ ...configForm, max_redeliveries: parseInt(e.target.value) })}
          />
          <TextField
            label="死信Topic (留空使用默认)" fullWidth margin="dense"
            value={configForm.dlq_topic}
            onChange={(e) => setConfigForm({ ...configForm, dlq_topic: e.target.value })}
            placeholder={`${configDialog.topic}-DLQ`}
          />
          <TextField
            label="重试Topic (留空使用默认)" fullWidth margin="dense"
            value={configForm.retry_topic}
            onChange={(e) => setConfigForm({ ...configForm, retry_topic: e.target.value })}
            placeholder={`${configDialog.topic}-RETRY`}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfigDialog({ open: false, topic: '', subscription: '' })}>取消</Button>
          <Button onClick={handleConfigureDLQ} variant="contained">保存</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={retryDialog.open} onClose={() => setRetryDialog({ open: false, topic: '', subscription: '' })}>
        <DialogTitle>从死信队列重试</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
            Topic: {retryDialog.topic} / Subscription: {retryDialog.subscription}
          </Typography>
          <TextField
            label="重试消息数量" type="number" fullWidth margin="dense"
            value={retryCount}
            onChange={(e) => setRetryCount(parseInt(e.target.value) || 100)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRetryDialog({ open: false, topic: '', subscription: '' })}>取消</Button>
          <Button onClick={handleRetryFromDLQ} variant="contained">开始重试</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={replayDialog.open} onClose={() => setReplayDialog({ open: false, topic: '' })} maxWidth="sm" fullWidth>
        <DialogTitle>消息重放 - {replayDialog.topic}</DialogTitle>
        <DialogContent>
          <TextField
            label="重放消息数量" type="number" fullWidth margin="dense"
            value={replayForm.count}
            onChange={(e) => setReplayForm({ ...replayForm, count: e.target.value })}
          />
          <TextField
            label="目标Topic (留空使用默认)" fullWidth margin="dense"
            value={replayForm.target_topic}
            onChange={(e) => setReplayForm({ ...replayForm, target_topic: e.target.value })}
            placeholder={`${replayDialog.topic}-replay`}
          />
          <TextField
            label="开始时间 (可选)" type="datetime-local" fullWidth margin="dense"
            value={replayForm.start_time}
            onChange={(e) => setReplayForm({ ...replayForm, start_time: e.target.value })}
            InputLabelProps={{ shrink: true }}
          />
          <TextField
            label="结束时间 (可选)" type="datetime-local" fullWidth margin="dense"
            value={replayForm.end_time}
            onChange={(e) => setReplayForm({ ...replayForm, end_time: e.target.value })}
            InputLabelProps={{ shrink: true }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReplayDialog({ open: false, topic: '' })}>取消</Button>
          <Button onClick={handleReplayByTime} variant="outlined">按时间重放</Button>
          <Button onClick={handleReplayLastN} variant="contained">重放最近N条</Button>
        </DialogActions>
      </Dialog>
    </div>
  );
}

export default DLQReplay;

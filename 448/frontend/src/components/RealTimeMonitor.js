import React, { useState, useEffect, useRef } from 'react';
import {
  Paper, Typography, Grid, Card, CardContent, Box, Button,
  Chip, Alert, LinearProgress,
} from '@mui/material';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, AreaChart, Area,
} from 'recharts';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StopIcon from '@mui/icons-material/Stop';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import api from '../services/api';

function RealTimeMonitor({ poolConfig, workload }) {
  const [monitoring, setMonitoring] = useState(false);
  const [snapshots, setSnapshots] = useState([]);
  const [latest, setLatest] = useState(null);
  const [dynamicSize, setDynamicSize] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const eventSourceRef = useRef(null);

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const startMonitor = async () => {
    try {
      await api.startMonitoring(poolConfig, workload);
      setMonitoring(true);
      connectSSE();
    } catch (err) {
      console.error('Failed to start monitoring:', err);
    }
  };

  const stopMonitor = async () => {
    try {
      await api.stopMonitoring();
      setMonitoring(false);
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    } catch (err) {
      console.error('Failed to stop monitoring:', err);
    }
  };

  const connectSSE = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const es = new EventSource(api.getMonitorStream());
    es.addEventListener('monitor', (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.snapshot) {
          setLatest(data.snapshot);
          setDynamicSize(data.dynamicMaxPoolSize);
          setSnapshots(prev => {
            const next = [...prev, {
              ...data.snapshot,
              time: new Date(data.snapshot.timestamp).toLocaleTimeString(),
            }];
            return next.length > 120 ? next.slice(-120) : next;
          });
        }
        if (data.activeAlerts) {
          setAlerts(data.activeAlerts);
        }
      } catch (e) {
        console.error('SSE parse error:', e);
      }
    });

    es.onerror = () => {
      es.close();
      if (monitoring) {
        setTimeout(connectSSE, 3000);
      }
    };

    eventSourceRef.current = es;
  };

  const utilizationColor = (val) => {
    if (val > 0.9) return 'error';
    if (val > 0.7) return 'warning';
    return 'success';
  };

  return (
    <Box>
      <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <FiberManualRecordIcon
              color={monitoring ? 'error' : 'disabled'}
              sx={{ mr: 1, animation: monitoring ? 'pulse 1.5s infinite' : 'none' }}
            />
            <Typography variant="h6">
              实时连接池监控
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            {dynamicSize && (
              <Chip label={`动态连接数: ${dynamicSize}`} color="primary" variant="outlined" />
            )}
            <Button
              variant={monitoring ? 'outlined' : 'contained'}
              color={monitoring ? 'error' : 'primary'}
              startIcon={monitoring ? <StopIcon /> : <PlayArrowIcon />}
              onClick={monitoring ? stopMonitor : startMonitor}
            >
              {monitoring ? '停止监控' : '启动监控'}
            </Button>
          </Box>
        </Box>

        {alerts.filter(a => !a.acknowledged).length > 0 && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {alerts.filter(a => !a.acknowledged).length} 个活跃告警！
            最严重：{alerts.filter(a => !a.acknowledged)[0]?.message?.substring(0, 80)}...
          </Alert>
        )}

        {latest && (
          <Grid container spacing={3}>
            <Grid item xs={12} sm={6} md={2}>
              <Card>
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary">活跃连接</Typography>
                  <Typography variant="h4">{latest.activeConnections}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    / {latest.totalConnections}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <Card>
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary">空闲连接</Typography>
                  <Typography variant="h4">{latest.idleConnections}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <Card>
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary">等待线程</Typography>
                  <Typography variant="h4" color={latest.waitingThreads > 0 ? 'error' : 'success'}>
                    {latest.waitingThreads}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <Card>
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary">利用率</Typography>
                  <Typography variant="h4" color={utilizationColor(latest.utilization)}>
                    {(latest.utilization * 100).toFixed(1)}%
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={latest.utilization * 100}
                    color={utilizationColor(latest.utilization)}
                    sx={{ mt: 1 }}
                  />
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <Card>
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary">平均借出时间</Typography>
                  <Typography variant="h4">{latest.avgBorrowTimeMs?.toFixed(1)} ms</Typography>
                  <Typography variant="caption" color="text.secondary">
                    最大: {latest.maxBorrowTimeMs?.toFixed(1)} ms
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <Card>
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary">吞吐量</Typography>
                  <Typography variant="h4">{latest.throughputLastSecond?.toFixed(0)}</Typography>
                  <Typography variant="caption" color="text.secondary">req/s</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}
      </Paper>

      {snapshots.length > 0 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Paper elevation={2} sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>连接数趋势</Typography>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={snapshots}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Area type="monotone" dataKey="activeConnections" stackId="1" stroke="#1976d2" fill="#1976d280" name="活跃" />
                  <Area type="monotone" dataKey="idleConnections" stackId="1" stroke="#4caf50" fill="#4caf5080" name="空闲" />
                  <Area type="monotone" dataKey="waitingThreads" stackId="2" stroke="#f44336" fill="#f4433680" name="等待" />
                </AreaChart>
              </ResponsiveContainer>
            </Paper>
          </Grid>
          <Grid item xs={12} md={6}>
            <Paper elevation={2} sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>利用率 & 借出时间</Typography>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={snapshots}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis yAxisId="left" label={{ value: '利用率 (%)', angle: -90, position: 'insideLeft' }} />
                  <YAxis yAxisId="right" orientation="right" label={{ value: '时间 (ms)', angle: 90, position: 'insideRight' }} />
                  <Tooltip />
                  <Legend />
                  <Line yAxisId="left" type="monotone" dataKey="utilization" stroke="#1976d2"
                        name="利用率" strokeWidth={2} dot={false}
                        formatter={v => (v * 100).toFixed(1) + '%'} />
                  <Line yAxisId="right" type="monotone" dataKey="avgBorrowTimeMs" stroke="#ff9800"
                        name="借出时间" strokeWidth={1.5} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </Paper>
          </Grid>
        </Grid>
      )}
    </Box>
  );
}

export default RealTimeMonitor;

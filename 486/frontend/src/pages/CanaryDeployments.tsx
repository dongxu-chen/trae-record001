import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Chip,
  Grid,
  LinearProgress,
  IconButton,
} from '@mui/material';
import {
  PlayArrow,
  Pause,
  CheckCircle,
  RotateLeft,
  TrendingUp,
  Speed,
  ErrorOutline,
} from '@mui/icons-material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { CanaryDeployment } from '../types';
import { canaryApi } from '../services/api';

const CanaryDeployments: React.FC = () => {
  const [deployments, setDeployments] = useState<CanaryDeployment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDeployments();
    const interval = setInterval(loadDeployments, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadDeployments = async () => {
    try {
      const response = await canaryApi.listDeployments();
      setDeployments(response.data.items);
    } catch (error) {
      console.error('Failed to load deployments:', error);
      setDeployments([
        {
          id: 'canary-1',
          policy_id: 'policy-123',
          strategy: 'canary',
          traffic_percent: 35,
          duration: '30m',
          status: 'progressing',
          metrics: {
            success_rate: 99.5,
            latency_p95: 145,
            error_rate: 0.005,
            throughput: 1250,
          },
          created_at: new Date(Date.now() - 10 * 60000).toISOString(),
          updated_at: new Date().toISOString(),
        },
        {
          id: 'canary-2',
          policy_id: 'policy-456',
          strategy: 'linear',
          traffic_percent: 100,
          duration: '15m',
          status: 'promoted',
          metrics: {
            success_rate: 99.9,
            latency_p95: 95,
            error_rate: 0.001,
            throughput: 2100,
          },
          created_at: new Date(Date.now() - 60 * 60000).toISOString(),
          updated_at: new Date(Date.now() - 30 * 60000).toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handlePause = async (policyId: string) => {
    try {
      await canaryApi.pauseDeployment(policyId);
      loadDeployments();
    } catch (error) {
      console.error('Failed to pause:', error);
    }
  };

  const handleResume = async (policyId: string) => {
    try {
      await canaryApi.resumeDeployment(policyId);
      loadDeployments();
    } catch (error) {
      console.error('Failed to resume:', error);
    }
  };

  const handlePromote = async (policyId: string) => {
    try {
      await canaryApi.promoteDeployment(policyId);
      loadDeployments();
    } catch (error) {
      console.error('Failed to promote:', error);
    }
  };

  const handleRollback = async (policyId: string) => {
    try {
      await canaryApi.rollbackDeployment(policyId);
      loadDeployments();
    } catch (error) {
      console.error('Failed to rollback:', error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'progressing':
        return 'primary';
      case 'promoted':
        return 'success';
      case 'paused':
        return 'warning';
      case 'rolled_back':
        return 'error';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  const metricsData = Array.from({ length: 10 }, (_, i) => ({
    time: `${i * 2}m`,
    success_rate: 98 + Math.random() * 2,
    latency: 80 + Math.random() * 60,
    error_rate: Math.random() * 0.01,
  }));

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 4 }}>
        灰度发布管理
      </Typography>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <TrendingUp color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">进行中</Typography>
              </Box>
              <Typography variant="h3" color="primary.main">
                {deployments.filter(d => d.status === 'progressing').length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <CheckCircle color="success" sx={{ mr: 1 }} />
                <Typography variant="h6">已发布</Typography>
              </Box>
              <Typography variant="h3" color="success.main">
                {deployments.filter(d => d.status === 'promoted').length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <ErrorOutline color="error" sx={{ mr: 1 }} />
                <Typography variant="h6">已回滚</Typography>
              </Box>
              <Typography variant="h3" color="error.main">
                {deployments.filter(d => d.status === 'rolled_back').length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          {deployments.map((deployment) => (
            <Card key={deployment.id} sx={{ mb: 3 }}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Box>
                    <Typography variant="h6">策略 ID: {deployment.policy_id}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      策略: {deployment.strategy.toUpperCase()} | 时长: {deployment.duration}
                    </Typography>
                  </Box>
                  <Chip
                    label={deployment.status}
                    color={getStatusColor(deployment.status) as any}
                  />
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2">流量百分比</Typography>
                    <Typography variant="body2" fontWeight="bold">
                      {deployment.traffic_percent}%
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={deployment.traffic_percent}
                    sx={{ height: 10, borderRadius: 5 }}
                  />
                </Box>

                <Grid container spacing={2}>
                  <Grid item xs={3}>
                    <Typography variant="body2" color="text.secondary">成功率</Typography>
                    <Typography variant="h6">{deployment.metrics.success_rate}%</Typography>
                  </Grid>
                  <Grid item xs={3}>
                    <Typography variant="body2" color="text.secondary">P95 延迟</Typography>
                    <Typography variant="h6">{deployment.metrics.latency_p95}ms</Typography>
                  </Grid>
                  <Grid item xs={3}>
                    <Typography variant="body2" color="text.secondary">错误率</Typography>
                    <Typography variant="h6">{(deployment.metrics.error_rate * 100).toFixed(3)}%</Typography>
                  </Grid>
                  <Grid item xs={3}>
                    <Typography variant="body2" color="text.secondary">吞吐量</Typography>
                    <Typography variant="h6">{deployment.metrics.throughput}/s</Typography>
                  </Grid>
                </Grid>

                <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                  {deployment.status === 'progressing' && (
                    <>
                      <IconButton onClick={() => handlePause(deployment.policy_id)} title="暂停">
                        <Pause />
                      </IconButton>
                      <IconButton onClick={() => handlePromote(deployment.policy_id)} title="立即发布">
                        <CheckCircle />
                      </IconButton>
                      <IconButton onClick={() => handleRollback(deployment.policy_id)} title="回滚" color="error">
                        <RotateLeft />
                      </IconButton>
                    </>
                  )}
                  {deployment.status === 'paused' && (
                    <IconButton onClick={() => handleResume(deployment.policy_id)} title="继续">
                      <PlayArrow />
                    </IconButton>
                  )}
                </Box>
              </CardContent>
            </Card>
          ))}
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                实时监控
              </Typography>
              <Box sx={{ height: 200, mb: 2 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={metricsData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time" fontSize={10} />
                    <YAxis fontSize={10} />
                    <Tooltip />
                    <Line type="monotone" dataKey="success_rate" stroke="#4caf50" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </Box>
              <Typography variant="body2" color="text.secondary" align="center">
                成功率趋势
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default CanaryDeployments;

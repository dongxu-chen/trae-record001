import React, { useState, useEffect } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  BugReport as FaultIcon,
  PlaylistPlay as ScenarioIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Schedule as RunningIcon,
} from '@mui/icons-material';
import { faultApi, scenarioApi, executionApi } from '../services/api';

function Dashboard() {
  const [stats, setStats] = useState({
    totalFaults: 0,
    runningFaults: 0,
    totalScenarios: 0,
    completedExecutions: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      setLoading(true);
      const [faults, scenarios, executions] = await Promise.all([
        faultApi.list(),
        scenarioApi.list(),
        executionApi.list(),
      ]);

      setStats({
        totalFaults: faults.length,
        runningFaults: faults.filter((f) => f.status === 'running').length,
        totalScenarios: scenarios.length,
        completedExecutions: executions.filter((e) => e.status === 'completed').length,
      });
    } catch (err) {
      setError('加载统计数据失败');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  const statCards = [
    {
      title: '故障总数',
      value: stats.totalFaults,
      icon: <FaultIcon sx={{ fontSize: 40 }} />,
      color: '#1976d2',
      bgColor: '#e3f2fd',
    },
    {
      title: '运行中故障',
      value: stats.runningFaults,
      icon: <RunningIcon sx={{ fontSize: 40 }} />,
      color: '#ff9800',
      bgColor: '#fff3e0',
    },
    {
      title: '场景总数',
      value: stats.totalScenarios,
      icon: <ScenarioIcon sx={{ fontSize: 40 }} />,
      color: '#9c27b0',
      bgColor: '#f3e5f5',
    },
    {
      title: '完成执行',
      value: stats.completedExecutions,
      icon: <SuccessIcon sx={{ fontSize: 40 }} />,
      color: '#4caf50',
      bgColor: '#e8f5e9',
    },
  ];

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        仪表盘
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        {statCards.map((card, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography variant="h6" color="text.secondary" gutterBottom>
                      {card.title}
                    </Typography>
                    <Typography variant="h3" fontWeight="bold" sx={{ color: card.color }}>
                      {card.value}
                    </Typography>
                  </Box>
                  <Box
                    sx={{
                      backgroundColor: card.bgColor,
                      borderRadius: 2,
                      p: 2,
                      color: card.color,
                    }}
                  >
                    {card.icon}
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Grid container spacing={3} sx={{ mt: 2 }}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                系统韧性测试概览
              </Typography>
              <Typography variant="body1" color="text.secondary">
                欢迎使用服务网格故障注入测试平台。本平台支持：
              </Typography>
              <Box component="ul" sx={{ mt: 2 }}>
                <li>延迟故障注入 - 测试系统在高延迟下的表现</li>
                <li>异常中断注入 - 模拟服务不可用场景</li>
                <li>错误码注入 - 测试错误处理逻辑</li>
                <li>故障场景编排 - 按顺序执行多个故障</li>
                <li>影响范围控制 - 精确控制故障影响范围</li>
                <li>观测指标采集 - Jaeger链路追踪集成</li>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                快速开始
              </Typography>
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle1" fontWeight="bold">
                  1. 创建故障
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  在故障管理页面创建延迟、中断或错误故障
                </Typography>

                <Typography variant="subtitle1" fontWeight="bold">
                  2. 编排场景（可选）
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  将多个故障组合成复杂的测试场景
                </Typography>

                <Typography variant="subtitle1" fontWeight="bold">
                  3. 执行并监控
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  执行故障/场景，在服务监控页面查看指标
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}

export default Dashboard;

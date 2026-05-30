import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Button,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Divider,
  Paper,
  LinearProgress,
  Alert,
} from '@mui/material';
import {
  Memory as MemoryIcon,
  Warning as WarningIcon,
  TrendingUp as TrendingUpIcon,
  Refresh as RefreshIcon,
  PlayArrow as PlayArrowIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
} from 'recharts';
import { capacityApi, serviceApi } from '../services/api';

const statusColors = {
  NORMAL: 'success',
  WARNING: 'warning',
  CRITICAL: 'error',
  NEEDS_EXPANSION: 'error',
  OVER_PROVISIONED: 'info',
};

const statusLabels = {
  NORMAL: '正常',
  WARNING: '警告',
  CRITICAL: '危急',
  NEEDS_EXPANSION: '需扩容',
  OVER_PROVISIONED: '配置过高',
};

function CapacityPlanning() {
  const [capacityPlans, setCapacityPlans] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [services, setServices] = useState([]);
  const [selectedService, setSelectedService] = useState(null);
  const [loading, setLoading] = useState(true);
  const [openDetail, setOpenDetail] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [plansRes, alertsRes, statsRes, servicesRes] = await Promise.all([
        capacityApi.getAll({ days: 7 }),
        capacityApi.getAlerts(),
        capacityApi.getStatistics(),
        serviceApi.getAll(),
      ]);

      setCapacityPlans(plansRes.data || []);
      setAlerts(alertsRes.data || []);
      setStatistics(statsRes.data);
      setServices(servicesRes.data || []);
    } catch (error) {
      console.error('Failed to fetch capacity data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async (serviceName) => {
    try {
      await capacityApi.generate(serviceName);
      fetchData();
    } catch (error) {
      console.error('Failed to generate capacity plan:', error);
    }
  };

  const handleViewDetail = (plan) => {
    setSelectedPlan(plan);
    setOpenDetail(true);
  };

  const latestPlans = capacityPlans.reduce((acc, plan) => {
    if (!acc[plan.serviceName] || new Date(plan.createdAt) > new Date(acc[plan.serviceName].createdAt)) {
      acc[plan.serviceName] = plan;
    }
    return acc;
  }, {});

  const latestPlanList = Object.values(latestPlans);

  const utilizationChartData = latestPlanList.map((plan) => ({
    name: plan.serviceName,
    当前利用率: plan.currentUtilization,
    预计7天: plan.predictedUtilization7d,
    预计30天: plan.predictedUtilization30d,
    阈值: 80,
  }));

  const getUtilizationColor = (utilization) => {
    if (utilization >= 90) return 'error';
    if (utilization >= 70) return 'warning';
    if (utilization < 30) return 'info';
    return 'success';
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4">容量规划</Typography>
          <Typography variant="subtitle1" color="textSecondary">
            基于历史数据预测资源需求，保障SLA所需的资源供给
          </Typography>
        </Box>
        <Box display="flex" gap={2}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={fetchData}
          >
            刷新
          </Button>
        </Box>
      </Box>

      {alerts.length > 0 && (
        <Alert severity="warning" sx={{ mb: 3 }} icon={<WarningIcon />}>
          检测到 {alerts.length} 个容量告警需要关注
        </Alert>
      )}

      {statistics && (
        <Grid container spacing={3} mb={3}>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography color="textSecondary" gutterBottom>
                      平均当前利用率
                    </Typography>
                    <Typography variant="h4" color={getUtilizationColor(statistics.averageCurrentUtilization)}>
                      {statistics.averageCurrentUtilization?.toFixed(1)}%
                    </Typography>
                  </Box>
                  <MemoryIcon sx={{ fontSize: 40, color: 'primary.main' }} />
                </Box>
                <Box mt={1}>
                  <LinearProgress
                    variant="determinate"
                    value={statistics.averageCurrentUtilization}
                    color={getUtilizationColor(statistics.averageCurrentUtilization)}
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography color="textSecondary" gutterBottom>
                      预计7天利用率
                    </Typography>
                    <Typography variant="h4" color={getUtilizationColor(statistics.averagePredictedUtilization7d)}>
                      {statistics.averagePredictedUtilization7d?.toFixed(1)}%
                    </Typography>
                  </Box>
                  <TrendingUpIcon sx={{ fontSize: 40, color: 'warning.main' }} />
                </Box>
                <Box mt={1}>
                  <LinearProgress
                    variant="determinate"
                    value={Math.min(100, statistics.averagePredictedUtilization7d)}
                    color={getUtilizationColor(statistics.averagePredictedUtilization7d)}
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography color="textSecondary" gutterBottom>
                      需扩容服务
                    </Typography>
                    <Typography variant="h4" color="error.main">
                      {statistics.needsExpansionPlans + statistics.criticalPlans}
                    </Typography>
                  </Box>
                  <WarningIcon sx={{ fontSize: 40, color: 'error.main' }} />
                </Box>
                <Typography variant="caption" color="textSecondary">
                  危急: {statistics.criticalPlans} | 警告: {statistics.warningPlans}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography color="textSecondary" gutterBottom>
                      配置过高服务
                    </Typography>
                    <Typography variant="h4" color="info.main">
                      {statistics.overProvisionedPlans}
                    </Typography>
                  </Box>
                  <InfoIcon sx={{ fontSize: 40, color: 'info.main' }} />
                </Box>
                <Typography variant="caption" color="textSecondary">
                  可考虑缩容优化成本
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      <Grid container spacing={3} mb={3}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                资源利用率趋势
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={utilizationChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis domain={[0, 100]} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="当前利用率" fill="#3f51b5" />
                  <Bar dataKey="预计7天" fill="#ff9800" />
                  <Bar dataKey="预计30天" fill="#f44336" />
                  <Line type="monotone" dataKey="阈值" stroke="#9e9e9e" strokeDasharray="5 5" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                快速操作
              </Typography>
              <Box display="flex" flexDirection="column" gap={2}>
                {services.map((service) => (
                  <Box key={service.serviceName} display="flex" justifyContent="space-between" alignItems="center">
                    <Box>
                      <Typography fontWeight="bold">{service.serviceName}</Typography>
                      {latestPlans[service.serviceName] && (
                        <Chip
                          label={statusLabels[latestPlans[service.serviceName].status]}
                          color={statusColors[latestPlans[service.serviceName].status]}
                          size="small"
                        />
                      )}
                    </Box>
                    <Button
                      variant="outlined"
                      size="small"
                      startIcon={<PlayArrowIcon />}
                      onClick={() => handleGenerate(service.serviceName)}
                    >
                      生成规划
                    </Button>
                  </Box>
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Typography variant="h6" gutterBottom>
        容量规划详情
      </Typography>
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>服务名称</TableCell>
              <TableCell>资源类型</TableCell>
              <TableCell>当前利用率</TableCell>
              <TableCell>预计7天</TableCell>
              <TableCell>预计30天</TableCell>
              <TableCell>QPS峰值</TableCell>
              <TableCell>预测QPS(7天)</TableCell>
              <TableCell>状态</TableCell>
              <TableCell>生成时间</TableCell>
              <TableCell>操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {latestPlanList.map((plan) => (
              <TableRow key={plan.id} hover>
                <TableCell>
                  <Typography fontWeight="bold">{plan.serviceName}</Typography>
                </TableCell>
                <TableCell>{plan.resourceType}</TableCell>
                <TableCell>
                  <Box>
                    <Typography color={getUtilizationColor(plan.currentUtilization)}>
                      {plan.currentUtilization?.toFixed(1)}%
                    </Typography>
                    <LinearProgress
                      variant="determinate"
                      value={plan.currentUtilization}
                      color={getUtilizationColor(plan.currentUtilization)}
                      sx={{ height: 4, borderRadius: 2 }}
                    />
                  </Box>
                </TableCell>
                <TableCell>
                  <Typography color={getUtilizationColor(plan.predictedUtilization7d)}>
                    {plan.predictedUtilization7d?.toFixed(1)}%
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography color={getUtilizationColor(plan.predictedUtilization30d)}>
                    {plan.predictedUtilization30d?.toFixed(1)}%
                  </Typography>
                </TableCell>
                <TableCell>{plan.peakRequestsPerSecond}</TableCell>
                <TableCell>{plan.predictedPeakRequests7d}</TableCell>
                <TableCell>
                  <Chip
                    label={statusLabels[plan.status]}
                    color={statusColors[plan.status]}
                    size="small"
                  />
                </TableCell>
                <TableCell>
                  {new Date(plan.createdAt).toLocaleString('zh-CN')}
                </TableCell>
                <TableCell>
                  <IconButton
                    size="small"
                    onClick={() => handleViewDetail(plan)}
                    title="查看详情"
                  >
                    <InfoIcon />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={openDetail} onClose={() => setOpenDetail(false)} maxWidth="md" fullWidth>
        <DialogTitle>容量规划详情</DialogTitle>
        <DialogContent>
          {selectedPlan && (
            <Box sx={{ pt: 2 }}>
              <Grid container spacing={2} mb={2}>
                <Grid item xs={12} md={6}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="subtitle2" color="textSecondary">服务名称</Typography>
                      <Typography variant="h6">{selectedPlan.serviceName}</Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="subtitle2" color="textSecondary">资源类型</Typography>
                      <Typography variant="h6">{selectedPlan.resourceType}</Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>

              <Divider sx={{ my: 2 }} />

              <Typography variant="h6" gutterBottom>利用率分析</Typography>
              <Grid container spacing={2} mb={2}>
                <Grid item xs={4}>
                  <Box textAlign="center">
                    <Typography variant="h4" color={getUtilizationColor(selectedPlan.currentUtilization)}>
                      {selectedPlan.currentUtilization?.toFixed(1)}%
                    </Typography>
                    <Typography variant="caption" color="textSecondary">当前</Typography>
                  </Box>
                </Grid>
                <Grid item xs={4}>
                  <Box textAlign="center">
                    <Typography variant="h4" color={getUtilizationColor(selectedPlan.predictedUtilization7d)}>
                      {selectedPlan.predictedUtilization7d?.toFixed(1)}%
                    </Typography>
                    <Typography variant="caption" color="textSecondary">7天预测</Typography>
                  </Box>
                </Grid>
                <Grid item xs={4}>
                  <Box textAlign="center">
                    <Typography variant="h4" color={getUtilizationColor(selectedPlan.predictedUtilization30d)}>
                      {selectedPlan.predictedUtilization30d?.toFixed(1)}%
                    </Typography>
                    <Typography variant="caption" color="textSecondary">30天预测</Typography>
                  </Box>
                </Grid>
              </Grid>

              <Divider sx={{ my: 2 }} />

              <Typography variant="h6" gutterBottom>容量指标</Typography>
              <Grid container spacing={2} mb={2}>
                <Grid item xs={6} md={3}>
                  <Typography variant="caption" color="textSecondary">QPS峰值</Typography>
                  <Typography variant="body1">{selectedPlan.peakRequestsPerSecond}</Typography>
                </Grid>
                <Grid item xs={6} md={3}>
                  <Typography variant="caption" color="textSecondary">7天预测QPS</Typography>
                  <Typography variant="body1">{selectedPlan.predictedPeakRequests7d}</Typography>
                </Grid>
                <Grid item xs={6} md={3}>
                  <Typography variant="caption" color="textSecondary">30天预测QPS</Typography>
                  <Typography variant="body1">{selectedPlan.predictedPeakRequests30d}</Typography>
                </Grid>
                <Grid item xs={6} md={3}>
                  <Typography variant="caption" color="textSecondary">增长率</Typography>
                  <Typography variant="body1">{selectedPlan.growthRate?.toFixed(2)}%</Typography>
                </Grid>
              </Grid>

              <Divider sx={{ my: 2 }} />

              <Typography variant="h6" gutterBottom>建议</Typography>
              <Card variant="outlined">
                <CardContent>
                  <Typography>{selectedPlan.recommendations}</Typography>
                </CardContent>
              </Card>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDetail(false)}>关闭</Button>
          <Button
            variant="contained"
            onClick={() => {
              handleGenerate(selectedPlan.serviceName);
              setOpenDetail(false);
            }}
          >
            重新生成
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default CapacityPlanning;

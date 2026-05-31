import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  CircularProgress,
  Alert,
  Chip,
  Divider,
  Button,
  IconButton,
  Tooltip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableRow,
  Paper,
} from '@mui/material';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip as ChartTooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Bar, Doughnut, Line } from 'react-chartjs-2';
import {
  Refresh as RefreshIcon,
  CompareArrows as CompareIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Remove as RemoveIcon,
} from '@mui/icons-material';
import { serviceApi, faultApi } from '../services/api';
import ServiceTopologySelector from '../components/ServiceTopologySelector';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  ChartTooltip,
  Legend,
  Filler
);

function Services() {
  const [services, setServices] = useState([]);
  const [selectedService, setSelectedService] = useState('');
  const [selectedFault, setSelectedFault] = useState('');
  const [faults, setFaults] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [beforeWindow, setBeforeWindow] = useState(5);
  const [afterWindow, setAfterWindow] = useState(5);
  const [topologyOpen, setTopologyOpen] = useState(false);
  const [viewMode, setViewMode] = useState('monitor');

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (selectedService) {
      loadMetrics();
    }
  }, [selectedService]);

  useEffect(() => {
    if (selectedService && selectedFault) {
      loadComparison();
    }
  }, [selectedService, selectedFault, beforeWindow, afterWindow]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [servicesData, faultsData] = await Promise.all([
        serviceApi.list().catch(() => []),
        faultApi.list().catch(() => []),
      ]);
      setServices(servicesData);
      setFaults(faultsData.filter((f) => f.started_at));
      if (servicesData.length > 0) {
        setSelectedService(servicesData[0]);
      }
    } catch (err) {
      setError('加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const loadMetrics = async () => {
    try {
      const data = await serviceApi.getMetrics(selectedService, '15m');
      setMetrics(data);
    } catch (err) {
      console.error('Failed to load metrics:', err);
    }
  };

  const loadComparison = async () => {
    try {
      const data = await serviceApi.getComparison(selectedService, {
        fault_id: selectedFault,
        before_window: beforeWindow,
        after_window: afterWindow,
      });
      setComparison(data);
    } catch (err) {
      console.error('Failed to load comparison:', err);
    }
  };

  const handleRefresh = () => {
    if (viewMode === 'monitor') {
      loadMetrics();
    } else {
      loadComparison();
    }
  };

  const formatChange = (value, isBetterHigher = false) => {
    if (value === 0 || value === undefined || value === null) {
      return <Chip label="无变化" size="small" />;
    }
    const isPositive = value > 0;
    const isBetter = isBetterHigher ? isPositive : !isPositive;
    const Icon = isPositive ? TrendingUpIcon : TrendingDownIcon;

    return (
      <Chip
        icon={<Icon fontSize="small" />}
        label={`${isPositive ? '+' : ''}${value.toFixed(2)}%`}
        color={isBetter ? 'success' : 'error'}
        size="small"
        variant="outlined"
      />
    );
  };

  const formatDiffValue = (value, unit = '') => {
    if (value === undefined || value === null) return '-';
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}${unit}`;
  };

  const latencyChartData = useMemo(() => {
    if (!metrics) return null;
    return {
      labels: ['平均延迟', 'P95延迟', 'P99延迟'],
      datasets: [
        {
          label: '延迟 (ms)',
          data: [metrics.avg_latency_ms, metrics.p95_latency_ms, metrics.p99_latency_ms],
          backgroundColor: [
            'rgba(54, 162, 235, 0.7)',
            'rgba(255, 206, 86, 0.7)',
            'rgba(255, 99, 132, 0.7)',
          ],
        },
      ],
    };
  }, [metrics]);

  const errorChartData = useMemo(() => {
    if (!metrics) return null;
    return {
      labels: ['成功请求', '错误请求'],
      datasets: [
        {
          data: [metrics.request_count - metrics.error_count, metrics.error_count],
          backgroundColor: ['rgba(75, 192, 192, 0.7)', 'rgba(255, 99, 132, 0.7)'],
        },
      ],
    };
  }, [metrics]);

  const comparisonLineChartData = useMemo(() => {
    if (!comparison || !comparison.before || !comparison.after) return null;

    const beforeSeries = comparison.before.latency_series || [];
    const afterSeries = comparison.after.latency_series || [];

    const beforeLabels = beforeSeries.map((p, i) => `T-${beforeSeries.length - i}`);
    const afterLabels = afterSeries.map((p, i) => `T+${i + 1}`);
    const labels = [...beforeLabels, ...afterLabels];

    const beforeData = beforeSeries.map((p) => p.value);
    const afterData = afterSeries.map((p) => p.value);

    return {
      labels,
      datasets: [
        {
          label: '故障前',
          data: beforeData,
          borderColor: 'rgba(75, 192, 192, 1)',
          backgroundColor: 'rgba(75, 192, 192, 0.1)',
          fill: true,
          tension: 0.3,
        },
        {
          label: '故障后',
          data: [...new Array(beforeData.length).fill(null), ...afterData],
          borderColor: 'rgba(255, 99, 132, 1)',
          backgroundColor: 'rgba(255, 99, 132, 0.1)',
          fill: true,
          tension: 0.3,
        },
      ],
    };
  }, [comparison]);

  const comparisonBarChartData = useMemo(() => {
    if (!comparison || !comparison.before || !comparison.after) return null;

    return {
      labels: ['平均延迟', 'P95延迟', 'P99延迟', '错误率(%)'],
      datasets: [
        {
          label: '故障前',
          data: [
            comparison.before.avg_latency_ms,
            comparison.before.p95_latency_ms,
            comparison.before.p99_latency_ms,
            comparison.before.error_rate,
          ],
          backgroundColor: 'rgba(75, 192, 192, 0.7)',
        },
        {
          label: '故障后',
          data: [
            comparison.after.avg_latency_ms,
            comparison.after.p95_latency_ms,
            comparison.after.p99_latency_ms,
            comparison.after.error_rate,
          ],
          backgroundColor: 'rgba(255, 99, 132, 0.7)',
        },
      ],
    };
  }, [comparison]);

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
        <Typography variant="h4">服务监控</Typography>
        <Box display="flex" gap={2} alignItems="center">
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <Select
              value={viewMode}
              onChange={(e) => setViewMode(e.target.value)}
              displayEmpty
            >
              <MenuItem value="monitor">实时监控</MenuItem>
              <MenuItem value="comparison">故障对比</MenuItem>
            </Select>
          </FormControl>
          <Tooltip title="刷新">
            <IconButton onClick={handleRefresh}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={5}>
          <FormControl fullWidth>
            <InputLabel>选择服务</InputLabel>
            <Select
              value={selectedService}
              onChange={(e) => setSelectedService(e.target.value)}
              label="选择服务"
              endAdornment={
                <IconButton size="small" sx={{ mr: 2 }} onClick={() => setTopologyOpen(true)}>
                  <CompareIcon fontSize="small" />
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

        {viewMode === 'comparison' && (
          <>
            <Grid item xs={12} sm={4}>
              <FormControl fullWidth>
                <InputLabel>选择故障</InputLabel>
                <Select
                  value={selectedFault}
                  onChange={(e) => setSelectedFault(e.target.value)}
                  label="选择故障"
                >
                  <MenuItem value="">
                    <em>选择要对比的故障</em>
                  </MenuItem>
                  {faults.map((f) => (
                    <MenuItem key={f.id} value={f.id}>
                      {f.name} ({new Date(f.started_at).toLocaleString()})
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={6} sm={1.5}>
              <FormControl fullWidth>
                <InputLabel>故障前(分钟)</InputLabel>
                <Select
                  value={beforeWindow}
                  onChange={(e) => setBeforeWindow(e.target.value)}
                  label="故障前(分钟)"
                >
                  <MenuItem value={1}>1</MenuItem>
                  <MenuItem value={3}>3</MenuItem>
                  <MenuItem value={5}>5</MenuItem>
                  <MenuItem value={10}>10</MenuItem>
                  <MenuItem value={15}>15</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={6} sm={1.5}>
              <FormControl fullWidth>
                <InputLabel>故障后(分钟)</InputLabel>
                <Select
                  value={afterWindow}
                  onChange={(e) => setAfterWindow(e.target.value)}
                  label="故障后(分钟)"
                >
                  <MenuItem value={1}>1</MenuItem>
                  <MenuItem value={3}>3</MenuItem>
                  <MenuItem value={5}>5</MenuItem>
                  <MenuItem value={10}>10</MenuItem>
                  <MenuItem value={15}>15</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </>
        )}
      </Grid>

      {selectedService && viewMode === 'monitor' && metrics && (
        <>
          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography variant="h6" color="text.secondary" gutterBottom>
                    请求总数
                  </Typography>
                  <Typography variant="h3" fontWeight="bold">
                    {metrics.request_count}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography variant="h6" color="text.secondary" gutterBottom>
                    平均延迟
                  </Typography>
                  <Typography variant="h3" fontWeight="bold" color="#1976d2">
                    {metrics.avg_latency_ms.toFixed(2)}
                    <Typography component="span" variant="body1">
                      {' '}ms
                    </Typography>
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography variant="h6" color="text.secondary" gutterBottom>
                    P99 延迟
                  </Typography>
                  <Typography variant="h3" fontWeight="bold" color="#ff9800">
                    {metrics.p99_latency_ms.toFixed(2)}
                    <Typography component="span" variant="body1">
                      {' '}ms
                    </Typography>
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography variant="h6" color="text.secondary" gutterBottom>
                    错误率
                  </Typography>
                  <Typography
                    variant="h3"
                    fontWeight="bold"
                    color={metrics.error_rate > 5 ? '#f44336' : '#4caf50'}
                  >
                    {metrics.error_rate.toFixed(2)}
                    <Typography component="span" variant="body1">
                      {' '}%
                    </Typography>
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    延迟分布
                  </Typography>
                  <Box sx={{ height: 300 }}>
                    <Bar
                      data={latencyChartData}
                      options={{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                      }}
                    />
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    成功率分布
                  </Typography>
                  <Box sx={{ height: 300, display: 'flex', justifyContent: 'center' }}>
                    <Doughnut
                      data={errorChartData}
                      options={{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { position: 'bottom' } },
                      }}
                    />
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </>
      )}

      {viewMode === 'comparison' && selectedFault && comparison && (
        <>
          <Box mb={3}>
            <Card variant="outlined" sx={{ backgroundColor: '#f5f5f5' }}>
              <CardContent>
                <Box display="flex" alignItems="center" gap={2} mb={2}>
                  <CompareIcon color="primary" />
                  <Typography variant="h6">
                    故障前后对比 - {faults.find((f) => f.id === selectedFault)?.name}
                  </Typography>
                </Box>
                <Box display="flex" gap={4}>
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      故障发生时间
                    </Typography>
                    <Typography variant="body1" fontWeight="bold">
                      {new Date(
                        faults.find((f) => f.id === selectedFault)?.started_at
                      ).toLocaleString()}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      时间窗口
                    </Typography>
                    <Typography variant="body1" fontWeight="bold">
                      故障前 {beforeWindow} 分钟 / 故障后 {afterWindow} 分钟
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Box>

          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    对比结果汇总
                  </Typography>
                  <TableContainer component={Paper} variant="outlined">
                    <Table size="small">
                      <TableBody>
                        <TableRow>
                          <TableCell>指标</TableCell>
                          <TableCell align="right">故障前</TableCell>
                          <TableCell align="right">故障后</TableCell>
                          <TableCell align="right">差值</TableCell>
                          <TableCell align="right">变化率</TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell>平均延迟 (ms)</TableCell>
                          <TableCell align="right">
                            {comparison.before?.avg_latency_ms?.toFixed(2) || '-'}
                          </TableCell>
                          <TableCell align="right">
                            {comparison.after?.avg_latency_ms?.toFixed(2) || '-'}
                          </TableCell>
                          <TableCell align="right">
                            {formatDiffValue(comparison.diff?.avg_latency_diff, ' ms')}
                          </TableCell>
                          <TableCell align="right">
                            {formatChange(comparison.diff?.avg_latency_change)}
                          </TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell>P95延迟 (ms)</TableCell>
                          <TableCell align="right">
                            {comparison.before?.p95_latency_ms?.toFixed(2) || '-'}
                          </TableCell>
                          <TableCell align="right">
                            {comparison.after?.p95_latency_ms?.toFixed(2) || '-'}
                          </TableCell>
                          <TableCell align="right">
                            {formatDiffValue(comparison.diff?.p95_latency_diff, ' ms')}
                          </TableCell>
                          <TableCell align="right">
                            {formatChange(comparison.diff?.p95_latency_change)}
                          </TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell>P99延迟 (ms)</TableCell>
                          <TableCell align="right">
                            {comparison.before?.p99_latency_ms?.toFixed(2) || '-'}
                          </TableCell>
                          <TableCell align="right">
                            {comparison.after?.p99_latency_ms?.toFixed(2) || '-'}
                          </TableCell>
                          <TableCell align="right">
                            {formatDiffValue(comparison.diff?.p99_latency_diff, ' ms')}
                          </TableCell>
                          <TableCell align="right">
                            {formatChange(comparison.diff?.p99_latency_change)}
                          </TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell>错误率 (%)</TableCell>
                          <TableCell align="right">
                            {comparison.before?.error_rate?.toFixed(2) || '-'}
                          </TableCell>
                          <TableCell align="right">
                            {comparison.after?.error_rate?.toFixed(2) || '-'}
                          </TableCell>
                          <TableCell align="right">
                            {formatDiffValue(comparison.diff?.error_rate_diff, '%')}
                          </TableCell>
                          <TableCell align="right">
                            {formatChange(comparison.diff?.error_rate_change, false)}
                          </TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell>请求数</TableCell>
                          <TableCell align="right">
                            {comparison.before?.request_count || '-'}
                          </TableCell>
                          <TableCell align="right">
                            {comparison.after?.request_count || '-'}
                          </TableCell>
                          <TableCell align="right">
                            {formatDiffValue(comparison.diff?.request_count_diff, '')}
                          </TableCell>
                          <TableCell align="right">
                            <RemoveIcon fontSize="small" />
                          </TableCell>
                        </TableRow>
                      </TableBody>
                    </Table>
                  </TableContainer>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          <Grid container spacing={3}>
            <Grid item xs={12} md={7}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    延迟时间序列对比
                  </Typography>
                  <Box sx={{ height: 350 }}>
                    {comparisonLineChartData ? (
                      <Line
                        data={comparisonLineChartData}
                        options={{
                          responsive: true,
                          maintainAspectRatio: false,
                          plugins: {
                            legend: { position: 'top' },
                          },
                          scales: {
                            x: {
                              grid: {
                                color: (context) => {
                                  const beforeLength = comparison.before?.latency_series?.length || 0;
                                  return context.index === beforeLength - 1
                                    ? 'rgba(255, 0, 0, 0.5)'
                                    : 'rgba(0, 0, 0, 0.1)';
                                },
                                lineWidth: (context) => {
                                  const beforeLength = comparison.before?.latency_series?.length || 0;
                                  return context.index === beforeLength - 1 ? 2 : 1;
                                },
                              },
                            },
                          },
                        }}
                      />
                    ) : (
                      <Box
                        display="flex"
                        justifyContent="center"
                        alignItems="center"
                        height="100%"
                      >
                        <Typography color="text.secondary">暂无时序数据</Typography>
                      </Box>
                    )}
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={5}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    指标对比柱状图
                  </Typography>
                  <Box sx={{ height: 350 }}>
                    {comparisonBarChartData ? (
                      <Bar
                        data={comparisonBarChartData}
                        options={{
                          responsive: true,
                          maintainAspectRatio: false,
                          plugins: {
                            legend: { position: 'top' },
                          },
                        }}
                      />
                    ) : (
                      <Box
                        display="flex"
                        justifyContent="center"
                        alignItems="center"
                        height="100%"
                      >
                        <Typography color="text.secondary">暂无对比数据</Typography>
                      </Box>
                    )}
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </>
      )}

      {viewMode === 'comparison' && !selectedFault && (
        <Alert severity="info">请选择一个故障进行前后对比分析</Alert>
      )}

      <ServiceTopologySelector
        open={topologyOpen}
        onClose={() => setTopologyOpen(false)}
        selectedService={selectedService}
        onSelect={(selection) => {
          setSelectedService(selection.service);
        }}
      />
    </Box>
  );
}

export default Services;

import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  Chip,
  LinearProgress,
  Button,
  Tabs,
  Tab,
  Paper,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import {
  Timeline as TimelineIcon,
  TrendingUp as TrendingUpIcon,
  Warning as WarningIcon,
  BugReport as BugReportIcon,
  DateRange as DateRangeIcon,
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
  ComposedChart,
  Bar,
} from 'recharts';
import dayjs from 'dayjs';
import { serviceApi, metricsApi } from '../services/api';

const WINDOW_TYPES = [
  { value: 'SLIDING_HOUR', label: '滑动1小时' },
  { value: 'SLIDING_DAY', label: '滑动1天' },
  { value: 'CALENDAR_DAY', label: '自然日' },
  { value: 'CALENDAR_WEEK', label: '自然周' },
  { value: 'CALENDAR_MONTH', label: '自然月' },
];

function ServiceDetail() {
  const { name } = useParams();
  const [service, setService] = useState(null);
  const [latestMetrics, setLatestMetrics] = useState(null);
  const [windowMetrics, setWindowMetrics] = useState(null);
  const [allWindows, setAllWindows] = useState({});
  const [historyData, setHistoryData] = useState([]);
  const [predictionData, setPredictionData] = useState(null);
  const [rootCause, setRootCause] = useState(null);
  const [activeTab, setActiveTab] = useState(0);
  const [windowType, setWindowType] = useState('SLIDING_HOUR');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [name, windowType]);

  const fetchData = async () => {
    try {
      const [serviceRes, metricsRes, windowRes, allWindowsRes, historyRes, predictionRes, rootCauseRes] =
        await Promise.all([
          serviceApi.getByName(name),
          metricsApi.getLatest(name),
          metricsApi.getWindowMetrics(name, windowType),
          metricsApi.getAllWindows(name),
          metricsApi.getHistory(name, 24, windowType),
          metricsApi.getPrediction(name),
          metricsApi.getRootCause(name),
        ]);

      setService(serviceRes.data);
      setLatestMetrics(metricsRes.data);
      setWindowMetrics(windowRes.data);
      setAllWindows(allWindowsRes.data || {});
      setHistoryData(historyRes.data || []);
      setPredictionData(predictionRes.data);
      setRootCause(rootCauseRes.data);
    } catch (error) {
      console.error('Failed to fetch service data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getEffectiveTarget = (field) => {
    if (!service) return null;
    return service[`effective${field.charAt(0).toUpperCase() + field.slice(1)}Target`] || service[`${field}Target`];
  };

  const chartData = historyData.map((item) => ({
    time: dayjs(item.timestamp).format('HH:mm'),
    availability: item.availability,
    latency: item.avgLatencyMs,
    errorRate: item.errorRate,
    sla: item.slaAchievementRate,
  }));

  const combinedPredictionData = [
    ...(predictionData?.historicalData || []).map((item) => ({
      time: dayjs(item.timestamp).format('HH:mm'),
      historical: item.value,
      predicted: null,
    })),
    ...(predictionData?.predictedData || []).map((item) => ({
      time: dayjs(item.timestamp).format('HH:mm'),
      historical: null,
      predicted: item.value,
    })),
  ];

  if (loading) {
    return <LinearProgress />;
  }

  const displayMetrics = windowMetrics || latestMetrics;
  const availTarget = getEffectiveTarget('availability');
  const latencyTarget = getEffectiveTarget('latencyMs');
  const errorTarget = getEffectiveTarget('errorRate');

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4">{name}</Typography>
          <Typography variant="subtitle1" color="textSecondary">
            {service?.description}
            {service?.slaTier && (
              <Chip
                label={service.slaTier.tierName}
                size="small"
                sx={{ ml: 1 }}
                color={service.slaTier.priorityLevel <= 2 ? 'error' : service.slaTier.priorityLevel <= 3 ? 'primary' : 'info'}
              />
            )}
          </Typography>
        </Box>
        <Box display="flex" gap={2} alignItems="center">
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel>窗口类型</InputLabel>
            <Select
              value={windowType}
              label="窗口类型"
              onChange={(e) => setWindowType(e.target.value)}
              startAdornment={<DateRangeIcon sx={{ mr: 1, color: 'action.active' }} />}
            >
              {WINDOW_TYPES.map((wt) => (
                <MenuItem key={wt.value} value={wt.value}>
                  {wt.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Chip
            label={displayMetrics?.slaViolated ? 'SLA违规' : '正常'}
            color={displayMetrics?.slaViolated ? 'error' : 'success'}
          />
          <Button
            variant="contained"
            onClick={() => metricsApi.simulate(name, 200).then(fetchData)}
          >
            生成流量
          </Button>
        </Box>
      </Box>

      {allWindows && Object.keys(allWindows).length > 0 && (
        <Grid container spacing={2} mb={3}>
          {WINDOW_TYPES.map((wt) => {
            const wm = allWindows[wt.value];
            if (!wm) return null;
            return (
              <Grid item xs={12} sm={6} md={2.4} key={wt.value}>
                <Card
                  sx={{
                    cursor: 'pointer',
                    border: windowType === wt.value ? 2 : 0,
                    borderColor: 'primary.main',
                  }}
                  onClick={() => setWindowType(wt.value)}
                >
                  <CardContent sx={{ py: 1.5, px: 2 }}>
                    <Typography variant="caption" color="textSecondary">
                      {wt.label}
                    </Typography>
                    <Box display="flex" justifyContent="space-between" alignItems="center">
                      <Typography variant="h6" color={wm.slaViolated ? 'error' : 'primary'}>
                        {wm.availability?.toFixed(1)}%
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        {wm.totalRequests || 0} 请求
                      </Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={wm.windowProgressPercent || 0}
                      sx={{ height: 4, borderRadius: 2, mt: 1 }}
                    />
                    <Typography variant="caption" color="textSecondary">
                      进度: {wm.windowProgressPercent?.toFixed(0) || 0}%
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            );
          })}
        </Grid>
      )}

      <Grid container spacing={3} mb={3}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                可用性
              </Typography>
              <Typography variant="h4" color={displayMetrics?.availability < availTarget ? 'error' : 'primary'}>
                {displayMetrics?.availability?.toFixed(2)}%
              </Typography>
              <Typography variant="caption">
                目标: {availTarget}%
                {service?.useTierTargets && service?.slaTier && ' (来自等级配置)'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                平均延迟
              </Typography>
              <Typography
                variant="h4"
                color={displayMetrics?.avgLatencyMs > latencyTarget ? 'error' : 'primary'}
              >
                {displayMetrics?.avgLatencyMs?.toFixed(0)}ms
              </Typography>
              <Typography variant="caption">
                目标: {latencyTarget}ms
                {service?.useTierTargets && service?.slaTier && ' (来自等级配置)'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                错误率
              </Typography>
              <Typography
                variant="h4"
                color={displayMetrics?.errorRate > errorTarget ? 'error' : 'primary'}
              >
                {displayMetrics?.errorRate?.toFixed(2)}%
              </Typography>
              <Typography variant="caption">
                目标: {errorTarget}%
                {service?.useTierTargets && service?.slaTier && ' (来自等级配置)'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                SLA 达成率
              </Typography>
              <Typography
                variant="h4"
                color={displayMetrics?.slaAchievementRate < 95 ? 'error' : 'primary'}
              >
                {displayMetrics?.slaAchievementRate?.toFixed(2)}%
              </Typography>
              <LinearProgress
                variant="determinate"
                value={displayMetrics?.slaAchievementRate || 0}
                sx={{ mt: 1 }}
              />
              <Box display="flex" justifyContent="space-between" mt={1}>
                <Typography variant="caption" color="textSecondary">
                  P95: {displayMetrics?.p95LatencyMs?.toFixed(0) || 0}ms
                </Typography>
                <Typography variant="caption" color="textSecondary">
                  P99: {displayMetrics?.p99LatencyMs?.toFixed(0) || 0}ms
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={activeTab}
          onChange={(_, newValue) => setActiveTab(newValue)}
          indicatorColor="primary"
          textColor="primary"
        >
          <Tab icon={<TimelineIcon />} label="指标趋势" />
          <Tab icon={<TrendingUpIcon />} label="趋势预测" />
          <Tab icon={<BugReportIcon />} label="根因分析" />
        </Tabs>
      </Paper>

      {activeTab === 0 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  可用性 & SLA达成率
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time" />
                    <YAxis domain={[90, 100]} />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="availability" stroke="#82ca9d" name="可用性" />
                    <Line type="monotone" dataKey="sla" stroke="#8884d8" name="SLA达成率" />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  延迟 & 错误率
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <ComposedChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time" />
                    <YAxis yAxisId="left" />
                    <YAxis yAxisId="right" orientation="right" />
                    <Tooltip />
                    <Legend />
                    <Bar yAxisId="left" dataKey="errorRate" fill="#ffc658" name="错误率(%)" />
                    <Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="latency"
                      stroke="#ff8042"
                      name="延迟(ms)"
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {activeTab === 1 && predictionData && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={8}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  SLA达成率预测
                </Typography>
                <ResponsiveContainer width="100%" height={400}>
                  <LineChart data={combinedPredictionData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time" />
                    <YAxis domain={[80, 100]} />
                    <Tooltip />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="historical"
                      stroke="#8884d8"
                      name="历史数据"
                      strokeWidth={2}
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="predicted"
                      stroke="#ffc658"
                      name="预测数据"
                      strokeWidth={2}
                      strokeDasharray="5 5"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  预测分析
                </Typography>
                <Box mb={2}>
                  <Typography color="textSecondary">趋势方向</Typography>
                  <Box display="flex" alignItems="center">
                    <TrendingUpIcon
                      color={
                        predictionData.trendDirection === 'IMPROVING'
                          ? 'success'
                          : predictionData.trendDirection === 'DEGRADING'
                          ? 'error'
                          : 'action'
                      }
                    />
                    <Typography variant="h6" ml={1}>
                      {predictionData.trendDirection === 'IMPROVING'
                        ? '改善中'
                        : predictionData.trendDirection === 'DEGRADING'
                        ? '下降中'
                        : predictionData.trendDirection === 'INSUFFICIENT_DATA'
                        ? '数据不足'
                        : '稳定'}
                    </Typography>
                  </Box>
                </Box>
                <Box mb={2}>
                  <Typography color="textSecondary">预测SLA达成率</Typography>
                  <Typography variant="h4">
                    {predictionData.predictedSlaRate?.toFixed(2)}%
                  </Typography>
                </Box>
                <Box mb={2}>
                  <Typography color="textSecondary">预测违规风险</Typography>
                  <Chip
                    label={predictionData.predictedViolation ? '高风险' : '低风险'}
                    color={predictionData.predictedViolation ? 'error' : 'success'}
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {activeTab === 2 && rootCause && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  根因分析结果
                </Typography>
                <Box mb={3}>
                  <Typography color="textSecondary">主要原因</Typography>
                  <Box display="flex" alignItems="center" mt={1}>
                    <WarningIcon color="warning" sx={{ mr: 1 }} />
                    <Typography variant="h6">
                      {rootCause.primaryCause === 'HIGH_ERROR_RATE'
                        ? '高错误率'
                        : rootCause.primaryCause === 'LATENCY_SPIKE'
                        ? '延迟突增'
                        : rootCause.primaryCause === 'TRAFFIC_SURGE'
                        ? '流量暴增'
                        : rootCause.primaryCause === 'INSUFFICIENT_DATA'
                        ? '数据不足'
                        : '未知'}
                    </Typography>
                  </Box>
                </Box>
                <Box mb={3}>
                  <Typography color="textSecondary">置信度</Typography>
                  <LinearProgress
                    variant="determinate"
                    value={(rootCause.confidenceScore || 0) * 100}
                    sx={{ mt: 1, height: 10, borderRadius: 5 }}
                  />
                  <Typography variant="body2" align="right">
                    {(rootCause.confidenceScore * 100)?.toFixed(0)}%
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  影响因素
                </Typography>
                <List>
                  {rootCause.contributingFactors?.map((factor, index) => (
                    <ListItem key={index}>
                      <ListItemIcon>
                        <BugReportIcon color="action" />
                      </ListItemIcon>
                      <ListItemText primary={factor} />
                    </ListItem>
                  ))}
                </List>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  建议措施
                </Typography>
                <List>
                  {rootCause.recommendations?.map((rec, index) => (
                    <ListItem key={index}>
                      <ListItemIcon>
                        <TrendingUpIcon color="primary" />
                      </ListItemIcon>
                      <ListItemText primary={rec} />
                    </ListItem>
                  ))}
                </List>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}
    </Box>
  );
}

export default ServiceDetail;

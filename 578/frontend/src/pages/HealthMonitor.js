import React, { useState, useEffect } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Paper,
  CircularProgress,
  Alert,
  Chip,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
  LinearProgress,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Favorite,
  Warning,
  Error,
  Info,
  TrendingDown,
  TrendingUp,
  TrendingFlat,
  Refresh,
  AccessTime,
  Memory,
  Speed,
  Layers,
  SwapHoriz,
} from '@mui/icons-material';
import { useParams } from 'react-router-dom';
import { jobApi } from '../services/api';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  Legend,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from 'recharts';

const HealthMonitor = () => {
  const { jobId } = useParams();
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadHealthData();
  }, [jobId]);

  const loadHealthData = async () => {
    try {
      setLoading(true);
      const response = await jobApi.getMockHealthDashboard();
      setHealthData(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to load health data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const getHealthColor = (score) => {
    if (score >= 0.8) return '#4caf50';
    if (score >= 0.6) return '#ff9800';
    if (score >= 0.4) return '#ff5722';
    return '#f44336';
  };

  const getHealthLevelColor = (level) => {
    switch (level) {
      case 'EXCELLENT': return '#4caf50';
      case 'GOOD': return '#8bc34a';
      case 'FAIR': return '#ff9800';
      case 'POOR': return '#ff5722';
      case 'CRITICAL': return '#f44336';
      default: return '#9e9e9e';
    }
  };

  const getSeverityIcon = (severity) => {
    switch (severity) {
      case 'CRITICAL': return <Error color="error" />;
      case 'WARNING': return <Warning color="warning" />;
      default: return <Info color="info" />;
    }
  };

  const getTrendIcon = (predicted, current) => {
    const diff = predicted - current;
    if (diff > 0.05) return <TrendingUp sx={{ color: '#4caf50' }} />;
    if (diff < -0.05) return <TrendingDown sx={{ color: '#f44336' }} />;
    return <TrendingFlat sx={{ color: '#ff9800' }} />;
  };

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleString();
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !healthData) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{error || 'No data available'}</Alert>
      </Box>
    );
  }

  const { healthScore, warnings, predictionMetrics, healthHistory } = healthData;

  const radarData = [
    { subject: 'CPU', A: healthScore.cpuHealth * 100, fullMark: 100 },
    { subject: 'Memory', A: healthScore.memoryHealth * 100, fullMark: 100 },
    { subject: 'Network', A: healthScore.networkHealth * 100, fullMark: 100 },
    { subject: 'Skew', A: healthScore.skewHealth * 100, fullMark: 100 },
    { subject: 'Throughput', A: healthScore.throughputHealth * 100, fullMark: 100 },
  ];

  const historyChartData = healthHistory?.map(h => ({
    time: new Date(h.timestamp).toLocaleDateString(),
    healthScore: h.healthScore * 100,
    cpu: h.cpuUtilization * 100,
    memory: h.memoryUtilization * 100,
  })) || [];

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3, alignItems: 'center' }}>
        <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#1a237e' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Favorite sx={{ color: '#e91e63' }} />
            Job Health Monitor
          </Box>
        </Typography>
        <Tooltip title="Refresh">
          <IconButton onClick={loadHealthData}>
            <Refresh />
          </IconButton>
        </Tooltip>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Card sx={{
            background: `linear-gradient(135deg, ${getHealthColor(healthScore.overallScore)} 0%, ${getHealthColor(healthScore.overallScore)}dd 100%)`,
            color: 'white',
            height: '100%'
          }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="body2" sx={{ opacity: 0.9, mb: 2 }}>
                Overall Health Score
              </Typography>
              <Typography variant="h2" sx={{ fontWeight: 'bold', mb: 1 }}>
                {Math.round(healthScore.overallScore * 100)}
              </Typography>
              <Chip
                label={healthScore.healthLevel}
                sx={{
                  bgcolor: 'rgba(255,255,255,0.3)',
                  color: 'white',
                  fontWeight: 'bold'
                }}
              />
              <Box sx={{ mt: 3 }}>
                <Grid container spacing={2}>
                  <Grid item xs={4}>
                    <Typography variant="body2" sx={{ opacity: 0.8 }}>1h Forecast</Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1 }}>
                      {getTrendIcon(healthScore.predictedScore1h, healthScore.overallScore)}
                      <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                        {Math.round(healthScore.predictedScore1h * 100)}
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={4}>
                    <Typography variant="body2" sx={{ opacity: 0.8 }}>6h Forecast</Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1 }}>
                      {getTrendIcon(healthScore.predictedScore6h, healthScore.overallScore)}
                      <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                        {Math.round(healthScore.predictedScore6h * 100)}
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={4}>
                    <Typography variant="body2" sx={{ opacity: 0.8 }}>24h Forecast</Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1 }}>
                      {getTrendIcon(healthScore.predictedScore24h, healthScore.overallScore)}
                      <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                        {Math.round(healthScore.predictedScore24h * 100)}
                      </Typography>
                    </Box>
                  </Grid>
                </Grid>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, height: '100%' }}>
            <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
              Health Dimensions
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Speed fontSize="small" /> CPU Health
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                    {Math.round(healthScore.cpuHealth * 100)}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={healthScore.cpuHealth * 100}
                  sx={{ height: 8, borderRadius: 4, bgcolor: '#e0e0e0',
                    '& .MuiLinearProgress-bar': { bgcolor: getHealthColor(healthScore.cpuHealth) } }}
                />
              </Box>
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Memory fontSize="small" /> Memory Health
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                    {Math.round(healthScore.memoryHealth * 100)}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={healthScore.memoryHealth * 100}
                  sx={{ height: 8, borderRadius: 4, bgcolor: '#e0e0e0',
                    '& .MuiLinearProgress-bar': { bgcolor: getHealthColor(healthScore.memoryHealth) } }}
                />
              </Box>
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <SwapHoriz fontSize="small" /> Network Health
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                    {Math.round(healthScore.networkHealth * 100)}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={healthScore.networkHealth * 100}
                  sx={{ height: 8, borderRadius: 4, bgcolor: '#e0e0e0',
                    '& .MuiLinearProgress-bar': { bgcolor: getHealthColor(healthScore.networkHealth) } }}
                />
              </Box>
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Layers fontSize="small" /> Skew Health
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                    {Math.round(healthScore.skewHealth * 100)}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={healthScore.skewHealth * 100}
                  sx={{ height: 8, borderRadius: 4, bgcolor: '#e0e0e0',
                    '& .MuiLinearProgress-bar': { bgcolor: getHealthColor(healthScore.skewHealth) } }}
                />
              </Box>
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <AccessTime fontSize="small" /> Throughput Health
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                    {Math.round(healthScore.throughputHealth * 100)}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={healthScore.throughputHealth * 100}
                  sx={{ height: 8, borderRadius: 4, bgcolor: '#e0e0e0',
                    '& .MuiLinearProgress-bar': { bgcolor: getHealthColor(healthScore.throughputHealth) } }}
                />
              </Box>
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, height: '100%' }}>
            <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
              Health Radar
            </Typography>
            <ResponsiveContainer width="100%" height={280}>
              <RadarChart data={radarData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="subject" />
                <PolarRadiusAxis angle={30} domain={[0, 100]} />
                <Radar
                  name="Health"
                  dataKey="A"
                  stroke={getHealthColor(healthScore.overallScore)}
                  fill={getHealthColor(healthScore.overallScore)}
                  fillOpacity={0.5}
                />
              </RadarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
              Health Factors
            </Typography>
            <List>
              {healthScore.healthFactors?.map((factor, i) => (
                <ListItem key={i} sx={{ py: 1 }}>
                  <ListItemIcon>
                    <Info color="primary" />
                  </ListItemIcon>
                  <ListItemText primary={factor} />
                </ListItem>
              ))}
            </List>
            {predictionMetrics && (
              <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid #e0e0e0' }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                  Prediction Metrics
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Typography variant="body2">
                      Prediction Confidence: {(predictionMetrics.predictionConfidence * 100)?.toFixed(0)}%
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2">
                      Data Points: {predictionMetrics.sampleCount}
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2">
                      CPU Trend: {(predictionMetrics.cpuTrendSlope * 100)?.toFixed(2)}%/h
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2">
                      Memory Trend: {(predictionMetrics.memoryTrendSlope * 100)?.toFixed(2)}%/h
                    </Typography>
                  </Grid>
                </Grid>
              </Box>
            )}
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Warning color="warning" />
                Warnings & Alerts
                {warnings && warnings.length > 0 && (
                  <Chip label={warnings.length} size="small" color="error" sx={{ ml: 1 }} />
                )}
              </Box>
            </Typography>
            {warnings && warnings.length > 0 ? (
              <List sx={{ maxHeight: 300, overflow: 'auto' }}>
                {warnings.map((warning, i) => (
                  <React.Fragment key={warning.warningId}>
                    <ListItem sx={{
                      bgcolor: warning.severity === 'CRITICAL' ? '#ffebee' :
                               warning.isPrediction ? '#f3e5f5' : '#fff8e1',
                      borderRadius: 1,
                      mb: 1
                    }}>
                      <ListItemIcon>
                        {getSeverityIcon(warning.severity)}
                      </ListItemIcon>
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                              {warning.message}
                            </Typography>
                            {warning.isPrediction && (
                              <Chip label="Predictive" size="small" color="secondary" />
                            )}
                          </Box>
                        }
                        secondary={
                          <Box sx={{ mt: 1 }}>
                            <Typography variant="caption" color="textSecondary">
                              Current: {(warning.currentValue * 100).toFixed(1)}% | 
                              Threshold: {(warning.threshold * 100).toFixed(0)}%
                              {warning.predictedValue && ` | Predicted: ${(warning.predictedValue * 100).toFixed(1)}%`}
                            </Typography>
                            <br />
                            <Typography variant="caption" color="textSecondary">
                              {formatTime(warning.timestamp)}
                            </Typography>
                            {warning.recommendations && warning.recommendations.length > 0 && (
                              <Box sx={{ mt: 1 }}>
                                {warning.recommendations.map((rec, j) => (
                                  <Typography key={j} variant="caption" sx={{ display: 'block', color: '#1565c0' }}>
                                    • {rec}
                                  </Typography>
                                ))}
                              </Box>
                            )}
                          </Box>
                        }
                      />
                    </ListItem>
                    {i < warnings.length - 1 && <Divider />}
                  </React.Fragment>
                ))}
              </List>
            ) : (
              <Box sx={{ textAlign: 'center', py: 4, color: 'text.secondary' }}>
                <Info sx={{ fontSize: 48, color: 'success.main', mb: 2 }} />
                <Typography>No warnings detected</Typography>
                <Typography variant="body2">All metrics within normal range</Typography>
              </Box>
            )}
          </Paper>
        </Grid>

        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
              Health History (7 Days)
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={historyChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis domain={[0, 100]} />
                <RechartsTooltip formatter={(value) => [`${value.toFixed(1)}%`, '']} />
                <Legend />
                <Area
                  type="monotone"
                  dataKey="healthScore"
                  stroke="#e91e63"
                  fill="#e91e63"
                  fillOpacity={0.2}
                  name="Health Score"
                  strokeWidth={2}
                />
                <Area
                  type="monotone"
                  dataKey="cpu"
                  stroke="#1976d2"
                  fill="#1976d2"
                  fillOpacity={0.1}
                  name="CPU Usage"
                  strokeWidth={2}
                />
                <Area
                  type="monotone"
                  dataKey="memory"
                  stroke="#388e3c"
                  fill="#388e3c"
                  fillOpacity={0.1}
                  name="Memory Usage"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default HealthMonitor;

import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Alert,
  Chip,
  LinearProgress,
  Divider,
  Paper,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import {
  Speed,
  Timeline,
  Shield,
  TrendingUp,
  Refresh,
  CheckCircle,
  Warning,
  Error,
  Info,
} from '@mui/icons-material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { resilienceApi, faultApi } from '../services/api';

const gradeColors = {
  S: '#1a9641',
  A: '#a6d96a',
  B: '#fdae61',
  C: '#f46d43',
  D: '#d73027',
  F: '#a50026',
};

const gradeDescriptions = {
  S: '卓越 - 系统韧性极佳',
  A: '优秀 - 系统韧性良好',
  B: '良好 - 系统韧性达标',
  C: '一般 - 需关注部分指标',
  D: '较差 - 建议重点优化',
  F: '危险 - 亟需改进',
};

function Resilience() {
  const [faults, setFaults] = useState([]);
  const [selectedFault, setSelectedFault] = useState('');
  const [beforeWindow, setBeforeWindow] = useState(5);
  const [afterWindow, setAfterWindow] = useState(5);
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    loadFaults();
  }, []);

  const loadFaults = async () => {
    try {
      const data = await faultApi.list();
      const completedFaults = data.filter((f) => f.started_at);
      setFaults(completedFaults);
    } catch (error) {
      console.error('Failed to load faults:', error);
    }
  };

  const handleCalculate = async () => {
    if (!selectedFault) return;

    try {
      setLoading(true);
      setError('');
      const data = await resilienceApi.getScore(selectedFault, {
        before_window: beforeWindow,
        after_window: afterWindow,
      });
      setReport(data);
    } catch (error) {
      console.error('Failed to calculate resilience score:', error);
      setError('计算韧性评分失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 90) return gradeColors.S;
    if (score >= 80) return gradeColors.A;
    if (score >= 70) return gradeColors.B;
    if (score >= 60) return gradeColors.C;
    if (score >= 50) return gradeColors.D;
    return gradeColors.F;
  };

  const renderGauge = (value, maxValue, color, label) => {
    const percentage = (value / maxValue) * 100;
    return (
      <Box>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
          <Typography variant="body2" color="text.secondary">
            {label}
          </Typography>
          <Typography variant="body2" fontWeight="bold" sx={{ color }}>
            {value.toFixed(1)}
          </Typography>
        </Box>
        <LinearProgress
          variant="determinate"
          value={percentage}
          sx={{
            height: 8,
            borderRadius: 4,
            bgcolor: 'grey.200',
            '& .MuiLinearProgress-bar': {
              backgroundColor: color,
            },
          }}
        />
      </Box>
    );
  };

  const renderRecoveryTrend = () => {
    if (!report?.recovery_trend?.length) return null;

    const data = report.recovery_trend.map((point, index) => ({
      name: `T${index}`,
      recovery: point.recovery_pct,
      latency: point.latency_ms,
      errorRate: point.error_rate_pct,
    }));

    return (
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>
            <Timeline sx={{ mr: 1, verticalAlign: 'middle' }} />
            恢复趋势
          </Typography>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis yAxisId="left" />
              <YAxis yAxisId="right" orientation="right" />
              <Tooltip />
              <Legend />
              <Area
                yAxisId="left"
                type="monotone"
                dataKey="recovery"
                name="恢复度 (%)"
                stroke="#1a9641"
                fill="#a6d96a"
                fillOpacity={0.3}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="latency"
                name="延迟 (ms)"
                stroke="#f46d43"
                strokeWidth={2}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="errorRate"
                name="错误率 (%)"
                stroke="#d73027"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    );
  };

  const renderRecommendations = () => {
    if (!report?.score?.recommendations?.length) return null;

    return (
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>
            <Info sx={{ mr: 1, verticalAlign: 'middle', color: 'info.main' }} />
            优化建议
          </Typography>
          <List>
            {report.score.recommendations.map((rec, index) => (
              <ListItem key={index} sx={{ px: 0 }}>
                <ListItemIcon>
                  {rec.includes('建议') || rec.includes('良好') ? (
                    <CheckCircle color="success" />
                  ) : rec.includes('优化') || rec.includes('检查') ? (
                    <Warning color="warning" />
                  ) : (
                    <Error color="error" />
                  )}
                </ListItemIcon>
                <ListItemText primary={rec} />
              </ListItem>
            ))}
          </List>
        </CardContent>
      </Card>
    );
  };

  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">
          <Shield sx={{ mr: 1, verticalAlign: 'middle' }} />
          韧性评分
        </Typography>
      </Box>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={3} alignItems="center">
            <Grid item xs={12} sm={4}>
              <FormControl fullWidth size="small">
                <InputLabel>选择故障</InputLabel>
                <Select
                  value={selectedFault}
                  label="选择故障"
                  onChange={(e) => setSelectedFault(e.target.value)}
                >
                  {faults.map((f) => (
                    <MenuItem key={f.id} value={f.id}>
                      {f.name} ({f.target_service})
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={6} sm={2}>
              <FormControl fullWidth size="small">
                <InputLabel>故障前窗口</InputLabel>
                <Select
                  value={beforeWindow}
                  label="故障前窗口"
                  onChange={(e) => setBeforeWindow(e.target.value)}
                >
                  {[1, 3, 5, 10, 15].map((m) => (
                    <MenuItem key={m} value={m}>
                      {m} 分钟
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={6} sm={2}>
              <FormControl fullWidth size="small">
                <InputLabel>故障后窗口</InputLabel>
                <Select
                  value={afterWindow}
                  label="故障后窗口"
                  onChange={(e) => setAfterWindow(e.target.value)}
                >
                  {[1, 3, 5, 10, 15].map((m) => (
                    <MenuItem key={m} value={m}>
                      {m} 分钟
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={4}>
              <Button
                variant="contained"
                fullWidth
                startIcon={loading ? <CircularProgress size={20} /> : <Refresh />}
                onClick={handleCalculate}
                disabled={!selectedFault || loading}
              >
                {loading ? '计算中...' : '计算韧性评分'}
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {report && (
        <>
          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Card sx={{ height: '100%' }}>
                <CardContent>
                  <Typography variant="h6" sx={{ mb: 2, textAlign: 'center' }}>
                    综合评分
                  </Typography>
                  <Box
                    sx={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      py: 3,
                    }}
                  >
                    <Box
                      sx={{
                        width: 150,
                        height: 150,
                        borderRadius: '50%',
                        border: `12px solid ${getScoreColor(report.score.overall_score)}`,
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        bgcolor: `${getScoreColor(report.score.overall_score)}15`,
                      }}
                    >
                      <Typography
                        variant="h2"
                        sx={{
                          fontWeight: 'bold',
                          color: getScoreColor(report.score.overall_score),
                        }}
                      >
                        {report.score.overall_score.toFixed(0)}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        / 100
                      </Typography>
                    </Box>
                    <Chip
                      label={report.score.grade}
                      sx={{
                        mt: 2,
                        fontWeight: 'bold',
                        fontSize: 20,
                        px: 2,
                        bgcolor: getScoreColor(report.score.overall_score),
                        color: 'white',
                      }}
                    />
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1, textAlign: 'center' }}>
                      {gradeDescriptions[report.score.grade]}
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={8}>
              <Card sx={{ height: '100%' }}>
                <CardContent>
                  <Typography variant="h6" sx={{ mb: 3 }}>
                    分项评分
                  </Typography>
                  <Grid container spacing={3}>
                    <Grid item xs={12} sm={6}>
                      {renderGauge(
                        report.score.recovery_speed_score,
                        100,
                        getScoreColor(report.score.recovery_speed_score),
                        '恢复速度',
                      )}
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                        恢复时间: {report.score.recovery_time_seconds.toFixed(1)} 秒
                      </Typography>
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      {renderGauge(
                        report.score.stability_score,
                        100,
                        getScoreColor(report.score.stability_score),
                        '稳定性',
                      )}
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                        最大退化: {report.score.max_degradation_pct.toFixed(1)}%
                      </Typography>
                    </Grid>
                    <Grid item xs={12} sm={6} sx={{ mt: 2 }}>
                      {renderGauge(
                        report.score.error_handling_score,
                        100,
                        getScoreColor(report.score.error_handling_score),
                        '错误处理',
                      )}
                    </Grid>
                    <Grid item xs={12} sm={6} sx={{ mt: 2 }}>
                      {renderGauge(
                        report.score.performance_score,
                        100,
                        getScoreColor(report.score.performance_score),
                        '性能恢复',
                      )}
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {renderRecoveryTrend()}
          {renderRecommendations()}
        </>
      )}

      {!report && !loading && !error && (
        <Paper sx={{ p: 6, textAlign: 'center' }}>
          <Shield sx={{ fontSize: 64, color: 'grey.300', mb: 2 }} />
          <Typography variant="h6" color="text.secondary">
            选择故障并点击"计算韧性评分"
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            系统将基于故障前后的指标数据，量化评估系统的恢复能力
          </Typography>
        </Paper>
      )}
    </Box>
  );
}

export default Resilience;

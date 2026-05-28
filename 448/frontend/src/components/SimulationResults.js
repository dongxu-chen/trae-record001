import React from 'react';
import {
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  Box,
  Alert,
  Divider,
} from '@mui/material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import StorageIcon from '@mui/icons-material/Storage';
import SpeedIcon from '@mui/icons-material/Speed';
import ErrorIcon from '@mui/icons-material/Error';
import BoltIcon from '@mui/icons-material/Bolt';

function SimulationResults({ result }) {
  const utilizationData = result.utilizationOverTime
    ? Object.entries(result.utilizationOverTime).map(([time, value]) => ({
        time: `${time}s`,
        utilization: Math.round(value * 100),
      }))
    : [];

  const waitTimeHistogram = React.useMemo(() => {
    if (!result.waitTimeSamples || result.waitTimeSamples.length === 0) return [];
    const maxWait = Math.max(...result.waitTimeSamples);
    const bucketCount = 10;
    const bucketSize = maxWait / bucketCount || 1;
    const histogram = Array(bucketCount).fill(0);

    result.waitTimeSamples.forEach((wait) => {
      const bucketIndex = Math.min(Math.floor(wait / bucketSize), bucketCount - 1);
      histogram[bucketIndex]++;
    });

    return histogram.map((count, i) => ({
      range: `${Math.round(i * bucketSize)}-${Math.round((i + 1) * bucketSize)}ms`,
      count,
    }));
  }, [result.waitTimeSamples]);

  return (
    <Box>
      <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          模拟结果概览
        </Typography>

        <Grid container spacing={3}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <AccessTimeIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="subtitle2" color="text.secondary">
                    平均等待时间
                  </Typography>
                </Box>
                <Typography variant="h4">{result.avgWaitTimeMs?.toFixed(2)} ms</Typography>
                <Typography variant="caption" color="text.secondary">
                  P95: {result.percentile95WaitTimeMs?.toFixed(2)} ms | 最大: {result.maxWaitTimeMs?.toFixed(2)} ms
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <StorageIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="subtitle2" color="text.secondary">
                    连接利用率
                  </Typography>
                </Box>
                <Typography variant="h4">{(result.connectionUtilization * 100).toFixed(1)}%</Typography>
                <Typography variant="caption" color="text.secondary">
                  活跃: {result.avgActiveConnections?.toFixed(1)} 个
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <SpeedIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="subtitle2" color="text.secondary">
                    吞吐量
                  </Typography>
                </Box>
                <Typography variant="h4">{result.throughput?.toFixed(1)}</Typography>
                <Typography variant="caption" color="text.secondary">
                  req/s (共 {result.totalRequests} 次请求)
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <ErrorIcon color="error" sx={{ mr: 1 }} />
                  <Typography variant="subtitle2" color="text.secondary">
                    失败/超时
                  </Typography>
                </Box>
                <Typography variant="h4" color={result.failedRequests > 0 ? 'error' : 'success'}>
                  {result.failedRequests}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  拒绝率: {(result.rejectRate * 100).toFixed(2)}%
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Paper>

      {result.burstinessMetrics && (
        <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <BoltIcon color="warning" sx={{ mr: 1 }} />
            <Typography variant="h6">
              突发性分析 (MAP 模型)
            </Typography>
          </Box>

          <Alert severity={result.burstinessMetrics.burstinessIndex > 2 ? 'warning' : 'success'} sx={{ mb: 2 }}>
            {result.burstinessMetrics.burstinessIndex > 2
              ? `突发指数 ${result.burstinessMetrics.burstinessIndex.toFixed(2)} 较高，流量波动剧烈，建议增加最小空闲连接`
              : `突发指数 ${result.burstinessMetrics.burstinessIndex.toFixed(2)} 适中，流量较为平稳`}
          </Alert>

          <Grid container spacing={2}>
            <Grid item xs={12} sm={4}>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">突发指数</Typography>
                <Typography variant="h6">{result.burstinessMetrics.burstinessIndex?.toFixed(2)}</Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={4}>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">到达间隔 SCV</Typography>
                <Typography variant="h6">{result.burstinessMetrics.interArrivalSquaredCV?.toFixed(2)}</Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={4}>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">突发次数</Typography>
                <Typography variant="h6">{result.burstinessMetrics.burstCount}</Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={4}>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">峰值到达率</Typography>
                <Typography variant="h6">{result.burstinessMetrics.peakArrivalRate?.toFixed(1)} req/s</Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={4}>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">谷值到达率</Typography>
                <Typography variant="h6">{result.burstinessMetrics.valleyArrivalRate?.toFixed(1)} req/s</Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={4}>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">平均突发持续时间</Typography>
                <Typography variant="h6">{result.burstinessMetrics.avgBurstDurationMs?.toFixed(0)} ms</Typography>
              </Box>
            </Grid>
          </Grid>
        </Paper>
      )}

      {result.mixedTransactionMetrics && (
        <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            混合事务分析
          </Typography>

          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Card variant="outlined" sx={{ bgcolor: '#e3f2fd' }}>
                <CardContent>
                  <Typography variant="subtitle1" color="primary" gutterBottom>
                    短查询 ({result.mixedTransactionMetrics.shortQueryCount} 次, {((result.mixedTransactionMetrics.shortQueryRatio || 0) * 100).toFixed(0)}%)
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">平均等待</Typography>
                      <Typography variant="body1">{result.mixedTransactionMetrics.shortQueryAvgWaitTimeMs?.toFixed(2)} ms</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">P95 等待</Typography>
                      <Typography variant="body1">{result.mixedTransactionMetrics.shortQueryP95WaitTimeMs?.toFixed(2)} ms</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">平均服务</Typography>
                      <Typography variant="body1">{result.mixedTransactionMetrics.shortQueryAvgServiceTimeMs?.toFixed(1)} ms</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">超时率</Typography>
                      <Typography variant="body1">{(result.mixedTransactionMetrics.shortQueryTimeoutRate * 100).toFixed(2)}%</Typography>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={6}>
              <Card variant="outlined" sx={{ bgcolor: '#fff3e0' }}>
                <CardContent>
                  <Typography variant="subtitle1" color="warning.dark" gutterBottom>
                    长查询 ({result.mixedTransactionMetrics.longQueryCount} 次, {((1 - (result.mixedTransactionMetrics.shortQueryRatio || 0)) * 100).toFixed(0)}%)
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">平均等待</Typography>
                      <Typography variant="body1">{result.mixedTransactionMetrics.longQueryAvgWaitTimeMs?.toFixed(2)} ms</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">P95 等待</Typography>
                      <Typography variant="body1">{result.mixedTransactionMetrics.longQueryP95WaitTimeMs?.toFixed(2)} ms</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">平均服务</Typography>
                      <Typography variant="body1">{result.mixedTransactionMetrics.longQueryAvgServiceTimeMs?.toFixed(1)} ms</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">超时率</Typography>
                      <Typography variant="body1">{(result.mixedTransactionMetrics.longQueryTimeoutRate * 100).toFixed(2)}%</Typography>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Paper>
      )}

      {result.queueMetrics && (
        <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            排队论分析指标
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={3}>
              <Box sx={{ mb: 1 }}>
                <Typography variant="subtitle2" color="text.secondary">平均队列长度</Typography>
                <Typography variant="h6">{result.queueMetrics.avgQueueLength?.toFixed(2)}</Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={3}>
              <Box sx={{ mb: 1 }}>
                <Typography variant="subtitle2" color="text.secondary">等待概率 (Erlang C)</Typography>
                <Typography variant="h6">{(result.queueMetrics.erlangC * 100).toFixed(1)}%</Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={3}>
              <Box sx={{ mb: 1 }}>
                <Typography variant="subtitle2" color="text.secondary">流量强度 (ρ)</Typography>
                <Typography variant="h6">{result.queueMetrics.trafficIntensity?.toFixed(2)}</Typography>
              </Box>
            </Grid>
            {result.queueMetrics.burstinessIndex > 1 && (
              <Grid item xs={12} sm={3}>
                <Box sx={{ mb: 1 }}>
                  <Typography variant="subtitle2" color="text.secondary">MAP 有效到达率</Typography>
                  <Typography variant="h6">{result.queueMetrics.mapEffectiveArrivalRate?.toFixed(1)}</Typography>
                </Box>
              </Grid>
            )}
          </Grid>
        </Paper>
      )}

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper elevation={2} sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              连接利用率随时间变化
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={utilizationData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis label={{ value: '利用率 (%)', angle: -90, position: 'insideLeft' }} />
                <Tooltip />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="utilization"
                  stroke="#1976d2"
                  name="利用率"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper elevation={2} sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              等待时间分布
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={waitTimeHistogram}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="range" />
                <YAxis label={{ value: '请求数', angle: -90, position: 'insideLeft' }} />
                <Tooltip />
                <Bar dataKey="count" fill="#1976d2" name="请求数" />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}

export default SimulationResults;

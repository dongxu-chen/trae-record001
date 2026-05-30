import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  TextField,
  MenuItem,
  Select,
  InputLabel,
  FormControl,
  Chip,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  PlayArrow as PlayArrowIcon,
  Check as CheckIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Timeline as TimelineIcon,
  Security as SecurityIcon,
  TrendingUp as TrendingUpIcon,
  ExpandMore as ExpandMoreIcon,
} from '@mui/icons-material';
import { SimulationResult, SimulationServiceImpact } from '../types';

const mockSimulationResult: SimulationResult = {
  simulation_id: 'sim-1735000000-0001',
  status: 'completed',
  policy_applied: true,
  is_dry_run: true,
  started_at: '2024-12-23T10:00:00Z',
  completed_at: '2024-12-23T10:05:00Z',
  traffic_analysis: {
    total_requests: 35000,
    allowed_requests: 32550,
    denied_requests: 2100,
    failed_requests: 350,
    allow_rate: 93.0,
    deny_rate: 6.0,
    error_rate: 1.0,
    avg_latency_ms: 52,
    p95_latency_ms: 98,
    before_comparison: {
      allow_rate_change: -2.5,
      deny_rate_change: 2.0,
      error_rate_change: 0.5,
      latency_change_pct: 8.3,
      impact_score: 65,
    },
  },
  service_impact: [
    {
      service_name: 'payment-service',
      namespace: 'prod',
      before_allow_rate: 98.5,
      after_allow_rate: 89.2,
      request_count: 8500,
      impact_level: 'high',
      impact_details: '通过率下降 9.3 个百分点，可能影响支付处理',
    },
    {
      service_name: 'user-service',
      namespace: 'prod',
      before_allow_rate: 97.0,
      after_allow_rate: 94.5,
      request_count: 6200,
      impact_level: 'medium',
      impact_details: '通过率下降 2.5 个百分点',
    },
    {
      service_name: 'order-service',
      namespace: 'prod',
      before_allow_rate: 96.0,
      after_allow_rate: 95.8,
      request_count: 5800,
      impact_level: 'low',
      impact_details: '通过率基本不变',
    },
  ],
  recommendations: [
    '警告：策略预计会对流量产生重大影响，建议进行灰度发布',
    '检测到 2 个策略冲突，建议先解决冲突后再应用',
  ],
};

const SimulationPage: React.FC = () => {
  const [selectedPolicy, setSelectedPolicy] = useState('');
  const [namespaces, setNamespaces] = useState<string[]>(['default']);
  const [duration, setDuration] = useState('5m');
  const [isRunning, setIsRunning] = useState(false);
  const [result, setResult] = useState<SimulationResult | null>(null);

  const handleRunSimulation = () => {
    setIsRunning(true);
    setTimeout(() => {
      setResult(mockSimulationResult);
      setIsRunning(false);
    }, 2000);
  };

  const getImpactColor = (level: string) => {
    switch (level) {
      case 'critical':
        return 'error';
      case 'high':
        return 'error';
      case 'medium':
        return 'warning';
      case 'low':
        return 'success';
      default:
        return 'default';
    }
  };

  const getImpactIcon = (level: string) => {
    switch (level) {
      case 'critical':
        return <ErrorIcon color="error" />;
      case 'high':
        return <ErrorIcon color="error" />;
      case 'medium':
        return <WarningIcon color="warning" />;
      case 'low':
        return <CheckIcon color="success" />;
      default:
        return <CheckIcon />;
    }
  };

  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      <Typography variant="h4" gutterBottom sx={{ mb: 4 }}>
        策略演练模式
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              演练配置
            </Typography>

            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>选择策略</InputLabel>
              <Select
                value={selectedPolicy}
                label="选择策略"
                onChange={(e) => setSelectedPolicy(e.target.value)}
              >
                <MenuItem value="policy-1">mTLS-STRICT - 生产环境</MenuItem>
                <MenuItem value="policy-2">DENY-外部访问 - 支付服务</MenuItem>
                <MenuItem value="policy-3">JWT-Auth - API网关</MenuItem>
              </Select>
            </FormControl>

            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>目标命名空间</InputLabel>
              <Select
                multiple
                value={namespaces}
                label="目标命名空间"
                onChange={(e) => setNamespaces(e.target.value as string[])}
                renderValue={(selected) => (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {selected.map((value) => (
                      <Chip key={value} label={value} size="small" />
                    ))}
                  </Box>
                )}
              >
                <MenuItem value="default">default</MenuItem>
                <MenuItem value="prod">prod</MenuItem>
                <MenuItem value="staging">staging</MenuItem>
                <MenuItem value="dev">dev</MenuItem>
              </Select>
            </FormControl>

            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>演练时长</InputLabel>
              <Select
                value={duration}
                label="演练时长"
                onChange={(e) => setDuration(e.target.value)}
              >
                <MenuItem value="1m">1 分钟</MenuItem>
                <MenuItem value="5m">5 分钟</MenuItem>
                <MenuItem value="15m">15 分钟</MenuItem>
                <MenuItem value="30m">30 分钟</MenuItem>
              </Select>
            </FormControl>

            <Button
              fullWidth
              variant="contained"
              color="primary"
              size="large"
              startIcon={isRunning ? null : <PlayArrowIcon />}
              onClick={handleRunSimulation}
              disabled={isRunning || !selectedPolicy}
              sx={{ mt: 2 }}
            >
              {isRunning ? '演练进行中...' : '开始演练'}
            </Button>

            {isRunning && (
              <Box sx={{ mt: 2 }}>
                <LinearProgress />
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  正在模拟策略应用效果...
                </Typography>
              </Box>
            )}
          </Paper>
        </Grid>

        <Grid item xs={12} md={8}>
          {result ? (
            <Box>
              <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={6} md={3}>
                  <Card>
                    <CardContent>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                        <CheckIcon color="success" sx={{ mr: 1 }} />
                        <Typography variant="h6">{result.traffic_analysis.allow_rate.toFixed(1)}%</Typography>
                      </Box>
                      <Typography variant="body2" color="text.secondary">请求通过率</Typography>
                      <Typography variant="caption" color={result.traffic_analysis.before_comparison.allow_rate_change < 0 ? 'error' : 'success'}>
                        {result.traffic_analysis.before_comparison.allow_rate_change > 0 ? '+' : ''}{result.traffic_analysis.before_comparison.allow_rate_change.toFixed(1)}%
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6} md={3}>
                  <Card>
                    <CardContent>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                        <ErrorIcon color="warning" sx={{ mr: 1 }} />
                        <Typography variant="h6">{result.traffic_analysis.deny_rate.toFixed(1)}%</Typography>
                      </Box>
                      <Typography variant="body2" color="text.secondary">请求拒绝率</Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6} md={3}>
                  <Card>
                    <CardContent>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                        <TimelineIcon color="info" sx={{ mr: 1 }} />
                        <Typography variant="h6">{result.traffic_analysis.p95_latency_ms}ms</Typography>
                      </Box>
                      <Typography variant="body2" color="text.secondary">P95 延迟</Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6} md={3}>
                  <Card>
                    <CardContent>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                        <TrendingUpIcon color={result.traffic_analysis.before_comparison.impact_score > 70 ? 'error' : 'warning'} sx={{ mr: 1 }} />
                        <Typography variant="h6">{result.traffic_analysis.before_comparison.impact_score}</Typography>
                      </Box>
                      <Typography variant="body2" color="text.secondary">影响评分</Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>

              {result.recommendations.length > 0 && (
                <Alert severity="warning" sx={{ mb: 3 }}>
                  <Box sx={{ mb: 1 }}>
                    <strong>演练建议：</strong>
                  </Box>
                  <ul style={{ margin: 0, paddingLeft: 20 }}>
                    {result.recommendations.map((rec, index) => (
                      <li key={index}>{rec}</li>
                    ))}
                  </ul>
                </Alert>
              )}

              <Accordion defaultExpanded>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography variant="h6">服务影响详情</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>服务</TableCell>
                          <TableCell>命名空间</TableCell>
                          <TableCell align="right">通过率变化</TableCell>
                          <TableCell>影响等级</TableCell>
                          <TableCell>详情</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {result.service_impact.map((impact, index) => (
                          <TableRow key={index}>
                            <TableCell>{impact.service_name}</TableCell>
                            <TableCell>
                              <Chip label={impact.namespace} size="small" variant="outlined" />
                            </TableCell>
                            <TableCell align="right">
                              <Typography color={impact.after_allow_rate - impact.before_allow_rate < 0 ? 'error' : 'success'}>
                                {(impact.after_allow_rate - impact.before_allow_rate).toFixed(1)}%
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                {getImpactIcon(impact.impact_level)}
                                <Chip
                                  label={impact.impact_level.toUpperCase()}
                                  size="small"
                                  color={getImpactColor(impact.impact_level) as any}
                                  sx={{ ml: 1 }}
                                />
                              </Box>
                            </TableCell>
                            <TableCell>{impact.impact_details}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </AccordionDetails>
              </Accordion>

              <Box sx={{ mt: 3, display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
                <Button variant="outlined" onClick={() => setResult(null)}>
                  重新演练
                </Button>
                <Button variant="contained" color="primary">
                  应用策略
                </Button>
                <Button variant="contained" color="success">
                  灰度发布
                </Button>
              </Box>
            </Box>
          ) : (
            <Paper sx={{ p: 6, textAlign: 'center' }}>
              <SecurityIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" color="text.secondary" gutterBottom>
                选择策略并开始演练
              </Typography>
              <Typography variant="body2" color="text.secondary">
                演练模式将模拟策略应用效果，不会实际下发到集群
              </Typography>
            </Paper>
          )}
        </Grid>
      </Grid>
    </Box>
  );
};

export default SimulationPage;

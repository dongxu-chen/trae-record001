import React, { useState, useEffect } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Paper,
  Chip,
  CircularProgress,
  Button,
  Alert,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Divider,
  Stepper,
  Step,
  StepLabel,
} from '@mui/material';
import {
  TrendingUp,
  AttachMoney,
  Memory,
  Speed,
  CheckCircle,
  Warning,
  ArrowBack,
  Refresh,
  Check,
  ArrowUpward,
  ArrowDownward,
} from '@mui/icons-material';
import { useNavigate, useParams } from 'react-router-dom';
import { recommendationApi } from '../services/api';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  RadialBarChart,
  RadialBar,
  Legend as RechartsLegend,
} from 'recharts';

const Recommendation = () => {
  const { jobId } = useParams();
  const [recommendation, setRecommendation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadRecommendation();
  }, [jobId]);

  const loadRecommendation = async () => {
    try {
      setLoading(true);
      const response = await recommendationApi.getMockRecommendation();
      setRecommendation(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to load recommendation data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !recommendation) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{error || 'No recommendation available'}</Alert>
      </Box>
    );
  }

  const current = recommendation.currentConfig;
  const proposed = recommendation.recommendedConfig;

  const comparisonData = [
    {
      name: 'TaskManagers',
      current: current.numTaskManagers,
      recommended: proposed.numTaskManagers,
    },
    {
      name: 'Parallelism',
      current: current.parallelism,
      recommended: proposed.parallelism,
    },
    {
      name: 'TM Memory (GB)',
      current: current.taskManagerMemoryMb / 1024,
      recommended: proposed.taskManagerMemoryMb / 1024,
    },
    {
      name: 'TM CPU',
      current: current.taskManagerCpuCores,
      recommended: proposed.taskManagerCpuCores,
    },
  ];

  const performanceData = [
    {
      name: 'Performance',
      value: recommendation.estimatedPerformanceImprovement,
      fill: '#4caf50',
    },
    {
      name: 'Latency Reduction',
      value: recommendation.expectedLatencyReduction,
      fill: '#2196f3',
    },
    {
      name: 'Throughput Gain',
      value: recommendation.expectedThroughputIncrease,
      fill: '#ff9800',
    },
  ];

  const getConfidenceColor = (level) => {
    switch (level) {
      case 'HIGH': return 'success';
      case 'MEDIUM': return 'warning';
      default: return 'error';
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3, alignItems: 'center' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Button startIcon={<ArrowBack />} onClick={() => navigate('/jobs/demo/analysis')}>
            Back to Analysis
          </Button>
          <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#1a237e' }}>
            Resource Recommendation
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            startIcon={<Refresh />}
            variant="outlined"
            onClick={loadRecommendation}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            color="success"
            startIcon={<Check />}
          >
            Apply Recommendation
          </Button>
        </Box>
      </Box>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={3} alignItems="center">
            <Grid item xs={12} md={4}>
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="body2" color="textSecondary">Confidence Level</Typography>
                <Chip
                  label={recommendation.confidenceLevel}
                  color={getConfidenceColor(recommendation.confidenceLevel)}
                  size="large"
                  sx={{ mt: 1, fontSize: '1.2rem', py: 2 }}
                />
              </Box>
            </Grid>
            <Grid item xs={12} md={8}>
              <Box sx={{ display: 'flex', gap: 4, justifyContent: 'space-around' }}>
                <Box sx={{ textAlign: 'center' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1 }}>
                    <TrendingUp color="success" />
                    <Typography variant="h5" sx={{ fontWeight: 'bold', color: '#2e7d32' }}>
                      +{recommendation.estimatedPerformanceImprovement.toFixed(1)}%
                    </Typography>
                  </Box>
                  <Typography variant="body2" color="textSecondary">Expected Performance Gain</Typography>
                </Box>
                <Box sx={{ textAlign: 'center' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1 }}>
                    {recommendation.costSavingsPercentage >= 0 ? (
                      <ArrowDownward color="success" />
                    ) : (
                      <ArrowUpward color="error" />
                    )}
                    <Typography
                      variant="h5"
                      sx={{
                        fontWeight: 'bold',
                        color: recommendation.costSavingsPercentage >= 0 ? '#2e7d32' : '#d32f2f',
                      }}
                    >
                      {recommendation.costSavingsPercentage >= 0 ? '+' : ''}
                      {recommendation.costSavingsPercentage.toFixed(1)}%
                    </Typography>
                  </Box>
                  <Typography variant="body2" color="textSecondary">Cost Change</Typography>
                </Box>
                <Box sx={{ textAlign: 'center' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1 }}>
                    <Speed color="primary" />
                    <Typography variant="h5" sx={{ fontWeight: 'bold', color: '#1976d2' }}>
                      -{recommendation.expectedLatencyReduction.toFixed(1)}%
                    </Typography>
                  </Box>
                  <Typography variant="body2" color="textSecondary">Latency Reduction</Typography>
                </Box>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
              Configuration Comparison
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={comparisonData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <RechartsLegend />
                <Bar dataKey="current" fill="#90caf9" name="Current" />
                <Bar dataKey="recommended" fill="#1976d2" name="Recommended" />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
              Expected Improvements
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <RadialBarChart
                cx="50%"
                cy="50%"
                innerRadius="20%"
                outerRadius="80%"
                data={performanceData}
                startAngle={180}
                endAngle={0}
              >
                <RadialBar
                  minAngle={15}
                  background
                  clockWise
                  dataKey="value"
                />
                <RechartsLegend iconSize={10} layout="horizontal" verticalAlign="bottom" align="center" />
                <Tooltip />
              </RadialBarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
      </Grid>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <CheckCircle color="success" />
                Reasoning
              </Box>
            </Typography>
            <List>
              {recommendation.reasoning.map((r, i) => (
                <ListItem key={i}>
                  <ListItemIcon>
                    <CheckCircle color="success" fontSize="small" />
                  </ListItemIcon>
                  <ListItemText primary={r} />
                </ListItem>
              ))}
            </List>
          </Paper>
        </Grid>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Warning color="warning" />
                Risks
              </Box>
            </Typography>
            <List>
              {recommendation.risks.map((r, i) => (
                <ListItem key={i}>
                  <ListItemIcon>
                    <Warning color="warning" fontSize="small" />
                  </ListItemIcon>
                  <ListItemText primary={r} />
                </ListItem>
              ))}
            </List>
          </Paper>
        </Grid>
      </Grid>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
          Vertex-level Recommendations
        </Typography>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                <TableCell><strong>Vertex</strong></TableCell>
                <TableCell align="center"><strong>Current Parallelism</strong></TableCell>
                <TableCell align="center"><strong>Recommended Parallelism</strong></TableCell>
                <TableCell align="center"><strong>Change</strong></TableCell>
                <TableCell><strong>Reason</strong></TableCell>
                <TableCell align="center"><strong>Expected Improvement</strong></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {Object.values(recommendation.vertexRecommendations).map((vr, i) => (
                <TableRow key={i} hover>
                  <TableCell>{vr.vertexName}</TableCell>
                  <TableCell align="center">{vr.currentParallelism}</TableCell>
                  <TableCell align="center">
                    <Chip
                      label={vr.recommendedParallelism}
                      color={vr.recommendedParallelism !== vr.currentParallelism ? 'primary' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell align="center">
                    {vr.recommendedParallelism > vr.currentParallelism ? (
                      <Chip label="Increase" color="primary" size="small" />
                    ) : vr.recommendedParallelism < vr.currentParallelism ? (
                      <Chip label="Decrease" color="warning" size="small" />
                    ) : (
                      <Chip label="No Change" size="small" />
                    )}
                  </TableCell>
                  <TableCell>{vr.reason}</TableCell>
                  <TableCell align="center">
                    <Typography
                      sx={{
                        color: vr.expectedImprovement > 0 ? '#2e7d32' : 'text.secondary',
                        fontWeight: 500,
                      }}
                    >
                      +{(vr.expectedImprovement * 100).toFixed(1)}%
                    </Typography>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <AttachMoney />
            Cost Analysis
          </Box>
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={12} md={4}>
            <Card sx={{ bgcolor: '#e3f2fd' }}>
              <CardContent>
                <Typography variant="subtitle2" color="textSecondary">Current Cost</Typography>
                <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#1976d2' }}>
                  ${recommendation.estimatedCostPerHour.toFixed(2)}
                </Typography>
                <Typography variant="body2">per hour</Typography>
                <Divider sx={{ my: 2 }} />
                <Typography variant="body2">Daily: ${recommendation.estimatedCostPerDay.toFixed(2)}</Typography>
                <Typography variant="body2">Monthly: ${recommendation.estimatedCostPerMonth.toFixed(2)}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <Card sx={{ bgcolor: '#e8f5e9' }}>
              <CardContent>
                <Typography variant="subtitle2" color="textSecondary">Recommended Cost</Typography>
                <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#2e7d32' }}>
                  ${recommendation.recommendedCostPerHour.toFixed(2)}
                </Typography>
                <Typography variant="body2">per hour</Typography>
                <Divider sx={{ my: 2 }} />
                <Typography variant="body2">Daily: ${recommendation.recommendedCostPerDay.toFixed(2)}</Typography>
                <Typography variant="body2">Monthly: ${recommendation.recommendedCostPerMonth.toFixed(2)}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <Card sx={{
              bgcolor: recommendation.costSavingsPercentage >= 0 ? '#fff3e0' : '#ffebee',
            }}>
              <CardContent>
                <Typography variant="subtitle2" color="textSecondary">Monthly Savings</Typography>
                <Typography
                  variant="h4"
                  sx={{
                    fontWeight: 'bold',
                    color: recommendation.costSavingsPercentage >= 0 ? '#f57c00' : '#d32f2f',
                  }}
                >
                  ${Math.abs(recommendation.estimatedCostPerMonth - recommendation.recommendedCostPerMonth).toFixed(2)}
                </Typography>
                <Typography variant="body2">
                  {recommendation.costSavingsPercentage >= 0 ? 'Savings' : 'Additional Cost'}
                </Typography>
                <Divider sx={{ my: 2 }} />
                <Typography variant="body2">
                  Yearly: ${Math.abs((recommendation.estimatedCostPerMonth - recommendation.recommendedCostPerMonth) * 12).toFixed(2)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Paper>
    </Box>
  );
};

export default Recommendation;

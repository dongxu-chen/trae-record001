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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Divider,
  Switch,
  FormControlLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Checkbox,
  IconButton,
  Tooltip,
  LinearProgress,
} from '@mui/material';
import {
  AutoFixHigh,
  CheckCircle,
  Warning,
  Error,
  ArrowUpward,
  ArrowDownward,
  Refresh,
  PlayArrow,
  Visibility,
  History,
  TrendingUp,
  AttachMoney,
  Memory,
  Speed,
  Check,
  Close,
  Info,
} from '@mui/icons-material';
import { useNavigate, useParams } from 'react-router-dom';
import { recommendationApi, jobApi } from '../services/api';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend as RechartsLegend,
  LineChart,
  Line,
} from 'recharts';

const mockJobs = [
  { id: 'job-001', name: 'User Behavior Analysis', type: 'ETL', status: 'RUNNING' },
  { id: 'job-002', name: 'Real-time Recommendation', type: 'ML', status: 'RUNNING' },
  { id: 'job-003', name: 'Fraud Detection', type: 'STREAMING', status: 'RUNNING' },
  { id: 'job-004', name: 'Log Processing Pipeline', type: 'ETL', status: 'RUNNING' },
  { id: 'job-005', name: 'Click Stream Analytics', type: 'ANALYTICS', status: 'RUNNING' },
];

const mockPreview = {
  jobId: 'job-001',
  jobName: 'User Behavior Analysis',
  currentConfig: {
    numTaskManagers: 8,
    parallelism: 32,
    taskManagerMemoryMb: 4096,
    taskManagerCpuCores: 2.0,
  },
  recommendedConfig: {
    numTaskManagers: 6,
    parallelism: 24,
    taskManagerMemoryMb: 6144,
    taskManagerCpuCores: 2.5,
  },
  expectedImprovements: {
    performanceGain: 15.3,
    costSavings: 22.5,
    latencyReduction: 18.7,
    stabilityImprovement: 25.0,
  },
  riskLevel: 'LOW',
  adjustmentReason: 'CPU utilization consistently below 30%, memory underutilized. Consolidating TaskManagers with increased per-instance resources for better efficiency.',
  appliedChanges: [
    'Reduce TaskManagers from 8 to 6',
    'Reduce parallelism from 32 to 24',
    'Increase TM memory from 4GB to 6GB',
    'Increase TM CPU from 2.0 to 2.5 cores',
  ],
  benefitAnalysis: {
    monthlyCostSavings: 285.50,
    performanceImprovement: 15.3,
    resourceUtilizationImprovement: 28.4,
    breakEvenHours: 2.5,
  },
};

const mockHistory = [
  {
    id: 'adj-001',
    jobId: 'job-001',
    jobName: 'User Behavior Analysis',
    timestamp: '2024-01-15 10:30:00',
    status: 'SUCCESS',
    previousConfig: { numTaskManagers: 10, parallelism: 40 },
    newConfig: { numTaskManagers: 8, parallelism: 32 },
    costSavings: 18.5,
    performanceChange: 2.3,
  },
  {
    id: 'adj-002',
    jobId: 'job-002',
    jobName: 'Real-time Recommendation',
    timestamp: '2024-01-14 15:45:00',
    status: 'SUCCESS',
    previousConfig: { numTaskManagers: 4, parallelism: 16 },
    newConfig: { numTaskManagers: 6, parallelism: 24 },
    costSavings: -12.3,
    performanceChange: 28.7,
  },
  {
    id: 'adj-003',
    jobId: 'job-003',
    jobName: 'Fraud Detection',
    timestamp: '2024-01-13 09:20:00',
    status: 'FAILED',
    previousConfig: { numTaskManagers: 3, parallelism: 12 },
    newConfig: { numTaskManagers: 5, parallelism: 20 },
    costSavings: 0,
    performanceChange: 0,
    errorMessage: 'Job restart timeout - rolled back to previous configuration',
  },
];

const mockAdjustmentResult = {
  adjustmentId: 'adj-004',
  jobId: 'job-001',
  jobName: 'User Behavior Analysis',
  status: 'COMPLETED',
  success: true,
  previousConfig: {
    numTaskManagers: 8,
    parallelism: 32,
    taskManagerMemoryMb: 4096,
    taskManagerCpuCores: 2.0,
  },
  newConfig: {
    numTaskManagers: 6,
    parallelism: 24,
    taskManagerMemoryMb: 6144,
    taskManagerCpuCores: 2.5,
  },
  appliedChanges: [
    'Reduce TaskManagers from 8 to 6',
    'Reduce parallelism from 32 to 24',
    'Increase TM memory from 4GB to 6GB',
    'Increase TM CPU from 2.0 to 2.5 cores',
  ],
  expectedImprovements: {
    performanceGain: 15.3,
    costSavings: 22.5,
    latencyReduction: 18.7,
  },
  adjustmentReason: 'CPU utilization consistently below 30%, memory underutilized.',
  timestamp: '2024-01-16 14:30:00',
  durationSeconds: 45,
};

const AutoAdjust = () => {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState(null);
  const [selectedJobs, setSelectedJobs] = useState(new Set([jobId || 'job-001']));
  const [dryRun, setDryRun] = useState(true);
  const [batchMode, setBatchMode] = useState(false);
  const [selectJobDialog, setSelectJobDialog] = useState(false);
  const [adjustResult, setAdjustResult] = useState(null);
  const [history, setHistory] = useState(mockHistory);
  const [activeTab, setActiveTab] = useState('preview');
  const [applying, setApplying] = useState(false);
  const [applyProgress, setApplyProgress] = useState(0);

  useEffect(() => {
    loadPreview();
  }, [jobId]);

  const loadPreview = async () => {
    try {
      setLoading(true);
      setTimeout(() => {
        setPreview(mockPreview);
        setLoading(false);
      }, 800);
    } catch (err) {
      console.error('Failed to load preview', err);
      setLoading(false);
    }
  };

  const handleJobSelect = (id) => {
    setSelectedJobs((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  const handleApplyAdjustment = async () => {
    setApplying(true);
    setApplyProgress(0);
    
    const interval = setInterval(() => {
      setApplyProgress((prev) => {
        if (prev >= 90) {
          clearInterval(interval);
          return prev;
        }
        return prev + 10;
      });
    }, 400);

    setTimeout(() => {
      clearInterval(interval);
      setApplyProgress(100);
      setAdjustResult(mockAdjustmentResult);
      setApplying(false);
    }, 4000);
  };

  const getRiskColor = (level) => {
    switch (level) {
      case 'LOW': return 'success';
      case 'MEDIUM': return 'warning';
      case 'HIGH': return 'error';
      default: return 'default';
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'SUCCESS':
      case 'COMPLETED': return 'success';
      case 'FAILED': return 'error';
      case 'DRY_RUN': return 'info';
      default: return 'default';
    }
  };

  const getResourceComparisonData = () => {
    if (!preview) return [];
    return [
      { name: 'TaskManagers', current: preview.currentConfig.numTaskManagers, recommended: preview.recommendedConfig.numTaskManagers },
      { name: 'Parallelism', current: preview.currentConfig.parallelism, recommended: preview.recommendedConfig.parallelism },
      { name: 'TM Memory (GB)', current: preview.currentConfig.taskManagerMemoryMb / 1024, recommended: preview.recommendedConfig.taskManagerMemoryMb / 1024 },
      { name: 'TM CPU', current: preview.currentConfig.taskManagerCpuCores, recommended: preview.recommendedConfig.taskManagerCpuCores },
    ];
  };

  const getImprovementsData = () => {
    if (!preview) return [];
    return [
      { name: 'Performance', value: preview.expectedImprovements.performanceGain, fill: '#4caf50' },
      { name: 'Cost Savings', value: preview.expectedImprovements.costSavings, fill: '#ff9800' },
      { name: 'Latency Reduction', value: preview.expectedImprovements.latencyReduction, fill: '#2196f3' },
      { name: 'Stability', value: preview.expectedImprovements.stabilityImprovement, fill: '#9c27b0' },
    ];
  };

  const getTrendData = () => {
    return Array.from({ length: 7 }, (_, i) => ({
      day: `Day ${i + 1}`,
      cpuUtilization: 25 + Math.random() * 15,
      memoryUtilization: 40 + Math.random() * 20,
    }));
  };

  const selectedJobNames = Array.from(selectedJobs).map(id => {
    const job = mockJobs.find(j => j.id === id);
    return job ? job.name : id;
  });

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3, alignItems: 'center' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#1a237e' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <AutoFixHigh sx={{ fontSize: 36 }} />
              Auto Resource Adjustment
            </Box>
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <FormControlLabel
            control={
              <Switch
                checked={batchMode}
                onChange={(e) => setBatchMode(e.target.checked)}
                color="primary"
              />
            }
            label="Batch Mode"
          />
          <FormControlLabel
            control={
              <Switch
                checked={dryRun}
                onChange={(e) => setDryRun(e.target.checked)}
                color="warning"
              />
            }
            label="Dry Run"
          />
          <Button startIcon={<Refresh />} variant="outlined" onClick={loadPreview}>
            Refresh
          </Button>
        </Box>
      </Box>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={3} alignItems="center">
            <Grid item xs={12} md={6}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Typography variant="subtitle1" color="textSecondary">
                  Target Job{batchMode ? 's' : ''}:
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {batchMode ? (
                    <>
                      {selectedJobNames.map((name, i) => (
                        <Chip key={i} label={name} size="small" color="primary" />
                      ))}
                      <Button size="small" onClick={() => setSelectJobDialog(true)}>
                        Select Jobs
                      </Button>
                    </>
                  ) : (
                    <Chip
                      label={preview?.jobName || jobId}
                      color="primary"
                      onDelete={() => setSelectJobDialog(true)}
                    />
                  )}
                </Box>
              </Box>
            </Grid>
            <Grid item xs={12} md={6}>
              <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
                {preview && (
                  <Chip
                    label={`Risk: ${preview.riskLevel}`}
                    color={getRiskColor(preview.riskLevel)}
                    icon={<Warning />}
                  />
                )}
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={dryRun ? <Visibility /> : <PlayArrow />}
                  onClick={handleApplyAdjustment}
                  disabled={applying || selectedJobs.size === 0}
                  sx={{ minWidth: 180 }}
                >
                  {dryRun ? 'Preview Adjustment' : 'Apply Adjustment'}
                </Button>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {applying && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
              <CircularProgress variant="determinate" value={applyProgress} size={60} />
              <Box sx={{ flex: 1 }}>
                <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 1 }}>
                  {dryRun ? 'Running Dry Run Analysis...' : 'Applying Resource Adjustment...'}
                </Typography>
                <LinearProgress variant="determinate" value={applyProgress} sx={{ mb: 1 }} />
                <Typography variant="body2" color="textSecondary">
                  {applyProgress < 30 ? 'Analyzing current resource utilization...' :
                   applyProgress < 60 ? 'Calculating optimal configuration...' :
                   applyProgress < 90 ? 'Preparing changes...' :
                   applyProgress < 100 ? 'Finalizing adjustment...' : 'Complete!'}
                </Typography>
              </Box>
            </Box>
          </CardContent>
        </Card>
      )}

      {adjustResult && (
        <Card sx={{ mb: 3, borderLeft: 6, borderColor: adjustResult.success ? 'success.main' : 'error.main' }}>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
              <Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
                  {adjustResult.success ? (
                    <CheckCircle color="success" sx={{ fontSize: 32 }} />
                  ) : (
                    <Error color="error" sx={{ fontSize: 32 }} />
                  )}
                  <Typography variant="h5" sx={{ fontWeight: 'bold' }}>
                    {dryRun ? 'Dry Run Complete' : 'Adjustment ' + (adjustResult.success ? 'Successful' : 'Failed')}
                  </Typography>
                </Box>
                <Typography variant="body2" color="textSecondary">
                  Adjustment ID: {adjustResult.adjustmentId} | Duration: {adjustResult.durationSeconds}s
                </Typography>
              </Box>
              <Chip
                label={adjustResult.status}
                color={getStatusColor(adjustResult.status)}
                size="large"
              />
            </Box>

            {adjustResult.success && (
              <Grid container spacing={3} sx={{ mb: 2 }}>
                <Grid item xs={12} md={3}>
                  <Card sx={{ bgcolor: '#e8f5e9', height: '100%' }}>
                    <CardContent sx={{ py: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <TrendingUp color="success" />
                        <Typography variant="body2" color="textSecondary">Performance</Typography>
                      </Box>
                      <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#2e7d32' }}>
                        +{adjustResult.expectedImprovements.performanceGain}%
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} md={3}>
                  <Card sx={{ bgcolor: '#fff3e0', height: '100%' }}>
                    <CardContent sx={{ py: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <AttachMoney color="warning" />
                        <Typography variant="body2" color="textSecondary">Cost Savings</Typography>
                      </Box>
                      <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#f57c00' }}>
                        +{adjustResult.expectedImprovements.costSavings}%
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} md={3}>
                  <Card sx={{ bgcolor: '#e3f2fd', height: '100%' }}>
                    <CardContent sx={{ py: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Speed color="primary" />
                        <Typography variant="body2" color="textSecondary">Latency</Typography>
                      </Box>
                      <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#1976d2' }}>
                        -{adjustResult.expectedImprovements.latencyReduction}%
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} md={3}>
                  <Card sx={{ bgcolor: '#f3e5f5', height: '100%' }}>
                    <CardContent sx={{ py: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Info color="secondary" />
                        <Typography variant="body2" color="textSecondary">Changes Applied</Typography>
                      </Box>
                      <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#7b1fa2' }}>
                        {adjustResult.appliedChanges.length}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            )}

            <Box sx={{ display: 'flex', gap: 2 }}>
              <Button size="small" onClick={() => setAdjustResult(null)}>
                Continue
              </Button>
              {!dryRun && adjustResult.success && (
                <Button size="small" variant="outlined" startIcon={<Visibility />}>
                  View Job Details
                </Button>
              )}
            </Box>
          </CardContent>
        </Card>
      )}

      <Box sx={{ display: 'flex', gap: 1, mb: 3 }}>
        <Button
          variant={activeTab === 'preview' ? 'contained' : 'outlined'}
          onClick={() => setActiveTab('preview')}
          startIcon={<Visibility />}
        >
          Adjustment Preview
        </Button>
        <Button
          variant={activeTab === 'benefit' ? 'contained' : 'outlined'}
          onClick={() => setActiveTab('benefit')}
          startIcon={<TrendingUp />}
        >
          Benefit Analysis
        </Button>
        <Button
          variant={activeTab === 'history' ? 'contained' : 'outlined'}
          onClick={() => setActiveTab('history')}
          startIcon={<History />}
        >
          Adjustment History
        </Button>
      </Box>

      {activeTab === 'preview' && preview && (
        <>
          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 3, height: '100%' }}>
                <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
                  Configuration Comparison
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={getResourceComparisonData()}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <RechartsTooltip />
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
                  <BarChart data={getImprovementsData()} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" />
                    <YAxis dataKey="name" type="category" width={120} />
                    <RechartsTooltip formatter={(v) => [`${v}%`, 'Improvement']} />
                    <Bar dataKey="value" fill="#4caf50" label={{ position: 'right', formatter: (v) => `${v}%` }} />
                  </BarChart>
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
                    Applied Changes
                  </Box>
                </Typography>
                <List>
                  {preview.appliedChanges.map((change, i) => (
                    <ListItem key={i} sx={{ py: 0.5 }}>
                      <ListItemIcon sx={{ minWidth: 36 }}>
                        {change.includes('Increase') || change.includes('from') && change.includes('to') && Number(change.split('to ')[1]) > Number(change.split('from ')[1].split(' ')[0]) ? (
                          <ArrowUpward color="primary" fontSize="small" />
                        ) : (
                          <ArrowDownward color="success" fontSize="small" />
                        )}
                      </ListItemIcon>
                      <ListItemText primary={change} />
                    </ListItem>
                  ))}
                </List>
              </Paper>
            </Grid>
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Info color="primary" />
                    Adjustment Reason
                  </Box>
                </Typography>
                <Typography variant="body1" sx={{ mb: 3, color: 'text.secondary' }}>
                  {preview.adjustmentReason}
                </Typography>
                <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
                  <Chip
                    label={`Risk: ${preview.riskLevel}`}
                    color={getRiskColor(preview.riskLevel)}
                  />
                </Box>
              </Paper>
            </Grid>
          </Grid>

          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
              Resource Utilization Trend (7 Days)
            </Typography>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={getTrendData()}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="day" />
                <YAxis />
                <RechartsTooltip />
                <RechartsLegend />
                <Line type="monotone" dataKey="cpuUtilization" stroke="#1976d2" strokeWidth={2} name="CPU %" dot={{ r: 4 }} />
                <Line type="monotone" dataKey="memoryUtilization" stroke="#4caf50" strokeWidth={2} name="Memory %" dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </Paper>
        </>
      )}

      {activeTab === 'benefit' && preview && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 3 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <AttachMoney color="warning" />
                  Cost Benefit Analysis
                </Box>
              </Typography>
              <TableContainer>
                <Table size="small">
                  <TableBody>
                    <TableRow>
                      <TableCell><strong>Current Monthly Cost</strong></TableCell>
                      <TableCell align="right">$1,140.00</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell><strong>Recommended Monthly Cost</strong></TableCell>
                      <TableCell align="right">$854.50</TableCell>
                    </TableRow>
                    <TableRow sx={{ bgcolor: '#e8f5e9' }}>
                      <TableCell><strong>Monthly Savings</strong></TableCell>
                      <TableCell align="right">
                        <Typography sx={{ color: '#2e7d32', fontWeight: 'bold' }}>
                          -${preview.benefitAnalysis.monthlyCostSavings.toFixed(2)} ({preview.expectedImprovements.costSavings}%)
                        </Typography>
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell><strong>Yearly Savings</strong></TableCell>
                      <TableCell align="right">${(preview.benefitAnalysis.monthlyCostSavings * 12).toFixed(2)}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell><strong>Break-even Point</strong></TableCell>
                      <TableCell align="right">{preview.benefitAnalysis.breakEvenHours} hours</TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          </Grid>
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 3 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <TrendingUp color="success" />
                  Performance Benefits
                </Box>
              </Typography>
              <TableContainer>
                <Table size="small">
                  <TableBody>
                    <TableRow>
                      <TableCell><strong>Expected Performance Gain</strong></TableCell>
                      <TableCell align="right">
                        <Chip label={`+${preview.benefitAnalysis.performanceImprovement}%`} color="success" />
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell><strong>Resource Utilization Improvement</strong></TableCell>
                      <TableCell align="right">
                        <Chip label={`+${preview.benefitAnalysis.resourceUtilizationImprovement}%`} color="primary" />
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell><strong>Expected Latency Reduction</strong></TableCell>
                      <TableCell align="right">
                        <Chip label={`-${preview.expectedImprovements.latencyReduction}%`} color="info" />
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell><strong>Stability Improvement</strong></TableCell>
                      <TableCell align="right">
                        <Chip label={`+${preview.expectedImprovements.stabilityImprovement}%`} color="secondary" />
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          </Grid>
        </Grid>
      )}

      {activeTab === 'history' && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <History />
              Adjustment History
            </Box>
          </Typography>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                  <TableCell><strong>Time</strong></TableCell>
                  <TableCell><strong>Job</strong></TableCell>
                  <TableCell><strong>Status</strong></TableCell>
                  <TableCell align="center"><strong>TM Change</strong></TableCell>
                  <TableCell align="center"><strong>Parallelism Change</strong></TableCell>
                  <TableCell align="center"><strong>Cost Impact</strong></TableCell>
                  <TableCell align="center"><strong>Performance Impact</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {history.map((item) => (
                  <TableRow key={item.id} hover>
                    <TableCell>{item.timestamp}</TableCell>
                    <TableCell>{item.jobName}</TableCell>
                    <TableCell>
                      <Chip
                        label={item.status}
                        color={getStatusColor(item.status)}
                        size="small"
                        icon={item.status === 'SUCCESS' ? <Check fontSize="small" /> : <Close fontSize="small" />}
                      />
                    </TableCell>
                    <TableCell align="center">
                      {item.previousConfig.numTaskManagers} → {item.newConfig.numTaskManagers}
                    </TableCell>
                    <TableCell align="center">
                      {item.previousConfig.parallelism} → {item.newConfig.parallelism}
                    </TableCell>
                    <TableCell align="center">
                      <Typography
                        sx={{
                          color: item.costSavings >= 0 ? '#2e7d32' : '#d32f2f',
                          fontWeight: 500,
                        }}
                      >
                        {item.costSavings >= 0 ? '+' : ''}{item.costSavings}%
                      </Typography>
                    </TableCell>
                    <TableCell align="center">
                      <Typography
                        sx={{
                          color: item.performanceChange >= 0 ? '#2e7d32' : '#d32f2f',
                          fontWeight: 500,
                        }}
                      >
                        {item.performanceChange >= 0 ? '+' : ''}{item.performanceChange}%
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}

      <Dialog open={selectJobDialog} onClose={() => setSelectJobDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Select Jobs for Adjustment</DialogTitle>
        <DialogContent>
          <List sx={{ pt: 0 }}>
            {mockJobs.map((job) => (
              <ListItem
                key={job.id}
                button
                onClick={() => handleJobSelect(job.id)}
                sx={{ borderRadius: 1, my: 0.5 }}
              >
                <ListItemIcon>
                  <Checkbox checked={selectedJobs.has(job.id)} />
                </ListItemIcon>
                <ListItemText
                  primary={job.name}
                  secondary={`Type: ${job.type} | Status: ${job.status}`}
                />
                <Chip label={job.status} size="small" color="success" variant="outlined" />
              </ListItem>
            ))}
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelectJobDialog(false)}>Cancel</Button>
          <Button
            onClick={() => {
              if (!batchMode && selectedJobs.size > 0) {
                const firstJob = Array.from(selectedJobs)[0];
                setSelectedJobs(new Set([firstJob]));
              }
              setSelectJobDialog(false);
            }}
            variant="contained"
          >
            Select ({selectedJobs.size})
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AutoAdjust;

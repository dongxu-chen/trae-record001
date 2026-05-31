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
  Button,
  TextField,
  MenuItem,
  IconButton,
  Tooltip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  LinearProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
} from '@mui/material';
import {
  Compare,
  TrendingUp,
  TrendingDown,
  Refresh,
  Info,
  Warning,
  EmojiEvents,
  Add,
  Close,
  BarChart,
  ArrowUpward,
  ArrowDownward,
  Settings,
} from '@mui/icons-material';
import { comparisonApi } from '../services/api';
import {
  BarChart as RechartsBarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from 'recharts';

const JobComparison = () => {
  const [comparisonData, setComparisonData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [jobTypes, setJobTypes] = useState([]);
  const [selectedType, setSelectedType] = useState('ETL');
  const [selectedJobs, setSelectedJobs] = useState([]);
  const [customDialogOpen, setCustomDialogOpen] = useState(false);
  const [allJobs, setAllJobs] = useState([
    { id: 'job-1', name: 'User Activity Pipeline' },
    { id: 'job-2', name: 'Transaction Processing' },
    { id: 'job-3', name: 'Click Stream Analysis' },
    { id: 'job-4', name: 'IoT Sensor Data' },
    { id: 'job-5', name: 'Log Aggregation' },
  ]);

  useEffect(() => {
    loadComparisonData();
    loadJobTypes();
  }, []);

  const loadComparisonData = async () => {
    try {
      setLoading(true);
      const response = await comparisonApi.getMockComparison();
      setComparisonData(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to load comparison data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadJobTypes = async () => {
    try {
      const response = await comparisonApi.getJobTypes();
      setJobTypes(response.data || ['ETL', 'TRANSACTION', 'IOT', 'LOG', 'ANALYTICS']);
    } catch (err) {
      console.error(err);
    }
  };

  const handleTypeChange = async (type) => {
    setSelectedType(type);
    try {
      setLoading(true);
      const response = await comparisonApi.compareByType(type);
      setComparisonData(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to load comparison data');
    } finally {
      setLoading(false);
    }
  };

  const handleCustomCompare = async () => {
    if (selectedJobs.length < 2) {
      setError('Please select at least 2 jobs for comparison');
      return;
    }
    try {
      setLoading(true);
      const response = await comparisonApi.compareCustom(selectedJobs);
      setComparisonData(response.data);
      setError(null);
      setCustomDialogOpen(false);
    } catch (err) {
      setError('Failed to load comparison data');
    } finally {
      setLoading(false);
    }
  };

  const getRankIcon = (rank) => {
    if (rank === 1) return <EmojiEvents sx={{ color: '#ffd700' }} />;
    if (rank === 2) return <EmojiEvents sx={{ color: '#c0c0c0' }} />;
    if (rank === 3) return <EmojiEvents sx={{ color: '#cd7f32' }} />;
    return <Typography variant="body2" sx={{ fontWeight: 'bold' }}>#{rank}</Typography>;
  };

  const getEfficiencyColor = (score) => {
    if (score >= 0.8) return '#4caf50';
    if (score >= 0.6) return '#ff9800';
    if (score >= 0.4) return '#ff5722';
    return '#f44336';
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error && !comparisonData) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  const { jobs, summary, optimizationSuggestions, groupName } = comparisonData;

  const barChartData = jobs?.map(job => ({
    name: job.jobName.substring(0, 15),
    cpu: job.avgCpuUtilization * 100,
    memory: job.avgMemoryUtilization * 100,
    network: job.avgNetworkUtilization * 100,
  })) || [];

  const radarData = jobs?.slice(0, 3).map((job, index) => ({
    subject: 'CPU',
    [job.jobName.substring(0, 8)]: job.avgCpuUtilization * 100,
    fullMark: 100,
  })) || [];

  const colors = ['#1976d2', '#388e3c', '#f57c00', '#e91e63', '#7b1fa2'];

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3, alignItems: 'center' }}>
        <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#1a237e' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Compare sx={{ color: '#1976d2' }} />
            Job Comparison
          </Box>
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <TextField
            select
            label="Job Type"
            value={selectedType}
            onChange={(e) => handleTypeChange(e.target.value)}
            size="small"
            sx={{ minWidth: 150 }}
          >
            {jobTypes.map(type => (
              <MenuItem key={type} value={type}>{type}</MenuItem>
            ))}
          </TextField>
          <Button
            variant="outlined"
            startIcon={<Add />}
            onClick={() => setCustomDialogOpen(true)}
          >
            Custom Compare
          </Button>
          <Tooltip title="Refresh">
            <IconButton onClick={loadComparisonData}>
              <Refresh />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {groupName && (
        <Box sx={{ mb: 2 }}>
          <Chip label={groupName} color="primary" />
        </Box>
      )}

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white' }}>
            <CardContent>
              <Typography variant="body2" sx={{ opacity: 0.8 }}>Jobs Compared</Typography>
              <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
                {jobs?.length || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, #43cea2 0%, #185a9d 100%)', color: 'white' }}>
            <CardContent>
              <Typography variant="body2" sx={{ opacity: 0.8 }}>Avg CPU Usage</Typography>
              <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
                {(summary?.avgCpuUtilization * 100 || 0).toFixed(1)}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', color: 'white' }}>
            <CardContent>
              <Typography variant="body2" sx={{ opacity: 0.8 }}>Best Efficiency</Typography>
              <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
                {((summary?.bestEfficiencyScore || 0) * 100).toFixed(0)}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)', color: 'white' }}>
            <CardContent>
              <Typography variant="body2" sx={{ opacity: 0.8 }}>Efficiency Gap</Typography>
              <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
                {(((summary?.bestEfficiencyScore || 0) - (jobs?.[jobs.length - 1]?.efficiencyScore || 0)) * 100).toFixed(1)}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <BarChart />
                Resource Utilization Comparison
              </Box>
            </Typography>
            <ResponsiveContainer width="100%" height={350}>
              <RechartsBarChart data={barChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 100]} />
                <RechartsTooltip formatter={(value) => [`${value.toFixed(1)}%`, '']} />
                <Legend />
                <Bar dataKey="cpu" fill="#1976d2" name="CPU %" />
                <Bar dataKey="memory" fill="#388e3c" name="Memory %" />
                <Bar dataKey="network" fill="#f57c00" name="Network %" />
              </RechartsBarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
              Group Summary
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="body2">Avg CPU</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                    {(summary?.avgCpuUtilization * 100 || 0).toFixed(1)}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={summary?.avgCpuUtilization * 100 || 0}
                  sx={{ height: 8, borderRadius: 4 }}
                />
              </Box>
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="body2">Avg Memory</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                    {(summary?.avgMemoryUtilization * 100 || 0).toFixed(1)}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={summary?.avgMemoryUtilization * 100 || 0}
                  sx={{ height: 8, borderRadius: 4 }}
                />
              </Box>
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="body2">CPU Std Dev</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                    {(summary?.cpuStdDev * 100 || 0).toFixed(1)}%
                  </Typography>
                </Box>
              </Box>
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="body2">Best Performer</Typography>
                  <Chip
                    label={jobs?.find(j => j.jobId === summary?.bestJobId)?.jobName || 'N/A'}
                    size="small"
                    color="success"
                  />
                </Box>
              </Box>
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="body2">Needs Improvement</Typography>
                  <Chip
                    label={jobs?.find(j => j.jobId === summary?.worstJobId)?.jobName || 'N/A'}
                    size="small"
                    color="error"
                  />
                </Box>
              </Box>
            </Box>
          </Paper>
        </Grid>
      </Grid>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
          Ranking Table
        </Typography>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                <TableCell sx={{ fontWeight: 'bold' }}>Rank</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Job Name</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Efficiency</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>CPU %</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Memory %</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Network %</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Skew Factor</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Throughput/Core</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Cost/Record</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Config</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {jobs?.map((job, index) => (
                <TableRow
                  key={job.jobId}
                  sx={{
                    '&:hover': { bgcolor: '#fafafa' },
                    bgcolor: job.rank === 1 ? '#fffde7' : 'white'
                  }}
                >
                  <TableCell>{getRankIcon(job.rank)}</TableCell>
                  <TableCell sx={{ fontWeight: job.rank === 1 ? 'bold' : 'normal' }}>
                    {job.jobName}
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Box sx={{
                        width: 8, height: 8, borderRadius: '50%',
                        bgcolor: getEfficiencyColor(job.efficiencyScore)
                      }} />
                      <Typography sx={{
                        fontWeight: 'bold',
                        color: getEfficiencyColor(job.efficiencyScore)
                      }}>
                        {(job.efficiencyScore * 100).toFixed(1)}%
                      </Typography>
                      {job.rank < jobs.length && (
                        <ArrowDownward sx={{ fontSize: 16, color: '#f44336' }} />
                      )}
                    </Box>
                  </TableCell>
                  <TableCell>{(job.avgCpuUtilization * 100).toFixed(1)}%</TableCell>
                  <TableCell>{(job.avgMemoryUtilization * 100).toFixed(1)}%</TableCell>
                  <TableCell>{(job.avgNetworkUtilization * 100).toFixed(1)}%</TableCell>
                  <TableCell>
                    <Chip
                      label={job.skewFactor.toFixed(2)}
                      size="small"
                      color={job.skewFactor > 0.5 ? 'error' : job.skewFactor > 0.3 ? 'warning' : 'success'}
                    />
                  </TableCell>
                  <TableCell>{(job.throughputPerCore / 1000).toFixed(1)}K/s</TableCell>
                  <TableCell>{job.costPerRecord.toFixed(4)}μ</TableCell>
                  <TableCell>
                    <Tooltip title={`TM: ${job.currentConfig?.numTaskManagers}, Mem: ${job.currentConfig?.taskManagerMemoryMb}MB, Cores: ${job.currentConfig?.taskManagerCpuCores}`}>
                      <Chip
                        label={`P=${job.currentConfig?.parallelism}`}
                        size="small"
                        variant="outlined"
                      />
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {optimizationSuggestions && optimizationSuggestions.length > 0 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Settings sx={{ color: '#1976d2' }} />
              Optimization Suggestions
            </Box>
          </Typography>
          {optimizationSuggestions.map((suggestion, i) => (
            <Box key={i} sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, mb: 1 }}>
              <Info color="primary" sx={{ mt: 0.3 }} />
              <Typography variant="body2">{suggestion}</Typography>
            </Box>
          ))}
        </Paper>
      )}

      <Dialog open={customDialogOpen} onClose={() => setCustomDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            Custom Job Comparison
            <IconButton onClick={() => setCustomDialogOpen(false)}>
              <Close />
            </IconButton>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" sx={{ mb: 2 }}>
              Select at least 2 jobs to compare:
            </Typography>
            {allJobs.map(job => (
              <Box key={job.id} sx={{
                display: 'flex', alignItems: 'center', p: 1,
                borderRadius: 1,
                bgcolor: selectedJobs.includes(job.id) ? '#e3f2fd' : 'transparent',
                '&:hover': { bgcolor: '#f5f5f5' },
                cursor: 'pointer'
              }}
              onClick={() => {
                if (selectedJobs.includes(job.id)) {
                  setSelectedJobs(selectedJobs.filter(id => id !== job.id));
                } else {
                  setSelectedJobs([...selectedJobs, job.id]);
                }
              }}
              >
                <Box sx={{ width: 24, height: 24, border: '2px solid',
                  borderColor: selectedJobs.includes(job.id) ? '#1976d2' : '#bdbdbd',
                  borderRadius: 0.5, display: 'flex', alignItems: 'center',
                  justifyContent: 'center', mr: 2 }}
                >
                  {selectedJobs.includes(job.id) && (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#1976d2" strokeWidth="3">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  )}
                </Box>
                <Typography>{job.name}</Typography>
              </Box>
            ))}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCustomDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleCustomCompare}
            disabled={selectedJobs.length < 2}
          >
            Compare ({selectedJobs.length})
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default JobComparison;

import React, { useState, useEffect } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  CircularProgress,
  Button,
  Alert,
} from '@mui/material';
import {
  Memory,
  Speed,
  Warning,
  TrendingUp,
  Visibility,
  Refresh,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { jobApi } from '../services/api';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

const Dashboard = () => {
  const [analysisData, setAnalysisData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadMockData();
  }, []);

  const loadMockData = async () => {
    try {
      setLoading(true);
      const response = await jobApi.getMockAnalysis();
      setAnalysisData(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to load dashboard data');
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

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  const vertexData = analysisData.vertexAnalyses.map((v) => ({
    name: v.vertexName.length > 20 ? v.vertexName.substring(0, 20) + '...' : v.vertexName,
    recordsPerSecond: Math.round(v.recordsPerSecond),
    duration: Math.round(v.durationPercentage),
    parallelism: v.parallelism,
  }));

  const skewData = [
    { name: 'Normal Subtasks', value: 6, color: '#4caf50' },
    { name: 'Skewed Subtasks', value: 2, color: '#f44336' },
  ];

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#1a237e' }}>
          Dashboard
        </Typography>
        <Button
          startIcon={<Refresh />}
          variant="outlined"
          onClick={loadMockData}
        >
          Refresh
        </Button>
      </Box>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography variant="body2" sx={{ opacity: 0.8 }}>Total Vertices</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 'bold', mt: 1 }}>
                    {analysisData.totalVertices}
                  </Typography>
                </Box>
                <Speed sx={{ fontSize: 48, opacity: 0.5 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%', background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', color: 'white' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography variant="body2" sx={{ opacity: 0.8 }}>Max Parallelism</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 'bold', mt: 1 }}>
                    {analysisData.maxParallelism}
                  </Typography>
                </Box>
                <Memory sx={{ fontSize: 48, opacity: 0.5 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%', background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)', color: 'white' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography variant="body2" sx={{ opacity: 0.8 }}>Bottlenecks</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 'bold', mt: 1 }}>
                    {analysisData.bottlenecks.length}
                  </Typography>
                </Box>
                <Warning sx={{ fontSize: 48, opacity: 0.5 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%', background: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)', color: 'white' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography variant="body2" sx={{ opacity: 0.8 }}>CPU Utilization</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 'bold', mt: 1 }}>
                    {Math.round(analysisData.resourceUtilization.avgCpuUtilization)}%
                  </Typography>
                </Box>
                <TrendingUp sx={{ fontSize: 48, opacity: 0.5 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 'bold' }}>
              Vertex Performance
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={vertexData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="recordsPerSecond" fill="#1976d2" name="Records/sec" />
                <Bar dataKey="duration" fill="#dc004e" name="Duration %" />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 'bold' }}>
              Data Skew Distribution
            </Typography>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={skewData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                >
                  {skewData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
              <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                Vertex Analysis
              </Typography>
              <Button
                variant="contained"
                color="primary"
                onClick={() => navigate('/jobs/demo/analysis')}
                startIcon={<Visibility />}
              >
                View Full Analysis
              </Button>
            </Box>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                    <TableCell><strong>Vertex Name</strong></TableCell>
                    <TableCell align="center"><strong>Parallelism</strong></TableCell>
                    <TableCell align="center"><strong>Duration %</strong></TableCell>
                    <TableCell align="center"><strong>Records/sec</strong></TableCell>
                    <TableCell align="center"><strong>Data Skew</strong></TableCell>
                    <TableCell align="center"><strong>Bottleneck</strong></TableCell>
                    <TableCell align="center"><strong>Action</strong></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {analysisData.vertexAnalyses.map((vertex, index) => (
                    <TableRow key={vertex.vertexId} hover>
                      <TableCell>{vertex.vertexName}</TableCell>
                      <TableCell align="center">{vertex.parallelism}</TableCell>
                      <TableCell align="center">{vertex.durationPercentage.toFixed(1)}%</TableCell>
                      <TableCell align="center">{vertex.recordsPerSecond.toLocaleString()}</TableCell>
                      <TableCell align="center">
                        <Chip
                          label={vertex.dataSkew.severity}
                          color={vertex.dataSkew.hasSkew ? 'error' : 'success'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={vertex.isBottleneck ? 'YES' : 'NO'}
                          color={vertex.isBottleneck ? 'warning' : 'default'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Button
                          size="small"
                          color="primary"
                          onClick={() => navigate('/jobs/demo/recommendation')}
                        >
                          Recommend
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;

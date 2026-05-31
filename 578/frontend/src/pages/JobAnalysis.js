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
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
} from '@mui/material';
import {
  ExpandMore,
  Warning,
  TrendingUp,
  Memory,
  Speed,
  BarChart as BarChartIcon,
  Refresh,
  ArrowBack,
  Timeline,
  SettingsBackupRestore,
  Key,
  Layers,
  CloudQueue,
  CheckCircle,
  Error,
  Storage,
} from '@mui/icons-material';
import { useNavigate, useParams } from 'react-router-dom';
import { jobApi } from '../services/api';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  Legend,
} from 'recharts';

const JobAnalysis = () => {
  const { jobId } = useParams();
  const [analysisData, setAnalysisData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadAnalysisData();
  }, [jobId]);

  const loadAnalysisData = async () => {
    try {
      setLoading(true);
      const response = await jobApi.getMockAnalysis();
      setAnalysisData(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to load job analysis data');
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

  if (error || !analysisData) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{error || 'No data available'}</Alert>
      </Box>
    );
  }

  const subtaskData = analysisData.vertexAnalyses[0]?.subtaskMetrics.map((s) => ({
    subtask: s.subtaskIndex,
    readRecords: s.readRecords / 1000,
    writeRecords: s.writeRecords / 1000,
    busyRatio: s.busyRatio * 100,
  })) || [];

  const throughputData = analysisData.vertexAnalyses.map((v) => ({
    name: v.vertexName.substring(0, 15),
    readThroughput: Math.round(v.bytesPerSecond / 1024 / 1024),
    recordThroughput: Math.round(v.recordsPerSecond),
  }));

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3, alignItems: 'center' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Button startIcon={<ArrowBack />} onClick={() => navigate('/')}>
            Back
          </Button>
          <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#1a237e' }}>
            Job Analysis
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            startIcon={<Refresh />}
            variant="outlined"
            onClick={loadAnalysisData}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            color="primary"
            onClick={() => navigate(`/jobs/${jobId}/recommendation`)}
          >
            Get Recommendation
          </Button>
        </Box>
      </Box>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
                Job Information
              </Typography>
              <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
                <Box>
                  <Typography variant="body2" color="textSecondary">Job ID</Typography>
                  <Typography variant="body1" sx={{ fontFamily: 'monospace' }}>
                    {analysisData.jobId}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="body2" color="textSecondary">Job Name</Typography>
                  <Typography variant="body1">{analysisData.jobName}</Typography>
                </Box>
                <Box>
                  <Typography variant="body2" color="textSecondary">Duration</Typography>
                  <Typography variant="body1">
                    {(analysisData.totalDuration / 1000 / 60).toFixed(2)} min
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="body2" color="textSecondary">Max Parallelism</Typography>
                  <Typography variant="body1">{analysisData.maxParallelism}</Typography>
                </Box>
              </Box>
            </Grid>
            <Grid item xs={12} md={6}>
              <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
                Resource Utilization
              </Typography>
              <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 2 }}>
                <Box sx={{ textAlign: 'center', p: 2, bgcolor: '#e3f2fd', borderRadius: 2 }}>
                  <Typography variant="h4" sx={{ color: '#1976d2', fontWeight: 'bold' }}>
                    {Math.round(analysisData.resourceUtilization.avgCpuUtilization)}%
                  </Typography>
                  <Typography variant="body2">CPU</Typography>
                </Box>
                <Box sx={{ textAlign: 'center', p: 2, bgcolor: '#e8f5e9', borderRadius: 2 }}>
                  <Typography variant="h4" sx={{ color: '#388e3c', fontWeight: 'bold' }}>
                    {Math.round(analysisData.resourceUtilization.avgNetworkInUtilization)}%
                  </Typography>
                  <Typography variant="body2">Network In</Typography>
                </Box>
                <Box sx={{ textAlign: 'center', p: 2, bgcolor: '#fff3e0', borderRadius: 2 }}>
                  <Typography variant="h4" sx={{ color: '#f57c00', fontWeight: 'bold' }}>
                    {Math.round(analysisData.resourceUtilization.avgNetworkOutUtilization)}%
                  </Typography>
                  <Typography variant="body2">Network Out</Typography>
                </Box>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Warning color="warning" />
                Bottlenecks Detected
              </Box>
            </Typography>
            <List>
              {analysisData.bottlenecks.map((b, i) => (
                <ListItem key={i}>
                  <ListItemIcon>
                    <Chip label={i + 1} size="small" color="warning" />
                  </ListItemIcon>
                  <ListItemText primary={b} />
                </ListItem>
              ))}
            </List>
          </Paper>
        </Grid>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <TrendingUp color="primary" />
                Recommendations
              </Box>
            </Typography>
            <List>
              {analysisData.recommendations.map((r, i) => (
                <ListItem key={i}>
                  <ListItemIcon>
                    <Chip label={i + 1} size="small" color="primary" />
                  </ListItemIcon>
                  <ListItemText primary={r} />
                </ListItem>
              ))}
            </List>
          </Paper>
        </Grid>
      </Grid>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
              Throughput by Vertex
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={throughputData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                <YAxis yAxisId="left" />
                <YAxis yAxisId="right" orientation="right" />
                <Tooltip />
                <Legend />
                <Bar yAxisId="left" dataKey="readThroughput" fill="#1976d2" name="MB/s" />
                <Bar yAxisId="right" dataKey="recordThroughput" fill="#388e3c" name="Records/s" />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
              Subtask Distribution
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={subtaskData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="subtask" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="readRecords" stroke="#1976d2" name="Read (K)" strokeWidth={2} />
                <Line type="monotone" dataKey="writeRecords" stroke="#388e3c" name="Write (K)" strokeWidth={2} />
                <Line type="monotone" dataKey="busyRatio" stroke="#f57c00" name="Busy %" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
      </Grid>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <SettingsBackupRestore color="primary" />
                Duration Calibration
              </Box>
            </Typography>
            {analysisData.vertexAnalyses.map((vertex) => (
              <Box key={vertex.vertexId} sx={{ mb: 2, p: 2, bgcolor: '#fafafa', borderRadius: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 500 }}>
                    {vertex.vertexName}
                  </Typography>
                  {vertex.durationCalibrated ? (
                    <Chip label="Calibrated" size="small" color="success" icon={<CheckCircle fontSize="small" />} />
                  ) : (
                    <Chip label="Raw" size="small" color="default" />
                  )}
                </Box>
                <Grid container spacing={2}>
                  <Grid item xs={4}>
                    <Typography variant="body2" color="textSecondary">Raw Duration</Typography>
                    <Typography variant="body1" sx={{ fontWeight: 500 }}>
                      {(vertex.duration / 1000).toFixed(1)}s
                    </Typography>
                  </Grid>
                  <Grid item xs={4}>
                    <Typography variant="body2" color="textSecondary">Calibrated</Typography>
                    <Typography variant="body1" sx={{ fontWeight: 500, color: '#1976d2' }}>
                      {(vertex.calibratedDuration / 1000).toFixed(1)}s
                    </Typography>
                  </Grid>
                  <Grid item xs={4}>
                    <Typography variant="body2" color="textSecondary">Calibration Error</Typography>
                    <Typography variant="body1" sx={{ fontWeight: 500 }}>
                      {vertex.calibrationError?.toFixed(2)}%
                    </Typography>
                  </Grid>
                </Grid>
                {vertex.durationCalibration && (
                  <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid #e0e0e0' }}>
                    <Typography variant="caption" color="textSecondary">
                      Method: {vertex.durationCalibration.calibrationMethod} | 
                      Confidence: {(vertex.durationCalibration.confidenceLevel * 100).toFixed(0)}% | 
                      Samples: {vertex.durationCalibration.historicalSampleCount}
                    </Typography>
                  </Box>
                )}
              </Box>
            ))}
          </Paper>
        </Grid>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Key color="error" />
                Advanced Skew Detection
              </Box>
            </Typography>
            {analysisData.vertexAnalyses.filter(v => v.dataSkew?.hasSkew).map((vertex) => (
              <Box key={vertex.vertexId} sx={{ mb: 2, p: 2, bgcolor: '#ffebee', borderRadius: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 500 }}>
                    {vertex.vertexName}
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <Chip 
                      label={`Gini: ${vertex.dataSkew.keyDistribution?.giniCoefficient?.toFixed(2) || 'N/A'}`} 
                      size="small" 
                      color="warning" 
                    />
                    <Chip 
                      label={vertex.dataSkew.samplingVerified ? 'Sampling Verified' : 'Not Verified'} 
                      size="small" 
                      color={vertex.dataSkew.samplingVerified ? 'success' : 'default'} 
                    />
                  </Box>
                </Box>

                {vertex.dataSkew.keyDistribution && (
                  <Grid container spacing={2} sx={{ mb: 2 }}>
                    <Grid item xs={4}>
                      <Box sx={{ textAlign: 'center', p: 1, bgcolor: 'white', borderRadius: 1 }}>
                        <Typography variant="body2" color="textSecondary">Top 1 Key</Typography>
                        <Typography variant="h6" sx={{ color: '#d32f2f', fontWeight: 'bold' }}>
                          {vertex.dataSkew.keyDistribution.top1KeyPercentage?.toFixed(1)}%
                        </Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={4}>
                      <Box sx={{ textAlign: 'center', p: 1, bgcolor: 'white', borderRadius: 1 }}>
                        <Typography variant="body2" color="textSecondary">Top 5 Keys</Typography>
                        <Typography variant="h6" sx={{ color: '#f57c00', fontWeight: 'bold' }}>
                          {vertex.dataSkew.keyDistribution.top5KeysPercentage?.toFixed(1)}%
                        </Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={4}>
                      <Box sx={{ textAlign: 'center', p: 1, bgcolor: 'white', borderRadius: 1 }}>
                        <Typography variant="body2" color="textSecondary">Entropy</Typography>
                        <Typography variant="h6" sx={{ color: '#1976d2', fontWeight: 'bold' }}>
                          {vertex.dataSkew.keyDistribution.entropy?.toFixed(2)}
                        </Typography>
                      </Box>
                    </Grid>
                  </Grid>
                )}

                {vertex.dataSkew.hotKeys && vertex.dataSkew.hotKeys.length > 0 && (
                  <Box>
                    <Typography variant="subtitle2" sx={{ fontWeight: 500, mb: 1 }}>
                      Hot Keys ({vertex.dataSkew.hotKeys.length})
                    </Typography>
                    {vertex.dataSkew.hotKeys.slice(0, 5).map((hk, i) => (
                      <Box key={i} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', py: 0.5 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Chip 
                            label={hk.keyType} 
                            size="small" 
                            color={hk.keyType === 'HOT' ? 'error' : 'warning'}
                          />
                          <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                            {hk.keyHash}
                          </Typography>
                        </Box>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                          <Typography variant="body2">
                            {hk.percentage.toFixed(1)}%
                          </Typography>
                          {hk.verifiedBySampling ? (
                            <CheckCircle fontSize="small" color="success" />
                          ) : (
                            <Error fontSize="small" color="disabled" />
                          )}
                        </Box>
                      </Box>
                    ))}
                  </Box>
                )}

                <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid #ef9a9a' }}>
                  <Typography variant="caption" color="textSecondary">
                    Unique Keys: {vertex.dataSkew.totalUniqueKeys?.toLocaleString()} | 
                    Sampled: {vertex.dataSkew.sampledKeys?.toLocaleString()} | 
                    Confidence: {(vertex.dataSkew.detectionConfidence * 100).toFixed(0)}%
                  </Typography>
                </Box>
              </Box>
            ))}

            {analysisData.vertexAnalyses.filter(v => v.dataSkew?.hasSkew).length === 0 && (
              <Box sx={{ textAlign: 'center', py: 4, color: 'text.secondary' }}>
                <CheckCircle sx={{ fontSize: 48, color: 'success.main', mb: 2 }} />
                <Typography>No data skew detected</Typography>
                <Typography variant="body2">All vertices have uniform key distribution</Typography>
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
          Vertex Details
        </Typography>
        {analysisData.vertexAnalyses.map((vertex) => (
          <Accordion key={vertex.vertexId}>
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
                <Typography sx={{ width: '30%', flexShrink: 0, fontWeight: 500 }}>
                  {vertex.vertexName}
                </Typography>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Chip
                    label={`Parallelism: ${vertex.parallelism}`}
                    size="small"
                    variant="outlined"
                  />
                  <Chip
                    label={`${vertex.durationPercentage.toFixed(1)}% time`}
                    size="small"
                    color={vertex.isBottleneck ? 'warning' : 'default'}
                  />
                  {vertex.dataSkew?.hasSkew && (
                    <Chip label="Data Skew" size="small" color="error" />
                  )}
                </Box>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <Grid container spacing={3}>
                <Grid item xs={12} md={4}>
                  <Box sx={{ p: 2, bgcolor: '#f5f5f5', borderRadius: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                      <Speed fontSize="small" />
                      <Typography variant="subtitle2">Performance</Typography>
                    </Box>
                    <Typography variant="body2">Records/s: {vertex.recordsPerSecond.toLocaleString()}</Typography>
                    <Typography variant="body2">Bytes/s: {(vertex.bytesPerSecond / 1024 / 1024).toFixed(2)} MB</Typography>
                    <Typography variant="body2">Avg Record: {vertex.avgRecordSize.toFixed(1)} bytes</Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} md={4}>
                  <Box sx={{ p: 2, bgcolor: '#f5f5f5', borderRadius: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                      <Memory fontSize="small" />
                      <Typography variant="subtitle2">Data Flow</Typography>
                    </Box>
                    <Typography variant="body2">Read: {(vertex.readBytes / 1024 / 1024 / 1024).toFixed(2)} GB</Typography>
                    <Typography variant="body2">Write: {(vertex.writeBytes / 1024 / 1024 / 1024).toFixed(2)} GB</Typography>
                    <Typography variant="body2">Records: {vertex.readRecords.toLocaleString()}</Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} md={4}>
                  <Box sx={{ p: 2, bgcolor: '#f5f5f5', borderRadius: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                      <BarChartIcon fontSize="small" />
                      <Typography variant="subtitle2">Data Skew</Typography>
                    </Box>
                    <Typography variant="body2">Has Skew: {vertex.dataSkew?.hasSkew ? 'Yes' : 'No'}</Typography>
                    <Typography variant="body2">Factor: {vertex.dataSkew?.skewFactor.toFixed(2)}</Typography>
                    <Typography variant="body2">Severity: {vertex.dataSkew?.severity}</Typography>
                  </Box>
                </Grid>
              </Grid>
            </AccordionDetails>
          </Accordion>
        ))}
      </Paper>
    </Box>
  );
};

export default JobAnalysis;

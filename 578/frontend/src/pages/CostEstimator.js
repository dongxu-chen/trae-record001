import React, { useState, useEffect } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Paper,
  TextField,
  Slider,
  Button,
  CircularProgress,
  Alert,
  Divider,
  InputAdornment,
} from '@mui/material';
import {
  AttachMoney,
  Calculate,
  Save,
  Refresh,
  CloudQueue,
  Layers,
  Router,
  SwapHoriz,
  Storage,
  AccountTree,
} from '@mui/icons-material';
import { costApi } from '../services/api';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  AreaChart,
  Area,
} from 'recharts';

const CostEstimator = () => {
  const [config, setConfig] = useState({
    jobManagerMemoryMb: 1024,
    taskManagerMemoryMb: 4096,
    taskManagerCpuCores: 1.0,
    numTaskManagers: 4,
    parallelism: 4,
  });
  const [costData, setCostData] = useState(null);
  const [scalingData, setScalingData] = useState(null);
  const [networkCostData, setNetworkCostData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    calculateCost();
    loadNetworkCostReport();
  }, []);

  const calculateCost = async () => {
    try {
      setLoading(true);
      const response = await costApi.calculateCost({
        ...config,
        jobId: 'estimator',
        jobName: 'Cost Estimator',
      });
      setCostData(response.data);
      generateScalingData();
      setError(null);
    } catch (err) {
      setError('Failed to calculate cost');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const generateScalingData = () => {
    const data = [];
    for (let i = 25; i <= 200; i += 25) {
      const factor = i / 100;
      const scaledTaskManagers = Math.max(1, Math.ceil(config.numTaskManagers * factor));
      const scaledMemory = config.taskManagerMemoryMb * scaledTaskManagers / 1024;
      const scaledCpu = config.taskManagerCpuCores * scaledTaskManagers;

      const costPerHour = (scaledCpu * 0.05) + (scaledMemory * 0.02);

      data.push({
        scale: `${i}%`,
        taskManagers: scaledTaskManagers,
        costPerHour: costPerHour,
        costPerDay: costPerHour * 24,
        costPerMonth: costPerHour * 24 * 30,
      });
    }
    setScalingData(data);
  };

  const loadNetworkCostReport = async () => {
    try {
      const response = await costApi.getNetworkCostReport();
      setNetworkCostData(response.data);
    } catch (err) {
      console.error('Failed to load network cost report', err);
    }
  };

  const handleConfigChange = (field, value) => {
    setConfig((prev) => ({ ...prev, [field]: value }));
  };

  const handleSliderChange = (field) => (event, value) => {
    handleConfigChange(field, value);
  };

  if (loading && !costData) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3, alignItems: 'center' }}>
        <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#1a237e' }}>
          Cost Estimator
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            startIcon={<Refresh />}
            variant="outlined"
            onClick={calculateCost}
          >
            Recalculate
          </Button>
          <Button
            variant="contained"
            color="primary"
            startIcon={<Save />}
          >
            Save Configuration
          </Button>
        </Box>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Calculate />
                Configuration
              </Box>
            </Typography>

            <Box sx={{ mb: 3 }}>
              <Typography gutterBottom>
                JobManager Memory: {config.jobManagerMemoryMb} MB
              </Typography>
              <Slider
                value={config.jobManagerMemoryMb}
                onChange={handleSliderChange('jobManagerMemoryMb')}
                min={512}
                max={8192}
                step={256}
                valueLabelDisplay="auto"
              />
            </Box>

            <Box sx={{ mb: 3 }}>
              <Typography gutterBottom>
                TaskManager Memory: {config.taskManagerMemoryMb} MB
              </Typography>
              <Slider
                value={config.taskManagerMemoryMb}
                onChange={handleSliderChange('taskManagerMemoryMb')}
                min={512}
                max={16384}
                step={512}
                valueLabelDisplay="auto"
              />
            </Box>

            <Box sx={{ mb: 3 }}>
              <Typography gutterBottom>
                TaskManager CPU Cores: {config.taskManagerCpuCores}
              </Typography>
              <Slider
                value={config.taskManagerCpuCores}
                onChange={handleSliderChange('taskManagerCpuCores')}
                min={0.5}
                max={8}
                step={0.5}
                valueLabelDisplay="auto"
              />
            </Box>

            <Box sx={{ mb: 3 }}>
              <Typography gutterBottom>
                Number of TaskManagers: {config.numTaskManagers}
              </Typography>
              <Slider
                value={config.numTaskManagers}
                onChange={handleSliderChange('numTaskManagers')}
                min={1}
                max={100}
                step={1}
                valueLabelDisplay="auto"
              />
            </Box>

            <Box>
              <Typography gutterBottom>
                Parallelism: {config.parallelism}
              </Typography>
              <Slider
                value={config.parallelism}
                onChange={handleSliderChange('parallelism')}
                min={1}
                max={256}
                step={1}
                valueLabelDisplay="auto"
              />
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={8}>
          {costData && (
            <>
              <Grid container spacing={3} sx={{ mb: 3 }}>
                <Grid item xs={12} sm={6} md={3}>
                  <Card sx={{ height: '100%', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white' }}>
                    <CardContent>
                      <Typography variant="body2" sx={{ opacity: 0.8 }}>Cost per Hour</Typography>
                      <Typography variant="h4" sx={{ fontWeight: 'bold', mt: 1 }}>
                        ${costData.costPerHour?.toFixed(4) || '0.00'}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Card sx={{ height: '100%', background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', color: 'white' }}>
                    <CardContent>
                      <Typography variant="body2" sx={{ opacity: 0.8 }}>Cost per Day</Typography>
                      <Typography variant="h4" sx={{ fontWeight: 'bold', mt: 1 }}>
                        ${costData.costPerDay?.toFixed(2) || '0.00'}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Card sx={{ height: '100%', background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)', color: 'white' }}>
                    <CardContent>
                      <Typography variant="body2" sx={{ opacity: 0.8 }}>Cost per Month</Typography>
                      <Typography variant="h4" sx={{ fontWeight: 'bold', mt: 1 }}>
                        ${costData.costPerMonth?.toFixed(2) || '0.00'}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Card sx={{ height: '100%', background: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)', color: 'white' }}>
                    <CardContent>
                      <Typography variant="body2" sx={{ opacity: 0.8 }}>Cost per Year</Typography>
                      <Typography variant="h4" sx={{ fontWeight: 'bold', mt: 1 }}>
                        ${costData.costPerYear?.toFixed(2) || '0.00'}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>

              <Paper sx={{ p: 3, mb: 3 }}>
                <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <AttachMoney />
                    Cost Breakdown
                  </Box>
                </Typography>
                <Grid container spacing={3}>
                  <Grid item xs={12} md={6}>
                    <Box sx={{ p: 2, bgcolor: '#f5f5f5', borderRadius: 2, mb: 2 }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                        Resource Summary
                      </Typography>
                      <Typography variant="body2">
                        Total CPU Cores: {costData.totalCpuCores?.toFixed(2) || 0}
                      </Typography>
                      <Typography variant="body2">
                        Total Memory: {costData.totalMemoryGb?.toFixed(2) || 0} GB
                      </Typography>
                    </Box>
                    {costData.costBreakdown && (
                      <Box sx={{ p: 2, bgcolor: '#f5f5f5', borderRadius: 2 }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                          Hourly Cost Breakdown
                        </Typography>
                        <Typography variant="body2">
                          TaskManager CPU: ${costData.costBreakdown.taskManagerCpuCostPerHour?.toFixed(4) || 0}
                        </Typography>
                        <Typography variant="body2">
                          TaskManager Memory: ${costData.costBreakdown.taskManagerMemoryCostPerHour?.toFixed(4) || 0}
                        </Typography>
                        <Typography variant="body2">
                          JobManager Memory: ${costData.costBreakdown.jobManagerMemoryCostPerHour?.toFixed(4) || 0}
                        </Typography>
                      </Box>
                    )}
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Box sx={{ p: 2, bgcolor: '#e3f2fd', borderRadius: 2 }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                        Cost Assumptions
                      </Typography>
                      <Typography variant="body2">
                        CPU Cost: $0.05 per core per hour
                      </Typography>
                      <Typography variant="body2">
                        Memory Cost: $0.02 per GB per hour
                      </Typography>
                      <Typography variant="body2">
                        Hours per day: 24
                      </Typography>
                      <Typography variant="body2">
                        Days per month: 30
                      </Typography>
                      <Typography variant="body2" color="textSecondary" sx={{ mt: 1, fontStyle: 'italic' }}>
                        * Costs are estimates based on cloud pricing models
                      </Typography>
                    </Box>
                  </Grid>
                </Grid>
              </Paper>

              {scalingData && (
                <Paper sx={{ p: 3, mb: 3 }}>
                  <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
                    Scaling Cost Projection
                  </Typography>
                  <ResponsiveContainer width="100%" height={350}>
                    <AreaChart data={scalingData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="scale" />
                      <YAxis />
                      <Tooltip
                        formatter={(value) => [`$${value.toFixed(2)}`, 'Cost']}
                      />
                      <Legend />
                      <Area
                        type="monotone"
                        dataKey="costPerHour"
                        stroke="#8884d8"
                        fill="#8884d8"
                        fillOpacity={0.3}
                        name="Cost/Hour"
                      />
                      <Area
                        type="monotone"
                        dataKey="costPerDay"
                        stroke="#82ca9d"
                        fill="#82ca9d"
                        fillOpacity={0.3}
                        name="Cost/Day"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                  <Typography variant="body2" color="textSecondary" sx={{ mt: 2, textAlign: 'center' }}>
                    Projected costs based on scaling TaskManager count relative to current configuration
                  </Typography>
                </Paper>
              )}

              {networkCostData && (
                <Paper sx={{ p: 3 }}>
                  <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 3 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <CloudQueue color="primary" />
                      Network Cost Analysis
                    </Box>
                  </Typography>

                  <Grid container spacing={3} sx={{ mb: 3 }}>
                    <Grid item xs={12} sm={6} md={3}>
                      <Card sx={{ height: '100%', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white' }}>
                        <CardContent>
                          <Typography variant="body2" sx={{ opacity: 0.8 }}>Network Cost/Hour</Typography>
                          <Typography variant="h5" sx={{ fontWeight: 'bold', mt: 1 }}>
                            ${networkCostData.totalNetworkCostPerHour?.toFixed(4) || '0.00'}
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                      <Card sx={{ height: '100%', background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', color: 'white' }}>
                        <CardContent>
                          <Typography variant="body2" sx={{ opacity: 0.8 }}>Cross-Rack Cost</Typography>
                          <Typography variant="h5" sx={{ fontWeight: 'bold', mt: 1 }}>
                            ${networkCostData.crossRackCostPerHour?.toFixed(4) || '0.00'}
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                      <Card sx={{ height: '100%', background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)', color: 'white' }}>
                        <CardContent>
                          <Typography variant="body2" sx={{ opacity: 0.8 }}>Cross-AZ Cost</Typography>
                          <Typography variant="h5" sx={{ fontWeight: 'bold', mt: 1 }}>
                            ${networkCostData.crossAzCostPerHour?.toFixed(4) || '0.00'}
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                      <Card sx={{ height: '100%', background: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)', color: 'white' }}>
                        <CardContent>
                          <Typography variant="body2" sx={{ opacity: 0.8 }}>Total Traffic</Typography>
                          <Typography variant="h5" sx={{ fontWeight: 'bold', mt: 1 }}>
                            {networkCostData.totalTrafficGbPerHour?.toFixed(2) || '0.00'} GB
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                  </Grid>

                  <Grid container spacing={3}>
                    <Grid item xs={12} md={6}>
                      <Box sx={{ p: 2, bgcolor: '#e8f5e9', borderRadius: 2, mb: 2 }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 2 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <AccountTree fontSize="small" />
                            Rack Topology
                          </Box>
                        </Typography>
                        <Typography variant="body2">
                          Total Availability Zones: {networkCostData.rackTopology?.numAvailabilityZones || 3}
                        </Typography>
                        <Typography variant="body2">
                          Total Racks: {networkCostData.rackTopology?.numRacks || 9}
                        </Typography>
                        <Typography variant="body2">
                          TaskManagers per Rack: {networkCostData.rackTopology?.taskManagersPerRack || 4}
                        </Typography>
                        <Typography variant="body2">
                          Cross-Rack Traffic Ratio: {(networkCostData.crossRackTrafficRatio * 100 || 0).toFixed(1)}%
                        </Typography>
                        <Typography variant="body2">
                          Cross-AZ Traffic Ratio: {(networkCostData.crossAzTrafficRatio * 100 || 0).toFixed(1)}%
                        </Typography>
                      </Box>

                      <Box sx={{ p: 2, bgcolor: '#fff3e0', borderRadius: 2 }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 2 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <SwapHoriz fontSize="small" />
                            Traffic Distribution
                          </Box>
                        </Typography>
                        <Typography variant="body2">
                          Shuffle Input Traffic: {networkCostData.shuffleInputTrafficGbPerHour?.toFixed(2) || '0.00'} GB/h
                        </Typography>
                        <Typography variant="body2">
                          Shuffle Output Traffic: {networkCostData.shuffleOutputTrafficGbPerHour?.toFixed(2) || '0.00'} GB/h
                        </Typography>
                        <Typography variant="body2">
                          Intra-DC Traffic: {networkCostData.intraDcTrafficGbPerHour?.toFixed(2) || '0.00'} GB/h
                        </Typography>
                        <Typography variant="body2">
                          Egress Traffic: {networkCostData.egressTrafficGbPerHour?.toFixed(2) || '0.00'} GB/h
                        </Typography>
                        <Typography variant="body2">
                          Shuffle Amplification Factor: {networkCostData.shuffleAmplificationFactor || '2.5'}x
                        </Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <Box sx={{ p: 2, bgcolor: '#e3f2fd', borderRadius: 2, mb: 2 }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 2 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Router fontSize="small" />
                            Cost Rates
                          </Box>
                        </Typography>
                        <Typography variant="body2">
                          Same Rack: $0.00/GB (free)
                        </Typography>
                        <Typography variant="body2">
                          Cross Rack: ${networkCostData.costModel?.costPerGbCrossRackTraffic || 0.02}/GB
                        </Typography>
                        <Typography variant="body2">
                          Cross AZ: ${networkCostData.costModel?.costPerGbCrossAzTraffic || 0.05}/GB
                        </Typography>
                        <Typography variant="body2">
                          Internet Egress: ${networkCostData.costModel?.costPerGbOutTraffic || 0.08}/GB
                        </Typography>
                      </Box>

                      {networkCostData.optimizationTips && networkCostData.optimizationTips.length > 0 && (
                        <Box sx={{ p: 2, bgcolor: '#fce4ec', borderRadius: 2 }}>
                          <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 2, color: '#c2185b' }}>
                            Optimization Tips
                          </Typography>
                          {networkCostData.optimizationTips.map((tip, i) => (
                            <Typography key={i} variant="body2" sx={{ mb: 1 }}>
                              • {tip}
                            </Typography>
                          ))}
                        </Box>
                      )}
                    </Grid>
                  </Grid>
                </Paper>
              )}
            </>
          )}
        </Grid>
      </Grid>
    </Box>
  );
};

export default CostEstimator;

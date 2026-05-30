import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  Checkbox,
  FormControlLabel,
  FormGroup,
  Paper,
  LinearProgress,
} from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  LineChart,
  Line,
} from 'recharts';
import { serviceApi, metricsApi } from '../services/api';

function ServiceComparison() {
  const [services, setServices] = useState([]);
  const [selectedServices, setSelectedServices] = useState([]);
  const [comparisonData, setComparisonData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchServices();
  }, []);

  useEffect(() => {
    if (selectedServices.length > 0) {
      fetchComparisonData();
    }
  }, [selectedServices]);

  const fetchServices = async () => {
    try {
      const response = await serviceApi.getActive();
      setServices(response.data);
      setSelectedServices(response.data.slice(0, 3).map((s) => s.serviceName));
    } catch (error) {
      console.error('Failed to fetch services:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchComparisonData = async () => {
    try {
      const response = await metricsApi.compare(selectedServices);
      setComparisonData(response.data);
    } catch (error) {
      console.error('Failed to fetch comparison data:', error);
    }
  };

  const handleServiceToggle = (serviceName) => {
    setSelectedServices((prev) =>
      prev.includes(serviceName)
        ? prev.filter((s) => s !== serviceName)
        : [...prev, serviceName]
    );
  };

  const radarData = comparisonData.map((item) => ({
    service: item.serviceName,
    可用性: item.availability,
    性能: Math.max(0, 100 - item.avgLatencyMs / 10),
    可靠性: 100 - item.errorRate * 10,
    SLA达成: item.slaAchievementRate,
  }));

  const barData = comparisonData.map((item) => ({
    name: item.serviceName,
    可用性: item.availability,
    SLA达成率: item.slaAchievementRate,
    错误率: 100 - item.errorRate * 10,
  }));

  if (loading) {
    return <LinearProgress />;
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        多服务对比
      </Typography>

      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          选择要对比的服务
        </Typography>
        <FormGroup row>
          {services.map((service) => (
            <FormControlLabel
              key={service.serviceName}
              control={
                <Checkbox
                  checked={selectedServices.includes(service.serviceName)}
                  onChange={() => handleServiceToggle(service.serviceName)}
                />
              }
              label={service.serviceName}
            />
          ))}
        </FormGroup>
      </Paper>

      {comparisonData.length > 0 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  SLA 达成率对比
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={barData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis domain={[0, 100]} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="SLA达成率" fill="#8884d8" />
                    <Bar dataKey="可用性" fill="#82ca9d" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  综合指标雷达图
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <RadarChart data={radarData}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="service" />
                    <PolarRadiusAxis angle={30} domain={[0, 100]} />
                    {selectedServices.map((service, index) => (
                      <Radar
                        key={service}
                        name={service}
                        dataKey="可用性"
                        stroke={['#8884d8', '#82ca9d', '#ffc658', '#ff8042'][index % 4]}
                        fill={['#8884d8', '#82ca9d', '#ffc658', '#ff8042'][index % 4]}
                        fillOpacity={0.3}
                      />
                    ))}
                    <Legend />
                    <Tooltip />
                  </RadarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  详细对比表
                </Typography>
                <Box sx={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr>
                        <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid #ddd' }}>
                          服务名称
                        </th>
                        <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid #ddd' }}>
                          可用性
                        </th>
                        <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid #ddd' }}>
                          平均延迟
                        </th>
                        <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid #ddd' }}>
                          错误率
                        </th>
                        <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid #ddd' }}>
                          SLA达成率
                        </th>
                        <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid #ddd' }}>
                          状态
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {comparisonData.map((item) => (
                        <tr key={item.serviceName}>
                          <td style={{ padding: '12px', borderBottom: '1px solid #ddd' }}>
                            {item.serviceName}
                          </td>
                          <td style={{ padding: '12px', borderBottom: '1px solid #ddd' }}>
                            {item.availability?.toFixed(2)}%
                          </td>
                          <td style={{ padding: '12px', borderBottom: '1px solid #ddd' }}>
                            {item.avgLatencyMs?.toFixed(0)}ms
                          </td>
                          <td style={{ padding: '12px', borderBottom: '1px solid #ddd' }}>
                            {item.errorRate?.toFixed(2)}%
                          </td>
                          <td style={{ padding: '12px', borderBottom: '1px solid #ddd' }}>
                            <LinearProgress
                              variant="determinate"
                              value={item.slaAchievementRate || 0}
                              color={item.slaViolated ? 'error' : 'primary'}
                              sx={{ mb: 1 }}
                            />
                            {item.slaAchievementRate?.toFixed(2)}%
                          </td>
                          <td style={{ padding: '12px', borderBottom: '1px solid #ddd' }}>
                            <span
                              style={{
                                color: item.slaViolated ? '#d32f2f' : '#388e3c',
                                fontWeight: 'bold',
                              }}
                            >
                              {item.slaViolated ? '违规' : '正常'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}
    </Box>
  );
}

export default ServiceComparison;

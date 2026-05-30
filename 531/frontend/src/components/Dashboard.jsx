import React, { useState, useEffect } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  LinearProgress,
  Button,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts';
import dayjs from 'dayjs';
import { serviceApi, metricsApi, alertApi } from '../services/api';

function Dashboard() {
  const navigate = useNavigate();
  const [services, setServices] = useState([]);
  const [metricsMap, setMetricsMap] = useState({});
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [servicesRes, alertsRes] = await Promise.all([
        serviceApi.getActive(),
        alertApi.getActive(),
      ]);

      setServices(servicesRes.data);
      setAlerts(alertsRes.data);

      const metricsPromises = servicesRes.data.map(async (service) => {
        try {
          const metricsRes = await metricsApi.getLatest(service.serviceName);
          return { serviceName: service.serviceName, metrics: metricsRes.data };
        } catch {
          return { serviceName: service.serviceName, metrics: null };
        }
      });

      const metricsResults = await Promise.all(metricsPromises);
      const metricsMapData = {};
      metricsResults.forEach(({ serviceName, metrics }) => {
        metricsMapData[serviceName] = metrics;
      });
      setMetricsMap(metricsMapData);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (metrics) => {
    if (!metrics) return 'default';
    if (metrics.slaViolated) return 'error';
    if (metrics.slaAchievementRate < 98) return 'warning';
    return 'success';
  };

  const getStatusText = (metrics) => {
    if (!metrics) return '无数据';
    if (metrics.slaViolated) return 'SLA违规';
    if (metrics.slaAchievementRate < 98) return '警告';
    return '正常';
  };

  if (loading) {
    return <LinearProgress />;
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">SLA 仪表板</Typography>
        <Button
          variant="contained"
          onClick={() => metricsApi.simulateAll().then(fetchData)}
        >
          生成模拟数据
        </Button>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                监控服务总数
              </Typography>
              <Typography variant="h3">{services.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                活跃告警
              </Typography>
              <Typography variant="h3" color="error">
                {alerts.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                SLA违规服务
              </Typography>
              <Typography variant="h3" color="error">
                {Object.values(metricsMap).filter((m) => m?.slaViolated).length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                平均SLA达成率
              </Typography>
              <Typography variant="h3" color="primary">
                {Object.values(metricsMap)
                  .filter((m) => m)
                  .reduce((acc, m) => acc + m.slaAchievementRate, 0) /
                    (Object.values(metricsMap).filter((m) => m).length || 1) || 0}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Typography variant="h5" gutterBottom>
            服务概览
          </Typography>
        </Grid>

        {services.map((service) => {
          const metrics = metricsMap[service.serviceName];
          return (
            <Grid item xs={12} md={6} lg={4} key={service.serviceName}>
              <Card
                style={{ cursor: 'pointer' }}
                onClick={() => navigate(`/service/${service.serviceName}`)}
              >
                <CardContent>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                    <Box>
                      <Typography variant="h6">{service.serviceName}</Typography>
                      {service.slaTier && (
                        <Typography variant="caption" color="textSecondary">
                          {service.slaTier.tierName}
                        </Typography>
                      )}
                    </Box>
                    <Chip
                      label={getStatusText(metrics)}
                      color={getStatusColor(metrics)}
                      size="small"
                    />
                  </Box>

                  <Box mb={2}>
                    <Typography variant="body2" color="textSecondary">
                      SLA 达成率
                    </Typography>
                    <Box display="flex" alignItems="center">
                      <Box flexGrow={1} mr={1}>
                        <LinearProgress
                          variant="determinate"
                          value={metrics?.slaAchievementRate || 0}
                          color={
                            metrics?.slaViolated
                              ? 'error'
                              : metrics?.slaAchievementRate < 98
                              ? 'warning'
                              : 'primary'
                          }
                        />
                      </Box>
                      <Typography variant="body2">
                        {metrics?.slaAchievementRate?.toFixed(2) || 0}%
                      </Typography>
                    </Box>
                  </Box>

                  <Grid container spacing={2}>
                    <Grid item xs={4}>
                      <Typography variant="body2" color="textSecondary">
                        可用性
                      </Typography>
                      <Typography variant="body1">
                        {metrics?.availability?.toFixed(2) || 0}%
                      </Typography>
                    </Grid>
                    <Grid item xs={4}>
                      <Typography variant="body2" color="textSecondary">
                        延迟
                      </Typography>
                      <Typography variant="body1">
                        {metrics?.avgLatencyMs?.toFixed(0) || 0}ms
                      </Typography>
                    </Grid>
                    <Grid item xs={4}>
                      <Typography variant="body2" color="textSecondary">
                        错误率
                      </Typography>
                      <Typography variant="body1">
                        {metrics?.errorRate?.toFixed(2) || 0}%
                      </Typography>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>
          );
        })}
      </Grid>
    </Box>
  );
}

export default Dashboard;
